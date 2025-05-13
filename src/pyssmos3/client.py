"""SSM client for SesameOS3.

This module defines SsmClient, which manages BLE connections, authentication,
lock/unlock commands, and automatic recovery from errors.
"""

from dataclasses import dataclass
import logging
import time
from typing import Callable
from .ble import ConnectionManager, GattManager, NotificationThreadManager
from .cipher import CipherManager, generate_token
from .const import BleHandle, DeviceStatus, SsmItemCode
from .protocol import ReceivedDataHandler
from .recovery import RecoveryManager

logger = logging.getLogger(__name__)


@dataclass
class SsmDevice:
    """Represents the state and credentials of an SSM device.

    Attributes:
        device_status (DeviceStatus): Current connection/status of the SSM device.
        mac_address (str): BLE MAC address of the SSM device.
        secret_key (bytes): Shared secret key for token generation.
        random_code (bytes): Random code received from the SSM device.
        token (bytes): Derived token for encryption.
    """

    device_status: DeviceStatus = DeviceStatus.SSM_DISCONNECTED
    mac_address: str = ""
    secret_key: bytes = b""
    random_code: bytes = b""
    token: bytes = b""


class SsmClient:  # Central client class, so pylint: disable=too-many-instance-attributes
    """Central client for managing SSM BLE operations.

    This class handles connection establishment, authentication,
    lock/unlock commands, notification handling, and automatic error recovery.

    Attributes:
        ssm_device (SsmDevice): State and credentials of the SSM device.
    """

    def __init__(
        self,
        on_status_changed: Callable[[dict, dict], None],
        on_connect: Callable[[bool], None],
    ) -> None:
        """Initializes the SsmClient with callback handlers and managers.

        Args:
            on_status_changed (Callable[[dict, dict], None]): Callback invoked when
                mechanical status changes, receives (webapi_status, raw_status).
            on_connect (Callable[[bool], None]): Callback invoked upon connection or
                recovery failure, receives a boolean indicating success.
        """
        self.ssm_device: SsmDevice = SsmDevice()
        self._callback_status: Callable[[dict, dict], None] = on_status_changed
        self._callback_on_connect: Callable[[bool], None] = on_connect
        self._recovery_manager: RecoveryManager = RecoveryManager(
            self.on_recovery_failed
        )
        self._connection_manager: ConnectionManager = ConnectionManager()
        self._received_data_handler: ReceivedDataHandler = ReceivedDataHandler(
            self.on_mechstatus_changed, self._recovery_manager.perform_recovery
        )
        self._gatt_manager: GattManager | None = None
        self._ble_thread_manager: NotificationThreadManager | None = None
        self._cipher_manager: CipherManager | None = None

    def connect(
        self, mac_address: str, secret_key: str, max_retries: int = 3, interval: int = 5
    ) -> None:
        """Connects to the SSM device and starts error monitoring.

        This method initializes the RecoveryManager with retry logic and then
        runs the internal sequence to establish BLE connection, perform
        authentication, and prepare for notifications.

        Args:
            mac_address (str): BLE MAC address of the SSM device.
            secret_key (str): Hex-encoded secret key string for token generation.
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
            interval (int, optional): Interval between retries in seconds. Defaults to 5.
        """
        if self.ssm_device.device_status != DeviceStatus.SSM_DISCONNECTED:
            logger.warning("Already connected to SSM device.")
            return

        self.ssm_device.mac_address = mac_address
        self.ssm_device.secret_key = bytes.fromhex(secret_key)

        self._recovery_manager.start_monitoring(self.reconnect, max_retries, interval)

        self._run()
        while self.ssm_device.device_status <= DeviceStatus.SSM_LOGGIN:
            if self._recovery_manager.is_recovery_failed:
                break
            time.sleep(0.1)

    def stop(self) -> None:
        """Stops the SSM client and disconnects from the device.

        This method terminates BLE communication, stops the notification
        thread, clears device state, and halts error monitoring.
        """
        self._disconnect_and_cleanup()
        if self._recovery_manager.is_running():
            self._recovery_manager.stop_monitoring()

    def lock(self, history_name: str) -> None:
        """Sends a lock command to the device.

        Args:
            history_name (str): Name to record in the operation history.
        """
        if self.ssm_device.device_status <= DeviceStatus.SSM_LOGGIN:
            logger.warning("Not logged in to SSM device.")
            return
        tag = history_name.encode()
        command = bytes([SsmItemCode.SSM_ITEM_CODE_LOCK, len(tag)]) + tag
        self._send(command, True)

    def unlock(self, history_name: str) -> None:
        """Sends an unlock command to the device.

        Args:
            history_name (str): Name to record in the operation history.
        """
        if self.ssm_device.device_status <= DeviceStatus.SSM_LOGGIN:
            logger.warning("Not logged in to SSM device.")
            return
        tag = history_name.encode()
        command = bytes([SsmItemCode.SSM_ITEM_CODE_UNLOCK, len(tag)]) + tag
        self._send(command, True)

    def on_mechstatus_changed(
        self, mech_status_webapi_format: dict, raw_mech_status: dict
    ) -> None:
        """Invoked when mechanical status changes are received.

        Args:
            mech_status_webapi_format (dict): Mechanical status in WebAPI format.
            raw_mech_status (dict): Raw mechanical status data from the device.
        """
        if raw_mech_status.get("is_lock_range"):
            self.ssm_device.device_status = DeviceStatus.SSM_LOCKED
        elif raw_mech_status.get("is_unlock_range"):
            self.ssm_device.device_status = DeviceStatus.SSM_UNLOCKED
        elif not raw_mech_status.get("is_stop"):
            self.ssm_device.device_status = DeviceStatus.SSM_MOVED
        self._callback_status(mech_status_webapi_format, raw_mech_status)

    def on_recovery_failed(self):
        """Callback triggered when all recovery attempts have failed."""
        self.ssm_device.device_status = DeviceStatus.SSM_DISCONNECTED
        self._callback_on_connect(False)

    def reconnect(self) -> None:
        """Reconnects to the SSM device after a failure.

        This method is intended to be triggered by the RestartManager when
        an error occurs. It performs a full cleanup and re-initializes the
        connection and authentication processes.
        """
        self._disconnect_and_cleanup()
        self._run()

    def _run(self) -> None:
        """Performs connecting, initialize, login, and starts waiting notification thread."""
        logger.debug("Starting SsmClient. SSM device: %s", self.ssm_device.mac_address)
        logger.debug("bleConnecting.")
        self.ssm_device.device_status = DeviceStatus.SSM_CONNECTING
        try:
            self._connection_manager.connect(self.ssm_device.mac_address)
        except ConnectionError as e:
            logger.error("Failed to connect to SSM device. Error: %s", e)
            self._recovery_manager.perform_recovery()
            return
        self.ssm_device.device_status = DeviceStatus.SSM_CONNECTED
        logger.debug("BLE connected.")

        self._gatt_manager = GattManager(
            self._connection_manager.peri,
            BleHandle.BLE_HANDLE_WRITE,
            BleHandle.BLE_HANDLE_NOTIFICATION,
            self._received_data_handler.process_data,
        )
        self._ble_thread_manager = NotificationThreadManager(
            self._connection_manager.peri, self._recovery_manager.perform_recovery
        )

        logger.debug("waitingGatt.")
        try:
            self._initial_ssm()
        except ConnectionError as e:
            logger.error("Failed to initialize SSM device. Error: %s", e)
            self._recovery_manager.perform_recovery()
            return

        self.ssm_device.random_code = self._received_data_handler.random_code
        try:
            self.ssm_device.token = generate_token(
                self.ssm_device.secret_key, self.ssm_device.random_code
            )
        except ValueError as e:
            logger.error("Failed to generate token. Error: %s", e)
            self._recovery_manager.perform_recovery()
            return

        logger.debug("bleLogining.")
        self._cipher_manager = CipherManager(
            self.ssm_device.random_code, self.ssm_device.token
        )
        self._received_data_handler.enable_decryption(self._cipher_manager)

        self.ssm_device.device_status = DeviceStatus.SSM_LOGGIN
        try:
            self._login()
        except ConnectionError as e:
            logger.error("Failed to login to SSM device. Error: %s", e)
            self._recovery_manager.perform_recovery()
            return
        self._recovery_manager.reset_fail_count()
        if self.ssm_device.device_status == DeviceStatus.SSM_LOGGIN:
            self.ssm_device.device_status = DeviceStatus.SSM_UNLOCKED
        logger.debug(
            "Login successful. timestamp: %s",
            self._received_data_handler.login_timestamp,
        )
        self._callback_on_connect(True)

    def _disconnect_and_cleanup(self) -> None:
        """Stops notification thread and disconnects from the SSM device."""
        if self._ble_thread_manager and self._ble_thread_manager.is_running():
            self._ble_thread_manager.stop_wait_for_notification()
        if self.ssm_device.device_status >= DeviceStatus.SSM_CONNECTED:
            self._connection_manager.disconnect()
            logger.debug("BLE disconnected.")
        self.ssm_device.device_status = DeviceStatus.SSM_DISCONNECTED
        self.ssm_device.random_code = b""
        self.ssm_device.token = b""
        logger.debug("SsmClient stopped.")

    def _send(self, data: bytes, should_encrypt: bool) -> None:
        """Encrypts (if required) and sends data via GATT manager.

        Args:
            data (bytes): Data to send.
            should_encrypt (bool): Whether to encrypt data before sending.
        """
        assert self._cipher_manager is not None
        assert self._gatt_manager is not None

        if should_encrypt:
            try:
                data = self._cipher_manager.encrypt(data)
            except ValueError as e:
                logger.error("Failed to encrypt data. Error: %s", e)
                self._recovery_manager.perform_recovery()
                return
        try:
            self._gatt_manager.write(data, should_encrypt)
        except ConnectionError as e:
            logger.error("Failed to send data to SSM device. Error: %s", e)
            self._recovery_manager.perform_recovery()
            return

    def _initial_ssm(self) -> None:
        """Performs initial by enabling notifications and waiting for random code.

        Raises:
            ConnectionError: If random code is not received in time.
        """
        assert self._gatt_manager is not None
        assert self._ble_thread_manager is not None

        self._gatt_manager.enable_notification()
        self._ble_thread_manager.start_wait_for_notification()
        counter = 0
        while not self._received_data_handler.random_code:
            if counter >= 50:
                logger.error("Failed to receive random code from SSM device.")
                raise ConnectionError("SSM device not responding.")
            time.sleep(0.1)
            counter += 1

    def _login(self) -> None:
        """Sends login command and waits for login timestamp.

        Raises:
            ConnectionError: If login timestamp is not received in time.
        """
        command = bytes([SsmItemCode.SSM_ITEM_CODE_LOGIN]) + self.ssm_device.token[:4]
        self._send(command, False)
        counter = 0
        while not self._received_data_handler.login_timestamp:
            if counter >= 50:
                logger.error("Failed to receive login timestamp from SSM device.")
                raise ConnectionError("SSM device not responding.")
            time.sleep(0.1)
            counter += 1
