// node_service/src/routes/index.js
const express = require('express');
const resourceRoutes = require('./resourceRoutes');
// const proxyRoutes = require('./proxyRoutes'); // For Flask API calls

const router = express.Router();

router.use('/resources', resourceRoutes);
// router.use(proxyRoutes); // Mount proxy routes for things like /auth, /communities, etc.

module.exports = router;