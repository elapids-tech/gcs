# DockerHubのベースとなるイメージを指定
FROM python:3.11-slim

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y git

# 必要なパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 作業ディレクトリを設定
WORKDIR /idls_app/backend

# スクリプトをコンテナにコピー
COPY main.py .

# Uvicornを実行
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
