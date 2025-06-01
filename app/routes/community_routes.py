# app/routes/community_routes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.community import Community
from app.models.post import Post 
from app.models.comment import Comment
from bson import ObjectId, errors as bson_errors

community_bp = Blueprint('community_bp', __name__)

# === Community Management Routes ===
# ... (Your existing and working community routes: POST, GET list, GET detail, join, leave) ...
@community_bp.route('/communities', methods=['POST'])
@jwt_required()
def create_community_route():
    data = request.get_json(); current_user_id = get_jwt_identity()
    name = data.get('name'); description = data.get('description')
    if not name or not description: return jsonify({"status": "fail", "message": "Name and description required."}), 400
    try:
        new_dict = Community.create_community(name=name, description=description, created_by_id=current_user_id, rules=data.get('rules'), icon_url=data.get('icon_url'), banner_image_url=data.get('banner_image_url'), tags=data.get('tags'))
        return jsonify({"status": "success", "data": {"community": new_dict}}), 201
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: current_app.logger.error(f"Err creating community: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err creating community."}), 500

@community_bp.route('/communities', methods=['GET'])
@jwt_required() 
def get_communities_route():
    try:
        page = request.args.get('page', 1, type=int); per_page = request.args.get('limit', 10, type=int)
        search_query = request.args.get('searchQuery', type=str) 
        result = Community.get_all_communities(page=page, per_page=per_page, search_query=search_query)
        return jsonify({"status": "success", "data": result['communities'], "pagination": {"total_items": result['total'], "total_pages": result['pages'], "current_page": result['page'], "per_page": result['per_page']}}), 200
    except Exception as e: current_app.logger.error(f"Err fetching communities: {e}", exc_info=True); return jsonify({"status": "error", "message": "Failed to retrieve communities."}), 500

@community_bp.route('/communities/<string:community_id_or_slug>', methods=['GET'])
@jwt_required()
def get_community_detail_route(community_id_or_slug):
    comm = None
    if ObjectId.is_valid(community_id_or_slug): comm = Community.find_by_id(community_id_or_slug)
    if not comm: comm = Community.find_by_slug(community_id_or_slug)
    if not comm: return jsonify({"status": "fail", "message": "Community not found."}), 404
    current_user_id = get_jwt_identity()
    comm['is_member'] = Community.is_member(comm['id'], current_user_id)
    return jsonify({"status": "success", "data": {"community": comm}}), 200

@community_bp.route('/communities/<string:community_id>/join', methods=['POST'])
@jwt_required()
def join_community_route(community_id):
    current_user_id = get_jwt_identity()
    try: # Wrap ObjectId conversion
        if Community.is_member(community_id, current_user_id): return jsonify({"status": "fail", "message": "Already a member."}), 409
        if Community.join_community(community_id, current_user_id): return jsonify({"status": "success", "message": "Joined community."}), 200
        else: return jsonify({"status": "fail", "message": "Could not join. Community may not exist or already a member."}), 400 
    except bson_errors.InvalidId: return jsonify({"status": "fail", "message": "Invalid community ID."}), 400
    except Exception as e: current_app.logger.error(f"Err joining C:{community_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err joining."}), 500

@community_bp.route('/communities/<string:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community_route(community_id):
    current_user_id = get_jwt_identity()
    try: # Wrap ObjectId conversion
        if not Community.is_member(community_id, current_user_id): return jsonify({"status": "fail", "message": "Not a member."}), 400
        if Community.leave_community(community_id, current_user_id): return jsonify({"status": "success", "message": "Left community."}), 200
        else: return jsonify({"status": "fail", "message": "Could not leave. Community may not exist or not a member."}), 400
    except bson_errors.InvalidId: return jsonify({"status": "fail", "message": "Invalid community ID."}), 400
    except Exception as e: current_app.logger.error(f"Err leaving C:{community_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err leaving."}), 500

# === Post Management Routes ===
@community_bp.route('/communities/<string:community_id_from_url>/posts', methods=['POST'])
@jwt_required()
def create_post_in_community_route(community_id_from_url):
    current_user_id_str = get_jwt_identity(); data = request.get_json()
    title = data.get('title'); content_type = data.get('content_type')
    content_text = data.get('content_text'); image_url = data.get('image_url')
    link_url = data.get('link_url'); tags = data.get('tags')
    if not title or not content_type: return jsonify({"status": "fail", "message": "Title & type required."}), 400
    if content_type == "text" and not content_text: return jsonify({"status": "fail", "message": "Text content required."}), 400
    if content_type == "image" and not image_url: return jsonify({"status": "fail", "message": "Image URL required."}), 400
    if content_type == "link" and not link_url: return jsonify({"status": "fail", "message": "Link URL required."}), 400
    try:
        new_post = Post.create_post(community_id_str=community_id_from_url, author_id_str=current_user_id_str, title=title, content_type=content_type, content_text=content_text, image_url=image_url, link_url=link_url, tags=tags)
        return jsonify({"status": "success", "data": {"post": new_post}}), 201
    except ValueError as ve: status_code = 404 if "not found" in str(ve).lower() else 400; return jsonify({"status": "fail", "message": str(ve)}), status_code
    except Exception as e: current_app.logger.error(f"Err creating post in C:{community_id_from_url}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err creating post."}), 500

@community_bp.route('/communities/<string:community_id>/posts', methods=['GET'])
@jwt_required()
def get_posts_for_community_route(community_id):
    current_user_id_str = get_jwt_identity(); 
    try:
        page = request.args.get('page', 1, type=int); per_page = request.args.get('limit', 10, type=int)
        sort_by = request.args.get('sortBy', 'new', type=str).lower()
        if page < 1: page = 1; 
        if per_page < 1: per_page = 1; 
        if per_page > 50: per_page = 50
        if sort_by not in ['new', 'hot', 'top']: sort_by = 'new'
        result = Post.get_posts_for_community_for_user(community_id_str=community_id, current_user_id_str=current_user_id_str, page=page, per_page=per_page, sort_by=sort_by)
        return jsonify({"status": "success", "data": result['posts'], "pagination": {"total_items": result['total'], "total_pages": result['pages'], "current_page": result['page'], "per_page": result['per_page'], "sort_by": sort_by }}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: current_app.logger.error(f"Err fetching posts for C:{community_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Failed to retrieve posts."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['GET'])
@jwt_required()
def get_post_detail_route(post_id):
    current_user_id_str = get_jwt_identity()
    post = Post.find_by_id_for_user(post_id, current_user_id_str) 
    if not post: return jsonify({"status": "fail", "message": "Post not found."}), 404
    return jsonify({"status": "success", "data": {"post": post}}), 200

@community_bp.route('/posts/<string:post_id>', methods=['PUT'])
@jwt_required()
def update_post_route(post_id):
    current_user_id_str = get_jwt_identity(); data = request.get_json()
    if not data: return jsonify({"status": "fail", "message": "Body empty."}), 400
    update_payload = {k: data[k] for k in data if k in ["title", "content_text", "image_url", "link_url", "tags"]}
    if not update_payload: return jsonify({"status": "fail", "message": "No updatable fields."}), 400
    try:
        result = Post.update_post(post_id, current_user_id_str, update_payload)
        if "post" in result: return jsonify({"status": "success", "message": result["message"], "data": {"post": result["post"]}}), 200
        else: current_app.logger.error(f"Post update {post_id} by {current_user_id_str} bad result: {result}"); return jsonify({"status": "error", "message": "Issue during update."}), 500
    except ValueError as ve: status_code = 404 if "not found" in str(ve).lower() else 400; return jsonify({"status": "fail", "message": str(ve)}), status_code
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: current_app.logger.error(f"Err updating post {post_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err updating post."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    try:
        success = Post.delete_post(post_id_str=post_id, user_id_str=current_user_id_str)
        if success:
            return jsonify({"status": "success", "message": "Post and associated comments deleted successfully."}), 200
        else:
            return jsonify({"status": "fail", "message": "Post not found or could not be deleted."}), 404
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: current_app.logger.error(f"Error deleting post {post_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "An unexpected error occurred while deleting post."}), 500

@community_bp.route('/posts/<string:post_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_post_route(post_id):
    current_user_id_str = get_jwt_identity(); data = request.get_json(); direction = data.get('direction')
    if not direction or direction not in ["up", "down", "none"]: return jsonify({"status": "fail", "message": "Invalid vote direction."}), 400
    try:
        result = Post.vote_on_post(post_id, current_user_id_str, direction)
        return jsonify({"status": "success", "message": result.get("message"), "data": {"upvotes": result.get("upvotes"), "downvotes": result.get("downvotes"), "user_vote": result.get("user_vote")}}), 200
    except ValueError as ve: status_code = 404 if "not found" in str(ve).lower() else 400; return jsonify({"status": "fail", "message": str(ve)}), status_code
    except Exception as e: current_app.logger.error(f"Err voting on post {post_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err voting on post."}), 500

# === Comment Management Routes ===
@community_bp.route('/posts/<string:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment_on_post_route(post_id):
    current_user_id_str = get_jwt_identity(); data = request.get_json(); text = data.get('text')
    parent_comment_id_str = data.get('parent_comment_id') # For replies
    if not text or not text.strip(): return jsonify({"status": "fail", "message": "Comment text empty."}), 400
    try:
        new_comment = Comment.create_comment(post_id_str=post_id, author_id_str=current_user_id_str, text=text, parent_comment_id_str=parent_comment_id_str)
        return jsonify({"status": "success", "data": {"comment": new_comment}}), 201
    except ValueError as ve: status_code = 404 if "not found" in str(ve).lower() else 400; return jsonify({"status": "fail", "message": str(ve)}), status_code
    except Exception as e: current_app.logger.error(f"Err creating comment on post {post_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err creating comment."}), 500

# GET /api/v1/posts/<postId>/comments - List TOP-LEVEL comments for a post
@community_bp.route('/posts/<string:post_id>/comments', methods=['GET'])
@jwt_required() 
def get_comments_for_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    try:
        page = request.args.get('page', 1, type=int); per_page = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sortBy', 'newest', type=str).lower()
        if page < 1: page = 1; 
        if per_page < 1: per_page = 1; 
        if per_page > 100: per_page = 100
        if sort_by not in ['newest', 'oldest']: sort_by = 'newest'
        
        # This fetches top-level comments by default (parent_id_str=None)
        result = Comment.get_comments_for_post_for_user(
            post_id_str=post_id, current_user_id_str=current_user_id_str, 
            page=page, per_page=per_page, sort_by=sort_by, parent_id_str=None 
        )
        return jsonify({"status": "success", "data": result['comments'], "pagination": {"total_items": result['total'], "total_pages": result['pages'], "current_page": result['page'], "per_page": result['per_page'], "sort_by": sort_by}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: current_app.logger.error(f"Err fetching comments for post {post_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Failed to retrieve comments."}), 500

# GET /api/v1/comments/<commentId>/replies - List REPLIES for a specific comment
@community_bp.route('/comments/<string:parent_comment_id>/replies', methods=['GET'])
@jwt_required()
def get_replies_for_comment_route(parent_comment_id):
    current_user_id_str = get_jwt_identity()
    # We need the post_id to which this parent_comment belongs, to ensure consistency
    # Or, the model method `get_comments_for_post_for_user` needs to be adapted if we don't pass post_id here
    # For now, let's assume we need to find the parent comment first to get its post_id
    parent_comment = Comment.find_by_id(parent_comment_id, current_user_id_str=None) # Don't need user_vote for parent itself here
    if not parent_comment:
        return jsonify({"status": "fail", "message": "Parent comment not found."}), 404
    
    post_id_for_replies = parent_comment.get("post_id")
    if not post_id_for_replies: # Should not happen if data is consistent
        return jsonify({"status": "error", "message": "Parent comment is not associated with a post."}), 500

    try:
        page = request.args.get('page', 1, type=int); per_page = request.args.get('limit', 10, type=int) # Fewer replies per page
        sort_by = request.args.get('sortBy', 'oldest', type=str).lower() # Replies often shown oldest first
        if page < 1: page = 1; 
        if per_page < 1: per_page = 1; 
        if per_page > 50: per_page = 50
        if sort_by not in ['newest', 'oldest']: sort_by = 'oldest'

        result = Comment.get_comments_for_post_for_user(
            post_id_str=post_id_for_replies, 
            current_user_id_str=current_user_id_str, 
            page=page, per_page=per_page, sort_by=sort_by, 
            parent_id_str=parent_comment_id # Pass the parent_id to fetch its children
        )
        return jsonify({
            "status": "success", "data": result['comments'],
            "pagination": {
                "total_items": result['total'], "total_pages": result['pages'],
                "current_page": result['page'], "per_page": result['per_page'],
                "sort_by": sort_by
            }
        }), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: current_app.logger.error(f"Err fetching replies for Cmnt:{parent_comment_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Failed to retrieve replies."}), 500


@community_bp.route('/comments/<string:comment_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_comment_route(comment_id):
    current_user_id_str = get_jwt_identity(); data = request.get_json(); direction = data.get('direction')
    if not direction or direction not in ["up", "down", "none"]: return jsonify({"status": "fail", "message": "Invalid vote direction."}), 400
    try:
        result = Comment.vote_on_comment(comment_id, current_user_id_str, direction)
        return jsonify({"status": "success", "message": result.get("message"), "data": {"upvotes": result.get("upvotes"), "downvotes": result.get("downvotes"), "user_vote": result.get("user_vote")}}), 200
    except ValueError as ve: status_code = 404 if "not found" in str(ve).lower() else 400; return jsonify({"status": "fail", "message": str(ve)}), status_code
    except Exception as e: current_app.logger.error(f"Err voting on comment {comment_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err voting on comment."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment_route(comment_id):
    current_user_id_str = get_jwt_identity(); data = request.get_json(); new_text = data.get('text')
    if not new_text or not new_text.strip(): return jsonify({"status": "fail", "message": "Comment text empty."}), 400
    try:
        updated_comment = Comment.update_comment(comment_id_str=comment_id, author_id_str=current_user_id_str, new_text=new_text)
        return jsonify({"status": "success", "data": {"comment": updated_comment}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: current_app.logger.error(f"Err updating comment {comment_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err updating comment."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    try:
        success = Comment.delete_comment(comment_id_str=comment_id, user_id_str=current_user_id_str)
        if success:
            return jsonify({"status": "success", "message": "Comment deleted successfully."}), 200
        else:
            return jsonify({"status": "fail", "message": "Comment not found or could not be deleted."}), 404
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: current_app.logger.error(f"Err deleting comment {comment_id}: {e}", exc_info=True); return jsonify({"status": "error", "message": "Err deleting comment."}), 500