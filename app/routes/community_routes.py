# app/routes/community_routes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.community import Community
from app.models.post import Post 
from bson import ObjectId

community_bp = Blueprint('community_bp', __name__)

# === Community Management Routes ===
@community_bp.route('/communities', methods=['POST'])
@jwt_required()
def create_community_route():
    data = request.get_json()
    current_user_id = get_jwt_identity()
    name = data.get('name')
    description = data.get('description')
    rules = data.get('rules') 
    icon_url = data.get('icon_url')
    banner_image_url = data.get('banner_image_url')
    tags = data.get('tags')

    if not name or not description:
        return jsonify({"status": "fail", "message": "Community name and description are required."}), 400
    try:
        new_community_dict = Community.create_community(
            name=name, description=description, created_by_id=current_user_id,
            rules=rules, icon_url=icon_url, banner_image_url=banner_image_url, tags=tags
        )
        current_app.logger.info(f"Community '{new_community_dict.get('name')}' created by user {current_user_id}")
        return jsonify({"status": "success", "data": {"community": new_community_dict}}), 201
    except ValueError as ve:
        current_app.logger.warning(f"ValueError creating community: {str(ve)}")
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating community: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@community_bp.route('/communities', methods=['GET'])
@jwt_required() 
def get_communities_route():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        search_query = request.args.get('searchQuery', type=str) 
        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 100: per_page = 100
        result = Community.get_all_communities(page=page, per_page=per_page, search_query=search_query)
        return jsonify({
            "status": "success", "data": result['communities'],
            "pagination": {
                "total_items": result['total'], "total_pages": result['pages'],
                "current_page": result['page'], "per_page": result['per_page']
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching communities: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to retrieve communities."}), 500

@community_bp.route('/communities/<string:community_id_or_slug>', methods=['GET'])
@jwt_required()
def get_community_detail_route(community_id_or_slug):
    community = None
    if ObjectId.is_valid(community_id_or_slug):
        community = Community.find_by_id(community_id_or_slug)
    if not community: 
        community = Community.find_by_slug(community_id_or_slug)
    if not community:
        return jsonify({"status": "fail", "message": "Community not found."}), 404
    current_user_id = get_jwt_identity()
    community['is_member'] = Community.is_member(community['id'], current_user_id)
    return jsonify({"status": "success", "data": {"community": community}}), 200

@community_bp.route('/communities/<string:community_id>/join', methods=['POST'])
@jwt_required()
def join_community_route(community_id):
    current_user_id = get_jwt_identity()
    if not ObjectId.is_valid(community_id):
        return jsonify({"status": "fail", "message": "Invalid community ID format."}), 400
    if Community.is_member(community_id, current_user_id):
        return jsonify({"status": "fail", "message": "You are already a member of this community."}), 409
    try:
        success = Community.join_community(community_id, current_user_id)
        if success:
            current_app.logger.info(f"User {current_user_id} joined community {community_id}")
            return jsonify({"status": "success", "message": "Successfully joined the community."}), 200
        else:
            return jsonify({"status": "fail", "message": "Could not join community. It may not exist."}), 400 
    except Exception as e:
        current_app.logger.error(f"Error joining community {community_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An error occurred."}), 500

@community_bp.route('/communities/<string:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community_route(community_id):
    current_user_id = get_jwt_identity()
    if not ObjectId.is_valid(community_id):
        return jsonify({"status": "fail", "message": "Invalid community ID format."}), 400
    if not Community.is_member(community_id, current_user_id):
        return jsonify({"status": "fail", "message": "You are not a member of this community."}), 400
    try:
        success = Community.leave_community(community_id, current_user_id)
        if success:
            current_app.logger.info(f"User {current_user_id} left community {community_id}")
            return jsonify({"status": "success", "message": "Successfully left the community."}), 200
        else:
            return jsonify({"status": "fail", "message": "Could not leave community. It may not exist."}), 400
    except Exception as e:
        current_app.logger.error(f"Error leaving community {community_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An error occurred."}), 500


# === Post Management Routes ===
@community_bp.route('/communities/<string:community_id>/posts', methods=['POST'])
@jwt_required()
def create_post_in_community_route(community_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    title = data.get('title')
    content_type = data.get('content_type')
    content_text = data.get('content_text')
    image_url = data.get('image_url')
    link_url = data.get('link_url')
    tags = data.get('tags')

    if not title or not content_type:
        return jsonify({"status": "fail", "message": "Post title and content_type are required."}), 400
    # Basic validation for content based on type (can be more robust)
    if content_type == "text" and not content_text: return jsonify({"status": "fail", "message": "Text content required."}), 400
    if content_type == "image" and not image_url: return jsonify({"status": "fail", "message": "Image URL required."}), 400
    if content_type == "link" and not link_url: return jsonify({"status": "fail", "message": "Link URL required."}), 400

    try:
        new_post_dict = Post.create_post(
            community_id=community_id, author_id=current_user_id, title=title,
            content_type=content_type, content_text=content_text, image_url=image_url,
            link_url=link_url, tags=tags
        )
        current_app.logger.info(f"Post '{title}' created in C:{community_id} by U:{current_user_id}")
        return jsonify({"status": "success", "data": {"post": new_post_dict}}), 201
    except ValueError as ve:
        current_app.logger.warning(f"ValueError creating post: {str(ve)}")
        status_code = 404 if "not found" in str(ve).lower() else 400
        return jsonify({"status": "fail", "message": str(ve)}), status_code
    except Exception as e:
        current_app.logger.error(f"Error creating post in C:{community_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@community_bp.route('/communities/<string:community_id>/posts', methods=['GET'])
@jwt_required()
def get_posts_for_community_route_updated(): # Updated name to avoid redefinition if you run this incrementally
    current_user_id_str = get_jwt_identity() 
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        sort_by = request.args.get('sortBy', 'new', type=str).lower()
        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 50: per_page = 50
        if sort_by not in ['new', 'hot', 'top']: sort_by = 'new'
        
        # Use the new method that includes user's vote status
        result = Post.get_posts_for_community_for_user(
            community_id_str=community_id, 
            current_user_id_str=current_user_id_str, 
            page=page, per_page=per_page, sort_by=sort_by
        )
        return jsonify({
            "status": "success", "data": result['posts'],
            "pagination": {
                "total_items": result['total'], "total_pages": result['pages'],
                "current_page": result['page'], "per_page": result['per_page'],
                "sort_by": sort_by
            }
        }), 200
    except ValueError as ve:
        current_app.logger.warning(f"ValueError fetching posts for C:{community_id}: {str(ve)}")
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching posts for C:{community_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to retrieve posts."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['GET'])
@jwt_required()
def get_post_detail_route_updated(post_id): # Updated name
    current_user_id_str = get_jwt_identity()
    # No need to check ObjectId.is_valid here, model method will handle it
    post = Post.find_by_id_for_user(post_id, current_user_id_str) 
    if not post:
        return jsonify({"status": "fail", "message": "Post not found."}), 404
    return jsonify({"status": "success", "data": {"post": post}}), 200

# --- NEW VOTING ENDPOINT ---
@community_bp.route('/posts/<string:post_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    direction = data.get('direction')

    if not direction or direction not in ["up", "down", "none"]:
        return jsonify({"status": "fail", "message": "Invalid vote direction. Must be 'up', 'down', or 'none'."}), 400
    
    # Post ID validation is handled by the model method, which raises ValueError for invalid format
    try:
        result = Post.vote_on_post(post_id, current_user_id_str, direction)
        current_app.logger.info(f"User {current_user_id_str} voted '{direction}' on post {post_id}")
        return jsonify({
            "status": "success", 
            "message": result.get("message", "Vote processed."), # Use message from model
            "data": {
                "upvotes": result.get("upvotes"),
                "downvotes": result.get("downvotes"),
                "user_vote": result.get("user_vote") 
            }
        }), 200
    except ValueError as ve:
        current_app.logger.warning(f"ValueError voting on post {post_id}: {str(ve)}")
        status_code = 404 if "not found" in str(ve).lower() else 400
        return jsonify({"status": "fail", "message": str(ve)}), status_code
    except Exception as e:
        current_app.logger.error(f"Error voting on post {post_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred while voting."}), 500