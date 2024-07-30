import json

file_path = 'data/test_project_data.json'

# JSONファイルを開いて読み込む
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

for marker_id in data['landmarks']:
    for i, pos in enumerate(data['landmarks'][marker_id]['corners']):
        str(marker_id) + 
        id = int(marker_id + str(i))
        print(id)
