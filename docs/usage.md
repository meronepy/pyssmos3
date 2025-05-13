# pyssmos3 Usage

**Python library to control SESAME5 over BLE.**

---

## Installation

Since this library uses `bluepy`, please install `libglib2.0-dev` beforehand.

- **Raspberry Pi OS**:
  ```bash
  sudo apt install libglib2.0-dev
  ```
- **Arch Linux ARM**:
  ```bash
  pacman -S glib2-devel pkg-config make gcc
  ```
- **Other distributions**:
  Install the package equivalent to `libglib2.0-dev` or `glib2-devel`.

Download the latest wheel file (`pyssmos3-x.x.x-py3-none-any.whl`) from the Releases tab on GitHub and install it with:

```bash
pip install pyssmos3-x.x.x-py3-none-any.whl
```

---

## Example

The following sample code locks and unlocks the SESAME5 based on keyboard input and prints device status updates in real time.

```python
import logging
from pyssmos3.client import SsmClient

logging.basicConfig(level=logging.INFO)

def on_status_changed(mech_status_webapi_format, _raw_mech_status):
    print(mech_status_webapi_format)

def on_connect(is_successful):
    if is_successful:
        print("Connection successful.")
    else:
        print("Connection failed.")

MAC_ADDRESS = "XX:XX:XX:XX:XX:XX"
SECRET_KEY  = "1234567890abcdef1234567890abcdef"
HISTORY_NAME = "yourname"

client = SsmClient(on_status_changed, on_connect)
client.connect(MAC_ADDRESS, SECRET_KEY)

while True:
    user_input = input()
    if user_input == "lock":
        client.lock(HISTORY_NAME)
    elif user_input == "unlock":
        client.unlock(HISTORY_NAME)
    elif user_input == "quit":
        client.stop()
        break
```

---

## Usage Overview

1. Create an `SsmClient` instance, passing callback functions for status changes and connection results.  
2. Connect to the device with `SsmClient.connect()`.  
3. Lock or unlock with `SsmClient.lock()` or `SsmClient.unlock()`.  
4. Disconnect with `SsmClient.stop()`.

---

## Classes and Methods

### SsmClient

- A class that handles connection, login, and operations on SESAME5.  
- If you need to manage multiple SESAME5 devices, create multiple instances.

**Constructor Arguments**:  
- `on_status_changed (callable)`  
  Callback invoked when the mechanical status changes.  
- `on_connect (callable)`  
  Callback to receive login success or reconnection results. Passes `True` on success, `False` on reconnection failure.

---

### on_status_changed

- The callback receives two arguments: `mech_status_webapi_format` and `raw_mech_status`.  
- Example:

  ```python
  # mech_status_webapi_format
  {'batteryPercentage': 100, 'batteryVoltage': 5.956, 'position': -48, 'CHSesame2Status': 'locked', 'timestamp': 1735657200}

  # raw_mech_status
  {'battery': 2978, 'target': -32768, 'position': -17, 'is_lock_range': True, 'is_unlock_range': False, 'is_critical': False, 'is_stop': True, 'is_low_battery': False, 'is_clockwise': False}
  ```

- Formats follow the official CANDY HOUSE documentation. See:  
  - [Web API (JP)](https://doc.candyhouse.co/ja/SesameAPI)  
  - [81 Mech Status (Mechanical Status) (EN)](https://github.com/CANDY-HOUSE/API_document/blob/master/SesameOS3/81_mechstatus.en.md)

> The `timestamp` is the time when the BLE notification was received, which may differ from the history shown in the official app.

---

### SsmClient.connect()

**Arguments**:  
- `mac_address (str)`  
  The MAC address of the SESAME5 device.  
- `secret_key (str)`  
  The manager-level (or higher) secret key extracted from the QR code.  
- `max_retries (int, optional)`  
  Number of reconnection attempts (default: 3).  
- `interval (int, optional)`  
  Interval between reconnection attempts in seconds (default: 5).

On connection or login failure, it will retry automatically. Set `max_retries=0` to disable auto-reconnect. On success, `on_connect` receives `True`; on failure after retries, it receives `False`.

#### Obtaining mac_address and secret_key

- Use tools like [nRF Connect for Mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) to identify the `mac_address` of SESAME5.  
- Use the [QR Code Reader for SESAME](https://sesame-qr-reader.vercel.app/) to extract the `secret_key` from a manager-level or higher QR code.

---

### SsmClient.lock() / SsmClient.unlock()

- Perform lock or unlock operations on SESAME5.  
- **Argument**:  
  - `history_name (str)`  
    The name shown in the operation history.

If the operation fails, it will attempt to reconnect automatically; no exceptions are thrown.

---

### SsmClient.stop()

- Disconnects and stops the reconnection monitoring thread.  
- Although the thread runs with `daemon=True`, explicit invocation is recommended.
