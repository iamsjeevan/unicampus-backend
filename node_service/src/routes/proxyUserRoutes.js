// node_service/src/routes/proxyUserRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader');
const router = express.Router();

const FLASK_USERS_URL = `${process.env.FLASK_API_BASE_URL}/users`;

// Generic proxy handler from proxyAuthRoutes.js could be refactored into a utility
const handleProxy = async (req, res, next, method, flaskEndpoint, data = null) => {
    try {
        console.log(`Node: Proxying ${method} ${req.path} to Flask: ${flaskEndpoint}`);
        const axiosConfig = { method, url: flaskEndpoint, headers: req.flaskHeaders };
        if (data) axiosConfig.data = data;
        const flaskResponse = await axios(axiosConfig);
        console.log(`Node: Flask response for ${req.path} - Status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);
    } catch (error) {
        console.error(`Node: Error proxying ${req.path} to Flask:`, error.message);
        if (error.response) { res.status(error.response.status).json(error.response.data); }
        else { res.status(502).json({ status: 'error', message: 'Bad gateway to user service.' }); }
    }
};

// Get Current User Profile
router.get('/me', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_USERS_URL}/me`);
});

// Update Current User Profile
router.put('/me', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'put', `${FLASK_USERS_URL}/me`, req.body);
});

// Get User Fees (Demo) - Assuming it was /users/me/fees
router.get('/me/fees', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_USERS_URL}/me/fees`);
});


module.exports = router;