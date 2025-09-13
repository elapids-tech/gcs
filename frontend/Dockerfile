FROM node:18-alpine

# 必要なツールをインストール
RUN apk add --no-cache bash python3 make g++

WORKDIR /idls_app/frontend

# 依存関係だけコピーしてインストール
COPY package*.json ./
RUN npm ci

# アプリ全体をコピー
COPY . .

EXPOSE 3000

CMD ["npm", "start"]