
# pyssmos3

BLE経由でSESAME5を操作するためのPythonライブラリ。

---

## はじめに

- BLE経由でSESAME5を操作するための非公式Pythonライブラリです。
- SESAME5 ProとSESAME5 USでも動くと思いますが、持っていないので分かりません。
- SESAME3とSESAME4はOSとかいろいろ違うので動きません。
- このライブラリは私の(ほぼ)初めてのPythonプログラムなのでコードが汚かったり、奇妙な仕様かもしれません。生暖かい目で見守ってやってください。

---

## 開発環境

- Python 3.11.2
- bluepy 1.3.0
- pycryptodome 3.22.0
- Raspberry Pi Zero 2W (Raspberry Pi OS Lite 64bit Bookworm)
- SESAME5 3.0-5-f826b5

---

## 対象デバイス

- SESAME5
- SESAME5 Pro (未テスト)
- SESAME5 US (未テスト)

---

## 機能

- 施錠と開錠
- リアルタイムでの状態変化通知  
  (lock state, battery voltage, battery percentage, target, position, is_critical, is_stop, is_low_battery, is_clockwise)
- エラー時の自動再接続

---

## メモ

設定が済んでいない SESAME5 を登録・操作することはできません。  
公式アプリで設定後ご利用ください。

---

## 使い方

`docs` ディレクトリ内の `usage.md` を参照してください。

---

## 注意事項

非公式ライブラリのため自己責任で使用してください。  
テストコードを作っておらず、ユニットテストが行えておりません。   
数日の連続稼働テストは行いましたが、安定動作は保証できません。

---

## 参考文献

- t_hoshiyama . “Sesame5をラズパイからPythonでアクセスする” . パソコンゲーム開発倶楽部 . 2024 . https://pgdc.pickle.ne.jp/access-sesame5/ , (2025-1-16)
- CANDY-HOUSE . "API_document" . github . 2024 . https://github.com/CANDY-HOUSE/API_document , (2025-1-16)
- CANDY-HOUSE . "SesameSDK_Android_with_DemoApp" . github . 2024 . https://github.com/CANDY-HOUSE/SesameSDK_Android_with_DemoApp , (2025-3-9)
- mochipon . "pysesameos2" . github . 2022 . https://github.com/mochipon/pysesameos2 , (2025-3-16)

---

## 感謝!

- 参考文献の著者様
- bluepy
- pycryptodome

---

## 余談

当初は `bleak` を使用しようとしましたが、SESAME5 のサービスが取得できず断念しました。  
`bluetoothctl menu gatt` でも同様に取得できませんでしたが、`gatttool` ではサービスの UUID と handle が取得可能でした。  
Dbus経由だとサービスが伝わっていない気がします。情報提供をお待ちしています。
> 解決しました。今まではBlueZ 5.66を使用していましたが、BlueZ 5.82を使用したところ、`bluetoothctl menu gatt`でも UUID が取得できました。`bleak`に移行できるかもしれません。
ライセンスは依存関係の `bluepy` が GPL-2.0 のため、本ライブラリも GPL-2.0 で公開しています。  
将来的に `bleak` で動作可能になった場合、そちらに移行する可能性があります。
