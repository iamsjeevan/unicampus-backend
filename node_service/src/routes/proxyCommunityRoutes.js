// node_service/src/routes/proxyCommunityRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader');
const router = express.Router();

const FLASK_COMMUNITY_URL_BASE = process.env.FLASK_API_BASE_URL; 

if (!FLASK_COMMUNITY_URL_BASE) {
    console.error("FATAL ERROR: FLASK_API_BASE_URL is not defined in Node.js environment.");
    // Consider process.exit(1) or a more graceful startup failure.
}

const handleProxy = async (req, res, method, flaskEndpoint, data = null) => {
    try {
        const headersForFlask = { ...(req.flaskHeaders || {}) };
        
        const axiosConfig = { 
            method, 
            url: flaskEndpoint, 
            headers: headersForFlask, 
            params: req.query // Forward query parameters for GET requests
        };

        if (data && (method.toLowerCase() === 'post' || method.toLowerCase() === 'put' || method.toLowerCase() === 'patch')) {
             axiosConfig.data = data;
        }
        
        // console.log(`\n--- NODE PROXY ---`);
        // console.log(`Timestamp: ${new Date().toISOString()}`);
        // console.log(`Original URL: ${req.originalUrl}`);
        // console.log(`Method: ${method.toUpperCase()}`);
        // console.log(`Proxying to Flask URL: ${flaskEndpoint}`);
        // console.log(`Query Params: ${JSON.stringify(req.query)}`);
        // console.log(`Headers sent to Flask: ${JSON.stringify(axiosConfig.headers, null, 2)}`);
        // if (axiosConfig.data) { try { console.log(`Data sent to Flask (body): ${JSON.stringify(axiosConfig.data, null, 2)}`); } catch (e) { console.log(`Data sent to Flask (body is not JSON stringifiable):`, axiosConfig.data); }}
        // console.log(`--- END NODE PROXY ---`);
        
        const flaskResponse = await axios(axiosConfig);
        res.status(flaskResponse.status).json(flaskResponse.data);

    } catch (error) {
        // console.error(`\n--- NODE PROXY ERROR ---`);
        // console.error(`Timestamp: ${new Date().toISOString()}`);
        // console.error(`Original URL: ${req.originalUrl}`);
        // console.error(`Error proxying to Flask URL ${flaskEndpoint}:`, error.message);
        if (error.response) { 
            // console.error("Flask Error Status:", error.response.status);
            // try { console.error("Flask Error Data:", JSON.stringify(error.response.data, null, 2)); } catch (e) { console.error("Flask Error Data (not JSON):", error.response.data); }
            // console.error("Flask Error Headers:", JSON.stringify(error.response.headers, null, 2));
            res.status(error.response.status).json(error.response.data); 
        } else if (error.request) {
            // console.error("Node Proxy Error: No response received from Flask. Request details:", error.request);
            res.status(502).json({ status: 'error', message: 'Bad gateway to community service: No response from backend.' });
        } else { 
            // console.error("Node Proxy Error: Error setting up the request to Flask:", error.message);
            res.status(500).json({ status: 'error', message: 'Internal error in proxy service.' }); 
        }
        // console.error(`--- END NODE PROXY ERROR ---`);
    }
};

// --- Communities ---
router.post('/communities', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities`, req.body);
});
router.get('/communities', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities`);
});
router.get('/communities/:communityIdOrSlug', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityIdOrSlug}`);
});
// THIS IS THE ADDED/CONFIRMED ROUTE FOR EDITING A COMMUNITY
router.put('/communities/:communityId', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'put', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}`, req.body);
});
router.post('/communities/:communityId/join', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/join`, req.body);
});
router.post('/communities/:communityId/leave', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/leave`, req.body);
});

// --- Posts ---
router.post('/communities/:communityId/posts', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/posts`, req.body);
});
router.get('/communities/:communityId/posts', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/posts`);
});
router.get('/posts/:postId', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`);
});
router.put('/posts/:postId', forwardAuthHeader, (req, res) => { // Already exists, good for editing posts
    handleProxy(req, res, 'put', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`, req.body);
});
router.delete('/posts/:postId', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'delete', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`);
});
router.post('/posts/:postId/vote', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/vote`, req.body);
});

// --- Comments ---
router.post('/posts/:postId/comments', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/comments`, req.body);
});
router.get('/posts/:postId/comments', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/comments`);
});
router.get('/comments/:commentId/replies', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'get', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}/replies`);
});
router.put('/comments/:commentId', forwardAuthHeader, (req, res) => { // Already exists, good for editing comments
    handleProxy(req, res, 'put', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}`, req.body);
});
router.delete('/comments/:commentId', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'delete', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}`);
});
router.post('/comments/:commentId/vote', forwardAuthHeader, (req, res) => {
    handleProxy(req, res, 'post', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}/vote`, req.body);
});

module.exports = router;