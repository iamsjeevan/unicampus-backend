# app/routes/community_routes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.community import Community
# from app.models.user import User # Not directly used here but good to have if needed for user validation
from bson import ObjectId # For ObjectId.is_valid checks
from app.models.post import Post # <-- IMPORT Post MODEL
community_bp = Blueprint('community_bp', __name__)

# POST /api/v1/communities (Create a new community)
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
            name=name, 
            description=description, 
            created_by_id=current_user_id,
            rules=rules,
            icon_url=icon_url,
            banner_image_url=banner_image_url,
            tags=tags
        )
        current_app.logger.info(f"Community '{new_community_dict.get('name')}' created by user {current_user_id}")
        return jsonify({"status": "success", "data": {"community": new_community_dict}}), 201
    except ValueError as ve: # Catch specific errors from the model
        current_app.logger.warning(f"ValueError creating community: {str(ve)}")
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Return model's error message
    except Exception as e:
        current_app.logger.error(f"Error creating community: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred while creating the community."}), 500

# GET /api/v1/communities (List all communities with pagination and search)
@community_bp.route('/communities', methods=['GET'])
@jwt_required() 
def get_communities_route():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        # Ensure searchQuery is treated as string, default to None if missing
        search_query = request.args.get('searchQuery', type=str) 
        
        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 100: per_page = 100

        result = Community.get_all_communities(page=page, per_page=per_page, search_query=search_query)
        
        return jsonify({
            "status": "success",
            "data": result['communities'],
            "pagination": {
                "total_items": result['total'],
                "total_pages": result['pages'],
                "current_page": result['page'],
                "per_page": result['per_page']
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching communities: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to retrieve communities."}), 500

# GET /api/v1/communities/{communityIdOrSlug} (Get a single community details)
@community_bp.route('/communities/<string:community_id_or_slug>', methods=['GET'])
@jwt_required()
def get_community_detail_route(community_id_or_slug):
    community = None
    # Try to interpret as ObjectId first
    if ObjectId.is_valid(community_id_or_slug):
        community = Community.find_by_id(community_id_or_slug)
    
    # If not found by ID (or it wasn't a valid ObjectId), try by slug
    if not community: 
        community = Community.find_by_slug(community_id_or_slug)

    if not community:
        return jsonify({"status": "fail", "message": "Community not found."}), 404
    
    current_user_id = get_jwt_identity()
    community['is_member'] = Community.is_member(community['id'], current_user_id)

    return jsonify({"status": "success", "data": {"community": community}}), 200

# POST /api/v1/communities/{communityId}/join
@community_bp.route('/communities/<string:community_id>/join', methods=['POST'])
@jwt_required()
def join_community_route(community_id):
    current_user_id = get_jwt_identity()
    
    if not ObjectId.is_valid(community_id):
        return jsonify({"status": "fail", "message": "Invalid community ID format."}), 400

    # No need to fetch community first if is_member and join_community handle "not found"
    # community = Community.find_by_id(community_id) 
    # if not community:
    #     return jsonify({"status": "fail", "message": "Community not found."}), 404

    if Community.is_member(community_id, current_user_id):
        return jsonify({"status": "fail", "message": "You are already a member of this community."}), 409

    try:
        success = Community.join_community(community_id, current_user_id)
        if success:
            current_app.logger.info(f"User {current_user_id} joined community {community_id}")
            return jsonify({"status": "success", "message": "Successfully joined the community."}), 200
        else:
            # This case means community not found or user was already member (handled by robust model method)
            return jsonify({"status": "fail", "message": "Could not join community. It may not exist or you are already a member."}), 400 
    except Exception as e:
        current_app.logger.error(f"Error joining community {community_id} for user {current_user_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An error occurred while trying to join the community."}), 500

# POST /api/v1/communities/{communityId}/leave
@community_bp.route('/communities/<string:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community_route(community_id):
    current_user_id = get_jwt_identity()

    if not ObjectId.is_valid(community_id):
        return jsonify({"status": "fail", "message": "Invalid community ID format."}), 400

    # community = Community.find_by_id(community_id) # Not strictly needed if model methods handle it
    # if not community:
    #     return jsonify({"status": "fail", "message": "Community not found."}), 404

    if not Community.is_member(community_id, current_user_id):
        return jsonify({"status": "fail", "message": "You are not a member of this community."}), 400

    try:
        success = Community.leave_community(community_id, current_user_id)
        if success:
            current_app.logger.info(f"User {current_user_id} left community {community_id}")
            return jsonify({"status": "success", "message": "Successfully left the community."}), 200
        else:
            return jsonify({"status": "fail", "message": "Could not leave community. It may not exist or you were not a member."}), 400
    except Exception as e:
        current_app.logger.error(f"Error leaving community {community_id} for user {current_user_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An error occurred while trying to leave the community."}), 500
@community_bp.route('/communities/<string:community_id>/posts', methods=['POST'])
@jwt_required()
def create_post_in_community_route(community_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()

    title = data.get('title')
    content_type = data.get('content_type') # "text", "image", or "link"
    content_text = data.get('content_text')
    image_url = data.get('image_url')
    link_url = data.get('link_url')
    tags = data.get('tags') # Optional list of strings

    if not title or not content_type:
        return jsonify({"status": "fail", "message": "Post title and content_type are required."}), 400

    # Basic validation for content based on type
    if content_type == "text" and not content_text:
        return jsonify({"status": "fail", "message": "Text content is required for a text post."}), 400
    if content_type == "image" and not image_url:
        return jsonify({"status": "fail", "message": "Image URL is required for an image post."}), 400
    if content_type == "link" and not link_url:
        return jsonify({"status": "fail", "message": "Link URL is required for a link post."}), 400

    try:
        # The Post.create_post method already validates if the community_id is valid
        new_post_dict = Post.create_post(
            community_id=community_id,
            author_id=current_user_id,
            title=title,
            content_type=content_type,
            content_text=content_text,
            image_url=image_url,
            link_url=link_url,
            tags=tags
        )
        current_app.logger.info(f"Post '{title}' created in community {community_id} by user {current_user_id}")
        return jsonify({"status": "success", "data": {"post": new_post_dict}}), 201
    except ValueError as ve:
        current_app.logger.warning(f"ValueError creating post: {str(ve)}")
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Or 404 if community not found
    except Exception as e:
        current_app.logger.error(f"Error creating post in community {community_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred while creating the post."}), 500

# GET /api/v1/communities/<communityId>/posts (List posts for a community)
@community_bp.route('/communities/<string:community_id>/posts', methods=['GET'])
@jwt_required() # Or public if desired
def get_posts_for_community_route(community_id):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        sort_by = request.args.get('sortBy', 'new', type=str).lower() # 'new', 'hot', 'top'

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 50: per_page = 50 # Max limit for posts
        if sort_by not in ['new', 'hot', 'top']: sort_by = 'new'

        if not ObjectId.is_valid(community_id):
             return jsonify({"status": "fail", "message": "Invalid community ID format."}), 400
        
        # Optional: Check if community exists before fetching posts
        # community = Community.find_by_id(community_id)
        # if not community:
        #     return jsonify({"status": "fail", "message": "Community not found."}), 404

        result = Post.get_posts_for_community(community_id=community_id, page=page, per_page=per_page, sort_by=sort_by)
        
        return jsonify({
            "status": "success",
            "data": result['posts'],
            "pagination": {
                "total_items": result['total'],
                "total_pages": result['pages'],
                "current_page": result['page'],
                "per_page": result['per_page'],
                "sort_by": sort_by
            }
        }), 200
    except ValueError as ve: # Catch specific errors like invalid community ID from model
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching posts for community {community_id}: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to retrieve posts for the community."}), 500

# GET /api/v1/posts/{postId} (Get a single post details)
# Note: This endpoint is not nested under /communities/ for direct access to a post if ID is known.
@community_bp.route('/posts/<string:post_id>', methods=['GET'])
@jwt_required() # Or public
def get_post_detail_route(post_id):
    if not ObjectId.is_valid(post_id):
        return jsonify({"status": "fail", "message": "Invalid post ID format."}), 400
        
    post = Post.find_by_id(post_id)
    if not post:
        return jsonify({"status": "fail", "message": "Post not found."}), 404
    
    # Optionally, add if current user has voted on this post, etc. (for later)
    return jsonify({"status": "success", "data": {"post": post}}), 200