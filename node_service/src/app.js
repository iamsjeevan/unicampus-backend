// node_service/src/app.js
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors'); // <--- IMPORT CORS
const mainRouter = require('./routes');

const app = express();

// --- APPLY CORS MIDDLEWARE (ALLOW ALL ORIGINS) ---
// This will set Access-Control-Allow-Origin: *
app.use(cors({
    credentials: true, // Important to allow cookies/authorization headers
    // You might still want to specify allowed methods and headers if your frontend uses them
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
}));
// No need for app.options('*', cors()) separately when using app.use(cors()) like this,
// as the cors middleware itself handles OPTIONS requests correctly by default.

// --- Database Connection ---
const dbURI = process.env.RESOURCES_MONGO_URI;
if (!dbURI) {
    console.error("FATAL ERROR: RESOURCES_MONGO_URI is not defined. Set it in node_service/.env");
    process.exit(1); // Exit if DB URI is missing
}

mongoose.connect(dbURI)
    .then(() => console.log('Node service successfully connected to MongoDB for Resources.'))
    .catch(err => {
        console.error('Node service MongoDB connection error for Resources:', err.message);
        // process.exit(1); // Optionally exit if DB connection fails on startup
    });
// --- End Database Connection ---


app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'Node.js Gateway/Resource Service' });
});

app.use('/api/v1', mainRouter);

// --- Not Found Handler (if no routes matched by mainRouter or /health) ---
app.use((req, res, next) => {
    const error = new Error(`Not Found - ${req.originalUrl}`);
    error.status = 404;
    next(error);
});

// --- Global Error Handler (must be the last app.use() call) ---
app.use((err, req, res, next) => {
  console.error("Node Service Error Handler Caught:", err.message, "Status:", err.status || err.statusCode);

  if (err.name === 'MongoServerError' && err.code === 11000) {
      return res.status(409).json({ status: 'fail', message: 'Duplicate key error.'});
  }
  if (err instanceof require('multer').MulterError) {
    return res.status(400).json({ status: 'fail', message: `File upload error: ${err.message}` });
  }
  if (err.message && err.message.includes('File type not allowed')) {
      return res.status(400).json({ status: 'fail', message: err.message });
  }

  if (res.headersSent) {
    return next(err);
  }

  res.status(err.status || err.statusCode || 500).json({
    status: 'error',
    message: err.message || 'An unexpected internal server error occurred in Node service.',
    ...(process.env.NODE_ENV === 'development' && err.stack && { stack: err.stack.substring(0, 300) + "..." })
  });
});

module.exports = app;