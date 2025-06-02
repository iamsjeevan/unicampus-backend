from flask import Blueprint, request, jsonify, current_app
from app.models.user import User
from app.services.college_portal_scraper import scrape_and_parse_college_data
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth_bp', __name__)

def format_user_for_login_response(user_doc):
    if not user_doc: return None
    return {
        "id": str(user_doc["_id"]),
        "usn": user_doc.get("usn"),
        "name": user_doc.get("name"),
        "email": user_doc.get("email"),
        "role": user_doc.get("role"),
        "collegeProfile": user_doc.get("college_profile"),
        "mostRecentCGPA": user_doc.get("most_recent_cgpa"),
        "avatar": user_doc.get("avatar"),
    }

@auth_bp.route('/login/student', methods=['POST'])
def login_student():
    data = request.get_json()
    if not data or not all(k in data for k in ['usn', 'dob_dd', 'dob_mm', 'dob_yyyy']):
        return jsonify({"status": "fail", "message": "USN and full Date of Birth (dob_dd, dob_mm, dob_yyyy) are required."}), 400

    usn = data['usn'].strip().upper()
    dob_dd = str(data['dob_dd']) # Ensure string for zfill
    dob_mm = str(data['dob_mm']) # Ensure string for zfill
    dob_yyyy = str(data['dob_yyyy'])

    current_app.logger.info(f"Login attempt for USN: {usn}")

    scraped_college_data, scrape_success = scrape_and_parse_college_data(usn, dob_dd, dob_mm, dob_yyyy)
    error_messages = scraped_college_data.get("errorMessages", [])

    if not scrape_success:
        current_app.logger.error(f"Scraping failed for USN {usn}. Errors: {error_messages}")
        if any("Invalid username or password" in e.lower() for e in error_messages) or \
           any("user name and password do not match" in e.lower() for e in error_messages):
            final_message = "College login failed: Invalid credentials provided to the portal."
            status_code = 401
        elif any("mismatch" in e.lower() for e in error_messages):
            final_message = "College login succeeded, but USN on portal does not match provided USN."
            status_code = 403
        elif not scraped_college_data.get("studentProfile", {}).get("usn") and any("login failed" not in e.lower() for e in error_messages): # No USN but not due to login credentials
            final_message = "Failed to retrieve valid student data from the portal. The portal might be down or its structure changed."
            status_code = 502
        else:
            final_message = "Could not retrieve data from college portal."
            if error_messages: final_message += " Details: " + "; ".join(error_messages[:2])
            status_code = 503
        return jsonify({"status": "fail", "message": final_message, "debug_details": error_messages}), status_code

    current_app.logger.info(f"Scraping successful for USN {usn}. Name: {scraped_college_data.get('studentProfile',{}).get('name')}")
    app_user = User.find_by_usn(usn)

    try:
        if app_user:
            current_app.logger.info(f"Updating existing user in DB: {usn}")
            updated_user_doc = User.update_user_with_scraped_data(app_user['_id'], scraped_college_data)
            app_user = updated_user_doc
        else:
            current_app.logger.info(f"Creating new user in DB: {usn}")
            new_user_doc = User.create_user_from_scraped_data(scraped_college_data, usn) 
            app_user = new_user_doc
    except ValueError as ve:
        current_app.logger.error(f"Database ValueError for {usn}: {str(ve)}")
        return jsonify({"status":"error", "message": f"Database error: {str(ve)}"}), 409
    except Exception as e:
        current_app.logger.error(f"Database interaction error for {usn}: {str(e)}", exc_info=True)
        return jsonify({"status":"error", "message": f"Error processing user data in application database."}), 500
    
    if not app_user:
        current_app.logger.error(f"User object is None after DB ops for USN {usn}")
        return jsonify({"status":"error", "message": "Failed to process user data after successful scrape."}), 500

    user_identity = str(app_user['_id'])
    access_token = create_access_token(identity=user_identity)
    refresh_token = create_refresh_token(identity=user_identity)
    current_app.logger.info(f"Tokens generated for user {app_user.get('usn')} (ID: {user_identity})")

    return jsonify({
        "status": "success",
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "data": {"user": format_user_for_login_response(app_user)}
    }), 200

@auth_bp.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token_student():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)
    current_app.logger.info(f"Access token refreshed for user ID: {current_user_id}")
    return jsonify({"status": "success", "accessToken": new_access_token}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout_student():
    # current_user_id = get_jwt_identity() # For logging if needed
    # For stateless JWT, logout is client-side. If blocklisting, do it here.
    current_app.logger.info(f"Logout request received for user ID: {get_jwt_identity()}")
    return jsonify({"status": "success", "message": "Successfully logged out. Please discard your tokens client-side."}), 200