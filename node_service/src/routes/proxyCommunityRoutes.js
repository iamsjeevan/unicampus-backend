// node_service/src/routes/proxyCommunityRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader'); // Assuming this populates req.flaskHeaders
const router = express.Router();

// Ensure FLASK_API_BASE_URL is defined in your .env for node_service
// e.g., FLASK_API_BASE_URL=http://flask_app:8000/api/v1
const FLASK_COMMUNITY_URL_BASE = process.env.FLASK_API_BASE_URL; 

if (!FLASK_COMMUNITY_URL_BASE) {
    console.error("FATAL ERROR: FLASK_API_BASE_URL is not defined in Node.js environment.");
    // process.exit(1); // Or handle more gracefully depending on needs
}

const handleProxy = async (req, res, method, flaskEndpoint, data = null) => {
    try {
        // req.flaskHeaders should be populated by forwardAuthHeader middleware
        // It should include 'Authorization' and potentially 'Content-Type' if needed to override axios defaults.
        // For POST/PUT with JSON data, axios typically sets Content-Type: application/json automatically.
        const headersForFlask = { ...(req.flaskHeaders || {}) }; // Start with headers from middleware

        // If data is being sent and it's a POST/PUT, ensure Content-Type is application/json
        // unless req.flaskHeaders already specified something else (e.g., for multipart/form-data)
        if (data && (method.toLowerCase() === 'post' || method.toLowerCase() === 'put')) {
            if (!headersForFlask['Content-Type'] && !headersForFlask['content-type']) {
                 // If forwardAuthHeader (or other middleware) didn't set a Content-Type,
                 // and we are sending JSON, axios will set it. If we were sending FormData,
                 // axios would also set multipart/form-data.
                 // So, usually, we don't need to manually set it here for JSON.
            }
        }
        
        const axiosConfig = { 
            method, 
            url: flaskEndpoint, 
            headers: headersForFlask, 
            params: req.query // For GET request query parameters
        };

        if (data && (method.toLowerCase() === 'post' || method.toLowerCase() === 'put')) {
             axiosConfig.data = data;
        }
        
        // --- START DEBUG LOGGING for Node.js proxy ---
        console.log(`\n--- NODE PROXY ---`);
        console.log(`Timestamp: ${new Date().toISOString()}`);
        console.log(`Original URL: ${req.originalUrl}`);
        console.log(`Method: ${method.toUpperCase()}`);
        console.log(`Proxying to Flask URL: ${flaskEndpoint}`);
        console.log(`Query Params: ${JSON.stringify(req.query)}`);
        console.log(`Headers sent to Flask: ${JSON.stringify(axiosConfig.headers, null, 2)}`);
        if (axiosConfig.data) {
            try {
                console.log(`Data sent to Flask (body): ${JSON.stringify(axiosConfig.data, null, 2)}`);
            } catch (e) {
                console.log(`Data sent to Flask (body could not be stringified, might be FormData):`, axiosConfig.data);
            }
        }
        console.log(`--- END NODE PROXY ---`);
        // --- END DEBUG LOGGING ---
        
        const flaskResponse = await axios(axiosConfig);
        // console.log(`Node: Flask response for ${req.originalUrl} - Status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);

    } catch (error) {
        console.error(`\n--- NODE PROXY ERROR ---`);
        console.error(`Timestamp: ${new Date().toISOString()}`);
        console.error(`Original URL: ${req.originalUrl}`);
        console.error(`Error proxying to Flask URL ${flaskEndpoint}:`, error.message);
        if (error.response) { 
            console.error("Flask Error Status:", error.response.status);
            // Log the full error response data from Flask
            try {
                console.error("Flask Error Data:", JSON.stringify(error.response.data, null, 2));
            } catch (e) {
                console.error("Flask Error Data (could not be stringified):", error.response.data);
            }
            console.error("Flask Error Headers:", JSON.stringify(error.response.headers, null, 2));
            res.status(error.response.status).json(error.response.data); 
        } else if (error.request) {
            console.error("Node Proxy Error: No response received from Flask. Request details:", error.request);
            res.status(502).json({ status: 'error', message: 'Bad gateway to community service: No response from Flask.' });
        } else { 
            console.error("Node Proxy Error: Error setting up the request to Flask:", error.message);
            res.status(500).json({ status: 'error', message: 'Internal error in Node.js proxy service.' }); 
        }
        console.error(`--- END NODE PROXY ERROR ---`);
    }
};

// --- Communities ---
router.post('/communities', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities`, req.body);
});
router.get('/communities', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities`);
});
router.get('/communities/:communityIdOrSlug', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityIdOrSlug}`);
});
router.post('/communities/:communityId/join', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/join`, req.body); // req.body might be empty, that's fine
});
router.post('/communities/:communityId/leave', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/leave`, req.body); // req.body might be empty
});

// --- Posts ---
router.post('/communities/:communityId/posts', forwardAuthHeader, (req, res, next) => {
    // This is the problematic route
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/posts`, req.body);
});
router.get('/communities/:communityId/posts', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/posts`);
});
router.get('/posts/:postId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`);
});
router.put('/posts/:postId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'put', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`, req.body);
});
router.delete('/posts/:postId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'delete', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`);
});
router.post('/posts/:postId/vote', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/vote`, req.body);
});

// --- Comments ---
router.post('/posts/:postId/comments', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/comments`, req.body);
});
router.get('/posts/:postId/comments', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/comments`);
});
router.get('/comments/:commentId/replies', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}/replies`);
});
router.put('/comments/:commentId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'put', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}`, req.body);
});
router.delete('/comments/:commentId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'delete', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}`);
});
router.post('/comments/:commentId/vote', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}/vote`, req.body);
});

module.exports = router;