# app/models/post.py
from app import mongo
from datetime import datetime
from bson import ObjectId
from app.models.community import Community 
from flask import current_app
# Import Comment model here as Post.delete_post will interact with it
from app.models.comment import Comment 

class Post:
    @staticmethod
    def get_collection():
        return mongo.db.posts

    @staticmethod
    def create_post(community_id_str, author_id_str, title, content_type, content_text=None, image_url=None, link_url=None, tags=None):
        if not community_id_str: raise ValueError("Community ID is required.")
        if not author_id_str: raise ValueError("Author ID is required.")
        if not title or len(title.strip()) < 3: raise ValueError("Post title required (min 3 chars).")
        if content_type not in ["text", "image", "link"]: raise ValueError("Invalid post content type.")

        if content_type == "text" and not (content_text and content_text.strip()): raise ValueError("Text content required for text post.")
        if content_type == "image" and not image_url: raise ValueError("Image URL required for image post.")
        if content_type == "link" and not link_url: raise ValueError("Link URL required for link post.")
        
        community = Community.find_by_id(community_id_str) 
        if not community:
            if not ObjectId.is_valid(community_id_str): 
                community = Community.find_by_slug(community_id_str)
            if not community: 
                raise ValueError(f"Community '{community_id_str}' not found.")
            community_id_str = community['id'] # Use the actual ID if found by slug

        try:
            community_id_obj = ObjectId(community_id_str)
            author_id_obj = ObjectId(author_id_str)
        except Exception: 
            raise ValueError("Invalid Community ID or Author ID format.")

        post_data = {
            "community_id": community_id_obj, 
            "community_slug": community.get('slug'), 
            "community_name": community.get('name'), 
            "author_id": author_id_obj,
            "title": title.strip(), 
            "content_type": content_type,
            "content_text": content_text.strip() if content_text else None,
            "image_url": image_url, 
            "link_url": link_url,
            "tags": [tag.strip().lower() for tag in tags if isinstance(tag, str) and tag.strip()] if tags else [],
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
        return Post.to_dict(post_data, current_user_id_str=str(author_id_obj))

    @staticmethod
    def vote_on_post(post_id_str, user_id_str, vote_direction):
        try:
            post_id_obj = ObjectId(post_id_str); user_id_obj = ObjectId(user_id_str)
        except Exception: raise ValueError("Invalid Post/User ID format for vote.")
        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post: raise ValueError("Post not found for vote.")

        is_up = user_id_obj in post.get("upvoted_by", [])
        is_down = user_id_obj in post.get("downvoted_by", [])
        pull_ops, add_ops, inc_ops = {}, {}, {}

        if vote_direction == "up":
            if is_up: pull_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = -1
            else:
                if is_down: pull_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = -1
                add_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = 1
        elif vote_direction == "down":
            if is_down: pull_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = -1
            else:
                if is_up: pull_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = -1
                add_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = 1
        elif vote_direction == "none":
            if is_up: pull_ops["upvoted_by"] = user_id_obj; inc_ops["upvotes"] = -1
            if is_down: pull_ops["downvoted_by"] = user_id_obj; inc_ops["downvotes"] = -1
        else: raise ValueError("Invalid vote direction.")

        update_q = {}; msg = "No change in vote status."
        if pull_ops: update_q["$pull"] = pull_ops
        if add_ops: update_q["$addToSet"] = add_ops
        if inc_ops: update_q["$inc"] = inc_ops
        if update_q:
            update_q["$set"] = {"updated_at": datetime.utcnow(), "last_activity_at": datetime.utcnow()}
            res = Post.get_collection().update_one({"_id": post_id_obj}, update_q)
            if res.modified_count > 0 or (inc_ops and res.matched_count > 0): msg = "Vote processed."
        
        curr_doc = Post.get_collection().find_one({"_id": post_id_obj})
        curr_dict = Post.to_dict(curr_doc, user_id_str)
        return {"message": msg, "upvotes": curr_dict.get("upvotes"), "downvotes": curr_dict.get("downvotes"), "user_vote": curr_dict.get("user_vote")}

    @staticmethod
    def update_post(post_id_str, author_id_str, update_data):
        try:
            post_id_obj = ObjectId(post_id_str); author_id_obj = ObjectId(author_id_str)
        except Exception: raise ValueError("Invalid Post/Author ID for update.")
        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post: raise ValueError("Post not found for update.")
        if post.get("author_id") != author_id_obj: raise PermissionError("Not authorized to edit post.")

        allowed_updates = {}
        if "title" in update_data:
            title = update_data["title"].strip() if update_data["title"] else ""
            if len(title) < 3: raise ValueError("Updated title too short (min 3 chars).")
            allowed_updates["title"] = title
        
        content_type = post.get("content_type")
        if "content_text" in update_data:
            allowed_updates["content_text"] = update_data["content_text"].strip() if update_data["content_text"] else None
            if content_type == "text" and not allowed_updates["content_text"]: raise ValueError("Text content cannot be empty.")
        if "image_url" in update_data and content_type == "image":
            if not update_data["image_url"]: raise ValueError("Image URL cannot be empty.")
            allowed_updates["image_url"] = update_data["image_url"]
        if "link_url" in update_data and content_type == "link":
            if not update_data["link_url"]: raise ValueError("Link URL cannot be empty.")
            allowed_updates["link_url"] = update_data["link_url"]
        if "tags" in update_data and isinstance(update_data["tags"], list):
            allowed_updates["tags"] = [tag.strip().lower() for tag in update_data["tags"] if isinstance(tag, str) and tag.strip()]
        
        if not allowed_updates: return {"message": "No valid fields or changes.", "post": Post.to_dict(post, author_id_str)}
        allowed_updates["updated_at"] = datetime.utcnow()

        res = Post.get_collection().update_one({"_id": post_id_obj, "author_id": author_id_obj}, {"$set": allowed_updates})
        updated_doc = Post.get_collection().find_one({"_id": post_id_obj})
        msg = "No changes detected."
        if res.modified_count > 0: msg = "Post updated successfully."
        return {"message": msg, "post": Post.to_dict(updated_doc, author_id_str)}

    @staticmethod
    def delete_post(post_id_str, user_id_str):
        try:
            post_id_obj = ObjectId(post_id_str)
            user_id_obj = ObjectId(user_id_str)
        except Exception: raise ValueError("Invalid Post ID or User ID format for delete.")
        post = Post.get_collection().find_one({"_id": post_id_obj})
        if not post: raise ValueError("Post not found to delete.")
        if post.get("author_id") != user_id_obj: raise PermissionError("User is not authorized to delete this post.")

        try:
            comment_delete_result = Comment.get_collection().delete_many({"post_id": post_id_obj})
            current_app.logger.info(f"Cascaded delete: {comment_delete_result.deleted_count} comments for post {post_id_str}")
        except Exception as e:
            current_app.logger.error(f"Error during cascading delete of comments for post {post_id_str}: {e}", exc_info=True)

        delete_result = Post.get_collection().delete_one({"_id": post_id_obj, "author_id": user_id_obj})
        if delete_result.deleted_count > 0: return True
        else:
            current_app.logger.warning(f"Post {post_id_str} delete op by author {user_id_str} affected 0 docs, though post was found.")
            return False

    @staticmethod
    def to_dict(post_doc, current_user_id_str=None):
        if not post_doc: return None
        data = {
            "id": str(post_doc["_id"]),
            "community_id": str(post_doc.get("community_id")),
            "community_slug": post_doc.get("community_slug"),
            "community_name": post_doc.get("community_name"),
            "author_id": str(post_doc.get("author_id")),
            "title": post_doc.get("title"), "content_type": post_doc.get("content_type"),
            "content_text": post_doc.get("content_text"), "image_url": post_doc.get("image_url"),
            "link_url": post_doc.get("link_url"), "tags": post_doc.get("tags", []),
            "upvotes": post_doc.get("upvotes", 0), "downvotes": post_doc.get("downvotes", 0),
            "comment_count": post_doc.get("comment_count", 0),
            "created_at": post_doc.get("created_at").isoformat() if post_doc.get("created_at") else None,
            "updated_at": post_doc.get("updated_at").isoformat() if post_doc.get("updated_at") else None,
            "last_activity_at": post_doc.get("last_activity_at").isoformat() if post_doc.get("last_activity_at") else None,
            "user_vote": None 
        }
        if current_user_id_str:
            try:
                user_obj_id = ObjectId(current_user_id_str)
                if user_obj_id in post_doc.get("upvoted_by", []): data["user_vote"] = "up"
                elif user_obj_id in post_doc.get("downvoted_by", []): data["user_vote"] = "down"
            except Exception as e: current_app.logger.warning(f"Vote determination error for user {current_user_id_str} on post {data['id']}: {e}")
        return data

    @staticmethod
    def find_by_id_for_user(post_id_str, current_user_id_str=None):
        try:
            post_doc = Post.get_collection().find_one({"_id": ObjectId(post_id_str)})
            return Post.to_dict(post_doc, current_user_id_str) if post_doc else None
        except Exception: return None

    @staticmethod
    def get_posts_for_community_for_user(community_id_str, current_user_id_str=None, page=1, per_page=10, sort_by="new"):
        try:
            community_id_obj = ObjectId(community_id_str)
        except Exception: raise ValueError("Invalid Community ID format")
        query = {"community_id": community_id_obj}
        sort_field, sort_order = "created_at", -1 
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