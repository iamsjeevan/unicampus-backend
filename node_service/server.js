// node_service/server.js
require('./src/config'); // Load .env variables first
const app = require('./src/app'); // Your Express app

const PORT = process.env.PORT || 3001;

app.listen(PORT, () => {
  console.log(`Node.js/Express service running on port ${PORT}`);
  console.log(`Flask API is expected at: ${process.env.FLASK_API_BASE_URL}`);
  console.log(`Resources MongoDB URI: ${process.env.RESOURCES_MONGO_URI ? 'Configured' : 'NOT CONFIGURED'}`);
});