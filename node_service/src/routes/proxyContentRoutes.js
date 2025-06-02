// node_service/src/routes/proxyContentRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader');
const router = express.Router();

const FLASK_CONTENT_URL_BASE = `${process.env.FLASK_API_BASE_URL}`;

const handleProxy = async (req, res, next, method, flaskEndpoint, data = null) => {
    try {
        console.log(`Node: Proxying ${method} ${req.originalUrl} to Flask: ${flaskEndpoint}`);
        const axiosConfig = { method, url: flaskEndpoint, headers: req.flaskHeaders, params: req.query };
        if (data) axiosConfig.data = data;
        const flaskResponse = await axios(axiosConfig);
        console.log(`Node: Flask response for ${req.originalUrl} - Status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);
    } catch (error) {
        console.error(`Node: Error proxying ${req.originalUrl} to Flask:`, error.message);
        if (error.response) { res.status(error.response.status).json(error.response.data); }
        else { res.status(502).json({ status: 'error', message: 'Bad gateway to content service.' }); }
    }
};

// App Info (might be public in Flask, check if auth needed)
router.get('/app/info', forwardAuthHeader, (req, res, next) => { // forwardAuthHeader won't hurt if Flask route is public
    handleProxy(req, res, next, 'get', `${FLASK_CONTENT_URL_BASE}/app/info`);
});

// Proctor Announcements (Demo)
router.get('/announcements/proctor', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_CONTENT_URL_BASE}/announcements/proctor`);
});

// College Clubs (Demo)
router.get('/content/clubs', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_CONTENT_URL_BASE}/content/clubs`);
});

// Academic Links (Demo)
router.get('/content/academics-links', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_CONTENT_URL_BASE}/content/academics-links`);
});

module.exports = router;