# app/routes/content_routes.py
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required # Assuming these might be protected later

content_bp = Blueprint('content_bp', __name__)

@content_bp.route('/announcements/proctor', methods=['GET'])
@jwt_required() # Let's assume proctor announcements require login
def get_proctor_announcements():
    current_app.logger.info("Accessed GET /announcements/proctor (demo)")
    # In a real implementation, you'd fetch this from a database
    demo_announcements = [
        {
            "id": "anno1",
            "title": "Upcoming CIE Schedule Revision",
            "message": "Please note that the CIE schedule for 6th semester has been revised. Check the notice board.",
            "postedDate": "2024-05-30T10:00:00Z", # ISO 8601 format
            "postedBy": "Dr. Proctor Smith"
        },
        {
            "id": "anno2",
            "title": "Holiday Declaration",
            "message": "The college will remain closed on 2024-06-05 on account of a public holiday.",
            "postedDate": "2024-05-28T15:30:00Z",
            "postedBy": "College Admin"
        }
    ]
    return jsonify({"status": "success", "data": demo_announcements}), 200

@content_bp.route('/content/clubs', methods=['GET'])
@jwt_required() # Assuming club info requires login
def get_college_clubs():
    current_app.logger.info("Accessed GET /content/clubs (demo)")
    demo_clubs = [
        {
            "id": "club1",
            "name": "Coding Mavericks",
            "iconUrl": "https://example.com/icons/coding_mavericks.png", # Or an iconName like 'code-slash'
            "description": "The official coding club of MSRIT. Conducts hackathons, workshops, and coding competitions.",
            "contactEmail": "codingclub@msrit.edu",
            "link": "https://msrit-coding-mavericks.example.com"
        },
        {
            "id": "club2",
            "name": "Literary Society 'Expressions'",
            "iconUrl": "https://example.com/icons/literary_society.png",
            "description": "For all the bookworms and wordsmiths. Debates, poetry slams, and more.",
            "contactEmail": "literaryclub@msrit.edu",
            "link": None # Can be null if no external link
        },
        {
            "id": "club3",
            "name": "Robotics Club 'MechAzure'",
            "iconUrl": "https://example.com/icons/robotics.png",
            "description": "Build and battle robots! Workshops on Arduino, Raspberry Pi, and more.",
            "contactEmail": "roboticsclub@msrit.edu",
            "link": "https://robotics-mechazure.example.com"
        }
    ]
    return jsonify({"status": "success", "data": demo_clubs}), 200

@content_bp.route('/content/academics-links', methods=['GET'])
@jwt_required() # Assuming academic links require login
def get_academic_links():
    current_app.logger.info("Accessed GET /content/academics-links (demo)")
    demo_links = [
        {
            "id": "link1",
            "name": "VTU Results Portal",
            "iconName": "graduation-cap", # Example FontAwesome icon name
            "url": "https://results.vtu.ac.in",
            "description": "Official Visvesvaraya Technological University results website."
        },
        {
            "id": "link2",
            "name": "MSRIT Library",
            "iconName": "book-open",
            "url": "https://msritlibrary.example.com", # Replace with actual if known
            "description": "Access digital resources, catalogs, and library services."
        },
        {
            "id": "link3",
            "name": "Syllabus Repository",
            "iconName": "file-alt",
            "url": "https://msrit-syllabus.example.com/cs", # Replace
            "description": "Download official syllabus copies for all departments."
        }
    ]
    return jsonify({"status": "success", "data": demo_links}), 200