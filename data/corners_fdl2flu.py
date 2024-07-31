import json
import numpy as np

file_path = '/idls_app/data/test_project_data.json'

landmarks_corners = []

# JSONファイルを開いて読み込む
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Transformation matrix
transformation_matrix = np.array([
    [1, 0, 0],
    [0, 0, 1],
    [0, -1, 0]
])

# Function to transform the coordinates
def transform_coordinates(coords):
    return transformation_matrix @ np.array(coords)

# Transforming all corner coordinates
for landmark in data["landmarks"].values():
    transformed_corners = [transform_coordinates(corner).tolist() for corner in landmark["corners"]]
    landmark["corners"] = transformed_corners

output_file = '/idls_app/data/transformed_data.json'
with open(output_file, 'w') as f:
    json.dump(data, f, indent=4)