FROM node:18-alpine

# Set working director
WORKDIR /idls_app/frontend

# COPY --chown=node:node package*.json ./
COPY package*.json ./

RUN npm install

# RUN mkdir node_modules/.cache && chmod -R 777 node_modules/.cache

EXPOSE 3000

# USER node

CMD ["npm", "start"]

# EXPOSE 3000

# CMD ["npm", "start"]

# # プロジェクトと作成する
# RUN npx create-react-app frontend --template typescript

# # Copy package.json and package-lock.json
# COPY frontend/package-lock.json frontend/package-lock.json /idls_app/frontend/

# # WORKDIR /idls_app/frontend

# # Install dependencies
# RUN npm install

# RUN cd frontend && npm install

# # Copy the rest of the application
# # COPY frontend /idls_app/frontend

# # Expose port
# EXPOSE 3000

# # Command to run the application
# CMD ["npm", "start"]