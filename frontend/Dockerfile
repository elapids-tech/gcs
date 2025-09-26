FROM node:18-alpine

# Set working director
WORKDIR /idls_app/frontend

# COPY --chown=node:node package*.json ./
COPY package*.json ./

RUN npm install

EXPOSE 3000

CMD ["npm", "start"]
