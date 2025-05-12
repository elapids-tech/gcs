from radio import Radio

radio = Radio()

# 制御パケットを送信（data=1）
radio.send_immediate("CONTROL_PACKET", 1)

# データパケットを送信（x, y, z）
radio.send_immediate("DATA_PACKET", [1.23, 4.56, 7.89])

# 受信データの取り出し
data_type, data = radio.popRxBuffer()
print(data_type, data)

# シャットダウン（任意）
radio.shutdown()
