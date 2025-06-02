// node_service/tests/setupTests.js
const path = require('path');
const dotenv = require('dotenv'); // Make sure dotenv is a devDependency or dependency

// Load the .env file from the root of node_service for tests
// This should be the first thing to ensure process.env variables are set before app/DB init
const envPath = path.resolve(__dirname, '..', '.env');
const envConfig = dotenv.config({ path: envPath });

if (envConfig.error) {
  console.warn(`Warning: Could not load .env file from ${envPath}. Tests might fail if ENV VARS are not set externally.`);
} else {
  console.log(`Successfully loaded .env file from ${envPath} for tests.`);
}


const mongoose = require('mongoose');

// Use a specific TEST database URI from .env or fallback
// It's highly recommended to use a different database for testing.
const jestMongoUri = process.env.TEST_RESOURCES_MONGO_URI || process.env.RESOURCES_MONGO_URI || 'mongodb://localhost:27017/unicampus_resources_jest_test_db_fallback';

if (!process.env.TEST_RESOURCES_MONGO_URI && !process.env.RESOURCES_MONGO_URI) {
    console.warn(`WARNING: Neither TEST_RESOURCES_MONGO_URI nor RESOURCES_MONGO_URI found in environment. Using fallback: ${jestMongoUri}`);
}


beforeAll(async () => {
    if (mongoose.connection.readyState === 0) { // 0 = disconnected
        try {
            await mongoose.connect(jestMongoUri);
            const dbNameForLog = jestMongoUri.includes('@') ? jestMongoUri.substring(jestMongoUri.lastIndexOf('@') + 1) : jestMongoUri;
            console.log(`Jest: Connected to MongoDB for Resources tests at: ${dbNameForLog}`);
        } catch (err) {
            console.error('Jest: Test MongoDB connection error:', err.message);
            console.error('Attempted URI:', jestMongoUri.replace(/:([^@:\/]+)@/, ':********@')); // Mask password
            process.exit(1); // Fail fast if DB connection fails
        }
    }
});

// Clean up the test database (relevant collections) after each test
afterEach(async () => {
    if (mongoose.connection.readyState === 1) { // 1 = connected
        const collections = mongoose.connection.collections;
        for (const key in collections) {
            // Be more specific about which collections to clear if sharing DB
            if (key === 'resources' || key === 'users_for_test_only') { // Example
                 const collection = collections[key];
                 await collection.deleteMany({});
            }
        }
        // If you are certain this DB is ONLY for these tests, you can clear all:
        // for (const key in collections) {
        //     const collection = collections[key];
        //     await collection.deleteMany({});
        // }
    }
});

// After all tests are done, disconnect from Mongoose
afterAll(async () => {
    if (mongoose.connection.readyState === 1) {
        await mongoose.connection.dropDatabase(); // Drops the entire test database
        await mongoose.disconnect();
        console.log('Jest: Disconnected from Test MongoDB and dropped test database.');
    }
});