// node_service/src/routes/proxyCommunityRoutes.js
const express = require('express');
const axios = require('axios');
const forwardAuthHeader = require('../middleware/forwardAuthHeader');
const router = express.Router();

const FLASK_COMMUNITY_URL_BASE = `${process.env.FLASK_API_BASE_URL}`;

const handleProxy = async (req, res, next, method, flaskEndpoint, data = null) => {
    try {
        // Construct the full Flask URL including any path parameters
        // req.originalUrl includes the full path after /api/v1, e.g. /communities/some-id/posts
        // req.path might be just /posts if the router is mounted on /communities/:id
        // For simplicity, we'll reconstruct.
        
        let fullFlaskUrl = `${FLASK_COMMUNITY_URL_BASE}${req.originalUrl.substring(req.baseUrl.length)}`;
        // req.baseUrl for this router will be empty if mounted at /api/v1 directly.
        // Or, if router is mounted as router.use('/communities', proxyCommunityRoutes), req.baseUrl would be /communities
        // Let's assume for this file, it handles /communities, /posts, /comments.
        // So, the full path is just req.originalUrl AFTER the /api/v1 prefix from the main router.
        // FLASK_COMMUNITY_URL_BASE already is http://flask_app:8000/api/v1
        // So we just need the part of req.originalUrl that comes AFTER /api/v1
        // For example, if Node route is /api/v1/communities and originalUrl is /api/v1/communities?page=1
        // then the path to append is /communities?page=1
        // A simpler way if FLASK_COMMUNITY_URL_BASE doesn't include /api/v1, but points to flask_app:8000
        // FLASK_RAW_BASE = http://flask_app:8000
        // fullFlaskUrl = `${FLASK_RAW_BASE}${req.originalUrl}` (if req.originalUrl is /api/v1/communities/...)
        // Let's assume FLASK_API_BASE_URL = http://flask_app:8000/api/v1
        // And this router is mounted at /api/v1 in Node.
        // Then if a request comes to Node at /api/v1/communities, req.path is /communities
        fullFlaskUrl = `${FLASK_COMMUNITY_URL_BASE}${req.path}`;
        if (Object.keys(req.params).length > 0) { // If there are path parameters like :communityId
            // This logic is tricky. A general proxy is hard.
            // It's often easier to define each route explicitly if paths differ or params are complex.
            // For now, let's rely on explicit path construction for each proxied route.
        }


        console.log(`Node: Proxying ${method} ${req.originalUrl} to Flask: ${flaskEndpoint}`);
        const axiosConfig = { method, url: flaskEndpoint, headers: req.flaskHeaders, params: req.query };
        if (data && (method.toLowerCase() === 'post' || method.toLowerCase() === 'put')) {
             axiosConfig.data = data;
        }
        
        const flaskResponse = await axios(axiosConfig);
        console.log(`Node: Flask response for ${req.originalUrl} - Status: ${flaskResponse.status}`);
        res.status(flaskResponse.status).json(flaskResponse.data);
    } catch (error) {
        console.error(`Node: Error proxying ${req.originalUrl} to Flask:`, error.message);
        if (error.response) { 
            console.error("Flask Error Data:", JSON.stringify(error.response.data));
            res.status(error.response.status).json(error.response.data); 
        } else { 
            res.status(502).json({ status: 'error', message: 'Bad gateway to community service.' }); 
        }
    }
};

// --- Communities ---
router.post('/communities', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities`, req.body);
});
router.get('/communities', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities`);
});
router.get('/communities/:communityIdOrSlug', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityIdOrSlug}`);
});
router.post('/communities/:communityId/join', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/join`);
});
router.post('/communities/:communityId/leave', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/leave`);
});

// --- Posts ---
router.post('/communities/:communityId/posts', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/posts`, req.body);
});
router.get('/communities/:communityId/posts', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_COMMUNITY_URL_BASE}/communities/${req.params.communityId}/posts`);
});
// Note: GET /posts/:postId, PUT /posts/:postId, DELETE /posts/:postId also need specific handling if mounted here.
// It's cleaner if routes for /posts and /comments are separate from /communities in Node router structure too.
// For now, adding them here:
router.get('/posts/:postId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`);
});
router.put('/posts/:postId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'put', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`, req.body);
});
router.delete('/posts/:postId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'delete', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}`);
});
router.post('/posts/:postId/vote', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/vote`, req.body);
});

// --- Comments ---
router.post('/posts/:postId/comments', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/comments`, req.body);
});
router.get('/posts/:postId/comments', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_COMMUNITY_URL_BASE}/posts/${req.params.postId}/comments`);
});
router.get('/comments/:commentId/replies', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'get', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}/replies`);
});
router.put('/comments/:commentId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'put', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}`, req.body);
});
router.delete('/comments/:commentId', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'delete', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}`);
});
router.post('/comments/:commentId/vote', forwardAuthHeader, (req, res, next) => {
    handleProxy(req, res, next, 'post', `${FLASK_COMMUNITY_URL_BASE}/comments/${req.params.commentId}/vote`, req.body);
});

module.exports = router;