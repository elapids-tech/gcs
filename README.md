# IndoorDroneLightShow-Configurator

## 開発環境構築
- /frontend/node_modules/ これを作成

## frontend
- ビルドし直す場合　node_modulesごと消さないといけない。

## 前提条件
- アプリ内はすべて **Z-Up 右手座標系** で処理する
- socketで通信するのは**DroneControl**, **テレメトリ情報**, **Project情報**

## 機能
- フォトグラメトリによるアルコマーカーの世界座標推定
- フライトプランの作成
- ドローンの設定
- ドローンの制御