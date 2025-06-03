// node_service/src/app.js (or server.js if you prefer DB connection there)
const express = require('express');
const mongoose = require('mongoose'); // Import Mongoose
const mainRouter = require('./routes');
// const config = require('./config'); // If you exported specific configs

const app = express();

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


app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'Node.js Gateway/Resource Service' });
});

app.use('/api/v1', mainRouter);

app.use((err, req, res, next) => {
  console.error("Node Service Error:", err.message);
  // If error is from multer (e.g. file too large)
  if (err instanceof require('multer').MulterError) {
    return res.status(400).json({ status: 'fail', message: `File upload error: ${err.message}` });
  }
  // If error has a custom message from fileFilter
  if (err.message.includes('File type not allowed')) {
      return res.status(400).json({ status: 'fail', message: err.message });
  }
  res.status(err.statusCode || 500).json({
    status: 'error',
    message: err.message || 'An unexpected internal server error occurred in Node service.',
  });
});

module.exports = app;