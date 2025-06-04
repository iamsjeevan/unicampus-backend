const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors'); // <-- import cors
const mainRouter = require('./routes');

const app = express();

// ✅ Enable CORS for multiple frontend origins
const allowedOrigins = [
  'https://unicampusmsrit.netlify.app',
  'http://localhost:3000',
  'https://your-other-frontend.com',
  'https://refactored-space-winner-9wgrw9gjxrphx5r9-8080.app.github.dev' // newly added origin
];

const corsOptions = {
  origin: function (origin, callback) {
    if (!origin) return callback(null, true); // allow tools like Postman
    if (allowedOrigins.includes(origin)) {
      return callback(null, true);
    } else {
      return callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true
};

app.use(cors(corsOptions));

// MongoDB connection
const dbURI = process.env.RESOURCES_MONGO_URI;
if (!dbURI) {
    console.error("FATAL ERROR: RESOURCES_MONGO_URI is not defined. Set it in node_service/.env");
    process.exit(1);
}

mongoose.connect(dbURI)
    .then(() => console.log('Node service successfully connected to MongoDB for Resources.'))
    .catch(err => {
        console.error('Node service MongoDB connection error for Resources:', err.message);
    });

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'Node.js Gateway/Resource Service' });
});

// API routing
app.use('/api/v1', mainRouter);

// Global error handler
app.use((err, req, res, next) => {
  console.error("Node Service Error:", err.message);
  if (err instanceof require('multer').MulterError) {
    return res.status(400).json({ status: 'fail', message: `File upload error: ${err.message}` });
  }
  if (err.message.includes('File type not allowed')) {
    return res.status(400).json({ status: 'fail', message: err.message });
  }
  res.status(err.statusCode || 500).json({
    status: 'error',
    message: err.message || 'An unexpected internal server error occurred in Node service.',
  });
});

module.exports = app;
