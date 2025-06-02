// node_service/tests/resource.test.js
const request = require('supertest');
const app = require('../src/app'); 
const mongoose = require('mongoose');
const Resource = require('../src/models/Resource');
const path = require('path');
const fs = require('fs');
const { FULL_UPLOAD_PATH } = require('../src/middleware/uploadMiddleware');

// This MOCK_USER_ID MUST match the one used in your tempAuthMiddleware if you are still using it,
// OR it should be the ID of a user for whom you can generate a valid test JWT.
// For now, matching the hardcoded ID in tempAuthMiddleware if that's still in use.
const MOCK_USER_ID_STRING = "683c2cc89c8c284ebb0eb0c3"; // The ID from your tempAuthMiddleware

// Mocking the auth middleware for these tests
// This mock will apply to all tests in this file.
jest.mock('../src/middleware/forwardAuthHeader', () => (req, res, next) => { // Or your actual Node auth middleware
    req.user = { id: MOCK_USER_ID_STRING }; 
    req.flaskHeaders = { 'Content-Type': req.headers['content-type'] || 'application/json' };
    // console.log("Mocked auth middleware called, req.user set to:", req.user);
    next();
});


describe('Resources API (/api/v1/resources)', () => {
    const testFileName = 'supertest_upload_notes.pdf';
    const testFilePath = path.join(__dirname, testFileName); // Creates dummy file in tests/ dir

    beforeAll(() => {
        if (!fs.existsSync(testFilePath)) {
            fs.writeFileSync(testFilePath, 'This is dummy PDF content for supertest.');
        }
    });

    afterAll(() => {
        if (fs.existsSync(testFilePath)) {
            fs.unlinkSync(testFilePath);
        }
    });
    
    // Helper function to create a resource for tests that need one
    const createTestFileResource = async () => {
        const response = await request(app)
            .post('/api/v1/resources')
            .field('title', `Test File - ${Date.now()}`) // Unique title
            .field('resource_type', 'file')
            .field('category', 'test-fixture')
            .field('description', 'Temporary file for testing.')
            .attach('resourceFile', testFilePath);
        expect(response.statusCode).toBe(201);
        return response.body.data.resource;
    };


    it('should upload a file resource successfully', async () => {
        const response = await request(app)
            .post('/api/v1/resources')
            .field('title', 'Supertest File Notes')
            .field('resource_type', 'file')
            .field('category', 'test-notes')
            .field('semester_tag', 'SemTest')
            .field('description', 'Uploaded via Supertest')
            .field('tags', 'supertest,file,pdf')
            .attach('resourceFile', testFilePath);

        expect(response.statusCode).toBe(201);
        expect(response.body.status).toBe('success');
        const resource = response.body.data.resource;
        expect(resource).toHaveProperty('id');
        expect(resource.title).toBe('Supertest File Notes');
        expect(resource.resourceType).toBe('file');
        expect(resource.originalFilename).toBe(testFileName);
        expect(resource.uploaderId).toBe(MOCK_USER_ID_STRING); // Check against the corrected MOCK_USER_ID

        const uploadedFilePath = path.join(FULL_UPLOAD_PATH, resource.filePath);
        expect(fs.existsSync(uploadedFilePath)).toBe(true);
        // Clean up this specific file after test
        if (fs.existsSync(uploadedFilePath)) fs.unlinkSync(uploadedFilePath);
    });

    it('should create a link resource successfully', async () => {
        const response = await request(app)
            .post('/api/v1/resources')
            .field('title', 'Supertest Link Resource')
            .field('resource_type', 'link')
            .field('link_url', 'https://jestjs.io')
            .field('category', 'testing-tool')
            .field('description', 'Jest testing framework official site.');
            
        expect(response.statusCode).toBe(201);
        expect(response.body.status).toBe('success');
        const resource = response.body.data.resource;
        expect(resource).toHaveProperty('id');
        expect(resource.title).toBe('Supertest Link Resource');
        expect(resource.resourceType).toBe('link');
        expect(resource.linkUrl).toBe('https://jestjs.io');
        expect(resource.uploaderId).toBe(MOCK_USER_ID_STRING);
    });

    it('should list resources, including newly created ones', async () => {
        // Create a resource to ensure list is not empty for this test
        const tempResource = await createTestFileResource();

        const response = await request(app)
            .get('/api/v1/resources')
            .query({ category: 'test-fixture' }); // Filter for our test resource

        expect(response.statusCode).toBe(200);
        expect(response.body.status).toBe('success');
        expect(response.body.data.length).toBeGreaterThanOrEqual(1);
        const foundResource = response.body.data.find(r => r.id === tempResource.id);
        expect(foundResource).toBeDefined();
        expect(foundResource.title).toBe(tempResource.title);
    });

    it('should get a specific resource by ID', async () => {
        const tempResource = await createTestFileResource(); // Create resource for this test

        const response = await request(app)
            .get(`/api/v1/resources/${tempResource.id}`);
        
        expect(response.statusCode).toBe(200);
        expect(response.body.status).toBe('success');
        expect(response.body.data.resource.id).toBe(tempResource.id);
        expect(response.body.data.resource.title).toBe(tempResource.title);
    });

    it('should download a file resource', async () => {
        const tempResource = await createTestFileResource(); // Create resource for this test
        const originalFilenameForDownload = tempResource.originalFilename;

        const response = await request(app)
            .get(`/api/v1/resources/${tempResource.id}/download`);

        expect(response.statusCode).toBe(200);
        // Supertest might not give exact filename match with space, check for part of it
        expect(response.headers['content-disposition']).toContain(`attachment; filename="${originalFilenameForDownload}"`);
        expect(response.body.toString()).toContain('This is dummy PDF content for supertest.');
        
        const detailResponse = await request(app).get(`/api/v1/resources/${tempResource.id}`);
        expect(detailResponse.body.data.resource.downloadCount).toBe(1);
    });
    
    it('should delete a resource', async () => {
        const tempResource = await createTestFileResource(); // Create resource for this test
        const filePathOnDisk = path.join(FULL_UPLOAD_PATH, tempResource.filePath);

        const response = await request(app)
            .delete(`/api/v1/resources/${tempResource.id}`);
        
        expect(response.statusCode).toBe(200);
        expect(response.body.status).toBe('success');
        expect(response.body.message).toBe('Resource deleted successfully.');

        const deletedResource = await Resource.findById(tempResource.id);
        expect(deletedResource).toBeNull();
        expect(fs.existsSync(filePathOnDisk)).toBe(false); // Verify file deleted from disk
    });

    it('should return 400 for non-existent resource download if ID format invalid', async () => {
        const response = await request(app)
            .get(`/api/v1/resources/invalidObjectIdFormat123/download`);
        expect(response.statusCode).toBe(400);
        expect(response.body.status).toBe('fail');
        expect(response.body.message).toContain('Invalid resource ID format');
    });

    it('should return 404 for non-existent resource download if ID format valid but not found', async () => {
        const fakeValidObjectId = new mongoose.Types.ObjectId().toString();
        const response = await request(app)
            .get(`/api/v1/resources/${fakeValidObjectId}/download`);
        expect(response.statusCode).toBe(404);
        expect(response.body.status).toBe('fail');
        expect(response.body.message).toContain('File resource not found or invalid');
    });

});