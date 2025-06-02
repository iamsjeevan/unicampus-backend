// node_service/src/models/Resource.js
const mongoose = require('mongoose');
const path = require('path'); 

const RESOURCE_UPLOAD_SUBDIR = process.env.RESOURCE_UPLOAD_SUBDIR || 'node_resources';

const resourceSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Resource title is required.'],
    trim: true,
    minlength: [3, 'Title must be at least 3 characters long.']
  },
  uploaderId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User', 
    required: [true, 'Uploader ID is required.']
  },
  resourceType: { 
    type: String,
    required: true,
    enum: ['file', 'link']
  },
  semesterTag: { 
    type: String,
    trim: true,
  },
  category: { 
    type: String,
    trim: true,
    required: [true, 'Category is required.']
  },
  description: {
    type: String,
    trim: true,
    maxlength: [1000, 'Description cannot exceed 1000 characters.']
  },
  tags: [{ 
    type: String,
    trim: true,
    lowercase: true
  }],
  filePath: { 
    type: String,
    required: function() { return this.resourceType === 'file'; }
  },
  originalFilename: {
    type: String,
    required: function() { return this.resourceType === 'file'; }
  },
  fileSize: { 
    type: Number,
    required: function() { return this.resourceType === 'file'; }
  },
  mimeType: { 
    type: String,
    required: function() { return this.resourceType === 'file'; }
  },
  linkUrl: {
    type: String,
    trim: true,
    required: function() { return this.resourceType === 'link'; },
    match: [/^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/, 'Please fill a valid URL']
  },
  downloadCount: {
    type: Number,
    default: 0
  },
}, {
  timestamps: true 
});

resourceSchema.set('toJSON', {
  virtuals: true,
  versionKey: false,
  transform: function (doc, ret) {
    ret.id = ret._id;
    delete ret._id;
    if (ret.resourceType === 'file' && ret.filePath) {
        ret.downloadUrl = `/api/v1/resources/${ret.id}/download`;
    } else if (ret.resourceType === 'link' && ret.linkUrl) {
        ret.downloadUrl = ret.linkUrl;
    }
  }
});

resourceSchema.index({
    title: 'text', description: 'text', tags: 'text',
    originalFilename: 'text', category: 'text', semesterTag: 'text'
});

const Resource = mongoose.model('Resource', resourceSchema);

module.exports = Resource;