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

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

You don’t have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn’t feel obligated to use this feature. However we understand that this tool wouldn’t be useful if you couldn’t customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).
