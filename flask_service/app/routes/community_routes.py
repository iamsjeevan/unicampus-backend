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

    icon_url_for_db = data.get('icon')  # Can be a URL, base64 string, or None
    banner_url_for_db = data.get('bannerImage')  # Can be a URL, base64 string, or None

    # Process icon if it's a base64 string
    if icon_url_for_db and isinstance(icon_url_for_db, str) and icon_url_for_db.startswith('data:image'):
        try:
            icon_url_for_db = save_base64_image(icon_url_for_db, 'community_icons', "cicon_new")
        except Exception as e:
            current_app.logger.error(f"Icon processing error during community creation: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Icon processing error: {str(e)}"}), 400

    # Process bannerImage if it's a base64 string
    if banner_url_for_db and isinstance(banner_url_for_db, str) and banner_url_for_db.startswith('data:image'):
        try:
            banner_url_for_db = save_base64_image(banner_url_for_db, 'community_banners', "cbanner_new")
        except Exception as e:
            current_app.logger.error(f"Banner processing error during community creation: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Banner processing error: {str(e)}"}), 400

    try:
        new_community = Community.create_community(
            name=data.get('name'),
            description=data.get('description'),
            created_by_id_str=current_user_id,
            rules=data.get('rules'),
            icon_url=icon_url_for_db,  # Use processed URL (or original if it was already a URL/None)
            banner_image_url=banner_url_for_db,  # Use processed URL
            tags=data.get('tags')
        )
        # create_community should raise ValueError if validation fails or name exists
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
    update_payload_for_model = {} # Data to pass to Community.update_community

    # Process textual fields that can be updated
    allowed_text_fields = ['name', 'description', 'rules', 'tags']
    for field in allowed_text_fields:
        if field in data: # Only include if field is present in request
            update_payload_for_model[field] = data[field]

    # Handle 'icon' from frontend (can be base64, URL, or None)
    # Model's update_community expects 'iconUrl' for DB storage
    if 'icon' in data:
        icon_data = data['icon']
        if icon_data and isinstance(icon_data, str) and icon_data.startswith('data:image'):
            try:
                icon_public_url = save_base64_image(icon_data, 'community_icons', f"cicon_{community_id}")
                update_payload_for_model['iconUrl'] = icon_public_url
            except Exception as e:
                current_app.logger.error(f"Icon processing error for community {community_id}: {e}", exc_info=True)
                return jsonify({"status": "fail", "message": f"Icon processing error: {str(e)}"}), 400
        elif icon_data is None: # Allow clearing the icon
            update_payload_for_model['iconUrl'] = None
        elif isinstance(icon_data, str): # Assume it's a direct URL if not base64 and not None
             update_payload_for_model['iconUrl'] = icon_data
        # If 'icon' is present but an invalid type (e.g., number, object), it's ignored here.
        # Add validation if specific error for bad type is needed.

    # Handle 'bannerImage' from frontend
    # Model's update_community expects 'bannerImage' (same as DB field name)
    if 'bannerImage' in data:
        banner_data = data['bannerImage']
        if banner_data and isinstance(banner_data, str) and banner_data.startswith('data:image'):
            try:
                banner_public_url = save_base64_image(banner_data, 'community_banners', f"cbanner_{community_id}")
                update_payload_for_model['bannerImage'] = banner_public_url
            except Exception as e:
                current_app.logger.error(f"Banner processing error for community {community_id}: {e}", exc_info=True)
                return jsonify({"status": "fail", "message": f"Banner image processing error: {str(e)}"}), 400
        elif banner_data is None: # Allow clearing
            update_payload_for_model['bannerImage'] = None
        elif isinstance(banner_data, str): # Assume direct URL
            update_payload_for_model['bannerImage'] = banner_data

    if not update_payload_for_model:
        return jsonify({"status": "fail", "message": "No valid fields to update provided."}), 400

    try:
        updated_community = Community.update_community(community_id, current_user_id_str, update_payload_for_model)
        return jsonify({"status": "success", "data": {"community": updated_community}}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
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
    except Exception: pass # If get_jwt_identity fails (e.g., no token), current_user_id_str remains None
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        search_query = request.args.get('searchQuery', type=str)
        result = Community.get_all_communities(page=page, per_page=per_page, search_query=search_query, current_user_id_str=current_user_id_str)
        return jsonify({"status": "success", "data": result['communities'], "results": result['total'],
                        "pagination": {"totalItems": result['total'], "totalPages": result['pages'],
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
        if result.get("already_member"): status_code = 409 # Conflict
        elif not result.get("modified"): status_code = 400 # Bad request or no change

        updated_community_data = None
        if result.get("modified"):
             # Fetch full community details again to include updated member count and user's membership status
            updated_community_data = Community.find_by_id_or_slug(community_id, current_user_id_str)

        return jsonify({
            "status": "success" if result.get("modified") else "fail",
            "message": result["message"],
            "data": {"community": updated_community_data} # Send updated community data if modified
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
        if result.get("not_member"): status_code = 400 # Bad request
        elif not result.get("modified"): status_code = 400 # No change or other issue

        updated_community_data = None
        if result.get("modified"):
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

    try:
        # Model's create_post expects snake_case keys in its parameters
        new_post = Post.create_post(
            community_id_str=community_id_from_url,
            author_id_str=current_user_id_str,
            title=data.get('title'),
            content_type=data.get('content_type'),
            content_text=data.get('content_text'),
            image_url=data.get('image_url'),
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
        sort_by = request.args.get('sortBy', 'new', type=str).lower() # Query params often camelCase

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        elif per_page > 50: per_page = 50 # Max limit
        if sort_by not in ['new', 'hot', 'top']: sort_by = 'new'

        result = Post.get_posts_for_community_for_user(
            community_id_str=community_id, current_user_id_str=current_user_id_str,
            page=page, per_page=per_page, sort_by=sort_by
        )
        return jsonify({"status": "success", "data": result.get('posts',[]), "results": result.get('total',0),
                        "pagination": {"totalItems": result.get('total',0), "totalPages": result.get('pages',0),
                                       "currentPage": result.get('page',1), "perPage": result.get('per_page',10), "sortBy": sort_by }}), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 404 # e.g. community not found
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
    except Exception as e:
        current_app.logger.error(f"Error getting post detail {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not get post details."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['PUT'])
@jwt_required()
def update_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data: return jsonify({"status": "fail", "message": "Request body is empty."}), 400

    # Model's update_post expects a dictionary with snake_case keys
    update_payload = {}
    if 'title' in data: update_payload['title'] = data['title']
    if 'content_text' in data: update_payload['content_text'] = data['content_text']
    # For image/link posts, typically content_text is not updated, but image_url/link_url might be
    # The Post.update_post model method should enforce this logic (e.g., only update content_text if type is 'text')
    if 'image_url' in data: update_payload['image_url'] = data['image_url']
    if 'link_url' in data: update_payload['link_url'] = data['link_url']
    if 'tags' in data: update_payload['tags'] = data['tags']


    if not update_payload: return jsonify({"status": "fail", "message": "No updatable fields provided or fields are empty."}), 400
    try:
        result = Post.update_post(post_id, current_user_id_str, update_payload)
        return jsonify({"status": "success", "message": result.get("message", "Post updated."), "data": {"post": result.get("post")}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400 # Or 404 if "not found"
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e:
        current_app.logger.error(f"Error updating post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not update post."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    try:
        # Model's delete_post now raises ValueError or PermissionError, or returns True
        Post.delete_post(post_id_str=post_id, user_id_str=current_user_id_str)
        return jsonify({"status": "success", "message": "Post deleted."}), 200
    except ValueError as ve: # Covers "Post not found"
        return jsonify({"status": "fail", "message": str(ve)}), 404
    except PermissionError as pe: # Covers "not authorized"
        return jsonify({"status": "fail", "message": str(pe)}), 403
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
                            "user_vote": updated_post_data.get("user_vote") # From Post.to_dict
                        }}), 200
    except ValueError as ve: # Covers "Post not found" or "Invalid vote direction" from model
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Or 404 if "not found"
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
    parent_comment_id_str = data.get('parent_comment_id') # Optional

    if not text or not text.strip(): return jsonify({"status": "fail", "message": "Comment text required."}), 400
    try:
        new_comment = Comment.create_comment(
            post_id_str=post_id,
            author_id_str=current_user_id_str,
            text=text,
            parent_comment_id_str=parent_comment_id_str
        )
        return jsonify({"status": "success", "data": {"comment": new_comment}}), 201
    except ValueError as ve: # Covers "Post not found", "Parent comment not found", "Text too long" etc.
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Or 404 if "not found"
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
        if sort_by not in ['newest', 'oldest', 'top']: sort_by = 'newest' # Add 'top' if implemented in model

        result = Comment.get_comments_for_post_for_user(
            post_id_str=post_id, current_user_id_str=current_user_id_str,
            page=page, per_page=per_page, sort_by=sort_by, parent_id_str=None # For top-level comments
        )
        return jsonify({"status": "success", "data": result.get('comments',[]), "results": result.get('total',0),
                        "pagination": {"totalItems": result.get('total',0), "totalPages": result.get('pages',0),
                                       "currentPage": result.get('page',1), "perPage": result.get('per_page',10), "sortBy": sort_by}}), 200
    except ValueError as ve: # e.g. "Invalid Post ID"
        return jsonify({"status": "fail", "message": str(ve)}), 400
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
        # First, validate parent comment exists and get its post_id
        parent_comment_doc = Comment.find_by_id(parent_comment_id) # This uses Comment.to_dict
        if not parent_comment_doc:
            return jsonify({"status": "fail", "message": "Parent comment not found."}), 404
        
        post_id_for_replies = parent_comment_doc.get("post_id")
        if not post_id_for_replies: # Should not happen if parent_comment_doc is valid
            return jsonify({"status": "error", "message": "Parent comment missing post association."}), 500

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        sort_by = request.args.get('sortBy', 'oldest', type=str).lower() # Replies usually oldest first

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        elif per_page > 50: per_page = 50
        if sort_by not in ['newest', 'oldest']: sort_by = 'oldest'

        result = Comment.get_comments_for_post_for_user(
            post_id_str=str(post_id_for_replies),
            current_user_id_str=current_user_id_str,
            page=page, per_page=per_page, sort_by=sort_by,
            parent_id_str=parent_comment_id # Filter by this parent
        )
        return jsonify({
            "status": "success", "data": result.get('comments',[]), "results": result.get('total',0),
            "pagination": {
                "totalItems": result.get('total',0), "totalPages": result.get('pages',0),
                "currentPage": result.get('page',1), "perPage": result.get('per_page',10),
                "sortBy": sort_by
            }
        }), 200
    except ValueError as ve:
        return jsonify({"status": "fail", "message": str(ve)}), 400
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
    except ValueError as ve: # Covers "Comment not found" or "Invalid vote direction"
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Or 404 if "not found"
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

    new_text = data.get('text') # Model's update_comment expects `new_text` as a direct arg

    if not new_text or not new_text.strip(): return jsonify({"status": "fail", "message": "Comment text cannot be empty."}), 400
    try:
        updated_comment = Comment.update_comment(
            comment_id_str=comment_id,
            author_id_str=current_user_id_str,
            new_text=new_text
        )
        return jsonify({"status": "success", "data": {"comment": updated_comment}}), 200
    except ValueError as ve: # Covers "Comment not found", "Text empty/long"
        return jsonify({"status": "fail", "message": str(ve)}), 400 # Or 404 if "not found"
    except PermissionError as pe:
        return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e:
        current_app.logger.error(f"Error updating Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not update comment."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    try:
        # Model's delete_comment raises ValueError or PermissionError, or returns True
        Comment.delete_comment(comment_id_str=comment_id, user_id_str=current_user_id_str)
        return jsonify({"status": "success", "message": "Comment deleted."}), 200
    except ValueError as ve: # Covers "Comment not found"
        return jsonify({"status": "fail", "message": str(ve)}), 404
    except PermissionError as pe: # Covers "not authorized"
        return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e:
        current_app.logger.error(f"Error deleting Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not delete comment."}), 500
