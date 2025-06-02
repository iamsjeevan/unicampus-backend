# node_service/Dockerfile
FROM node:18-slim
WORKDIR /test
CMD ["node", "-v"]# node_service/Dockerfile

FROM node:18-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (or yarn.lock if you use Yarn)
# This leverages Docker cache: if these files haven't changed, subsequent RUN npm install won't re-run
COPY package*.json ./

# Install app dependencies
# Using --only=production for smaller final images.
# If you have build scripts (e.g., TypeScript compilation) that are part of your `npm run build`,
# you might need to run `npm install` (to get devDependencies) then `npm run build` before this.
RUN npm install --only=production 

# If you had a build step (e.g., for TypeScript or frontend assets if bundled with Node):
# COPY . . 
# RUN npm run build
# Then, for the final stage, you might copy only the built artifacts and production node_modules.
# For a simple Express app, copying all source might be okay for now.

# Bundle app source code into the container
COPY . .

# Expose the port the app will run on (should match PORT in your .env for Node app)
EXPOSE 3001

# Define environment variables (can be overridden by docker-compose or runtime)
ENV NODE_ENV=production
ENV PORT=3001 
# It's good practice to have defaults here even if .env is used by docker-compose,
# for cases where the image might be run directly without docker-compose.
# ENV FLASK_API_BASE_URL=http://flask_service:8000/api/v1
# ENV RESOURCES_MONGO_URI="mongodb://mongo:27017/uni_campus_resources_db"


# Command to run the application
CMD [ "node", "server.js" ]