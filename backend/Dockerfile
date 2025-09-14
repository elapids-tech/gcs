# DockerHubのベースとなるイメージを指定
FROM python:3.11-slim

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    procps \
    netcat-openbsd \
    curl \
    git \
    ca-certificates \
    gcc \
    g++ \
    make \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    iputils-ping \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /idls_app/backend

# 必要なパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# スクリプトをコンテナにコピー
COPY main.py .

CMD ["sleep", "infinity"]