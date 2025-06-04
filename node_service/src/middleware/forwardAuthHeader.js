// node_service/src/middleware/forwardAuthHeader.js
const forwardAuthHeader = (req, res, next) => {
    const incomingContentType = req.headers['content-type'];
    const finalContentType = incomingContentType || 'application/json'; // Default to application/json if not provided

    req.flaskHeaders = {
        'Content-Type': finalContentType
        // Add other headers you always want to forward from client to Flask
    };

    const authHeader = req.headers.authorization;
    if (authHeader) {
        req.flaskHeaders['Authorization'] = authHeader;
    }

    // --- DETAILED LOGGING ---
    console.log(`\n--- NODE forwardAuthHeader Middleware ---`);
    console.log(`Timestamp: ${new Date().toISOString()}`);
    console.log(`Original URL: ${req.originalUrl}`);
    console.log(`Incoming 'Content-Type' from client: ${incomingContentType}`);
    console.log(`'Content-Type' being set for Flask request: ${finalContentType}`);
    if (authHeader) {
        console.log(`'Authorization' header IS being forwarded.`);
    } else {
        console.log(`'Authorization' header IS NOT present in incoming request.`);
    }
    console.log(`All headers prepared for Flask (req.flaskHeaders): ${JSON.stringify(req.flaskHeaders, null, 2)}`);
    console.log(`--- END NODE forwardAuthHeader Middleware ---`);
    // --- END DETAILED LOGGING ---
    
    next();
};

module.exports = forwardAuthHeader;