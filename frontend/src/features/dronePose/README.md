
## ディレクトリ構成
```
src/
├── features/
│   ├── dronePose/                    # ドローンの姿勢・座標を管理・表示する機能
│   │   ├── components/
│   │   │   └── DronePoseViewer.tsx   # ドローンの姿勢・座標を3Dで表示するコンポーネント例
│   │   ├── hooks/
│   │   │   └── useDronePose.ts       # ドローンの姿勢・座標を取得・管理するカスタムフック例
│   │   ├── services/
│   │   │   └── dronePoseService.ts   # APIやWebSocketから姿勢・座標データを取得するサービス例
│   │   └── types.ts                  # ドローン姿勢・座標の型定義
```