#!/bin/bash

# Script to create the initial directory structure and empty files
# for the node_service within the unicampus-backend project.
# Run this script from the unicampus-backend project root.

NODE_SERVICE_DIR="node_service"

echo "Creating directory structure for $NODE_SERVICE_DIR..."

# Create the main node_service directory if it doesn't exist
mkdir -p "$NODE_SERVICE_DIR"

# Create subdirectories within node_service
mkdir -p "$NODE_SERVICE_DIR/src"
mkdir -p "$NODE_SERVICE_DIR/src/config"
mkdir -p "$NODE_SERVICE_DIR/src/controllers"
mkdir -p "$NODE_SERVICE_DIR/src/models"
mkdir -p "$NODE_SERVICE_DIR/src/routes"
mkdir -p "$NODE_SERVICE_DIR/src/middleware"
mkdir -p "$NODE_SERVICE_DIR/tests" # For JavaScript/Node tests
mkdir -p "$NODE_SERVICE_DIR/uploads/node_resources" # For local resource file storage

echo "Creating empty files..."

# Create main files in node_service
touch "$NODE_SERVICE_DIR/server.js"
touch "$NODE_SERVICE_DIR/package.json" # Will be populated by npm init
touch "$NODE_SERVICE_DIR/Dockerfile"
touch "$NODE_SERVICE_DIR/.env"

# Create files in src/
touch "$NODE_SERVICE_DIR/src/app.js"

# Create files in src/config/
touch "$NODE_SERVICE_DIR/src/config/index.js"

# Create files in src/controllers/
touch "$NODE_SERVICE_DIR/src/controllers/resourceController.js"
# touch "$NODE_SERVICE_DIR/src/controllers/proxyAuthController.js" # Placeholder for later
# touch "$NODE_SERVICE_DIR/src/controllers/proxyCommunityController.js" # Placeholder for later

# Create files in src/models/
touch "$NODE_SERVICE_DIR/src/models/Resource.js"

# Create files in src/routes/
touch "$NODE_SERVICE_DIR/src/routes/index.js"
touch "$NODE_SERVICE_DIR/src/routes/resourceRoutes.js"
# touch "$NODE_SERVICE_DIR/src/routes/proxyRoutes.js" # Placeholder for later

# Create files in src/middleware/
# touch "$NODE_SERVICE_DIR/src/middleware/authMiddleware.js" # Placeholder for later

echo "Basic file and directory structure for $NODE_SERVICE_DIR created."
echo "Next steps:"
echo "1. cd $NODE_SERVICE_DIR"
echo "2. Run 'npm init -y' to initialize package.json"
echo "3. Run 'npm install express dotenv axios mongoose jsonwebtoken multer' for dependencies"
echo "4. Run 'npm install -D nodemon eslint prettier jest supertest' for dev dependencies"
echo "5. Populate the created .js, .env, and Dockerfile with the provided code."