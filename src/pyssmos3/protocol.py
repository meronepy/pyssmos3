"""Handler for incoming BLE data from SSM device.

This module defines ReceivedDataHandler, which handles decryption (if needed),
parses operation and item codes, extracts random codes and login timestamps,
and processes mechanical status updates to be passed to a callback.
"""

import logging
import time
from typing import Any, Callable
from .cipher import CipherManager
from .const import SsmItemCode, SsmOpCode

logger = logging.getLogger(__name__)


class ReceivedDataHandler:
    """
    Handler for processing incoming BLE data from a SESAME SSM device.

    Decrypts data if enabled, parses operation and item codes, extracts random codes and
    login timestamps, and processes mechanical status updates for a provided callback.

    Attributes:
        random_code (bytes): Random code received during initialization publish.
        login_timestamp (int): UNIX timestamp received in the login response.
    """

    def __init__(
        self,
        callback: Callable[[dict[str, Any], dict[str, Any]], None],
        recovery_handler: Callable[[], None],
    ) -> None:
        """
        Initialize a ReceivedDataHandler.

        Args:
            callback (Callable[[dict[str, Any], dict[str, Any]], None]):
                Function to call with formatted and raw mechanical status data.
            recovery_handler (Callable[[], None]):
                Function to call when recovery logic is required (e.g., on decryption failure).
        """
        self.random_code: bytes = b""
        self.login_timestamp: int = 0
        self._callback: Callable[[dict[str, Any], dict[str, Any]], None] = callback
        self._recovery_handler: Callable[[], None] = recovery_handler
        self._cipher: CipherManager | None = None

    def enable_decryption(self, cipher: CipherManager) -> None:
        """Enable decryption of future BLE data.

        Args:
            cipher (CipherManager): Cipher instance to use for decryption.
        """
        self._cipher = cipher

    def process_data(self, data: bytes, is_encrypted: bool) -> None:
        """Process BLE data, decrypt if necessary, and dispatch based on op code.

        Args:
            data (bytes): Raw bytes received from the BLE device.
            is_encrypted (bool): Whether the incoming data is encrypted.
        """
        if is_encrypted:
            if self._cipher is None:
                logger.error("Encrypted data received while decryption is disabled.")
                self._recovery_handler()
                return
            try:
                data = self._cipher.decrypt(data)
            except ValueError as e:
                logger.error("Failed to decrypt data. Error: %s", e)
                self._recovery_handler()
                return
        op_code = data[0]
        item_code = data[1]
        match op_code:
            case SsmOpCode.SSM_OP_CODE_RESPONSE:
                payload = data[3:]
                self._handle_response(item_code, payload)
            case SsmOpCode.SSM_OP_CODE_PUBLISH:
                payload = data[2:]
                self._handle_publish(item_code, payload)
            case _:
                logger.debug("Unknown op code. op_code: %s", op_code)

    def _handle_response(self, item_code: int, payload: bytes) -> None:
        """Handle response-type BLE messages.

        Args:
            item_code (int): Indicates which type of response this is.
            payload (bytes): The response payload excluding the header.
        """
        match item_code:
            case SsmItemCode.SSM_ITEM_CODE_LOGIN:
                self._handle_login_response(payload)
            case _:
                logger.debug("Unknown response. item_code: %s", item_code)

    def _handle_publish(self, item_code: int, payload: bytes) -> None:
        """Handle publish-type BLE messages.

        Args:
            item_code (int): Indicates which type of publish this is.
            payload (bytes): The publish payload excluding the header.
        """
        match item_code:
            case SsmItemCode.SSM_ITEM_CODE_INITIAL:
                self._handle_initial_publish(payload)
            case SsmItemCode.SSM_ITEM_CODE_MECH_STATUS:
                self._handle_mech_status_publish(payload)
            case _:
                logger.debug("Unknown publish. item_code: %s", item_code)

    def _handle_login_response(self, payload: bytes) -> None:
        """Store login timestamp from the login response payload.

        Args:
            payload (bytes): 4-byte little-endian timestamp.
        """
        timestamp = int.from_bytes(payload, "little")
        self.login_timestamp = timestamp

    def _handle_initial_publish(self, payload: bytes) -> None:
        """Store the random code from the initialize message.

        Args:
            payload (bytes): Random code as a byte sequence.
        """
        self.random_code = payload

    def _handle_mech_status_publish(self, payload: bytes) -> None:
        """Parse mechanical status and call the callback with parsed results.

        Args:
            payload (bytes): Contains voltage, position, and status flags.
        """
        battery_voltage = int.from_bytes(payload[0:2], "little")
        target = int.from_bytes(payload[2:4], "little", signed=True)
        position = int.from_bytes(payload[4:6], "little", signed=True)
        status_flags = payload[6]
        status_flags_tuple = tuple(bool(status_flags & (1 << i)) for i in range(7))
        raw_mech_status = {
            "battery": battery_voltage,
            "target": target,
            "position": position,
            "is_clutch_failed": status_flags_tuple[0],
            "is_lock_range": status_flags_tuple[1],
            "is_unlock_range": status_flags_tuple[2],
            "is_critical": status_flags_tuple[3],
            "is_stop": status_flags_tuple[4],
            "is_low_battery": status_flags_tuple[5],
            "is_clockwise": status_flags_tuple[6],
        }
        mech_status_webapi_format = self._convert_to_webapi_format(raw_mech_status)
        self._callback(mech_status_webapi_format, raw_mech_status)

    def _convert_to_webapi_format(
        self, raw_mech_status: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert raw mechanical status to a format compatible with a Web API.

        Args:
            raw_mech_status (dict[str, Any]): Raw mechanical data parsed from BLE payload.

        Returns:
            dict[str, Any]: Formatted status containing battery level, position, lock state,
                and timestamp.
        """
        battery_voltage = raw_mech_status["battery"] * 2 / 1000
        battery_percentage = self._calculate_battery_percentage(battery_voltage)
        position = int(raw_mech_status["position"] * 1024 / 360)
        if raw_mech_status["is_lock_range"]:
            lock_status = "locked"
        elif raw_mech_status["is_unlock_range"]:
            lock_status = "unlocked"
        else:
            lock_status = "unknown"
        timestamp = int(time.time())
        mech_status_webapi_format = {
            "batteryPercentage": battery_percentage,
            "batteryVoltage": battery_voltage,
            "position": position,
            "CHSesame2Status": lock_status,
            "timestamp": timestamp,
        }
        return mech_status_webapi_format

    def _calculate_battery_percentage(self, voltage: float) -> int:
        """Convert voltage reading to estimated battery percentage.

        Args:
            voltage (float): Battery voltage in volts.

        Returns:
            int: Battery percentage between 0 and 100.
        """
        voltage_levels = (
            5.85,
            5.82,
            5.79,
            5.76,
            5.73,
            5.70,
            5.65,
            5.60,
            5.55,
            5.50,
            5.40,
            5.20,
            5.10,
            5.0,
            4.8,
            4.6,
        )
        battery_percentages = (
            100.0,
            95.0,
            90.0,
            85.0,
            80.0,
            70.0,
            60.0,
            50.0,
            40.0,
            32.0,
            21.0,
            13.0,
            10.0,
            7.0,
            3.0,
            0.0,
        )
        if voltage >= voltage_levels[0]:
            return int(battery_percentages[0])
        if voltage <= voltage_levels[-1]:
            return int(battery_percentages[-1])
        for i in range(len(voltage_levels) - 1):
            upper_voltage = voltage_levels[i]
            lower_voltage = voltage_levels[i + 1]
            if lower_voltage < voltage <= upper_voltage:
                voltage_ratio = (voltage - lower_voltage) / (
                    upper_voltage - lower_voltage
                )
                upper_percent = battery_percentages[i]
                lower_percent = battery_percentages[i + 1]
                return int(
                    (upper_percent - lower_percent) * voltage_ratio + lower_percent
                )
        return 0
