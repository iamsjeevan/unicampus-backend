// node_service/src/routes/proxyAuthRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader');
const router = express.Router();

const FLASK_AUTH_URL = `${process.env.FLASK_API_BASE_URL}/auth`;

const handleProxy = async (req, res, next, method, flaskEndpoint, data = null) => {
    try {
        console.log(`Node: Proxying ${method} ${req.path} to Flask: ${flaskEndpoint}`);
        const axiosConfig = {
            method: method,
            url: flaskEndpoint,
            headers: req.flaskHeaders, // Forwarded by middleware
        };
        if (data) {
            axiosConfig.data = data;
        }

        const flaskResponse = await axios(axiosConfig);
        console.log(`Node: Flask response for ${req.path} - Status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);
    } catch (error) {
        console.error(`Node: Error proxying ${req.path} to Flask:`, error.message);
        if (error.response) {
            console.error("Flask Error Data:", error.response.data);
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(502).json({ status: 'error', message: 'Bad gateway to backend service.' }); // 502 for network/unreachable
        }
    }
};

// Student Login
router.post('/login/student', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_AUTH_URL}/login/student`, req.body);
});

// Refresh Token
router.post('/refresh-token', forwardAuthHeader, (req, res, next) => {
    // Refresh token itself is in req.flaskHeaders.Authorization
    handleProxy(req, res, next, 'post', `${FLASK_AUTH_URL}/refresh-token`);
});

// Logout
router.post('/logout', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_AUTH_URL}/logout`);
});

module.exports = router;