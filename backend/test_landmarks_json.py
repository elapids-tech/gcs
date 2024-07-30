import json

file_path = 'data/test_project_data.json'

landmarks_corners = []

# JSONファイルを開いて読み込む
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

for marker_id in data['landmarks']:
    for i, pos in enumerate(data['landmarks'][marker_id]['corners']):
        id = str(marker_id) + str(i)
        landmarks_corners.append({"id":id, "x":pos[0], "y":pos[1], "z":pos[2]})

for i in landmarks_corners:
    print(i)
