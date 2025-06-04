# flask_service/app/models/post.py
from app import mongo
from datetime import datetime, timezone # Added timezone for consistency if needed
from bson import ObjectId, errors as bson_errors
from app.models.community import Community 
from flask import current_app
from app.models.comment import Comment 

class Post:
    @staticmethod
    def get_collection():
        return mongo.db.posts

    @staticmethod
    def create_post(community_id_str, author_id_str, title, content_type, content_text=None, image_url=None, link_url=None, tags=None):
        # --- Validations for required fields ---
        if not community_id_str: raise ValueError("Community ID is required.")
        if not author_id_str: raise ValueError("Author ID is required.")
        if not title or len(title.strip()) < 3: raise ValueError("Post title required (min 3 chars).")
        
        # This validation is crucial and was the source of the "Invalid post content type"
        if content_type not in ["text", "image", "link"]: 
            current_app.logger.error(f"Post.create_post - Received invalid content_type: '{content_type}'")
            raise ValueError("Invalid post content type. Must be 'text', 'image', or 'link'.")

        if content_type == "text" and not (content_text and content_text.strip()): raise ValueError("Text content required for text post.")
        if content_type == "image" and not image_url: raise ValueError("Image URL required for image post.")
        if content_type == "link" and not link_url: raise ValueError("Link URL required for link post.")
        
        # --- Fetch and validate community using the existing find_by_id_or_slug method ---
        # Pass None for current_user_id_str as it's likely not needed for this specific check.
        # Your Community.find_by_id_or_slug should handle current_user_id_str=None.
        community_dict = Community.find_by_id_or_slug(community_id_str, current_user_id_str=None) 
        
        if not community_dict: 
            raise ValueError(f"Community '{community_id_str}' not found when creating post.")
        
        # Get the resolved ID from the fetched community dictionary.
        # Your Community.to_dict returns 'id' as the string representation of _id.
        resolved_community_id_str = community_dict.get('id')
        if not resolved_community_id_str:
             raise ValueError(f"Could not resolve community ID for '{community_id_str}' from fetched community data.")

        try:
            community_id_obj = ObjectId(resolved_community_id_str)
            author_id_obj = ObjectId(author_id_str)
        except bson_errors.InvalidId: 
            current_app.logger.error(f"Post.create_post - Invalid ObjectId format. Resolved Community ID: '{resolved_community_id_str}', Author ID: '{author_id_str}'")
            raise ValueError("Invalid Community ID or Author ID format.")
        except Exception as e: # Catch other potential errors during ObjectId conversion
            current_app.logger.error(f"Post.create_post - Unexpected error during ObjectId conversion: {e}", exc_info=True)
            raise ValueError("Error processing Community or Author ID.")

        post_data = {
            "community_id": community_id_obj, 
            "community_slug": community_dict.get('slug'), 
            "community_name": community_dict.get('name'), 
            "author_id": author_id_obj,
            "title": title.strip(), 
            "content_type": content_type,
            "content_text": content_text.strip() if content_text else None,
            "image_url": image_url,  # Assuming these are passed as snake_case from routes
            "link_url": link_url,    # Assuming these are passed as snake_case from routes
            "tags": [tag.strip().lower() for tag in tags if isinstance(tag, str) and tag.strip()] if tags else [],
            "upvotes": 0, 
            "downvotes": 0, 
            "upvoted_by": [], 
            "downvoted_by": [],
            "comment_count": 0, 
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc), 
            "last_activity_at": datetime.now(timezone.utc) 
        }
        result = Post.get_collection().insert_one(post_data)
        post_data['_id'] = result.inserted_id
        # Pass author_id as current_user_id_str for initial vote status in to_dict
        return Post.to_dict(post_data, current_user_id_str=str(author_id_obj))

    # ... (rest of your Post model: vote_on_post, update_post, delete_post, to_dict, find_by_id_for_user, get_posts_for_community_for_user)
    # Ensure your to_dict and other methods are consistent with data structures.
    @staticmethod
    def to_dict(post_doc, current_user_id_str=None):
        if not post_doc: return None

        author_display_name = "Unknown Author" # Default
        author_id_for_object = "unknown"
        author_avatar_url = None

        author_id_obj = post_doc.get("author_id")
        if author_id_obj:
            author_id_for_object = str(author_id_obj) # Store the ID regardless
            author_doc_from_db = User.find_by_id(str(author_id_obj)) 
            if author_doc_from_db:
                full_name = author_doc_from_db.get("name")
                usn = author_doc_from_db.get("usn")
                
                if full_name and usn:
                    author_display_name = f"{full_name} - {usn.upper()}"
                elif full_name:
                    author_display_name = full_name
                elif usn: # Should ideally not happen if name is always present for a user
                    author_display_name = usn.upper()
                else: # Name and USN both missing from user doc
                    author_display_name = "User Details Missing"
                
                author_avatar_url = author_doc_from_db.get("avatar")
            else:
                # Author ID present but user not found
                author_display_name = f"User Not Found ({str(author_id_obj)[:8]}...)"
        else:
            # No author_id in post_doc
            author_display_name = "Author ID Missing"
            
        author_details = {
            "id": author_id_for_object,
            "name": author_display_name, # Combined name and USN
            "avatarUrl": author_avatar_url 
        }

        data = {
            "id": str(post_doc["_id"]),
            "community_id": str(post_doc.get("community_id")),
            "community_slug": post_doc.get("community_slug"),
            "community_name": post_doc.get("community_name"),
            "author": author_details, # EMBEDDED AUTHOR OBJECT with combined name
            "title": post_doc.get("title"), 
            "content_type": post_doc.get("content_type"),
            "content_text": post_doc.get("content_text"), 
            "image_url": post_doc.get("image_url"),
            "link_url": post_doc.get("link_url"), 
            "tags": post_doc.get("tags", []),
            "upvotes": post_doc.get("upvotes", 0), 
            "downvotes": post_doc.get("downvotes", 0),
            "comment_count": post_doc.get("comment_count", 0),
            "created_at": post_doc.get("created_at").isoformat() if post_doc.get("created_at") else None,
            "updated_at": post_doc.get("updated_at").isoformat() if post_doc.get("updated_at") else None,
            "last_activity_at": post_doc.get("last_activity_at").isoformat() if post_doc.get("last_activity_at") else None,
            "user_vote": None 
        }
        # ... (user_vote logic remains the same) ...
        if current_user_id_str:
            try:
                user_obj_id = ObjectId(current_user_id_str)
                if user_obj_id in post_doc.get("upvoted_by", []): data["user_vote"] = "up"
                elif user_obj_id in post_doc.get("downvoted_by", []): data["user_vote"] = "down"
            except bson_errors.InvalidId:
                current_app.logger.warning(f"Post.to_dict: Invalid current_user_id_str for vote check: {current_user_id_str}")
            except Exception as e: 
                current_app.logger.warning(f"Vote determination error for user {current_user_id_str} on post {data['id']}: {e}")
        return data

    # Example for find_by_id_for_user (should already exist based on your routes)
    @staticmethod
    def find_by_id_for_user(post_id_str, current_user_id_str=None):
        try:
            post_doc = Post.get_collection().find_one({"_id": ObjectId(post_id_str)})
            return Post.to_dict(post_doc, current_user_id_str) if post_doc else None
        except bson_errors.InvalidId:
            current_app.logger.warning(f"Post.find_by_id_for_user: Invalid post_id_str: {post_id_str}")
            return None
        except Exception as e:
            current_app.logger.error(f"Post.find_by_id_for_user: Error finding post {post_id_str}: {e}", exc_info=True)
            return None
    
    # Example for get_posts_for_community_for_user (should already exist)
    @staticmethod
    def get_posts_for_community_for_user(community_id_str, current_user_id_str=None, page=1, per_page=10, sort_by="new"):
        try:
            community_id_obj = ObjectId(community_id_str)
        except bson_errors.InvalidId: 
            raise ValueError("Invalid Community ID format")
        query = {"community_id": community_id_obj}
        sort_field, sort_order = "created_at", -1 
        if sort_by == "hot": sort_field = "last_activity_at" 
        elif sort_by == "top": sort_field = "upvotes" # Consider adding an index for this if used often
        
        skip_count = (page - 1) * per_page
        posts_cursor = Post.get_collection().find(query).sort(sort_field, sort_order).skip(skip_count).limit(per_page)
        posts_list = [Post.to_dict(post, current_user_id_str) for post in posts_cursor]
        total_posts = Post.get_collection().count_documents(query)
        return {
            "posts": posts_list, "total": total_posts, "page": page,
            "per_page": per_page, "pages": (total_posts + per_page - 1) // per_page if per_page > 0 else 0
        }

    # Add other methods like update_post, delete_post, vote_on_post if they are not already complete
    # For example:
    @staticmethod
    def update_post(post_id_str, author_id_str, update_data):
        try:
            post_id_obj = ObjectId(post_id_str)
            author_id_obj = ObjectId(author_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid Post/Author ID for update.")
        
        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post: raise ValueError("Post not found for update.")
        if post.get("author_id") != author_id_obj: raise PermissionError("Not authorized to edit this post.")

        allowed_updates = {}
        if "title" in update_data and update_data["title"] is not None: # Check for None
            title = update_data["title"].strip()
            if len(title) < 3: raise ValueError("Updated title too short (min 3 chars).")
            allowed_updates["title"] = title
        
        content_type_from_db = post.get("content_type") # Get content_type from existing post

        # Only update content based on its original type. Type change is not typically allowed in simple updates.
        if "content_text" in update_data and content_type_from_db == "text":
            allowed_updates["content_text"] = update_data["content_text"].strip() if update_data["content_text"] else None
            if not allowed_updates["content_text"]: raise ValueError("Text content cannot be empty for a text post.")
        if "image_url" in update_data and content_type_from_db == "image":
            allowed_updates["image_url"] = update_data["image_url"]
            if not allowed_updates["image_url"]: raise ValueError("Image URL cannot be empty for an image post.")
        if "link_url" in update_data and content_type_from_db == "link":
            allowed_updates["link_url"] = update_data["link_url"]
            if not allowed_updates["link_url"]: raise ValueError("Link URL cannot be empty for a link post.")
        
        if "tags" in update_data and isinstance(update_data["tags"], list):
            allowed_updates["tags"] = [tag.strip().lower() for tag in update_data["tags"] if isinstance(tag, str) and tag.strip()]
        
        if not allowed_updates: 
            # Return current post if no valid changes were made
            return {"message": "No valid fields to update or no changes detected.", "post": Post.to_dict(post, author_id_str)}

        allowed_updates["updated_at"] = datetime.now(timezone.utc)
        allowed_updates["last_activity_at"] = datetime.now(timezone.utc) # Also update last activity

        res = Post.get_collection().update_one({"_id": post_id_obj, "author_id": author_id_obj}, {"$set": allowed_updates})
        
        updated_doc = Post.get_collection().find_one({"_id": post_id_obj}) # Fetch the updated document
        msg = "No changes applied."
        if res.modified_count > 0: msg = "Post updated successfully."
        return {"message": msg, "post": Post.to_dict(updated_doc, author_id_str)}


    @staticmethod
    def delete_post(post_id_str, user_id_str): 
        try:
            post_id_obj = ObjectId(post_id_str)
            user_id_obj = ObjectId(user_id_str)
        except bson_errors.InvalidId:
            raise ValueError("Invalid Post ID or User ID format for delete.")

        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post:
            raise ValueError("Post not found to delete.")

        if post.get("author_id") != user_id_obj: # Ensure author_id is stored as ObjectId in DB
            raise PermissionError("User is not authorized to delete this post.")
        
        community_id_obj = post.get("community_id") # Get community_id from the post

        # 1. Delete all comments associated with this post
        try:
            comment_delete_result = Comment.get_collection().delete_many({"post_id": post_id_obj})
            current_app.logger.info(f"Cascaded delete: {comment_delete_result.deleted_count} comments for post {post_id_str}")
        except Exception as e:
            current_app.logger.error(f"Error during cascading delete of comments for post {post_id_str}: {e}", exc_info=True)
            # Decide if this should halt the post deletion or just be logged

        # 2. Delete the post itself
        delete_result = Post.get_collection().delete_one({"_id": post_id_obj, "author_id": user_id_obj})

        if delete_result.deleted_count > 0:
            # 3. Decrement postCount in the community
            if community_id_obj: # Check if community_id was found
                Community.increment_post_count(community_id_obj, amount=-1)
            return True
        else:
            current_app.logger.warning(f"Post {post_id_str} delete operation by author {user_id_str} affected 0 documents, though post was initially found.")
            return False # Should not happen if the initial find and permission check passed

    @staticmethod
    def vote_on_post(post_id_str, user_id_str, vote_direction):
        try:
            post_id_obj = ObjectId(post_id_str)
            user_id_obj = ObjectId(user_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid Post/User ID format for vote.")
        
        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post: raise ValueError("Post not found for vote.")

        is_up = user_id_obj in post.get("upvoted_by", [])
        is_down = user_id_obj in post.get("downvoted_by", [])
        pull_ops, add_ops, inc_ops = {}, {}, {}

        if vote_direction == "up":
            if is_up: 
                pull_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = -1
            else:
                if is_down: 
                    pull_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = -1
                add_ops["$addToSet"] = {"upvoted_by": user_id_obj}; inc_ops["upvotes"] = 1 # Use $addToSet for add_ops
        elif vote_direction == "down":
            if is_down: 
                pull_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = -1
            else:
                if is_up: 
                    pull_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = -1
                add_ops["$addToSet"] = {"downvoted_by": user_id_obj}; inc_ops["downvotes"] = 1 # Use $addToSet for add_ops
        elif vote_direction == "none": # Retract vote
            if is_up: 
                pull_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = -1
            if is_down: 
                pull_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = -1
        else: 
            raise ValueError("Invalid vote direction.")

        update_query = {}
        msg = "No change in vote status."

        if pull_ops: 
            update_query.setdefault("$pull", {}).update(pull_ops)
        if add_ops: # add_ops now contains {"$addToSet": ...}
            update_query.update(add_ops)
        if inc_ops: 
            update_query.setdefault("$inc", {}).update(inc_ops)
        
        if update_query: # Only update if there are actual operations
            update_query.setdefault("$set", {}).update({"updated_at": datetime.now(timezone.utc), "last_activity_at": datetime.now(timezone.utc)})
            
            result = Post.get_collection().update_one({"_id": post_id_obj}, update_query)
            
            if result.modified_count > 0 or (inc_ops and result.matched_count > 0):
                msg = "Vote processed successfully."
        
        current_post_doc = Post.get_collection().find_one({"_id": post_id_obj})
        current_post_dict = Post.to_dict(current_post_doc, user_id_str) # Pass user_id_str to get updated user_vote
        
        return {
            "message": msg, 
            "upvotes": current_post_dict.get("upvotes"), 
            "downvotes": current_post_dict.get("downvotes"), 
            "user_vote": current_post_dict.get("user_vote")
        }