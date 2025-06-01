# app/models/comment.py
from app import mongo
from datetime import datetime
from bson import ObjectId
# from app.models.post import Post # Not strictly needed here, but Post model will update comment_count
# from app.models.user import User # For author details if embedding later

class Comment:
    @staticmethod
    def get_collection():
        return mongo.db.comments

    @staticmethod
    def create_comment(post_id, author_id, text, parent_comment_id=None):
        if not post_id:
            raise ValueError("Post ID is required to create a comment.")
        if not author_id:
            raise ValueError("Author ID is required to create a comment.")
        if not text or len(text.strip()) == 0:
            raise ValueError("Comment text cannot be empty.")
        if len(text.strip()) > 2000: # Example max length
            raise ValueError("Comment text is too long.")

        # Validate post_id (ensure post exists)
        # This import is here to avoid circular dependency if Post model also imports Comment
        from app.models.post import Post 
        post = Post.find_by_id_for_user(post_id) # Use existing method that returns dict or None
        if not post:
            raise ValueError(f"Post with ID '{post_id}' not found.")

        comment_data = {
            "post_id": ObjectId(post_id),
            "author_id": ObjectId(author_id),
            "text": text.strip(),
            "parent_comment_id": ObjectId(parent_comment_id) if parent_comment_id and ObjectId.is_valid(parent_comment_id) else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "upvotes": 0, # Placeholder for comment voting later
            "downvotes": 0 # Placeholder
            # "replies_count": 0 # If doing threaded replies with counts
        }

        result = Comment.get_collection().insert_one(comment_data)
        comment_data['_id'] = result.inserted_id
        
        # Increment comment_count on the Post document
        Post.get_collection().update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"comment_count": 1}, "$set": {"last_activity_at": datetime.utcnow()}}
        )
        
        return Comment.to_dict(comment_data)

    @staticmethod
    def find_by_id(comment_id):
        try:
            comment_doc = Comment.get_collection().find_one({"_id": ObjectId(comment_id)})
            return Comment.to_dict(comment_doc) if comment_doc else None
        except Exception:
            return None

    @staticmethod
    def get_comments_for_post(post_id_str, page=1, per_page=20, sort_by="new"): # Increased default per_page
        try:
            post_id_obj = ObjectId(post_id_str)
        except Exception:
            raise ValueError("Invalid Post ID format for fetching comments.")

        query = {"post_id": post_id_obj}
        
        # For now, only supporting parent_comment_id: null (top-level comments)
        # Threaded replies would require more complex querying (e.g., fetching replies for a parent)
        query["parent_comment_id"] = None 
        
        sort_field = "created_at"
        sort_order = 1 # Ascending for 'new' (oldest first at top of thread typically)
                       # Or -1 if you want newest comments first in the flat list

        if sort_by == "oldest": # Example alternative sort
            sort_order = 1
        elif sort_by == "newest": # Default is newest first
            sort_order = -1
            
        skip_count = (page - 1) * per_page
        comments_cursor = Comment.get_collection().find(query).sort(sort_field, sort_order).skip(skip_count).limit(per_page)
        
        comments_list = [Comment.to_dict(comment) for comment in comments_cursor]
        total_comments = Comment.get_collection().count_documents(query) # Count only top-level for now
        
        return {
            "comments": comments_list,
            "total": total_comments,
            "page": page,
            "per_page": per_page,
            "pages": (total_comments + per_page - 1) // per_page if per_page > 0 else 0
        }
        
    # Placeholder for editing (own comment)
    # @staticmethod
    # def update_comment(comment_id, author_id, new_text): ...

    # Placeholder for deleting (own comment or admin/mod)
    # This would also need to decrement post.comment_count
    # @staticmethod
    # def delete_comment(comment_id, user_id, user_role='member'): ...

    @staticmethod
    def to_dict(comment_doc):
        if not comment_doc:
            return None
        
        # In future, you might fetch author_name and avatar here via User model lookup
        return {
            "id": str(comment_doc["_id"]),
            "post_id": str(comment_doc.get("post_id")),
            "author_id": str(comment_doc.get("author_id")),
            # "author_name": "Fetched Author Name", # Placeholder
            # "author_avatar_url": "path/to/avatar.jpg", # Placeholder
            "text": comment_doc.get("text"),
            "parent_comment_id": str(comment_doc.get("parent_comment_id")) if comment_doc.get("parent_comment_id") else None,
            "created_at": comment_doc.get("created_at").isoformat() if comment_doc.get("created_at") else None,
            "updated_at": comment_doc.get("updated_at").isoformat() if comment_doc.get("updated_at") else None,
            "upvotes": comment_doc.get("upvotes", 0),
            "downvotes": comment_doc.get("downvotes", 0)
        }