"""BLE connection and GATT management.

This module provides classes for managing BLE connections to peripheral devices,
handling GATT notifications, and sending GATT write commands.
"""

import logging
import threading
from typing import Callable
from bluepy import btle

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage BLE peripheral connections.

    Attributes:
        peri (btle.Peripheral | None): The connected BLE peripheral or None if not connected.
    """

    def __init__(self) -> None:
        """Initialize a ConnectionManager with no active connection.

        Sets peri to None and initializes MAC address storage.
        """
        self.peri: btle.Peripheral | None = None
        self._mac_address: str = ""

    def connect(self, mac_address: str) -> None:
        """Establish a BLE connection to the specified peripheral device.

        Args:
            mac_address (str): MAC address of the BLE device to connect to.

        Raises:
            ConnectionError: If the connection attempt fails.
        """
        self._mac_address = mac_address
        try:
            self.peri = btle.Peripheral()
            self.peri.connect(self._mac_address, btle.ADDR_TYPE_RANDOM)
        except btle.BTLEException as e:
            raise ConnectionError(
                f"Failed to connect. mac_address: {self._mac_address}"
            ) from e

    def disconnect(self) -> None:
        """Terminate the BLE connection.

        Raises:
            RuntimeError: If no peripheral is currently connected.
            ConnectionError: If the disconnection attempt fails.
        """
        if self.peri is None:
            raise RuntimeError("No peripherals connected.")
        try:
            self.peri.disconnect()
        except btle.BTLEException as e:
            raise ConnectionError(
                f"Failed to disconnect. mac_address: {self._mac_address}"
            ) from e


class GattManager(btle.DefaultDelegate):
    """Manage GATT write and notification operations for a BLE peripheral.

    This delegate handles sending segmented write commands and processing
    incoming notifications, invoking a user-provided callback when complete
    messages are received.
    """

    def __init__(
        self,
        peri: btle.Peripheral,
        handle_write: int,
        handle_notify: int,
        callback: Callable[[bytes, bool], None],
    ) -> None:
        """Initialize the GattManager.

        Note:
            Bit flags in header byte:
                0b001: Beginning of a fragmented packet.
                0b010: End of a fragmented plaintext packet.
                0b100: End of a fragmented encrypted packet.

        Args:
            peri (btle.Peripheral): The BLE peripheral to manage.
            handle_write (int): The handle for the write characteristic.
            handle_notify (int): The handle for the notify characteristic.
            callback (Callable[[bytes, bool], None]): Callback invoked with
                complete payloads and encryption status.
        """
        super().__init__()
        self._peri: btle.Peripheral = peri
        self._callback: Callable[[bytes, bool], None] = callback
        self._handle_write: int = handle_write
        self._handle_notify: int = handle_notify
        self._buffer: bytes = b""
        self._peri.withDelegate(self)

    def enable_notification(self) -> None:
        """Enable GATT notifications on the peripheral device.

        Registers this instance as the notification delegate and writes to the
        CCCD (Client Characteristic Configuration Descriptor) to enable notifications.

        Raises:
            ConnectionError: If enabling notifications fails.
        """
        try:
            self._peri.writeCharacteristic(self._handle_notify + 1, b"\x01\x00", True)
        except btle.BTLEException as e:
            raise ConnectionError("Failed to enable notification.") from e

    # bluepy name, so pylint: disable-next=invalid-name
    def handleNotification(self, _cHandle, data: bytes) -> None:
        """Handle an incoming GATT notification.

        Accumulates fragments of notification data. When a complete message is
        detected (based on header flags), invokes the callback with the full payload.

        Args:
            _cHandle (int): Handle of the characteristic that generated the notification.
            data (bytes): Notification payload, including a header byte.
        """
        is_beginning = bool(data[0] & 0b1)
        is_end = bool(data[0] & 0b110)
        is_encrypted = bool(data[0] & 0b100)
        if is_beginning:
            self._buffer = b""
        self._buffer += data[1:]
        if not is_end:
            return
        self._callback(self._buffer, is_encrypted)

    def write(self, data: bytes, is_encrypted: bool) -> None:
        """Send data to the BLE write characteristic in segmented packets.

        Data is split into 20-byte segments. Each segment includes a header byte
        indicating its position in the sequence and whether the data is encrypted.

        Args:
            data (bytes): Payload to write.
            is_encrypted (bool): Whether the data is encrypted.

        Raises:
            ConnectionError: If a write operation fails.
        """
        remains = len(data)
        offset = 0
        while remains:
            is_beginning = not bool(offset)
            if remains <= 19:
                buffer = data[offset:]
                remains = 0
                is_end = True
            else:
                buffer = data[offset : offset + 20]
                offset += 19
                remains -= 19
                is_end = False
            header = is_beginning + (is_end << (1 + is_encrypted))
            try:
                self._peri.writeCharacteristic(
                    self._handle_write, bytes([header]) + buffer, True
                )
            except btle.BTLEException as e:
                raise ConnectionError("Failed to write GATT.") from e


class NotificationThreadManager:
    """Manage a background thread that waits for BLE notifications.

    Starts and stops a daemon thread invoking a recovery handler on errors.
    """

    def __init__(
        self, peri: btle.Peripheral, recovery_handler: Callable[[], None]
    ) -> None:
        """Initialize NotificationThreadManager.

        Args:
            peri (btle.Peripheral): The BLE peripheral whose notifications to wait for.
            recovery_handler (Callable[[], None]): Handler called on notification errors.
        """
        self._peri: btle.Peripheral = peri
        self._recovery_handler: Callable[[], None] = recovery_handler
        self._stop_thread: bool = False
        self._thread: threading.Thread | None = None

    def start_wait_for_notification(self) -> None:
        """Start a background daemon thread to wait for BLE notifications.

        If the thread is already running, raises a RuntimeError. If an exception
        occurs in the loop, the recovery handler is invoked.

        Raises:
            RuntimeError: If a notification thread is already running.
        """

        def notification_loop() -> None:
            while not self._stop_thread:
                try:
                    if self._peri.waitForNotifications(1.0):
                        continue
                except btle.BTLEException as e:
                    logger.error("Error in notification loop. Error: %s", e)
                    self._recovery_handler()
                    break

        if self._thread and self._thread.is_alive():
            raise RuntimeError("Waiting BLE notification thread already running.")
        self._stop_thread = False
        self._thread = threading.Thread(target=notification_loop, daemon=True)
        self._thread.start()
        logger.debug("Waiting BLE notification thread started.")

    def stop_wait_for_notification(self) -> None:
        """Stop the background notification thread.

        Raises:
            RuntimeError: If no notification thread is currently running.
        """
        if not (self._thread and self._thread.is_alive()):
            raise RuntimeError("Waiting BLE notification thread is not running.")
        self._stop_thread = True
        self._thread.join()
        logger.debug("Waiting BLE notification thread stopped.")

    def is_running(self) -> bool:
        """Check whether the notification thread is active.

        Returns:
            bool: True if the thread is running; False otherwise.
        """
        return bool(self._thread and self._thread.is_alive())
