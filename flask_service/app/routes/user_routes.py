from flask import Blueprint, request, jsonify, current_app
from app.models.user import User
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    if not ObjectId.is_valid(current_user_id):
        current_app.logger.warning(f"/me GET: Invalid user ID format in token: {current_user_id}")
        return jsonify({"status": "error", "message": "Invalid user ID format in token"}), 400
        
    user_doc = User.find_by_id(current_user_id)
    if not user_doc:
        current_app.logger.warning(f"/me GET: User not found for ID: {current_user_id}")
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    current_app.logger.info(f"/me GET: Successfully retrieved profile for user ID: {current_user_id}")
    return jsonify({
        "status": "success",
        "data": {"user": User.to_dict(user_doc)}
    }), 200

@user_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    current_user_id = get_jwt_identity()
    if not ObjectId.is_valid(current_user_id):
        current_app.logger.warning(f"/me PUT: Invalid user ID format in token: {current_user_id}")
        return jsonify({"status": "error", "message": "Invalid user ID format in token"}), 400

    data = request.get_json()
    if not data:
        current_app.logger.warning(f"/me PUT: Empty request body for user ID: {current_user_id}")
        return jsonify({"status": "error", "message": "Request body cannot be empty"}), 400

    allowed_updates = {"avatar", "name"} 
    update_payload = {key: data[key] for key in data if key in allowed_updates}

    if not update_payload:
        current_app.logger.warning(f"/me PUT: No valid fields to update for user ID: {current_user_id}. Payload: {data}")
        return jsonify({"status": "error", "message": "No valid fields to update provided"}), 400
    
    if any(key in update_payload for key in ['email', 'usn', 'role']): # Defensive check
        current_app.logger.warning(f"/me PUT: Attempt to update restricted field for user ID: {current_user_id}. Payload: {update_payload}")
        return jsonify({"status":"error", "message": "Cannot update email, USN or role via this endpoint"}), 403

    success = User.update_profile(current_user_id, update_payload)

    if success:
        updated_user_doc = User.find_by_id(current_user_id)
        current_app.logger.info(f"/me PUT: Profile updated successfully for user ID: {current_user_id}")
        return jsonify({
            "status": "success",
            "message": "User profile updated successfully",
            "data": {"user": User.to_dict(updated_user_doc)}
        }), 200
    else:
        # This branch should ideally not be hit if update_payload is validated and DB is responsive
        current_app.logger.error(f"/me PUT: Profile update failed unexpectedly for user ID: {current_user_id}")
        return jsonify({"status": "error", "message": "Profile update failed or no changes made"}), 400
    
@user_bp.route('/me/fees', methods=['GET'])
@jwt_required()
def get_user_fees_status():
    current_user_id = get_jwt_identity() # We have the user context
    # In a real scenario, you'd fetch this data based on current_user_id
    # or it would be part of the main user document if scraped/synced.
    # For now, it's a demo.
    current_app.logger.info(f"Accessed GET /users/me/fees (demo) for user {current_user_id}")

    # Placeholder data - this would ideally come from a dedicated fees scrape or admin input
    demo_fees_status = {
        "status": "Paid", # Could be "Due", "Partially Paid"
        "amountDue": 0.00,
        "dueDate": None, # Or an actual date string if due, e.g., "2024-07-15"
        "lastPaymentDate": "2024-01-10",
        "totalFees": 150000.00,
        "paidAmount": 150000.00,
        "paymentHistoryLink": "https://parents.msrit.edu/newparents/index.php?option=com_fees", # Example link
        "remarks": "All dues cleared for the current academic year."
    }
    return jsonify({"status": "success", "data": demo_fees_status}), 200