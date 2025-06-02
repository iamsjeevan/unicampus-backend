# node_service/Dockerfile

FROM node:18-slim  # Or your preferred Node LTS version

WORKDIR /usr/src/app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install app dependencies
RUN npm install --only=production # Install only production dependencies for smaller image
# If you have build steps:
# RUN npm install 
# RUN npm run build 

# Bundle app source
COPY . .

# Expose the port the app runs on (should match PORT in .env)
EXPOSE 3001 

# Define environment variables that might be needed if not from .env file by compose
ENV NODE_ENV=production
ENV PORT=3001
# ENV FLASK_API_BASE_URL=http://flask_service:8000/api/v1 # Good to have a default if .env missing
# ENV RESOURCES_MONGO_URI= # Default this too if appropriate

CMD [ "node", "server.js" ]