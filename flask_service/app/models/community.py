# app/models/community.py
from app import mongo
from datetime import datetime
from bson import ObjectId
import re

class Community:
    @staticmethod
    def get_collection():
        return mongo.db.communities

    @staticmethod
    def create_community(name, description, created_by_id, rules=None, icon_url=None, banner_image_url=None, tags=None):
        if not name or len(name) < 3:
            raise ValueError("Community name is required and must be at least 3 characters long.")
        if not description:
            raise ValueError("Community description is required.")
        if not created_by_id:
            raise ValueError("Community creator ID is required.")

        # Generate a slug for the community name (for URLs, if needed later)
        slug = re.sub(r'[^\w]+', '-', name.lower())
        # Ensure slug is unique (you might want to add a counter if not unique, e.g., slug-1, slug-2)
        # For now, we'll assume initial creation makes it unique enough or handle conflict at DB level.

        community_data = {
            "name": name,
            "slug": slug,
            "description": description,
            "rules": rules or [],
            "icon_url": icon_url,
            "banner_image_url": banner_image_url,
            "created_by": ObjectId(created_by_id),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "member_count": 1,  # Creator is the first member
            "members": [ObjectId(created_by_id)], # Store list of member user IDs
            "tags": tags or [] # e.g., ['academics', 'cse', 'semester-6']
            # 'moderators': [ObjectId(created_by_id)] # Creator is also initial moderator
        }

        # Basic check for existing community name (case-insensitive for user-friendliness)
        # For more robust uniqueness, use a unique index on 'name' or 'slug' in MongoDB
        existing_community = Community.get_collection().find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
        if existing_community:
            raise ValueError(f"A community with the name '{name}' already exists.")

        result = Community.get_collection().insert_one(community_data)
        community_data['_id'] = result.inserted_id
        return Community.to_dict(community_data) # Return a dict representation

    @staticmethod
    def find_by_id(community_id):
        try:
            community_doc = Community.get_collection().find_one({"_id": ObjectId(community_id)})
            return Community.to_dict(community_doc) if community_doc else None
        except Exception:
            return None
            
    @staticmethod
    def find_by_slug(slug):
        community_doc = Community.get_collection().find_one({"slug": slug})
        return Community.to_dict(community_doc) if community_doc else None

    @staticmethod
    def get_all_communities(page=1, per_page=10, search_query=None):
        query = {}
        if search_query:
            # Basic text search on name and description
            # For better search, enable text index in MongoDB:
            # Community.get_collection().create_index([("name", "text"), ("description", "text")])
            # query = {"$text": {"$search": search_query}}
            # For now, regex based search (less performant for large datasets)
            query["$or"] = [
                {"name": {"$regex": search_query, "$options": "i"}},
                {"description": {"$regex": search_query, "$options": "i"}},
            ]
        
        skip_count = (page - 1) * per_page
        communities_cursor = Community.get_collection().find(query).sort("created_at", -1).skip(skip_count).limit(per_page)
        
        communities_list = [Community.to_dict(community) for community in communities_cursor]
        total_communities = Community.get_collection().count_documents(query)
        
        return {
            "communities": communities_list,
            "total": total_communities,
            "page": page,
            "per_page": per_page,
            "pages": (total_communities + per_page - 1) // per_page # Calculate total pages
        }

    @staticmethod
    def join_community(community_id, user_id):
        community_id_obj = ObjectId(community_id)
        user_id_obj = ObjectId(user_id)

        # Use $addToSet to ensure user_id is not added multiple times
        # and $inc to increment member_count
        result = Community.get_collection().update_one(
            {"_id": community_id_obj},
            {
                "$addToSet": {"members": user_id_obj},
                "$inc": {"member_count": 1} # This will increment even if user was already a member due to addToSet
                                            # Better to check if user is already a member first, then inc if not.
            }
        )
        # More robust update:
        # community = Community.get_collection().find_one({"_id": community_id_obj, "members": {"$ne": user_id_obj}})
        # if community:
        #     Community.get_collection().update_one(
        #         {"_id": community_id_obj},
        #         {"$push": {"members": user_id_obj}, "$inc": {"member_count": 1}}
        #     )
        #     return True
        # return False # User already a member or community not found

        return result.modified_count > 0 # Or result.matched_count > 0 if member_count logic is adjusted

    @staticmethod
    def leave_community(community_id, user_id):
        community_id_obj = ObjectId(community_id)
        user_id_obj = ObjectId(user_id)
        
        # Use $pull to remove user_id and $inc to decrement member_count
        # Ensure user is actually a member before decrementing.
        community = Community.get_collection().find_one({"_id": community_id_obj, "members": user_id_obj})
        if community:
            result = Community.get_collection().update_one(
                {"_id": community_id_obj},
                {
                    "$pull": {"members": user_id_obj},
                    "$inc": {"member_count": -1}
                }
            )
            return result.modified_count > 0
        return False # User not a member or community not found

    @staticmethod
    def is_member(community_id, user_id):
        try:
            count = Community.get_collection().count_documents({
                "_id": ObjectId(community_id),
                "members": ObjectId(user_id)
            })
            return count > 0
        except Exception:
            return False


    @staticmethod
    def to_dict(community_doc):
        if not community_doc:
            return None
        return {
            "id": str(community_doc["_id"]),
            "name": community_doc.get("name"),
            "slug": community_doc.get("slug"),
            "description": community_doc.get("description"),
            "rules": community_doc.get("rules", []),
            "icon_url": community_doc.get("icon_url"),
            "banner_image_url": community_doc.get("banner_image_url"),
            "created_by": str(community_doc.get("created_by")),
            "created_at": community_doc.get("created_at").isoformat() if community_doc.get("created_at") else None,
            "updated_at": community_doc.get("updated_at").isoformat() if community_doc.get("updated_at") else None,
            "member_count": community_doc.get("member_count", 0),
            "tags": community_doc.get("tags", [])
            # "members": [str(member_id) for member_id in community_doc.get("members", [])], # Don't usually expose full member list here
        }