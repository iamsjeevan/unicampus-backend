// node_service/jest.config.js
module.exports = {
  testEnvironment: 'node', // Use Node.js environment for backend tests
  setupFilesAfterEnv: ['./tests/setupTests.js'], // Optional: for global setup/teardown
  // preset: '@shelf/jest-mongodb', // If using jest-mongodb for in-memory DB
  // watchPathIgnorePatterns: ['globalConfig'], // For jest-mongodb if used
  verbose: true,
  // Automatically clear mock calls and instances between every test
  clearMocks: true,
  // Coverage reporting
  collectCoverage: true,
  coverageDirectory: "coverage",
  coverageReporters: ["json", "lcov", "text", "clover"],
  collectCoverageFrom: [
    "src/**/*.js", // Files to include in coverage
    "!src/config/**",
    "!src/app.js",    // Usually less logic here
    "!server.js",     // Entry point
    "!src/middleware/uploadMiddleware.js" // Multer setup might be harder to unit test simply
  ],
  // You might need to transform code if using ES6 modules not natively supported by your Node version in Jest
  // transform: {
  //   '^.+\\.js$': 'babel-jest', // If using Babel
  // },
};