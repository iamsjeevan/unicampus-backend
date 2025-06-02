// node_service/src/controllers/resourceController.js
const Resource = require('../models/Resource');
const fs = require('fs');
const path = require('path');
const { FULL_UPLOAD_PATH } = require('../middleware/uploadMiddleware');

exports.createResource = async (req, res, next) => {
    // --- BEGIN DEBUGGING LOGS ---
    console.log("--- Inside createResource Controller ---");
    console.log("Received req.body from multer (text fields):", JSON.stringify(req.body, null, 2));
    console.log("Received req.file from multer (file details):", req.file);
    // --- END DEBUGGING LOGS ---

    try {
        // Note: Multer populates req.body with text fields and req.file with file info.
        // Field names in req.body will match the names used in your form-data (-F "name=value").
        const title = req.body.title;
        const resourceType = req.body.resource_type; // Matches -F "resource_type=file"
        const description = req.body.description;
        const semesterTag = req.body.semester_tag;
        const category = req.body.category;
        const tagsString = req.body.tags; // e.g., "c,programming,notes"
        const linkUrl = req.body.link_url;

        const uploaderId = req.user?.id; // Assuming JWT auth middleware adds 'user' to req

        if (!uploaderId) {
            // This check will likely be hit if your tempAuthMiddleware is not setting req.user.id
            // or if real auth middleware is missing/failing.
            console.error("Uploader ID missing from req.user. Ensure auth middleware is working.");
            return res.status(401).json({ status: 'fail', message: 'User not authenticated for upload.' });
        }

        if (resourceType === 'file' && !req.file) {
            return res.status(400).json({ status: 'fail', message: 'File is required for resource type "file".' });
        }
        if (!resourceType) { // Explicit check if resourceType itself is missing from parsed body
            return res.status(400).json({ status: 'fail', message: 'resource_type field is missing from request.' });
        }


        let fileDetails = {};
        if (resourceType === 'file' && req.file) {
            fileDetails = {
                filePath: req.file.filename, 
                originalFilename: req.file.originalname,
                fileSize: req.file.size,
                mimeType: req.file.mimetype
            };
        }

        const resourceData = {
            title,
            uploaderId,
            resourceType,
            description,
            semesterTag,
            category,
            tags: tagsString ? (Array.isArray(tagsString) ? tagsString : tagsString.split(',').map(tag => tag.trim())) : [],
            linkUrl: resourceType === 'link' ? linkUrl : undefined,
            ...fileDetails
        };
        
        console.log("Data prepared for Mongoose model:", JSON.stringify(resourceData, null, 2));

        const newResource = new Resource(resourceData);
        await newResource.save();
        
        const resourceResponse = newResource.toJSON ? newResource.toJSON() : newResource.toObject();

        res.status(201).json({
            status: 'success',
            data: { resource: resourceResponse }
        });
    } catch (error) {
        console.error("Error in createResource controller:", error);
        if (error.code === 'LIMIT_FILE_SIZE' || (error.message && error.message.includes('File type not allowed'))) {
            return res.status(400).json({ status: 'fail', message: error.message });
        }
        if (error.name === 'ValidationError') {
            const messages = Object.values(error.errors).map(val => val.message);
            return res.status(400).json({ status: 'fail', message: messages.join(', ') });
        }
        // Fallback for other errors
        res.status(500).json({ status: 'error', message: 'Failed to create resource.', details: error.message });
    }
};

exports.getAllResources = async (req, res, next) => {
    try {
        const { page = 1, limit = 10, semester, category, searchQuery, sortBy = 'newest' } = req.query;
        const queryOptions = {};
        if (semester && semester !== 'all') queryOptions.semesterTag = semester;
        if (category) queryOptions.category = category;

        if (searchQuery && searchQuery.trim()) {
            queryOptions.$text = { $search: searchQuery.trim() };
        }
        
        const skip = (parseInt(page) - 1) * parseInt(limit);
        const resources = await Resource.find(queryOptions)
            .sort(sortBy === 'oldest' ? { createdAt: 1 } : sortBy === 'downloads' ? { downloadCount: -1 } : { createdAt: -1 })
            .skip(skip)
            .limit(parseInt(limit))
            // .populate('uploaderId', 'name usn'); 

        const totalResources = await Resource.countDocuments(queryOptions);
        const totalPages = Math.ceil(totalResources / parseInt(limit));

        res.status(200).json({
            status: 'success',
            data: resources.map(r => r.toJSON ? r.toJSON() : r.toObject()),
            pagination: {
                total_items: totalResources, total_pages: totalPages,
                current_page: parseInt(page), per_page: parseInt(limit),
                filters: { semester, category, searchQuery }, sort_by: sortBy
            }
        });
    } catch (error) {
        console.error("Error fetching resources:", error);
        res.status(500).json({ status: 'error', message: 'Failed to retrieve resources.' });
    }
};
    
exports.getResourceById = async (req, res, next) => {
    try {
        const resource = await Resource.findById(req.params.resourceId);
        if (!resource) {
            return res.status(404).json({ status: 'fail', message: 'Resource not found.' });
        }
        res.status(200).json({ status: 'success', data: { resource: resource.toJSON ? resource.toJSON() : resource.toObject() } });
    } catch (error) {
        if (error.name === 'CastError') {
             return res.status(400).json({ status: 'fail', message: 'Invalid resource ID format.' });
        }
        console.error("Error fetching resource by ID:", error);
        res.status(500).json({ status: 'error', message: 'Failed to retrieve resource.' });
    }
};

exports.downloadResourceFile = async (req, res, next) => {
    try {
        const resource = await Resource.findById(req.params.resourceId);
        if (!resource || resource.resourceType !== 'file' || !resource.filePath) {
            return res.status(404).json({ status: 'fail', message: 'File resource not found or invalid.' });
        }
        const filePathOnServer = path.join(FULL_UPLOAD_PATH, resource.filePath);
        if (!fs.existsSync(filePathOnServer)) {
            console.error(`File not found on disk for download: ${filePathOnServer}`);
            return res.status(404).json({ status: 'error', message: 'File not found on server.' });
        }
        resource.downloadCount += 1;
        await resource.save();
        console.log(`Attempting to send file: ${filePathOnServer} as ${resource.originalFilename}`);
        res.download(filePathOnServer, resource.originalFilename, (err) => {
            if (err) {
                console.error("Error during res.download:", err);
                if (!res.headersSent) {
                     res.status(500).json({ status: 'error', message: 'Could not download file.' });
                }
            }
        });
    } catch (error) {
         if (error.name === 'CastError') {
             return res.status(400).json({ status: 'fail', message: 'Invalid resource ID format.' });
        }
        console.error("Error downloading resource file:", error);
        if (!res.headersSent) {
            res.status(500).json({ status: 'error', message: 'Failed to download resource file.' });
        }
    }
};

exports.deleteResource = async (req, res, next) => {
    try {
        const resourceId = req.params.resourceId;
        const uploaderId = req.user?.id;
        const resource = await Resource.findById(resourceId);
        if (!resource) {
            return res.status(404).json({ status: 'fail', message: 'Resource not found.' });
        }
        if (resource.uploaderId.toString() !== uploaderId) { // Add admin role check later
            return res.status(403).json({ status: 'fail', message: 'You are not authorized to delete this resource.' });
        }
        if (resource.resourceType === 'file' && resource.filePath) {
            const filePathOnServer = path.join(FULL_UPLOAD_PATH, resource.filePath);
            if (fs.existsSync(filePathOnServer)) {
                fs.unlinkSync(filePathOnServer);
                console.log(`Deleted file from disk: ${filePathOnServer}`);
            } else {
                console.warn(`File not found on disk for deletion: ${filePathOnServer}`);
            }
        }
        await Resource.findByIdAndDelete(resourceId);
        res.status(200).json({ status: 'success', message: 'Resource deleted successfully.' });
    } catch (error) {
        if (error.name === 'CastError') {
             return res.status(400).json({ status: 'fail', message: 'Invalid resource ID format.' });
        }
        console.error("Error deleting resource:", error);
        res.status(500).json({ status: 'error', message: 'Failed to delete resource.' });
    }
};