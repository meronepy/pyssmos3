"""Constants for BLE handles and SSM device codes.

This module defines IntEnum classes for BLE GATT handles (BleHandle),
device statuses (DeviceStatus), and SSM item/op command codes
(SsmItemCode, SsmOpCode).
"""

from enum import IntEnum


class BleHandle(IntEnum):
    """BLE GATT characteristic handles for write and notification operations.

    Attributes:
        BLE_HANDLE_WRITE (int): Handle for write characteristic.
        BLE_HANDLE_NOTIFICATION (int): Handle for notification characteristic.
    """

    BLE_HANDLE_WRITE = 0x000D
    BLE_HANDLE_NOTIFICATION = 0x000F


class DeviceStatus(IntEnum):
    """Enumeration of possible SSM device connection and operational statuses.

    Attributes:
        SSM_NOUSE (int): Unused state.
        SSM_DISCONNECTED (int): Device is disconnected.
        SSM_SCANNING (int): Device is scanning.
        SSM_CONNECTING (int): Device is in the process of BLE connecting.
        SSM_CONNECTED (int): Device is connected and in the process of enabling BLE notify.
        SSM_LOGGIN (int): Device is in the process of logging in.
        SSM_LOCKED (int): Device is locked.
        SSM_UNLOCKED (int): Device is unlocked.
        SSM_MOVED (int): Device mechanism is moving.
    """

    SSM_NOUSE = 0
    SSM_DISCONNECTED = 1
    SSM_SCANNING = 2
    SSM_CONNECTING = 3
    SSM_CONNECTED = 4
    SSM_LOGGIN = 5
    SSM_LOCKED = 6
    SSM_UNLOCKED = 7
    SSM_MOVED = 8


class SsmItemCode(IntEnum):
    """SSM item command codes for various operations.

    Attributes:
        SSM_ITEM_CODE_NONE (int): No operation.
        SSM_ITEM_CODE_REGISTRATION (int): Registration command.
        SSM_ITEM_CODE_LOGIN (int): Login command.
        SSM_ITEM_CODE_USER (int): User command.
        SSM_ITEM_CODE_HISTORY (int): History retrieval command.
        SSM_ITEM_CODE_VERSION_DETAIL (int): Version detail command.
        SSM_ITEM_CODE_DISCONNECT_REBOOT_NOW (int): Immediate reboot command.
        SSM_ITEM_CODE_ENABLE_DFU (int): Enable DFU command.
        SSM_ITEM_CODE_TIME (int): Time synchronization command.
        SSM_ITEM_CODE_INITIAL (int): Initial (request random code) command.
        SSM_ITEM_CODE_MAGNET (int): Magnet sensor command.
        SSM_ITEM_CODE_MECH_SETTING (int): Mechanism setting command.
        SSM_ITEM_CODE_MECH_STATUS (int): Mechanism status command.
        SSM_ITEM_CODE_LOCK (int): Lock command.
        SSM_ITEM_CODE_UNLOCK (int): Unlock command.
        SSM2_ITEM_OPS_TIMER_SETTING (int): Timer setting command.
    """

    SSM_ITEM_CODE_NONE = 0
    SSM_ITEM_CODE_REGISTRATION = 1
    SSM_ITEM_CODE_LOGIN = 2
    SSM_ITEM_CODE_USER = 3
    SSM_ITEM_CODE_HISTORY = 4
    SSM_ITEM_CODE_VERSION_DETAIL = 5
    SSM_ITEM_CODE_DISCONNECT_REBOOT_NOW = 6
    SSM_ITEM_CODE_ENABLE_DFU = 7
    SSM_ITEM_CODE_TIME = 8
    SSM_ITEM_CODE_INITIAL = 14
    SSM_ITEM_CODE_MAGNET = 17
    SSM_ITEM_CODE_MECH_SETTING = 80
    SSM_ITEM_CODE_MECH_STATUS = 81
    SSM_ITEM_CODE_LOCK = 82
    SSM_ITEM_CODE_UNLOCK = 83
    SSM2_ITEM_OPS_TIMER_SETTING = 92


class SsmOpCode(IntEnum):
    """SSM operation codes for response and publish messages.

    Attributes:
        SSM_OP_CODE_RESPONSE (int): Response operation code.
        SSM_OP_CODE_PUBLISH (int): Publish operation code.
    """

    SSM_OP_CODE_RESPONSE = 0x07
    SSM_OP_CODE_PUBLISH = 0x08
