# Main Page Specification

![main_page_ui](./main_page.drawio.svg)

## Components

### SERVER STATE Display
- サーバーの状態、接続状態などを表示します。
- WebSocket TCP を使用し状態を受け取ります。

### DRONE STATE Display
- ドローンがどのモードに入っているのかを表示します。
- WebSocket TCP を使用し GCS Server からドローンの状態を受け取ります。

### TAKEOFF Button
- ドローンに離陸の指示するためのボタンです。
- ボタンが押下されると、WebSocket TCP を使用し GCS Server へ離陸コマンド送信します。

### LANDING Button
- ドローンに着陸の指示するためのボタンです。
- ボタンが押下されると、WebSocket TCP を使用し GCS Server へ着陸コマンド送信します。

### EMERGENCY STOP Button
- モーターの回転を完全に停止させるためのボタンです。
- ボタンが押下されると、WebSocket TCP を使用し GCS Server へモーター停止コマンド送信します。