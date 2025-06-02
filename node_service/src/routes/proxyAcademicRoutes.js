// node_service/src/routes/proxyAcademicRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader');
const router = express.Router();

const FLASK_ACADEMIC_URL_BASE = `${process.env.FLASK_API_BASE_URL}`; // Flask routes are /results/* and /attendance/*

const handleProxy = async (req, res, next, method, flaskEndpoint, data = null) => {
    try {
        console.log(`Node: Proxying ${method} ${req.originalUrl} to Flask: ${flaskEndpoint}`); // Log originalUrl
        const axiosConfig = { method, url: flaskEndpoint, headers: req.flaskHeaders, params: req.query }; // Pass query params
        if (data) axiosConfig.data = data;
        const flaskResponse = await axios(axiosConfig);
        console.log(`Node: Flask response for ${req.originalUrl} - Status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);
    } catch (error) {
        console.error(`Node: Error proxying ${req.originalUrl} to Flask:`, error.message);
        if (error.response) { res.status(error.response.status).json(error.response.data); }
        else { res.status(502).json({ status: 'error', message: 'Bad gateway to academic service.' }); }
    }
};

// Get CIE Results
router.get('/results/cie', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_ACADEMIC_URL_BASE}/results/cie`);
});

// Get SEE Results
router.get('/results/see', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_ACADEMIC_URL_BASE}/results/see`);
});

// Get Attendance Summary
router.get('/attendance/summary', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_ACADEMIC_URL_BASE}/attendance/summary`);
});

module.exports = router;