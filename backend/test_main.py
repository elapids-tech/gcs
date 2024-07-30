# test_main.py
from fastapi.testclient import TestClient
from main import app, ProjectManager
import json

client = TestClient(app)

project = ProjectManager()

# def test_upload_file():
#     # テスト前に初期化
#     project.landmarks_corners = []

#     # テストデータを作成
#     test_data = {
#         "landmarks": [
#             {
#                 "corners": [1, 2, 3]
#             },
#             {
#                 "corners": [4, 5, 6]
#             }
#         ]
#     }
    
#     # JSON形式に変換
#     json_data = json.dumps(test_data)
    
#     # POSTリクエストを送信
#     response = client.post("/upload/", data=json_data)
    
#     # ステータスコードを確認
#     assert response.status_code == 200
    
#     # レスポンスの内容を確認
#     assert response.json() == {"state_message": 0}
    
#     # データが適切に追加されたか確認
#     expected_corners = [
#         {"id": 10, "x": 0, "y": 0, "z": 0},
#         {"id": 11, "x": 0, "y": 0, "z": 0},
#         {"id": 12, "x": 0, "y": 0, "z": 0},
#         {"id": 20, "x": 0, "y": 0, "z": 0},
#         {"id": 21, "x": 0, "y": 0, "z": 0},
#         {"id": 22, "x": 0, "y": 0, "z": 0}
#     ]
#     assert project.landmarks_corners == expected_corners

#     print(project.landmarks_corners)

