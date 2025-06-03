# IDLS Configurator

## ディレクトリ構成
```
src/
├── features/                                   # 機能（ドメイン）ごとにまとめる
│   ├── auth/                                   # 認証機能（ログイン、サインアップなど）
│   │   ├── components/                         # 認証に関する再利用可能なUI部品（LoginFormなど）
│   │   │   └── LoginForm.tsx
│   │   │   └── LoginForm.module.css            # CSS Modulesによるスタイル
│   │   ├── pages/                              # ページ単位のコンポーネント（React Routerの対象）
│   │   │   └── LoginPage.tsx
│   │   ├── hooks/                              # 認証用カスタムフック（useLoginなど）
│   │   │   └── useLogin.ts
│   │   ├── services/                           # 認証APIとの通信処理
│   │   │   └── authService.ts
│   │   └── types.ts                            # 認証に関する型定義（LoginPayloadなど）
│
│   ├── user/                                   # ユーザー機能（プロフィール表示・編集など）
│   │   ├── components/
│   │   │   └── UserProfile.tsx
│   │   │   └── UserProfile.module.css
│   │   ├── pages/
│   │   │   └── ProfilePage.tsx
│   │   ├── hooks/
│   │   │   └── useUserProfile.ts
│   │   ├── services/
│   │   │   └── userService.ts
│   │   └── types.ts
│
│   └── dashboard/                              # ダッシュボード機能（統計、カード表示など）
│       ├── components/
│       │   └── DashboardCard.tsx
│       │   └── DashboardCard.module.css
│       ├── pages/
│       │   └── DashboardPage.tsx
│       ├── hooks/
│       │   └── useDashboard.ts
│       ├── services/
│       │   └── dashboardService.ts
│       └── types.ts
│
├── shared/                                     # 全機能で共有される部品・ロジック・型
│   ├── components/                             # 汎用UI（Button, Modalなど）
│   │   └── Button.tsx
│   │   └── Button.module.css
│   ├── hooks/                                  # 共通カスタムフック（useDebounceなど）
│   │   └── useDebounce.ts
│   ├── utils/                                  # 汎用ユーティリティ関数（formatDateなど）
│   │   └── formatDate.ts
│   └── types/                                  # アプリ全体で使う共通型定義
│       └── common.ts
│
├── store/                                      # グローバル状態管理（Redux Toolkitなど）
│   ├── index.ts                                # Store全体の初期化とProvider連携
│   └── slices/                                 # Slice単位で状態を分離
│       ├── authSlice.ts
│       └── userSlice.ts
│
├── assets/                                     # 静的アセット類（画像、グローバルCSSなど）
│   ├── images/                                 # ロゴ、アイコン、背景画像など
│   └── styles/
│       └── variables.css                       # 全体のカラー変数やリセットCSSなど
│
├── App.tsx                                     # アプリ全体のルーティング構成（React Router）
├── main.tsx                                    # エントリーポイント（ReactDOM.createRoot）
└── vite-env.d.ts                               # Viteの環境変数用型定義ファイル
```