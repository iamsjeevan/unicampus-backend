# app/models/post.py
from app import mongo
from datetime import datetime
from bson import ObjectId
from app.models.community import Community 
from flask import current_app

class Post:
    @staticmethod
    def get_collection():
        return mongo.db.posts

    @staticmethod
    def create_post(community_id, author_id, title, content_type, content_text=None, image_url=None, link_url=None, tags=None):
        if not community_id:
            raise ValueError("Community ID is required to create a post.")
        if not author_id:
            raise ValueError("Author ID is required to create a post.")
        if not title or len(title.strip()) < 3:
            raise ValueError("Post title is required and must be at least 3 characters long.")
        if not content_type in ["text", "image", "link"]:
            raise ValueError("Invalid post content type. Must be 'text', 'image', or 'link'.")

        if content_type == "text" and (not content_text or len(content_text.strip()) == 0):
            raise ValueError("Text content is required for a text post.")
        if content_type == "image" and not image_url:
            raise ValueError("Image URL is required for an image post.")
        if content_type == "link" and not link_url:
            raise ValueError("Link URL is required for a link post.")
        
        community = Community.find_by_id(community_id) 
        if not community:
            if not ObjectId.is_valid(community_id): 
                community = Community.find_by_slug(community_id)
            if not community: 
                raise ValueError(f"Community with ID or slug '{community_id}' not found.")
            community_id = community['id'] 

        post_data = {
            "community_id": ObjectId(community_id),
            "community_slug": community.get('slug'), 
            "community_name": community.get('name'), 
            "author_id": ObjectId(author_id),
            "title": title.strip(),
            "content_type": content_type,
            "content_text": content_text.strip() if content_text else None,
            "image_url": image_url,
            "link_url": link_url,
            "tags": [tag.strip().lower() for tag in tags if tag.strip()] if tags else [],
            "upvotes": 0,
            "downvotes": 0,
            "upvoted_by": [], 
            "downvoted_by": [],
            "comment_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_activity_at": datetime.utcnow() 
        }
        result = Post.get_collection().insert_one(post_data)
        post_data['_id'] = result.inserted_id
        return Post.to_dict(post_data, current_user_id_str=str(author_id))

    @staticmethod
    def vote_on_post(post_id_str, user_id_str, vote_direction):
        try:
            post_id_obj = ObjectId(post_id_str)
            user_id_obj = ObjectId(user_id_str)
        except Exception:
            raise ValueError("Invalid Post ID or User ID format.")

        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post:
            raise ValueError("Post not found.")

        is_currently_upvoted = user_id_obj in post.get("upvoted_by", [])
        is_currently_downvoted = user_id_obj in post.get("downvoted_by", [])
        
        pull_ops = {}
        add_to_set_ops = {} 
        inc_ops = {}

        if vote_direction == "up":
            if is_currently_upvoted: 
                pull_ops["upvoted_by"] = user_id_obj
                if "upvotes" not in inc_ops: inc_ops["upvotes"] = 0
                inc_ops["upvotes"] -= 1
            else: 
                if is_currently_downvoted:
                    pull_ops["downvoted_by"] = user_id_obj
                    if "downvotes" not in inc_ops: inc_ops["downvotes"] = 0
                    inc_ops["downvotes"] -= 1
                add_to_set_ops["upvoted_by"] = user_id_obj
                if "upvotes" not in inc_ops: inc_ops["upvotes"] = 0
                inc_ops["upvotes"] += 1
        
        elif vote_direction == "down":
            if is_currently_downvoted: 
                pull_ops["downvoted_by"] = user_id_obj
                if "downvotes" not in inc_ops: inc_ops["downvotes"] = 0
                inc_ops["downvotes"] -= 1
            else: 
                if is_currently_upvoted:
                    pull_ops["upvoted_by"] = user_id_obj
                    if "upvotes" not in inc_ops: inc_ops["upvotes"] = 0
                    inc_ops["upvotes"] -= 1
                add_to_set_ops["downvoted_by"] = user_id_obj
                if "downvotes" not in inc_ops: inc_ops["downvotes"] = 0
                inc_ops["downvotes"] += 1

        elif vote_direction == "none": 
            if is_currently_upvoted:
                pull_ops["upvoted_by"] = user_id_obj
                if "upvotes" not in inc_ops: inc_ops["upvotes"] = 0
                inc_ops["upvotes"] -= 1
            if is_currently_downvoted: 
                pull_ops["downvoted_by"] = user_id_obj
                if "downvotes" not in inc_ops: inc_ops["downvotes"] = 0
                inc_ops["downvotes"] -= 1
        else:
            raise ValueError("Invalid vote direction. Must be 'up', 'down', or 'none'.")

        update_query = {}
        if pull_ops: 
            update_query["$pull"] = pull_ops # <<< --- CORRECTED HERE ---
        if add_to_set_ops: 
            update_query["$addToSet"] = add_to_set_ops
        if inc_ops: 
            update_query["$inc"] = inc_ops
        
        final_message = "No change in vote status or vote already in desired state."

        if update_query: 
            update_query["$set"] = {"updated_at": datetime.utcnow(), "last_activity_at": datetime.utcnow()}
            result = Post.get_collection().update_one({"_id": post_id_obj}, update_query)
            
            # Check if any actual modification to arrays or counts happened
            # modified_count is for $set, $unset, $rename, etc.
            # $inc always matches if doc exists, so check if value actually changed or if an array was modified
            # A more reliable check might be to compare vote counts before and after for $inc
            if result.modified_count > 0 or pull_ops or add_to_set_ops or (inc_ops and result.matched_count > 0):
                final_message = "Vote processed successfully."
        
        current_post_doc = Post.get_collection().find_one({"_id": post_id_obj})
        current_post_dict = Post.to_dict(current_post_doc, user_id_str)
        return {
            "message": final_message,
            "upvotes": current_post_dict.get("upvotes"),
            "downvotes": current_post_dict.get("downvotes"),
            "user_vote": current_post_dict.get("user_vote")
        }

    @staticmethod
    def to_dict(post_doc, current_user_id_str=None):
        if not post_doc:
            return None
        
        data = {
            "id": str(post_doc["_id"]),
            "community_id": str(post_doc.get("community_id")),
            "community_slug": post_doc.get("community_slug"),
            "community_name": post_doc.get("community_name"),
            "author_id": str(post_doc.get("author_id")),
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

        if current_user_id_str:
            try:
                user_id_obj_for_vote_check = ObjectId(current_user_id_str)
                upvoted_by_list = post_doc.get("upvoted_by", [])
                downvoted_by_list = post_doc.get("downvoted_by", [])
                if user_id_obj_for_vote_check in upvoted_by_list:
                    data["user_vote"] = "up"
                elif user_id_obj_for_vote_check in downvoted_by_list:
                    data["user_vote"] = "down"
            except Exception as e:
                current_app.logger.warning(f"Error determining user vote for user {current_user_id_str} on post {data['id']}: {e}")
        return data

    @staticmethod
    def find_by_id_for_user(post_id_str, current_user_id_str=None):
        try:
            post_doc = Post.get_collection().find_one({"_id": ObjectId(post_id_str)})
            return Post.to_dict(post_doc, current_user_id_str) if post_doc else None
        except Exception:
            return None

    @staticmethod
    def get_posts_for_community_for_user(community_id_str, current_user_id_str=None, page=1, per_page=10, sort_by="new"):
        try:
            community_id_obj = ObjectId(community_id_str)
        except Exception:
            raise ValueError("Invalid Community ID format")

        query = {"community_id": community_id_obj}
        sort_field = "created_at"
        sort_order = -1 
        if sort_by == "hot": sort_field = "last_activity_at" 
        elif sort_by == "top": sort_field = "upvotes"
        
        skip_count = (page - 1) * per_page
        posts_cursor = Post.get_collection().find(query).sort(sort_field, sort_order).skip(skip_count).limit(per_page)
        posts_list = [Post.to_dict(post, current_user_id_str) for post in posts_cursor]
        total_posts = Post.get_collection().count_documents(query)
        
        return {
            "posts": posts_list, "total": total_posts, "page": page,
            "per_page": per_page, "pages": (total_posts + per_page - 1) // per_page if per_page > 0 else 0
        }

    @staticmethod
    def update_post(post_id_str, author_id_str, update_data):
        try:
            post_id_obj = ObjectId(post_id_str)
            author_id_obj = ObjectId(author_id_str)
        except Exception:
            raise ValueError("Invalid Post ID or Author ID format.")

        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post:
            raise ValueError("Post not found.")

        if post.get("author_id") != author_id_obj:
            # In a real app, admins or community moderators might also be able to edit.
            # For now, only the author can edit.
            raise PermissionError("User is not authorized to edit this post.")

        allowed_to_update = {}
        if "title" in update_data and update_data["title"] and len(update_data["title"].strip()) >= 3:
            allowed_to_update["title"] = update_data["title"].strip()
        elif "title" in update_data and (not update_data["title"] or len(update_data["title"].strip()) < 3) :
             raise ValueError("Post title must be at least 3 characters long if provided for update.")


        # Assuming content_type cannot be changed.
        # If it could, you'd need to validate the new content against the new type.
        current_content_type = post.get("content_type")

        if current_content_type == "text":
            if "content_text" in update_data:
                if not update_data["content_text"] or len(update_data["content_text"].strip()) == 0:
                    raise ValueError("Text content cannot be empty for a text post if provided for update.")
                allowed_to_update["content_text"] = update_data["content_text"].strip()
        elif current_content_type == "image":
            if "image_url" in update_data: # Allow updating image_url
                if not update_data["image_url"]:
                     raise ValueError("Image URL cannot be empty if provided for update.")
                allowed_to_update["image_url"] = update_data["image_url"]
            if "content_text" in update_data: # Image posts can also have descriptive text
                allowed_to_update["content_text"] = update_data["content_text"].strip() if update_data["content_text"] else None
        elif current_content_type == "link":
            if "link_url" in update_data: # Allow updating link_url
                if not update_data["link_url"]:
                    raise ValueError("Link URL cannot be empty if provided for update.")
                allowed_to_update["link_url"] = update_data["link_url"]
            if "content_text" in update_data: # Link posts can also have descriptive text
                allowed_to_update["content_text"] = update_data["content_text"].strip() if update_data["content_text"] else None
        
        if "tags" in update_data and isinstance(update_data["tags"], list):
            allowed_to_update["tags"] = [tag.strip().lower() for tag in update_data["tags"] if tag.strip()]
        
        if not allowed_to_update:
            # No valid fields to update were provided, or no changes from original
            # For simplicity, we can just say no changes, or raise an error.
            # Let's return the current post if no valid fields are provided.
            # A more sophisticated approach might check if allowed_to_update actually differs from current post data.
            return {"message": "No valid fields provided for update or no changes made.", "post": Post.to_dict(post, author_id_str)}


        allowed_to_update["updated_at"] = datetime.utcnow()
        # last_activity_at is usually not updated on edit unless it's a significant interaction

        result = Post.get_collection().update_one(
            {"_id": post_id_obj, "author_id": author_id_obj}, # Ensure author matches again for safety
            {"$set": allowed_to_update}
        )

        if result.modified_count > 0:
            updated_post_doc = Post.get_collection().find_one({"_id": post_id_obj})
            return {"message": "Post updated successfully.", "post": Post.to_dict(updated_post_doc, author_id_str)}
        elif result.matched_count > 0 and not allowed_to_update: # Matched but no fields were actually different to update
            return {"message": "No changes detected in the provided data.", "post": Post.to_dict(post, author_id_str)}
        else: # Matched but no modification (e.g., submitted same data), or didn't match (should have been caught by initial find)
            # This case implies that even though the document was found and authorized,
            # the update operation with $set didn't change anything (e.g., data was identical)
            # or something went wrong with the update itself not applying despite a match.
            current_app.logger.warning(f"Post update for {post_id_str} matched but modified_count was 0. Data: {allowed_to_update}")
            # Re-fetch and return the current state.
            current_post_doc = Post.get_collection().find_one({"_id": post_id_obj})
            return {"message": "Post matched but no fields were modified by the update.", "post": Post.to_dict(current_post_doc, author_id_str)}

    # Placeholder for deleting (own post or admin/mod)
    # @staticmethod
    # def delete_post(post_id, user_id, user_role='member'): ...