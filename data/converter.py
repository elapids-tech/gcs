import json

# 入力ファイル名
input_filename = "/idls_app/data/converted_coordinates_3d.json"

# 出力ファイル名
output_filename = "/idls_app/data/output.json"

# プログラムの処理
def process_json(input_file, output_file):
    # JSONファイルを読み込む
    with open(input_file, "r") as infile:
        data = json.load(infile)

    # 出力データ構造を初期化
    output = []
    seen = set()  # 重複を防ぐためのセット

    # データ変換
    for entry in data:
        type_id = str(entry["type"])  # typeを文字列として扱う
        centers = entry["centers"]
        ids = [int(digit) for digit in type_id]  # typeを桁ごとに分割してIDにする
        for i, center in enumerate(centers):
            if i < len(ids):  # centersに対応するIDがある場合のみ処理
                element = {"id": ids[i], "center": center}
                # IDと座標が一致するものを除外
                if (ids[i], tuple(center)) not in seen:
                    output.append(element)
                    seen.add((ids[i], tuple(center)))

    # 結果をJSONファイルに書き出す
    with open(output_file, "w") as outfile:
        json.dump(output, outfile, indent=4)

# 実行
process_json(input_filename, output_filename)
print(f"処理が完了しました。出力ファイル: {output_filename}")
