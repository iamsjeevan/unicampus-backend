# app/models/post.py
from app import mongo
from datetime import datetime
from bson import ObjectId
from app.models.community import Community # To validate community exists
# from app.models.user import User # To potentially fetch author details if embedding

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

        # Validate content based on type
        if content_type == "text" and (not content_text or len(content_text.strip()) == 0):
            raise ValueError("Text content is required for a text post.")
        if content_type == "image" and not image_url:
            raise ValueError("Image URL is required for an image post.")
        if content_type == "link" and not link_url:
            raise ValueError("Link URL is required for a link post.")
        
        # Ensure the community exists
        community = Community.find_by_id(community_id) # Assuming Community.find_by_id returns a dict or None
        if not community:
            raise ValueError(f"Community with ID '{community_id}' not found.")

        post_data = {
            "community_id": ObjectId(community_id),
            "community_slug": community.get('slug'), # Store slug for easier querying/linking
            "community_name": community.get('name'), # Store name for display
            "author_id": ObjectId(author_id),
            "title": title.strip(),
            "content_type": content_type, # "text", "image", "link"
            "content_text": content_text.strip() if content_text else None,
            "image_url": image_url,
            "link_url": link_url,
            "tags": tags or [],
            "upvotes": 0,
            "downvotes": 0,
            "comment_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_activity_at": datetime.utcnow() # For sorting by hot/activity
            # "votes": {} # To store individual user votes: { "user_id": "up/down" }
        }

        result = Post.get_collection().insert_one(post_data)
        post_data['_id'] = result.inserted_id
        return Post.to_dict(post_data) # Return a dict representation

    @staticmethod
    def find_by_id(post_id):
        try:
            post_doc = Post.get_collection().find_one({"_id": ObjectId(post_id)})
            return Post.to_dict(post_doc) if post_doc else None
        except Exception:
            return None

    @staticmethod
    def get_posts_for_community(community_id, page=1, per_page=10, sort_by="new"):
        # Validate community_id
        if not ObjectId.is_valid(community_id):
            raise ValueError("Invalid Community ID format")

        query = {"community_id": ObjectId(community_id)}
        
        sort_field = "created_at"
        sort_order = -1 # Descending for 'new'

        if sort_by == "hot": # Simple 'hot' could be last_activity_at or a calculated score
            sort_field = "last_activity_at" 
        elif sort_by == "top": # Simple 'top' could be based on upvotes (upvotes - downvotes)
            # For a true top sort, you'd project a score: (upvotes - downvotes)
            # This requires aggregation or adding a 'score' field updated on votes.
            # For simplicity now, let's sort by upvotes.
            sort_field = "upvotes"
        # 'new' is default (created_at desc)

        skip_count = (page - 1) * per_page
        posts_cursor = Post.get_collection().find(query).sort(sort_field, sort_order).skip(skip_count).limit(per_page)
        
        posts_list = [Post.to_dict(post) for post in posts_cursor]
        total_posts = Post.get_collection().count_documents(query)
        
        return {
            "posts": posts_list,
            "total": total_posts,
            "page": page,
            "per_page": per_page,
            "pages": (total_posts + per_page - 1) // per_page if per_page > 0 else 0
        }
        
    # Placeholder for editing (own post)
    # @staticmethod
    # def update_post(post_id, author_id, update_data): ...

    # Placeholder for deleting (own post or admin/mod)
    # @staticmethod
    # def delete_post(post_id, user_id, user_role='member'): ...


    @staticmethod
    def to_dict(post_doc):
        if not post_doc:
            return None
        
        # Basic author info - for more details, an aggregation/lookup would be needed
        # or fetch separately in the route based on author_id.
        # For now, just sending author_id.
        # author_details = User.find_by_id(str(post_doc.get("author_id"))) # Example if you had User model here
        # author_name = author_details.get('name') if author_details else "Unknown Author"
        
        return {
            "id": str(post_doc["_id"]),
            "community_id": str(post_doc.get("community_id")),
            "community_slug": post_doc.get("community_slug"),
            "community_name": post_doc.get("community_name"),
            "author_id": str(post_doc.get("author_id")),
            # "author_name": author_name, # If fetching author name
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
        }