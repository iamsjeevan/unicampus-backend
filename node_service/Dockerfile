# node_service/Dockerfile
FROM node:18-slim
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm ci --only=production 
COPY . .
EXPOSE 3001
ENV NODE_ENV=production
ENV PORT=3001
CMD [ "node", "server.js" ] # Production command
