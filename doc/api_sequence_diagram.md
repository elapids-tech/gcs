# API Sequence Diagram

## Project Settings
### register sfm camera parameter
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend

    User->>Frontend:パラメーターを入力
    Frontend->>Backend:パラメータを登録
    Backend->>Backend:チェック
    Backend->>Backend:登録
    Backend->>Frontend:結果
    Frontend->>Frontend:結果表示
```

### register sfm camera parameter from json
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend

    User->>Frontend:jsonをアップロード
    Frontend->>Backend:パラメータを登録
    Backend->>Backend:チェック
    Backend->>Backend:登録
    Backend->>Frontend:結果
    Frontend->>Frontend:結果表示
```

### export sfm camera parameter json

### register detect landmark camera parameter

### register detect dot parameter

### register sfm json

### send images for sfm to server

### run sfm

## Trajectory Editor
### register trajectory
### set trajectory

## Drone Settings
### set pid
### set detect dot parameter
### set trajectory

## Drone Control
### send heartbeat
### read heartbeat
### start
### stop
### pause
