// node_service/src/config/index.js
const dotenv = require('dotenv');
const path = require('path');

// Load .env file from the root of node_service directory
dotenv.config({ path: path.resolve(__dirname, '..', '..', '.env') });

// You can export specific config values if needed, or just let process.env be used
// module.exports = {
//   port: process.env.PORT,
//   flaskApiBaseUrl: process.env.FLASK_API_BASE_URL,
//   resourcesMongoUri: process.env.RESOURCES_MONGO_URI,
//   nodeJwtSecret: process.env.NODE_JWT_SECRET,
// };