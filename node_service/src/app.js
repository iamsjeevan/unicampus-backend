// node_service/src/app.js
const express = require('express');
const mainRouter = require('./routes'); // We'll create this next

const app = express();

app.use(express.json()); // Middleware to parse JSON bodies
app.use(express.urlencoded({ extended: true })); // Middleware to parse URL-encoded bodies

// Health check for Node service
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'Node.js Gateway/Resource Service' });
});

// Mount main router
app.use('/api/v1', mainRouter); // All routes will be prefixed with /api/v1

// Basic error handler (can be improved)
app.use((err, req, res, next) => {
  console.error("Error in Node/Express app:", err.stack || err);
  res.status(err.statusCode || 500).json({
    status: 'error',
    message: err.message || 'An unexpected internal server error occurred.',
  });
});

module.exports = app;