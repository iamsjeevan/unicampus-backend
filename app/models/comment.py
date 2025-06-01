# app/models/comment.py
from app import mongo
from datetime import datetime
from bson import ObjectId
from flask import current_app

class Comment:
    @staticmethod
    def get_collection():
        return mongo.db.comments

    @staticmethod
    def create_comment(post_id_str, author_id_str, text, parent_comment_id_str=None):
        from app.models.post import Post # Local import to avoid circular dependency

        if not post_id_str: raise ValueError("Post ID is required to create a comment.")
        if not author_id_str: raise ValueError("Author ID is required to create a comment.")
        if not text or len(text.strip()) == 0: raise ValueError("Comment text cannot be empty.")
        if len(text.strip()) > 2000: raise ValueError("Comment text is too long (max 2000 characters).")

        try:
            post_id_obj = ObjectId(post_id_str)
            author_id_obj = ObjectId(author_id_str)
        except Exception: raise ValueError("Invalid Post ID or Author ID format.")

        # Validate post exists
        post = Post.get_collection().find_one({"_id": post_id_obj}) 
        if not post:
            raise ValueError(f"Post with ID '{post_id_str}' not found.")

        parent_obj_id = None
        if parent_comment_id_str and ObjectId.is_valid(parent_comment_id_str):
            # Optional: Further validation if parent_comment must exist and belong to same post
            parent_obj_id = ObjectId(parent_comment_id_str)

        comment_data = {
            "post_id": post_id_obj,
            "author_id": author_id_obj,
            "text": text.strip(),
            "parent_comment_id": parent_obj_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "upvotes": 0,
            "downvotes": 0,
            "upvoted_by": [], 
            "downvoted_by": []
        }
        result = Comment.get_collection().insert_one(comment_data)
        comment_data['_id'] = result.inserted_id
        
        Post.get_collection().update_one(
            {"_id": post_id_obj},
            {"$inc": {"comment_count": 1}, "$set": {"last_activity_at": datetime.utcnow()}}
        )
        return Comment.to_dict(comment_data, current_user_id_str=str(author_id_obj))

    @staticmethod
    def find_by_id(comment_id_str, current_user_id_str=None):
        try:
            comment_doc = Comment.get_collection().find_one({"_id": ObjectId(comment_id_str)})
            return Comment.to_dict(comment_doc, current_user_id_str) if comment_doc else None
        except Exception: return None

    @staticmethod
    def vote_on_comment(comment_id_str, user_id_str, vote_direction):
        try:
            comment_id_obj = ObjectId(comment_id_str); user_id_obj = ObjectId(user_id_str)
        except Exception: raise ValueError("Invalid Comment/User ID for vote.")
        comment = Comment.get_collection().find_one({"_id": comment_id_obj})
        if not comment: raise ValueError("Comment not found for vote.")

        is_up = user_id_obj in comment.get("upvoted_by", [])
        is_down = user_id_obj in comment.get("downvoted_by", [])
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

        update_q = {}; msg = "No change in comment vote status."
        if pull_ops: update_q["$pull"] = pull_ops
        if add_ops: update_q["$addToSet"] = add_ops
        if inc_ops: update_q["$inc"] = inc_ops
        if update_q:
            update_q["$set"] = {"updated_at": datetime.utcnow()}
            res = Comment.get_collection().update_one({"_id": comment_id_obj}, update_q)
            if res.modified_count > 0 or (inc_ops and res.matched_count > 0): msg = "Vote on comment processed."
        
        curr_doc = Comment.get_collection().find_one({"_id": comment_id_obj})
        curr_dict = Comment.to_dict(curr_doc, user_id_str)
        return {"message": msg, "upvotes": curr_dict.get("upvotes"), "downvotes": curr_dict.get("downvotes"), "user_vote": curr_dict.get("user_vote")}

    @staticmethod
    def update_comment(comment_id_str, author_id_str, new_text):
        if not new_text or len(new_text.strip()) == 0: raise ValueError("Updated comment text cannot be empty.")
        if len(new_text.strip()) > 2000: raise ValueError("Updated comment text is too long.")
        try:
            comment_id_obj = ObjectId(comment_id_str); author_id_obj = ObjectId(author_id_str)
        except Exception: raise ValueError("Invalid Comment/Author ID for update.")

        comment = Comment.get_collection().find_one({"_id": comment_id_obj})
        if not comment: raise ValueError("Comment not found for update.")
        if comment.get("author_id") != author_id_obj: raise PermissionError("Not authorized to edit this comment.")

        update_fields = {"text": new_text.strip(), "updated_at": datetime.utcnow()}
        res = Comment.get_collection().update_one({"_id": comment_id_obj, "author_id": author_id_obj}, {"$set": update_fields})
        
        if res.modified_count > 0:
            updated_doc = Comment.get_collection().find_one({"_id": comment_id_obj})
            return Comment.to_dict(updated_doc, author_id_str)
        elif res.matched_count > 0: return Comment.to_dict(comment, author_id_str) # Text was identical
        else: raise Exception("Comment update failed unexpectedly.") # Should not happen
            
    @staticmethod
    def delete_comment(comment_id_str, user_id_str):
        from app.models.post import Post # Local import
        try:
            comment_id_obj = ObjectId(comment_id_str); user_id_obj = ObjectId(user_id_str)
        except Exception: raise ValueError("Invalid Comment/User ID for delete.")

        comment = Comment.get_collection().find_one({"_id": comment_id_obj})
        if not comment: raise ValueError("Comment not found to delete.")
        if comment.get("author_id") != user_id_obj: raise PermissionError("Not authorized to delete this comment.")

        # TODO: Handle deletion of replies if this comment was a parent
        delete_result = Comment.get_collection().delete_one({"_id": comment_id_obj, "author_id": user_id_obj})
        if delete_result.deleted_count > 0:
            post_id_obj = comment.get("post_id")
            if post_id_obj:
                Post.get_collection().update_one(
                    {"_id": post_id_obj},
                    {"$inc": {"comment_count": -1}}
                )
            return True
        else:
            current_app.logger.warning(f"Comment {comment_id_str} delete by author {user_id_str} removed 0 docs.")
            return False

    @staticmethod
    def get_comments_for_post_for_user(post_id_str, current_user_id_str=None, page=1, per_page=20, sort_by="newest"):
        try:
            post_id_obj = ObjectId(post_id_str)
        except Exception: raise ValueError("Invalid Post ID format for fetching comments.")
        # For Phase 1, only fetch top-level comments
        query = {"post_id": post_id_obj, "parent_comment_id": None } 
        sort_field, sort_order = "created_at", -1 
        if sort_by == "oldest": sort_order = 1
        skip_count = (page - 1) * per_page
        comments_cursor = Comment.get_collection().find(query).sort(sort_field, sort_order).skip(skip_count).limit(per_page)
        comments_list = [Comment.to_dict(comment, current_user_id_str) for comment in comments_cursor]
        total_comments = Comment.get_collection().count_documents(query) # Count only top-level for pagination
        return {
            "comments": comments_list, "total": total_comments, "page": page,
            "per_page": per_page, "pages": (total_comments + per_page - 1) // per_page if per_page > 0 else 0
        }

    @staticmethod
    def to_dict(comment_doc, current_user_id_str=None):
        if not comment_doc: return None
        data = {
            "id": str(comment_doc["_id"]),
            "post_id": str(comment_doc.get("post_id")),
            "author_id": str(comment_doc.get("author_id")),
            "text": comment_doc.get("text"),
            "parent_comment_id": str(comment_doc.get("parent_comment_id")) if comment_doc.get("parent_comment_id") else None,
            "created_at": comment_doc.get("created_at").isoformat() if comment_doc.get("created_at") else None,
            "updated_at": comment_doc.get("updated_at").isoformat() if comment_doc.get("updated_at") else None,
            "upvotes": comment_doc.get("upvotes", 0), "downvotes": comment_doc.get("downvotes", 0),
            "user_vote": None 
        }
        if current_user_id_str:
            try:
                user_obj_id = ObjectId(current_user_id_str)
                if user_obj_id in comment_doc.get("upvoted_by", []): data["user_vote"] = "up"
                elif user_obj_id in comment_doc.get("downvoted_by", []): data["user_vote"] = "down"
            except Exception as e: current_app.logger.warning(f"Vote determination for user {current_user_id_str} on comment {data['id']}: {e}")
        return data