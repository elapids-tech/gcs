# E2E テスト
## 操作指示

## DroneApp モード遷移
### 事前実施 疎通確認
#### GUI ボタン押下しRPiが正しくMAVLink Messageを受信できている
- [ ] コンフィギュレーションページに移行したら、RPiはCONFIGモード定期シグナルを受信している。
- [ ] RPiは正しくCONFIGモードに遷移できている。
- [ ] RPiは動画ストリーミングできている。
- [ ] GCSサーバはUDPで受信できている。
- [ ] CONFIGモード中は操作コマンドがMAVLink Router経由でFCUに流れていない。