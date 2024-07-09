import qrcode                          #ライブラリのインポート
img = qrcode.make('ctc-g-14ba2d, 6aad31b3b2261') #QRコードの作成
img.save('techis_hp_url.png')          #画像の保存
