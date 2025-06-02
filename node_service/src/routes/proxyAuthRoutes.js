// node_service/src/routes/proxyAuthRoutes.js
const express = require('express');
const axios = require('axios');
const router = express.Router();

// FLASK_API_BASE_URL should be like 'http://flask_service:8000/api/v1' from .env
const FLASK_AUTH_URL = `${process.env.FLASK_API_BASE_URL}/auth`;

router.post('/login/student', async (req, res, next) => {
    try {
        console.log(`Node Service: Proxying login request for USN ${req.body.usn} to Flask...`);
        const flaskResponse = await axios.post(`${FLASK_AUTH_URL}/login/student`, req.body, {
            headers: {
                'Content-Type': 'application/json'
                // Forward any other relevant headers if needed, but typically not for login
            }
        });
        console.log(`Node Service: Received response from Flask login, status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);
    } catch (error) {
        console.error("Node Service: Error proxying login to Flask:", error.message);
        if (error.response) {
            // Forward the error response from Flask
            console.error("Flask Error Data:", error.response.data);
            res.status(error.response.status).json(error.response.data);
        } else {
            // Network error or other issue before getting a response from Flask
            res.status(500).json({ status: 'error', message: 'Failed to connect to authentication service.' });
        }
    }
});

// You can add other auth proxy routes here later (refresh, logout)

module.exports = router;