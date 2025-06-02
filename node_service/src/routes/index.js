// node_service/src/routes/index.js
const express = require('express');
const resourceRoutes = require('./resourceRoutes'); // Native Node.js routes
const proxyAuthRoutes = require('./proxyAuthRoutes');
const proxyUserRoutes = require('./proxyUserRoutes');
const proxyAcademicRoutes = require('./proxyAcademicRoutes');
const proxyContentRoutes = require('./proxyContentRoutes');
const proxyCommunityRoutes = require('./proxyCommunityRoutes'); // Handles /communities, /posts, /comments

const router = express.Router();

// Native Node.js implemented routes
router.use('/resources', resourceRoutes);

// Proxied routes to Flask service
router.use('/auth', proxyAuthRoutes);
router.use('/users', proxyUserRoutes); // For /users/me, /users/me/fees
router.use(proxyAcademicRoutes);      // For /results/*, /attendance/*
router.use(proxyContentRoutes);       // For /app/info, /content/*, /announcements/*
router.use(proxyCommunityRoutes);     // For /communities/*, /posts/*, /comments/*

module.exports = router;