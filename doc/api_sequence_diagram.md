# API Sequence Diagram

## Project Settings
### register sfm camera parameter
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

### register detect landmark camera parameter

### register detect dot parameter

### register sfm json

### send images for sfm to server

### run sfm

## Trajectory Editor
### register trajectory

## Drone Settings
### set pid

### set trajectory

## Drone Control
### start
### stop
### pause