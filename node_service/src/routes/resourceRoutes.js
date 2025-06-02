// node_service/src/routes/resourceRoutes.js
const express = require('express');
const resourceController = require('../controllers/resourceController');
const { upload } = require('../middleware/uploadMiddleware');

const router = express.Router();

// Temporary placeholder for auth middleware
const tempAuthMiddleware = (req, res, next) => {
    // FOR TESTING ONLY - REMOVE/REPLACE WITH REAL JWT AUTH MIDDLEWARE
    // This mock ensures `req.user.id` is available for the controller.
    if (!req.user) {
        // Use a consistent, valid ObjectId string for testing if your User model expects it.
        // This ID should correspond to the user whose $ACCESS_TOKEN you are using in curl.
        // You can get this ID from the response of your Flask login API.
        req.user = { id: "683c2cc89c8c284ebb0eb0c3" }; // Example: your test user ID
        console.warn(`WARNING: Using MOCKED user ID '${req.user.id}' in tempAuthMiddleware for resource routes.`);
    } else {
        console.log("Temp Auth Middleware: req.user already exists (perhaps from a real auth middleware if added).");
    }
    next();
};

router.post('/', tempAuthMiddleware, upload.single('resourceFile'), resourceController.createResource);
router.get('/', tempAuthMiddleware, resourceController.getAllResources);
router.get('/:resourceId', tempAuthMiddleware, resourceController.getResourceById);
router.get('/:resourceId/download', tempAuthMiddleware, resourceController.downloadResourceFile);
router.delete('/:resourceId', tempAuthMiddleware, resourceController.deleteResource);

module.exports = router;