# flask_service/app/routes/community_routes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.community import Community
from app.models.post import Post
from app.models.comment import Comment
from bson import ObjectId, errors as bson_errors
from app.services.file_handler import save_base64_image # Ensure this service exists

community_bp = Blueprint('community_bp', __name__)

# === Community Management Routes ===

@community_bp.route('/communities', methods=['POST'])
@jwt_required()
def create_community_route():
    data = request.get_json()
    if not data:
        return jsonify({"status": "fail", "message": "Request body is empty or not JSON."}), 400
    current_user_id = get_jwt_identity()

    icon_url_for_db = data.get('icon')
    banner_url_for_db = data.get('bannerImage')

    if icon_url_for_db and isinstance(icon_url_for_db, str) and icon_url_for_db.startswith('data:image'):
        try:
            icon_url_for_db = save_base64_image(icon_url_for_db, 'community_icons', "cicon_new")
        except Exception as e:
            current_app.logger.error(f"Icon processing error during community creation: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Icon processing error: {str(e)}"}), 400
    elif isinstance(icon_url_for_db, str) and not icon_url_for_db.startswith('http'): # If it's not base64 and not a URL, treat as invalid
        icon_url_for_db = None


    if banner_url_for_db and isinstance(banner_url_for_db, str) and banner_url_for_db.startswith('data:image'):
        try:
            banner_url_for_db = save_base64_image(banner_url_for_db, 'community_banners', "cbanner_new")
        except Exception as e:
            current_app.logger.error(f"Banner processing error during community creation: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Banner processing error: {str(e)}"}), 400
    elif isinstance(banner_url_for_db, str) and not banner_url_for_db.startswith('http'):
        banner_url_for_db = None

    try:
        new_community = Community.create_community(
            name=data.get('name'),
            description=data.get('description'),
            created_by_id_str=current_user_id,
            rules=data.get('rules'),
            icon_url=icon_url_for_db,
            banner_image_url=banner_url_for_db,
            tags=data.get('tags')
        )
        return jsonify({"status": "success", "data": {"community": new_community}}), 201
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating community: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not create community due to an internal server error."}), 500

@community_bp.route('/communities/<string:community_id>', methods=['PUT'])
@jwt_required()
def update_community_route(community_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "fail", "message": "No data provided for update."}), 400

    current_user_id_str = get_jwt_identity()
    update_payload_for_model = {}

    allowed_text_fields = ['name', 'description', 'rules', 'tags']
    for field in allowed_text_fields:
        if field in data:
            update_payload_for_model[field] = data[field]

    if 'icon' in data:
        icon_data = data['icon']
        if icon_data and isinstance(icon_data, str) and icon_data.startswith('data:image'):
            try:
                icon_public_url = save_base64_image(icon_data, 'community_icons', f"cicon_{community_id}")
                update_payload_for_model['iconUrl'] = icon_public_url
            except Exception as e:
                current_app.logger.error(f"Icon processing error for community {community_id}: {e}", exc_info=True)
                return jsonify({"status": "fail", "message": f"Icon processing error: {str(e)}"}), 400
        elif icon_data is None:
            update_payload_for_model['iconUrl'] = None
        elif isinstance(icon_data, str) and (icon_data.startswith('http') or icon_data == ""): # Allow empty string to clear if model handles it
             update_payload_for_model['iconUrl'] = icon_data if icon_data else None


    if 'bannerImage' in data:
        banner_data = data['bannerImage']
        if banner_data and isinstance(banner_data, str) and banner_data.startswith('data:image'):
            try:
                banner_public_url = save_base64_image(banner_data, 'community_banners', f"cbanner_{community_id}")
                update_payload_for_model['bannerImage'] = banner_public_url
            except Exception as e:
                current_app.logger.error(f"Banner processing error for community {community_id}: {e}", exc_info=True)
                return jsonify({"status": "fail", "message": f"Banner image processing error: {str(e)}"}), 400
        elif banner_data is None:
            update_payload_for_model['bannerImage'] = None
        elif isinstance(banner_data, str) and (banner_data.startswith('http') or banner_data == ""):
            update_payload_for_model['bannerImage'] = banner_data if banner_data else None


    if not update_payload_for_model:
        return jsonify({"status": "fail", "message": "No valid fields to update provided."}), 400

    try:
        updated_community = Community.update_community(community_id, current_user_id_str, update_payload_for_model)
        return jsonify({"status": "success", "data": {"community": updated_community}}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Handles "not found" or validation errors from model
    except PermissionError as pe:
        return jsonify({"status": "fail", "message": str(pe)}), 403
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid community ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating community {community_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred while updating community."}), 500

@community_bp.route('/communities', methods=['GET'])
@jwt_required(optional=True)
def get_communities_route():
    current_user_id_str = None
    try:
        user_identity = get_jwt_identity()
        current_user_id_str = str(user_identity) if user_identity else None
    except Exception: pass
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        search_query = request.args.get('searchQuery', type=str)
        result = Community.get_all_communities(page=page, per_page=per_page, search_query=search_query, current_user_id_str=current_user_id_str)
        return jsonify({"status": "success", "data": result['communities'], "results": result['total'],
                        "pagination": result['pagination'] if 'pagination' in result else {"totalItems": result['total'], "totalPages": result['pages'],
                                       "currentPage": result['page'], "perPage": result['per_page']}}), 200
    except Exception as e:
        current_app.logger.error(f"Error listing communities: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to list communities."}), 500

@community_bp.route('/communities/<string:community_id_or_slug>', methods=['GET'])
@jwt_required(optional=True)
def get_community_detail_route(community_id_or_slug):
    current_user_id_str = None
    try:
        user_identity = get_jwt_identity()
        current_user_id_str = str(user_identity) if user_identity else None
    except Exception: pass
    try:
        community_dict = Community.find_by_id_or_slug(community_id_or_slug, current_user_id_str)
        if not community_dict: return jsonify({"status": "fail", "message": "Community not found."}), 404
        return jsonify({"status": "success", "data": {"community": community_dict}}), 200
    except Exception as e:
        current_app.logger.error(f"Error getting community detail {community_id_or_slug}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not get community details."}), 500

@community_bp.route('/communities/<string:community_id>/join', methods=['POST'])
@jwt_required()
def join_community_route(community_id):
    current_user_id_str = get_jwt_identity()
    try:
        result = Community.join_community(community_id, current_user_id_str)
        status_code = 200
        if result.get("already_member"): status_code = 409
        elif not result.get("modified"): status_code = 400

        updated_community_data = None
        if result.get("modified") or result.get("already_member"): # Also return data if already member
            updated_community_data = Community.find_by_id_or_slug(community_id, current_user_id_str)

        return jsonify({
            "status": "success" if result.get("modified") or result.get("already_member") else "fail",
            "message": result["message"],
            "data": {"community": updated_community_data}
        }), status_code
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error joining community {community_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not join community."}), 500

@community_bp.route('/communities/<string:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community_route(community_id):
    current_user_id_str = get_jwt_identity()
    try:
        result = Community.leave_community(community_id, current_user_id_str)
        status_code = 200
        if result.get("not_member"): status_code = 400
        elif not result.get("modified"): status_code = 400

        updated_community_data = None
        if result.get("modified") or result.get("not_member"): # Also return data if not member (to show updated state)
            updated_community_data = Community.find_by_id_or_slug(community_id, current_user_id_str)

        return jsonify({
            "status": "success" if result.get("modified") else "fail",
            "message": result["message"],
            "data": {"community": updated_community_data}
        }), status_code
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error leaving community {community_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not leave community."}), 500


# === Post Management Routes ===
@community_bp.route('/communities/<string:community_id_from_url>/posts', methods=['POST'])
@jwt_required()
def create_post_in_community_route(community_id_from_url):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"status": "fail", "message": "Request body is empty or not JSON."}), 400
    
    # --- Handling potential image upload for new post ---
    image_url_for_db = data.get('image_url') # Could be an existing URL
    image_base64 = data.get('image_base64') # Frontend might send base64 for new upload

    if image_base64 and isinstance(image_base64, str) and image_base64.startswith('data:image'):
        try:
            # Create a unique enough prefix, perhaps involving community_id if desired, or just "postimg_new"
            image_url_for_db = save_base64_image(image_base64, 'post_images', f"postimg_{community_id_from_url}_new")
        except Exception as e:
            current_app.logger.error(f"Post image processing error during post creation: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Post image processing error: {str(e)}"}), 400
    elif image_url_for_db and not isinstance(image_url_for_db, str) and not image_url_for_db.startswith('http'):
        image_url_for_db = None # Invalid URL if not http and not base64
    # --- End image handling for new post ---

    try:
        new_post = Post.create_post(
            community_id_str=community_id_from_url,
            author_id_str=current_user_id_str,
            title=data.get('title'),
            content_type=data.get('content_type'),
            content_text=data.get('content_text'),
            image_url=image_url_for_db, # Use processed URL
            link_url=data.get('link_url'),
            tags=data.get('tags')
        )
        return jsonify({"status": "success", "data": {"post": new_post}}), 201
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating post in C:{community_id_from_url}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not create post due to an internal error."}), 500

@community_bp.route('/communities/<string:community_id>/posts', methods=['GET'])
@jwt_required(optional=True)
def get_posts_for_community_route(community_id):
    current_user_id_str = None
    try:
        user_identity = get_jwt_identity()
        current_user_id_str = str(user_identity) if user_identity else None
    except Exception: pass

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        sort_by = request.args.get('sortBy', 'new', type=str).lower()

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        elif per_page > 50: per_page = 50
        if sort_by not in ['new', 'hot', 'top']: sort_by = 'new'

        result = Post.get_posts_for_community_for_user(
            community_id_str=community_id, current_user_id_str=current_user_id_str,
            page=page, per_page=per_page, sort_by=sort_by
        )
        return jsonify({"status": "success", "data": result.get('posts',[]), "results": result.get('total',0),
                        "pagination": result.get('pagination', {"totalItems": result.get('total',0), "totalPages": result.get('pages',0),
                                       "currentPage": result.get('page',1), "perPage": result.get('per_page',10), "sortBy": sort_by })}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting posts for C:{community_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to get posts."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['GET'])
@jwt_required(optional=True)
def get_post_detail_route(post_id):
    current_user_id_str = None
    try:
        user_identity = get_jwt_identity()
        current_user_id_str = str(user_identity) if user_identity else None
    except Exception: pass
    try:
        post = Post.find_by_id_for_user(post_id, current_user_id_str)
        if not post: return jsonify({"status": "fail", "message": "Post not found."}), 404
        return jsonify({"status": "success", "data": {"post": post}}), 200
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid post ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting post detail {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not get post details."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['PUT'])
@jwt_required()
def update_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data: return jsonify({"status": "fail", "message": "Request body is empty."}), 400

    update_payload = {}
    if 'title' in data: update_payload['title'] = data['title']
    if 'content_text' in data: update_payload['content_text'] = data['content_text']
    if 'link_url' in data: update_payload['link_url'] = data['link_url'] # For link posts
    if 'tags' in data: update_payload['tags'] = data['tags']

    # --- MODIFICATION: Handle image update for posts ---
    # Frontend can send 'image_base64' for new upload, or 'image_url' to set/clear URL
    if 'image_base64' in data:
        image_data_base64 = data['image_base64']
        if image_data_base64 and isinstance(image_data_base64, str) and image_data_base64.startswith('data:image'):
            try:
                # Ensure your save_base64_image function exists and works as expected
                # 'post_images' is a suggested subfolder for post-specific images
                image_public_url = save_base64_image(image_data_base64, 'post_images', f"postimg_{post_id}")
                update_payload['image_url'] = image_public_url
            except Exception as e:
                current_app.logger.error(f"Post image processing error for post {post_id}: {e}", exc_info=True)
                return jsonify({"status": "fail", "message": f"Post image processing error: {str(e)}"}), 400
        elif image_data_base64 is None: # Explicitly clear image if frontend sends null for base64
            update_payload['image_url'] = None
    elif 'image_url' in data: # If frontend sends image_url (could be existing, new, or empty string/null to clear)
        image_url_input = data['image_url']
        if image_url_input is None or (isinstance(image_url_input, str) and image_url_input == ""):
            update_payload['image_url'] = None # Clear image
        elif isinstance(image_url_input, str) and image_url_input.startswith('http'):
            update_payload['image_url'] = image_url_input # Set to new/existing URL
    # --- END MODIFICATION ---

    if not update_payload: return jsonify({"status": "fail", "message": "No updatable fields provided or fields are empty."}), 400
    
    try:
        result = Post.update_post(post_id, current_user_id_str, update_payload)
        # result should contain {"post": updated_post_dict, "message": "..."}
        return jsonify({"status": "success", "message": result.get("message", "Post updated."), "data": {"post": result.get("post")}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400 
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid post ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not update post."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    try:
        Post.delete_post(post_id_str=post_id, user_id_str=current_user_id_str)
        return jsonify({"status": "success", "message": "Post deleted."}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 404
    except PermissionError as pe:
        return jsonify({"status": "fail", "message": str(pe)}), 403
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid post ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error deleting post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not delete post."}), 500

@community_bp.route('/posts/<string:post_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data or 'direction' not in data:
        return jsonify({"status": "fail", "message": "Vote direction is required."}), 400
    direction = data.get('direction')
    if direction not in ["up", "down", "none"]:
        return jsonify({"status": "fail", "message": "Invalid vote direction. Must be 'up', 'down', or 'none'."}), 400
    try:
        updated_post_data = Post.vote_on_post(post_id, current_user_id_str, direction)
        return jsonify({"status": "success", "message": updated_post_data.get("message", "Vote processed."),
                        "data": {
                            "upvotes": updated_post_data.get("upvotes"),
                            "downvotes": updated_post_data.get("downvotes"),
                            "user_vote": updated_post_data.get("user_vote")
                        }}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid post ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error voting on post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not process vote."}), 500

# === Comment Management Routes ===
@community_bp.route('/posts/<string:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment_on_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data: return jsonify({"status": "fail", "message": "Request body is empty or not JSON."}), 400

    text = data.get('text')
    parent_comment_id_str = data.get('parent_comment_id')

    if not text or not text.strip(): return jsonify({"status": "fail", "message": "Comment text required."}), 400
    try:
        new_comment = Comment.create_comment(
            post_id_str=post_id,
            author_id_str=current_user_id_str,
            text=text,
            parent_comment_id_str=parent_comment_id_str
        )
        return jsonify({"status": "success", "data": {"comment": new_comment}}), 201
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except bson_errors.InvalidId: # Catch invalid post_id or parent_comment_id if applicable
        return jsonify({"status": "fail", "message": "Invalid ID format for post or parent comment."}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating comment on P:{post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not create comment."}), 500

@community_bp.route('/posts/<string:post_id>/comments', methods=['GET'])
@jwt_required(optional=True)
def get_comments_for_post_route(post_id):
    current_user_id_str = None
    try:
        user_identity = get_jwt_identity()
        current_user_id_str = str(user_identity) if user_identity else None
    except Exception: pass

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sortBy', 'newest', type=str).lower()

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        elif per_page > 100: per_page = 100
        if sort_by not in ['newest', 'oldest', 'top']: sort_by = 'newest'

        result = Comment.get_comments_for_post_for_user(
            post_id_str=post_id, current_user_id_str=current_user_id_str,
            page=page, per_page=per_page, sort_by=sort_by, parent_id_str=None
        )
        return jsonify({"status": "success", "data": result.get('comments',[]), "results": result.get('total',0),
                        "pagination": result.get('pagination', {"totalItems": result.get('total',0), "totalPages": result.get('pages',0),
                                       "currentPage": result.get('page',1), "perPage": result.get('per_page',10), "sortBy": sort_by}}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid post ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching comments for P:{post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to get comments."}), 500

@community_bp.route('/comments/<string:parent_comment_id>/replies', methods=['GET'])
@jwt_required(optional=True)
def get_replies_for_comment_route(parent_comment_id):
    current_user_id_str = None
    try:
        user_identity = get_jwt_identity()
        current_user_id_str = str(user_identity) if user_identity else None
    except Exception: pass
    try:
        parent_comment_doc = Comment.find_by_id(parent_comment_id) # This should return a dict or None
        if not parent_comment_doc:
            return jsonify({"status": "fail", "message": "Parent comment not found."}), 404
        
        post_id_for_replies = parent_comment_doc.get("post_id")
        if not post_id_for_replies:
            return jsonify({"status": "error", "message": "Parent comment missing post association."}), 500

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        sort_by = request.args.get('sortBy', 'oldest', type=str).lower()

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        elif per_page > 50: per_page = 50
        if sort_by not in ['newest', 'oldest', 'top']: sort_by = 'oldest' # 'top' for replies might be less common

        result = Comment.get_comments_for_post_for_user(
            post_id_str=str(post_id_for_replies),
            current_user_id_str=current_user_id_str,
            page=page, per_page=per_page, sort_by=sort_by,
            parent_id_str=parent_comment_id
        )
        return jsonify({
            "status": "success", "data": result.get('comments',[]), "results": result.get('total',0),
            "pagination": result.get('pagination', {
                "totalItems": result.get('total',0), "totalPages": result.get('pages',0),
                "currentPage": result.get('page',1), "perPage": result.get('per_page',10),
                "sortBy": sort_by
            })
        }), 200
    except ValueError as ve: # From get_comments_for_post_for_user if post_id is invalid (shouldn't happen here)
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid parent comment ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching replies for Cmnt:{parent_comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to get replies."}), 500

@community_bp.route('/comments/<string:comment_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data or 'direction' not in data:
        return jsonify({"status": "fail", "message": "Vote direction is required."}), 400
    direction = data.get('direction')
    if direction not in ["up", "down", "none"]:
        return jsonify({"status": "fail", "message": "Invalid vote direction. Must be 'up', 'down', or 'none'."}), 400
    try:
        result_dict = Comment.vote_on_comment(comment_id, current_user_id_str, direction)
        return jsonify({"status": "success", "message": result_dict.get("message"),
                        "data": {"upvotes": result_dict.get("upvotes"), "downvotes": result_dict.get("downvotes"),
                                 "user_vote": result_dict.get("user_vote")}}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid comment ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error voting on Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not process vote."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data or 'text' not in data :
         return jsonify({"status": "fail", "message": "Comment text required in payload."}), 400

    new_text = data.get('text')

    if not new_text or not new_text.strip(): return jsonify({"status": "fail", "message": "Comment text cannot be empty."}), 400
    try:
        updated_comment = Comment.update_comment(
            comment_id_str=comment_id,
            author_id_str=current_user_id_str,
            new_text=new_text
        )
        return jsonify({"status": "success", "data": {"comment": updated_comment}}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except PermissionError as pe:
        return jsonify({"status": "fail", "message": str(pe)}), 403
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid comment ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not update comment."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    try:
        Comment.delete_comment(comment_id_str=comment_id, user_id_str=current_user_id_str)
        return jsonify({"status": "success", "message": "Comment deleted."}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 404
    except PermissionError as pe:
        return jsonify({"status": "fail", "message": str(pe)}), 403
    except bson_errors.InvalidId:
        return jsonify({"status": "fail", "message": "Invalid comment ID format."}), 400
    except Exception as e:
        current_app.logger.error(f"Error deleting Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not delete comment."}), 500