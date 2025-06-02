// node_service/src/middleware/uploadMiddleware.js
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const UPLOAD_DIR_NAME = process.env.RESOURCE_UPLOAD_SUBDIR || 'node_resources';
const UPLOAD_BASE_PATH = path.resolve(__dirname, '..', '..', 'uploads');
const FULL_UPLOAD_PATH = path.join(UPLOAD_BASE_PATH, UPLOAD_DIR_NAME);

if (!fs.existsSync(FULL_UPLOAD_PATH)) {
    fs.mkdirSync(FULL_UPLOAD_PATH, { recursive: true });
    console.log(`Created upload directory: ${FULL_UPLOAD_PATH}`);
}

const ALLOWED_EXTENSIONS = new Set(['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx', 'xls', 'xlsx', 'zip', 'png', 'jpg', 'jpeg', 'gif']);
const MAX_FILE_SIZE_MB = 10; 

const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, FULL_UPLOAD_PATH);
    },
    filename: function (req, file, cb) {
        const uniqueSuffix = uuidv4();
        const extension = path.extname(file.originalname).toLowerCase();
        cb(null, `${uniqueSuffix}${extension}`);
    }
});

const fileFilter = (req, file, cb) => {
    const extension = path.extname(file.originalname).substring(1).toLowerCase();
    if (ALLOWED_EXTENSIONS.has(extension)) {
        cb(null, true);
    } else {
        cb(new Error('Error: File type not allowed! Allowed: ' + Array.from(ALLOWED_EXTENSIONS).join(', ')), false);
    }
};

const upload = multer({
    storage: storage,
    fileFilter: fileFilter,
    limits: {
        fileSize: MAX_FILE_SIZE_MB * 1024 * 1024
    }
});

module.exports = { upload, FULL_UPLOAD_PATH, UPLOAD_DIR_NAME };