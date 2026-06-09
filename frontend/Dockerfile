FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
	 ca-certificates \
	 curl \
	 gnupg \
	 && mkdir -p /etc/apt/keyrings \
	 && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
		 | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
	 && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
		 > /etc/apt/sources.list.d/nodesource.list \
	 && apt-get update \
	 && apt-get install -y nodejs \
	 && apt-get clean \
	 && rm -rf /var/lib/apt/lists/*

# Set working director
WORKDIR /gcs/frontend

# COPY --chown=node:node package*.json ./
COPY package*.json ./

RUN npm install

EXPOSE 3000

CMD ["npm", "start"]
