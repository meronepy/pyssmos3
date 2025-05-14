# pyssmos3 使用方法

**SESAME5をBLE経由で操作するPythonライブラリ。**

---

## インストール

`bluepy`を使用しているため、事前に`libglib2.0-dev`をインストールしてください。

- **Raspberry Pi OS**:
  ```bash
  sudo apt install libglib2.0-dev
  ```
- **Arch Linux ARM**:
  ```bash
  pacman -S glib2-devel pkg-config make gcc
  ```
- **その他のディストリビューション**:
  `libglib2.0-dev`または`glib2-devel`に相当するパッケージをインストールしてください。

GitHubのReleasesタブから最新のホイールファイル (`pyssmos3-x.x.x-py3-none-any.whl`) をダウンロードし、以下のコマンドでインストールします。

```bash
pip install pyssmos3-x.x.x-py3-none-any.whl
```

---

## 使用例

以下は、キーボード入力に応じてSESAME5を施錠・開錠し、デバイスの状態変化をリアルタイム表示するサンプルコードです。

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

## 使い方の概要

1. `SsmClient`インスタンスを作成し、状態変化と接続可否のコールバック関数を渡す。
2. `SsmClient.connect()`でデバイスに接続。
3. `SsmClient.lock()`または`SsmClient.unlock()`で施錠・開錠。
4. `SsmClient.stop()`で切断。

---

## クラスと関数

### SsmClient

- SESAME5への接続、ログイン、操作を行うクラス。
- 複数のSESAME5を扱う場合は、インスタンスを複数生成してください。

**引数**:
- `on_status_changed (callable)`  
  `mech_status`変更時に呼び出すコールバック関数。  
- `on_connect (callable)`  
  ログイン成功や再接続結果を受け取るコールバック関数。成功時は`True`、再接続失敗時は`False`が返されます。

---

### on_status_changedについて

- コールバック関数には、`mech_status_webapi_format`と`raw_mech_status`の2つの引数が渡されます。
- 例:

  ```python
  # mech_status_webapi_format
  {'batteryPercentage': 100, 'batteryVoltage': 5.956, 'position': -48, 'CHSesame2Status': 'locked', 'timestamp': 1735657200}

  # raw_mech_status
  {'battery': 2978, 'target': -32768, 'position': -17, 'is_lock_range': True, 'is_unlock_range': False, 'is_critical': False, 'is_stop': True, 'is_low_battery': False, 'is_clockwise': False}
  ```

- CANDY HOUSE公式ドキュメントに準拠した形式です。詳しくは  
  - [Web API (JP)](https://doc.candyhouse.co/ja/SesameAPI)  
  - [81 Mech Status (Mechanical Status) (EN)](https://github.com/CANDY-HOUSE/API_document/blob/master/SesameOS3/81_mechstatus.en.md)

> `timestamp`はBLE通知を受信した時刻を示しているため、公式アプリの履歴と異なる場合があります。

---

### SsmClient.connect()

**引数**:
- `mac_address (str)`  
  SESAME5のMACアドレス。  
- `secret_key (str)`  
  QRコードから抽出したマネージャー権限以上のシークレットキー。  
- `max_retries (int, optional)`  
  再接続試行回数（デフォルト: 3）。  
- `interval (int, optional)`  
  再接続間隔（秒単位、デフォルト: 5）。

接続やログインに失敗した場合、自動的に再接続を試みます。`max_retries=0`で自動再接続を無効化可能。接続可能になると`on_connect`に`True`、再接続失敗時に`False`が渡されます。

#### mac_addressとsecret_keyの取得

- `mac_address (str)`: SESAME5のmac address。[nRF Connect for Mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile)を使用するなどして自力で頑張って特定してください。
- `secret_key (str)`: mochipon様作成の[QR Code Reader for SESAME](https://sesame-qr-reader.vercel.app/)を使用して、マネージャー権限以上のQRコードから抽出できます。

---

### SsmClient.lock() / SsmClient.unlock()

- SESAME5への施錠・開錠を行います。
- **引数**:  
  - `history_name (str)`  
    操作履歴に表示される名前。

失敗時は自動再接続を行い、例外は発生しません。

---

### SsmClient.stop()

- 接続を切断し、再接続監視スレッドを停止します。
- スレッドは`daemon=True`で動作しますが、明示的に呼び出すことを推奨します。
