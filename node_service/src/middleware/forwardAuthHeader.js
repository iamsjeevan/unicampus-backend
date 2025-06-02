// node_service/src/middleware/forwardAuthHeader.js
const forwardAuthHeader = (req, res, next) => {
    req.flaskHeaders = {
        'Content-Type': req.headers['content-type'] || 'application/json',
        // Add other headers you always want to forward from client to Flask
    };
    const authHeader = req.headers.authorization;
    if (authHeader) {
        req.flaskHeaders['Authorization'] = authHeader;
    }
    // console.log('Forwarding headers to Flask:', req.flaskHeaders);
    next();
};

module.exports = forwardAuthHeader;