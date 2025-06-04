# flask_service/app/routes/community_routes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.community import Community
from app.models.post import Post 
from app.models.comment import Comment
from bson import ObjectId, errors as bson_errors

community_bp = Blueprint('community_bp', __name__)

# === Community Management Routes ===
@community_bp.route('/communities', methods=['POST'])
@jwt_required()
def create_community_route():
    # Assuming frontend sends camelCase for community creation based on your model.
    # If it sends snake_case, adjust data.get('icon') to data.get('icon_url') etc.
    data = request.get_json() 
    current_user_id = get_jwt_identity()
    try:
        new_community = Community.create_community(
            name=data.get('name'), 
            description=data.get('description'), 
            created_by_id_str=current_user_id,
            rules=data.get('rules'), 
            icon_url=data.get('icon'), # Matches Community.create_community expecting icon_url
            banner_image_url=data.get('bannerImage'), # Matches Community.create_community
            tags=data.get('tags')
        )
        if not new_community:
             return jsonify({"status": "fail", "message": "Community could not be created."}), 400
        return jsonify({"status": "success", "data": {"community": new_community}}), 201
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: 
        current_app.logger.error(f"Error creating community: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not create community."}), 500

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
        search_query = request.args.get('searchQuery', type=str) # Query params often camelCase
        result = Community.get_all_communities(page=page, per_page=per_page, search_query=search_query, current_user_id_str=current_user_id_str)
        return jsonify({"status": "success", "data": result['communities'], "results": result['total'],
                        "pagination": {"totalItems": result['total'], "totalPages": result['pages'], 
                                       "currentPage": result['page'], "perPage": result['per_page']}}), 200
    except Exception as e: 
        current_app.logger.error(f"Error list communities: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed list communities."}), 500

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
        current_app.logger.error(f"Err C detail {community_id_or_slug}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not get C details."}), 500

@community_bp.route('/communities/<string:community_id>/join', methods=['POST'])
@jwt_required()
def join_community_route(community_id):
    current_user_id = get_jwt_identity()
    try:
        result = Community.join_community(community_id, current_user_id)
        status_code = 200
        if result.get("already_member"): status_code = 409
        elif not result.get("modified"): status_code = 400
        
        updated_community_data = Community.find_by_id_or_slug(community_id, current_user_id) if result.get("modified") else None
        
        return jsonify({
            "status": "success" if result.get("modified") else "fail", 
            "message": result["message"],
            "data": {"community": updated_community_data} if updated_community_data else None
        }), status_code
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: 
        current_app.logger.error(f"Err joining C {community_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not join community."}), 500

@community_bp.route('/communities/<string:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community_route(community_id):
    current_user_id = get_jwt_identity()
    try:
        result = Community.leave_community(community_id, current_user_id)
        status_code = 200
        if result.get("not_member"): status_code = 400
        elif not result.get("modified"): status_code = 400
        
        updated_community_data = Community.find_by_id_or_slug(community_id, current_user_id) if result.get("modified") else None

        return jsonify({
            "status": "success" if result.get("modified") else "fail", 
            "message": result["message"],
            "data": {"community": updated_community_data} if updated_community_data else None
        }), status_code
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: 
        current_app.logger.error(f"Err leaving C {community_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not leave community."}), 500


# === Post Management Routes ===
@community_bp.route('/communities/<string:community_id_from_url>/posts', methods=['POST'])
@jwt_required()
def create_post_in_community_route(community_id_from_url):
    current_user_id_str = get_jwt_identity()
    
    current_app.logger.info(f"--- FLASK: Attempting to create post in community: {community_id_from_url} by user: {current_user_id_str} ---")
    current_app.logger.info(f"FLASK create_post - Request Headers: {request.headers}")
    current_app.logger.info(f"FLASK create_post - Request Mimetype: {request.mimetype}")
    
    received_data = None
    try:
        received_data = request.get_json()
        current_app.logger.info(f"FLASK create_post - Successfully parsed JSON data: {received_data}")
    except Exception as e:
        current_app.logger.error(f"FLASK create_post - Failed to parse request body as JSON: {e}", exc_info=True)
        try:
            raw_data = request.get_data(as_text=True)
            current_app.logger.info(f"FLASK create_post - Raw request data (if not JSON): {raw_data[:500]}...")
        except Exception as data_err:
            current_app.logger.error(f"FLASK create_post - Could not get raw request data: {data_err}")
        return jsonify({"status": "fail", "message": "Invalid JSON format in request body."}), 400
    
    if received_data is None:
        current_app.logger.error(f"FLASK create_post - Data is None after get_json() call, but no exception was raised.")
        return jsonify({"status": "fail", "message": "Request body is empty or not processed."}), 400

    data = received_data 

    try:
        # Log with the keys we are *actually* using to retrieve values from the parsed JSON
        current_app.logger.info(f"FLASK create_post - Calling Post.create_post with title: '{data.get('title')}', content_type from data.get('content_type'): '{data.get('content_type')}'")
        
        new_post = Post.create_post(
            community_id_str=community_id_from_url, 
            author_id_str=current_user_id_str, 
            title=data.get('title'), 
            content_type=data.get('content_type'),      # Expect snake_case from JSON
            content_text=data.get('content_text'),      # Expect snake_case from JSON
            image_url=data.get('image_url'),            # Expect snake_case from JSON
            link_url=data.get('link_url'),              # Expect snake_case from JSON
            tags=data.get('tags')                       # Assuming 'tags' is fine as is
        )
        current_app.logger.info(f"FLASK create_post - Post created successfully: {new_post.get('id') if new_post else 'None'}")
        return jsonify({"status": "success", "data": {"post": new_post}}), 201
    except ValueError as ve: 
        current_app.logger.warning(f"FLASK create_post - ValueError during Post.create_post: {str(ve)}")
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: 
        current_app.logger.error(f"FLASK create_post - Unexpected error during Post.create_post for C:{community_id_from_url}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not create post due to an internal error."}), 500

# ... (The rest of your routes: GET posts, PUT post, DELETE post, POST vote, comment routes, etc.
#      Ensure consistency in how you expect JSON keys (snake_case vs camelCase) for those routes too.
#      I've updated them below assuming snake_case for request bodies where applicable,
#      but kept query params like 'sortBy' as camelCase as that's common.)

@community_bp.route('/communities/<string:community_id>/posts', methods=['GET'])
@jwt_required(optional=True)
def get_posts_for_community_route(community_id):
    current_app.logger.info(f"--- FLASK ROUTE HIT: /communities/{community_id}/posts (Full path from Blueprint root) ---")
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
        
        current_app.logger.info(f"--- FLASK: Posts for C:{community_id} - Found: {len(result.get('posts',[]))}, Total: {result.get('total',0)} ---")
        return jsonify({"status": "success", "data": result.get('posts',[]), "results": result.get('total',0),
                        "pagination": {"totalItems": result.get('total',0), "totalPages": result.get('pages',0), 
                                       "currentPage": result.get('page',1), "perPage": result.get('per_page',10), "sortBy": sort_by }}), 200
    except ValueError as ve: 
        current_app.logger.warn(f"ValueError C posts {community_id}: {ve}")
        return jsonify({"status": "fail", "message": str(ve)}), 404
    except Exception as e: 
        current_app.logger.error(f"Error C posts {community_id}: {e}", exc_info=True)
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
        current_app.logger.error(f"Err get post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not get post."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['PUT'])
@jwt_required()
def update_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    if not data: return jsonify({"status": "fail", "message": "Request body is empty."}), 400
    
    update_payload = {}
    if 'title' in data: update_payload['title'] = data['title']
    if 'content_text' in data: update_payload['content_text'] = data['content_text']
    if 'image_url' in data: update_payload['image_url'] = data['image_url']
    if 'link_url' in data: update_payload['link_url'] = data['link_url']
    if 'tags' in data: update_payload['tags'] = data['tags']

    if not update_payload: return jsonify({"status": "fail", "message": "No updatable fields provided or fields are empty."}), 400
    try:
        result = Post.update_post(post_id, current_user_id_str, update_payload)
        return jsonify({"status": "success", "message": result.get("message", "Post updated."), "data": {"post": result.get("post")}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: 
        current_app.logger.error(f"Err updating post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not update post."}), 500

@community_bp.route('/posts/<string:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    try:
        success = Post.delete_post(post_id_str=post_id, user_id_str=current_user_id_str)
        if success: return jsonify({"status": "success", "message": "Post deleted."}), 200
        else: return jsonify({"status": "fail", "message": "Post not found or not authorized."}), 404
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: 
        current_app.logger.error(f"Err deleting post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not delete post."}), 500

@community_bp.route('/posts/<string:post_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    direction = data.get('direction')
    if not direction or direction not in ["up", "down", "none"]: return jsonify({"status": "fail", "message": "Invalid vote direction."}), 400
    try:
        updated_post_data = Post.vote_on_post(post_id, current_user_id_str, direction)
        return jsonify({"status": "success", "message": "Vote processed.", 
                        "data": { 
                            "upvotes": updated_post_data.get("upvotes"), 
                            "downvotes": updated_post_data.get("downvotes"), 
                            "user_vote": updated_post_data.get("userVote")
                        }}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except Exception as e: 
        current_app.logger.error(f"Err voting on post {post_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not process vote."}), 500

# === Comment Management Routes ===
@community_bp.route('/posts/<string:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment_on_post_route(post_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    text = data.get('text')
    parent_comment_id_str = data.get('parent_comment_id') # Expect snake_case from JSON
    if not text or not text.strip(): return jsonify({"status": "fail", "message": "Comment text required."}), 400
    try:
        new_comment = Comment.create_comment(post_id_str=post_id, author_id_str=current_user_id_str, text=text, parent_comment_id_str=parent_comment_id_str)
        return jsonify({"status": "success", "data": {"comment": new_comment}}), 201
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except Exception as e: 
        current_app.logger.error(f"Err creating comment on P:{post_id}: {e}", exc_info=True)
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
                        "pagination": {"totalItems": result.get('total',0), "totalPages": result.get('pages',0), 
                                       "currentPage": result.get('page',1), "perPage": result.get('per_page',10), "sortBy": sort_by}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: 
        current_app.logger.error(f"Err fetching comments for P:{post_id}: {e}", exc_info=True)
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
        parent_comment = Comment.find_by_id(parent_comment_id)
        if not parent_comment: return jsonify({"status": "fail", "message": "Parent comment not found."}), 404
        post_id_for_replies = parent_comment.get("post_id") # Assuming Comment model returns snake_case
        if not post_id_for_replies: return jsonify({"status": "error", "message": "Parent comment missing post association."}), 500

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int) 
        sort_by = request.args.get('sortBy', 'oldest', type=str).lower() 
        
        if page < 1: page = 1
        if per_page < 1: per_page = 1
        elif per_page > 50: per_page = 50
        if sort_by not in ['newest', 'oldest']: sort_by = 'oldest'

        result = Comment.get_comments_for_post_for_user(
            post_id_str=str(post_id_for_replies), 
            current_user_id_str=current_user_id_str, 
            page=page, per_page=per_page, sort_by=sort_by, 
            parent_id_str=parent_comment_id
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
        current_app.logger.warn(f"ValueError getting replies for Cmnt:{parent_comment_id}: {ve}")
        return jsonify({"status": "fail", "message": str(ve)}), 400
    except Exception as e: 
        current_app.logger.error(f"Err fetching replies for Cmnt:{parent_comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to get replies."}), 500

@community_bp.route('/comments/<string:comment_id>/vote', methods=['POST'])
@jwt_required()
def vote_on_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    direction = data.get('direction')
    if not direction or direction not in ["up", "down", "none"]: return jsonify({"status": "fail", "message": "Invalid vote direction."}), 400
    try:
        result_dict = Comment.vote_on_comment(comment_id, current_user_id_str, direction)
        return jsonify({"status": "success", "message": result_dict.get("message"), 
                        "data": {"upvotes": result_dict.get("upvotes"), "downvotes": result_dict.get("downvotes"), 
                                 "user_vote": result_dict.get("user_vote")}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except Exception as e: 
        current_app.logger.error(f"Err voting on Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not process vote."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    data = request.get_json()
    new_text = data.get('text')
    if not new_text or not new_text.strip(): return jsonify({"status": "fail", "message": "Comment text required."}), 400
    try:
        updated_comment = Comment.update_comment(comment_id_str=comment_id, author_id_str=current_user_id_str, new_text=new_text)
        return jsonify({"status": "success", "data": {"comment": updated_comment}}), 200
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404 if "not found" in str(ve).lower() else 400
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: 
        current_app.logger.error(f"Err updating Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not update comment."}), 500

@community_bp.route('/comments/<string:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment_route(comment_id):
    current_user_id_str = get_jwt_identity()
    try:
        success = Comment.delete_comment(comment_id_str=comment_id, user_id_str=current_user_id_str)
        if success: return jsonify({"status": "success", "message": "Comment deleted."}), 200
        else: return jsonify({"status": "fail", "message": "Comment not found or not authorized."}), 404
    except ValueError as ve: return jsonify({"status": "fail", "message": str(ve)}), 404
    except PermissionError as pe: return jsonify({"status": "fail", "message": str(pe)}), 403
    except Exception as e: 
        current_app.logger.error(f"Err deleting Cmnt {comment_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Could not delete comment."}), 500