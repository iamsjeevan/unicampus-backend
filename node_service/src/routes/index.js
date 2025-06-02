// node_service/src/routes/index.js
const express = require('express');
const resourceRoutes = require('./resourceRoutes');
const proxyAuthRoutes = require('./proxyAuthRoutes'); // <--- IMPORT

const router = express.Router();

router.use('/resources', resourceRoutes);
router.use('/auth', proxyAuthRoutes); // <--- MOUNT for /api/v1/auth/...

module.exports = router;