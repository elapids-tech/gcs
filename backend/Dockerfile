# DockerHubのベースとなるイメージを指定
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

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
    python3 \
    python3-pip \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    iputils-ping \
    tcpdump \
    && python3 -m pip install --no-cache-dir --upgrade pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /gcs/backend

# 必要なパッケージをインストール
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# スクリプトをコンテナにコピー
COPY main.py .

CMD ["sleep", "infinity"]