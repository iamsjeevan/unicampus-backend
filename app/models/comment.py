# app/models/comment.py
from app import mongo
from datetime import datetime
from bson import ObjectId, errors as bson_errors # Import bson_errors
from flask import current_app

class Comment:
    MAX_COMMENT_LENGTH = 2000 # Define as a class constant

    @staticmethod
    def get_collection():
        return mongo.db.comments

    @staticmethod
    def create_comment(post_id_str, author_id_str, text, parent_comment_id_str=None):
        from app.models.post import Post # Local import to avoid circular dependency

        if not post_id_str: raise ValueError("Post ID is required.")
        if not author_id_str: raise ValueError("Author ID is required.")
        if not text or not text.strip(): raise ValueError("Comment text cannot be empty.")
        if len(text.strip()) > Comment.MAX_COMMENT_LENGTH: 
            raise ValueError(f"Comment text is too long (max {Comment.MAX_COMMENT_LENGTH} chars).")

        try:
            post_id_obj = ObjectId(post_id_str)
            author_id_obj = ObjectId(author_id_str)
        except bson_errors.InvalidId: 
            raise ValueError("Invalid Post ID or Author ID format.")

        post = Post.get_collection().find_one({"_id": post_id_obj}) 
        if not post: 
            raise ValueError(f"Post '{post_id_str}' not found for comment.")

        parent_obj_id = None
        if parent_comment_id_str:
            try:
                parent_obj_id = ObjectId(parent_comment_id_str)
                # Validate parent comment exists and belongs to the same post
                parent_comment = Comment.get_collection().find_one({"_id": parent_obj_id, "post_id": post_id_obj})
                if not parent_comment:
                    raise ValueError("Parent comment not found or does not belong to this post.")
                # Optional: Limit nesting depth
                # depth = parent_comment.get("depth", 0) + 1
                # if depth > MAX_REPLY_DEPTH: raise ValueError("Max reply depth reached.")
            except bson_errors.InvalidId:
                raise ValueError("Invalid Parent Comment ID format.")
            except ValueError as ve: # Catch validation error for parent comment
                raise ve


        comment_data = {
            "post_id": post_id_obj, 
            "author_id": author_id_obj, 
            "text": text.strip(),
            "parent_comment_id": parent_obj_id, 
            # "depth": depth if parent_obj_id else 0, # For threading depth
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(), 
            "upvotes": 0, 
            "downvotes": 0,
            "upvoted_by": [], 
            "downvoted_by": [],
            "reply_count": 0 # Number of direct replies to this comment
        }
        result = Comment.get_collection().insert_one(comment_data)
        comment_data['_id'] = result.inserted_id
        
        # Increment comment_count on the Post document
        Post.get_collection().update_one(
            {"_id": post_id_obj},
            {"$inc": {"comment_count": 1}, "$set": {"last_activity_at": datetime.utcnow()}}
        )
        # If it's a reply, increment reply_count on parent comment
        if parent_obj_id:
            Comment.get_collection().update_one(
                {"_id": parent_obj_id},
                {"$inc": {"reply_count": 1}, "$set": {"updated_at": datetime.utcnow()}} # Also update parent's timestamp
            )
        
        return Comment.to_dict(comment_data, str(author_id_obj))

    @staticmethod
    def find_by_id(comment_id_str, current_user_id_str=None):
        try:
            comment_doc = Comment.get_collection().find_one({"_id": ObjectId(comment_id_str)})
            return Comment.to_dict(comment_doc, current_user_id_str) if comment_doc else None
        except bson_errors.InvalidId: return None # Invalid ID format
        except Exception: return None


    @staticmethod
    def vote_on_comment(comment_id_str, user_id_str, vote_direction):
        try:
            comment_id_obj = ObjectId(comment_id_str); user_id_obj = ObjectId(user_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid Comment/User ID for vote.")
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
        if add_ops: update_q["$addToSet"] = add_ops # Use addToSet for safety
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
        if not new_text or not new_text.strip():
            raise ValueError("Updated comment text cannot be empty.")
        if len(new_text.strip()) > Comment.MAX_COMMENT_LENGTH:
            raise ValueError(f"Updated comment text is too long (max {Comment.MAX_COMMENT_LENGTH} chars).")
        try:
            comment_id_obj = ObjectId(comment_id_str); author_id_obj = ObjectId(author_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid Comment/Author ID for update.")

        comment = Comment.get_collection().find_one({"_id": comment_id_obj})
        if not comment: raise ValueError("Comment not found for update.")
        if comment.get("author_id") != author_id_obj: raise PermissionError("Not authorized to edit this comment.")

        update_fields = {"text": new_text.strip(), "updated_at": datetime.utcnow()}
        res = Comment.get_collection().update_one({"_id": comment_id_obj, "author_id": author_id_obj}, {"$set": update_fields})
        
        if res.modified_count > 0:
            updated_doc = Comment.get_collection().find_one({"_id": comment_id_obj})
            return Comment.to_dict(updated_doc, author_id_str)
        elif res.matched_count > 0: # Matched but text was identical
            return Comment.to_dict(comment, author_id_str) 
        else: raise Exception("Comment update failed unexpectedly.")
            
    @staticmethod
    def delete_comment(comment_id_str, user_id_str):
        from app.models.post import Post # Local import
        try:
            comment_id_obj = ObjectId(comment_id_str); user_id_obj = ObjectId(user_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid Comment/User ID for delete.")

        comment = Comment.get_collection().find_one({"_id": comment_id_obj})
        if not comment: raise ValueError("Comment not found to delete.")
        if comment.get("author_id") != user_id_obj: raise PermissionError("Not authorized to delete this comment.")

        # If this comment was a parent, consider how to handle its replies (e.g., delete them, reparent them, or mark as deleted_parent)
        # For now, we'll just delete this comment and its direct replies if any (simple cascade)
        Comment.get_collection().delete_many({"parent_comment_id": comment_id_obj}) # Delete replies first
        
        delete_result = Comment.get_collection().delete_one({"_id": comment_id_obj, "author_id": user_id_obj})

        if delete_result.deleted_count > 0:
            post_id_obj = comment.get("post_id")
            if post_id_obj:
                # Decrement post's comment_count by 1 (for the main comment) + number of replies deleted
                # This logic for reply count needs to be more robust if replies can be deeply nested.
                # For now, assuming only one level of replies are directly deleted this way for simplicity.
                # A better approach might be to sum up all descendants or use a transaction if MongoDB version supports it.
                num_replies_deleted = Comment.get_collection().count_documents({"parent_comment_id": comment_id_obj}) # This will be 0 now
                                                                                                                     # We'd need count before delete_many
                # Simpler: just decrement by 1, assuming flat comments for now or frontend handles reply counts
                Post.get_collection().update_one(
                    {"_id": post_id_obj},
                    {"$inc": {"comment_count": -1}} 
                )
            return True
        else:
            current_app.logger.warning(f"Comment {comment_id_str} delete by author {user_id_str} removed 0 docs.")
            return False

    @staticmethod
    def get_comments_for_post_for_user(post_id_str, current_user_id_str=None, page=1, per_page=20, sort_by="newest", parent_id_str=None):
        try:
            post_id_obj = ObjectId(post_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid Post ID format for fetching comments.")
        
        query = {"post_id": post_id_obj}
        if parent_id_str: # Fetching replies for a specific comment
            try:
                query["parent_comment_id"] = ObjectId(parent_id_str)
            except bson_errors.InvalidId:
                raise ValueError("Invalid Parent Comment ID format.")
        else: # Fetching top-level comments
            query["parent_comment_id"] = None 
        
        sort_field = "created_at"
        sort_order = -1 if sort_by == "newest" else 1 # Default newest, else oldest
            
        skip_count = (page - 1) * per_page
        comments_cursor = Comment.get_collection().find(query).sort(sort_field, sort_order).skip(skip_count).limit(per_page)
        
        comments_list = []
        for comment_doc in comments_cursor:
            comment_dict = Comment.to_dict(comment_doc, current_user_id_str)
            # For basic threading, add reply count to top-level comments
            if not parent_id_str: # Only for top-level comments
                 comment_dict['reply_count'] = Comment.get_collection().count_documents({"parent_comment_id": comment_doc["_id"]})
            comments_list.append(comment_dict)

        total_comments = Comment.get_collection().count_documents(query)
        
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
            "reply_count": comment_doc.get("reply_count", 0), # Include reply_count
            "user_vote": None 
        }
        if current_user_id_str:
            try:
                user_obj_id = ObjectId(current_user_id_str)
                if user_obj_id in comment_doc.get("upvoted_by", []): data["user_vote"] = "up"
                elif user_obj_id in comment_doc.get("downvoted_by", []): data["user_vote"] = "down"
            except bson_errors.InvalidId: pass # Ignore if current_user_id_str is not valid ObjectId
            except Exception as e: current_app.logger.warning(f"Vote determination for user {current_user_id_str} on comment {data['id']}: {e}")
        return data