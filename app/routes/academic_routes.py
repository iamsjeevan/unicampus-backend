# app/routes/academic_routes.py

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User # Assuming your User model is in app.models.user
from bson import ObjectId # For validating ObjectId if necessary

academic_bp = Blueprint('academic_bp', __name__)

@academic_bp.route('/results/cie', methods=['GET'])
@jwt_required()
def get_cie_results():
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        current_app.logger.warning(f"CIE results: User not found for ID {current_user_id}")
        return jsonify({"status": "error", "message": "User not found"}), 404

    # academic_summaries should contain CIE and attendance data
    cie_data = user.get("academic_summaries", [])
    
    # You can format this further if needed, or return as is
    # Example: Extracting only relevant fields for CIE
    formatted_cie_results = []
    for subject_summary in cie_data:
        formatted_cie_results.append({
            "code": subject_summary.get("code"),
            "name": subject_summary.get("name"),
            "cieTotal": subject_summary.get("cieTotal")
            # Add other fields if your frontend expects them for CIE display
        })
    
    current_app.logger.info(f"CIE results retrieved for user {user.get('usn')}")
    return jsonify({
        "status": "success",
        "data": {
            "subjects": formatted_cie_results 
            # Or simply: "subjects": cie_data if no specific formatting is needed
        }
    }), 200

@academic_bp.route('/results/see', methods=['GET'])
@jwt_required()
def get_see_results():
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        current_app.logger.warning(f"SEE results: User not found for ID {current_user_id}")
        return jsonify({"status": "error", "message": "User not found"}), 404

    see_data = {
        "mostRecentCGPA": user.get("most_recent_cgpa"),
        "semesters": user.get("exam_history", []) # This is the list of semester results
    }
    
    current_app.logger.info(f"SEE results retrieved for user {user.get('usn')}")
    return jsonify({"status": "success", "data": see_data}), 200

@academic_bp.route('/attendance/summary', methods=['GET'])
@jwt_required()
def get_attendance_summary():
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        current_app.logger.warning(f"Attendance summary: User not found for ID {current_user_id}")
        return jsonify({"status": "error", "message": "User not found"}), 404

    # academic_summaries should contain CIE and attendance data
    attendance_data = user.get("academic_summaries", [])

    # Example: Extracting only relevant fields for attendance
    formatted_attendance_summary = []
    for subject_summary in attendance_data:
        formatted_attendance_summary.append({
            "code": subject_summary.get("code"),
            "name": subject_summary.get("name"),
            "attendancePercentage": subject_summary.get("attendancePercentage")
            # Add color or other frontend-specific hints if desired
        })
        
    current_app.logger.info(f"Attendance summary retrieved for user {user.get('usn')}")
    return jsonify({
        "status": "success",
        "data": {
            "subjects": formatted_attendance_summary
            # Or simply: "subjects": attendance_data
        }
    }), 200