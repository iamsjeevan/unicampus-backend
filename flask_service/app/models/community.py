# app/models/community.py
from app import mongo
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors
import re
from flask import current_app

# Placeholder for User model interaction - replace with your actual User model/functions
class UserModelPlaceholder:
    @staticmethod
    def find_by_id_str(user_id_str):
        if not ObjectId.is_valid(user_id_str):
            return None
        user_doc = mongo.db.users.find_one({"_id": ObjectId(user_id_str)})
        if user_doc:
            return {
                "id": str(user_doc["_id"]),
                "name": user_doc.get("name", "Unknown User"),
                "avatarUrl": user_doc.get("avatar") 
            }
        return {"id": user_id_str, "name": "User " + user_id_str[:4], "avatarUrl": None}

class Community:
    @staticmethod
    def get_collection():
        return mongo.db.communities

    # --- THIS to_dict METHOD ACCEPTS current_user_id_str ---
    @staticmethod
    def to_dict(community_doc, current_user_id_str=None):
        if not community_doc: return None
        
        community_id_str = str(community_doc["_id"])
        is_member_status = False
        # Check membership if current_user_id_str is provided and valid
        if current_user_id_str and ObjectId.is_valid(current_user_id_str):
            user_obj_id_for_check = ObjectId(current_user_id_str)
            # Assuming 'members' field in DB stores an array of ObjectIds
            if user_obj_id_for_check in community_doc.get("members", []):
                is_member_status = True
        
        # Assuming your DB fields are camelCase as per previous discussion for consistency
        return {
            "id": community_id_str,
            "_id": community_id_str, 
            "name": community_doc.get("name"),
            "slug": community_doc.get("slug"),
            "description": community_doc.get("description"),
            "rules": community_doc.get("rules", []),
            "icon": community_doc.get("iconUrl"),      
            "bannerImage": community_doc.get("bannerImage"), 
            "createdBy": str(community_doc.get("createdBy")) if community_doc.get("createdBy") else None,
            "createdAt": community_doc.get("createdAt").isoformat() if community_doc.get("createdAt") else None,
            "updatedAt": community_doc.get("updatedAt").isoformat() if community_doc.get("updatedAt") else None,
            "memberCount": community_doc.get("memberCount", 0),
            "postCount": community_doc.get("postCount", 0),
            "tags": community_doc.get("tags", []),
            "is_member": is_member_status # Crucial flag
        }

    @staticmethod
    def create_community(name, description, created_by_id_str, rules=None, icon_url=None, banner_image_url=None, tags=None):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        if not name or len(name.strip()) < 3: raise ValueError("Name required (min 3 chars).")
        if not description or len(description.strip()) < 10 : raise ValueError("Description required (min 10 chars).")
        if not created_by_id_str: raise ValueError("Creator ID required.")
        try: creator_obj_id = ObjectId(created_by_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid creator ID format.")

        name_clean = name.strip()
        slug = re.sub(r'[^\w\s-]', '', name_clean.lower()).strip()
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        if not slug: slug = str(ObjectId())[:12]

        name_regex = f"^{re.escape(name_clean)}$"
        if Community.get_collection().find_one({"name": {"$regex": name_regex, "$options": "i"}}):
            raise ValueError(f"Community name '{name_clean}' already exists.")
        
        temp_slug, counter = slug, 1
        while Community.get_collection().find_one({"slug": temp_slug}):
            temp_slug = f"{slug}-{counter}"; counter += 1
        slug = temp_slug

        community_data = { # Storing in DB with camelCase
            "name": name_clean, "slug": slug, "description": description.strip(),
            "rules": rules or [], "iconUrl": icon_url, "bannerImage": banner_image_url,
            "createdBy": creator_obj_id, "createdAt": datetime.now(timezone.utc), 
            "updatedAt": datetime.now(timezone.utc), "memberCount": 1,
            "members": [creator_obj_id], "postCount": 0,
            "tags": [tag.strip().lower() for tag in tags if isinstance(tag, str) and tag.strip()] if tags else []
        }
        result = Community.get_collection().insert_one(community_data)
        inserted_doc = Community.get_collection().find_one({"_id": result.inserted_id})
        return Community.to_dict(inserted_doc, current_user_id_str=created_by_id_str)


    @staticmethod
    def find_by_id_or_slug(id_or_slug_str, current_user_id_str=None):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        community_doc = None
        if ObjectId.is_valid(id_or_slug_str):
            try: community_doc = Community.get_collection().find_one({"_id": ObjectId(id_or_slug_str)})
            except bson_errors.InvalidId: pass
        if not community_doc:
            community_doc = Community.get_collection().find_one({"slug": id_or_slug_str})
        return Community.to_dict(community_doc, current_user_id_str)


    # --- THIS METHOD NOW ACCEPTS current_user_id_str ---
    @staticmethod
    def get_all_communities(page=1, per_page=10, search_query=None, current_user_id_str=None):
        query = {}
        if search_query:
            search_regex = re.escape(search_query)
            query["$or"] = [
                {"name": {"$regex": search_regex, "$options": "i"}},
                {"description": {"$regex": search_regex, "$options": "i"}},
                {"tags": {"$regex": search_regex, "$options": "i"}} # Search tags too
            ]
        
        skip_count = (page - 1) * per_page
        # Sort by memberCount first, then by creation date
        communities_cursor = Community.get_collection().find(query).sort([("memberCount", -1), ("createdAt", -1)]).skip(skip_count).limit(per_page)
        
        communities_list = []
        for community_doc in communities_cursor:
            # Pass current_user_id_str to to_dict
            community_dict = Community.to_dict(community_doc, current_user_id_str)
            if community_dict:
                communities_list.append(community_dict)
            
        total_communities = Community.get_collection().count_documents(query)
        
        return {
            "communities": communities_list,
            "total": total_communities,
            "page": page,
            "per_page": per_page,
            "pages": (total_communities + per_page - 1) // per_page if per_page > 0 else 0
        }

    @staticmethod
    def _update_membership(community_id_str, user_id_str, action):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        if not ObjectId.is_valid(community_id_str) or not ObjectId.is_valid(user_id_str):
            raise ValueError("Invalid community or user ID format.")
        community_id_obj, user_id_obj = ObjectId(community_id_str), ObjectId(user_id_str)

        community = Community.get_collection().find_one({"_id": community_id_obj})
        if not community: raise ValueError("Community not found.")

        is_current_member = user_id_obj in community.get("members", [])
        update_op, member_count_change = None, 0

        if action == "join" and not is_current_member:
            update_op = {"$addToSet": {"members": user_id_obj}}
            member_count_change = 1
        elif action == "leave" and is_current_member:
            update_op = {"$pull": {"members": user_id_obj}}
            member_count_change = -1
        
        if update_op:
            new_member_count = max(0, community.get("memberCount", 0) + member_count_change)
            update_op["$set"] = {"memberCount": new_member_count, "updatedAt": datetime.now(timezone.utc)}
            result = Community.get_collection().update_one({"_id": community_id_obj}, update_op)
            return result.modified_count > 0
        return False

    @staticmethod
    def join_community(community_id_str, user_id_str):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        try:
            if Community.is_user_member(community_id_str, user_id_str):
                 return {"message": "Already a member.", "already_member": True, "modified": False}
            if Community._update_membership(community_id_str, user_id_str, "join"):
                return {"message": "Successfully joined community.", "modified": True}
        except ValueError as ve: raise ve 
        raise ValueError("Could not join community (e.g. community not found).")


    @staticmethod
    def leave_community(community_id_str, user_id_str):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        try:
            if not Community.is_user_member(community_id_str, user_id_str):
                return {"message": "Not a member of this community.", "not_member": True, "modified": False}
            if Community._update_membership(community_id_str, user_id_str, "leave"):
                return {"message": "Successfully left community.", "modified": True}
        except ValueError as ve: raise ve
        raise ValueError("Could not leave community (e.g. community not found).")

    @staticmethod
    def is_user_member(community_id_str, user_id_str):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        if not community_id_str or not user_id_str or \
           not ObjectId.is_valid(community_id_str) or not ObjectId.is_valid(user_id_str):
            return False
        try:
            return Community.get_collection().count_documents({
                "_id": ObjectId(community_id_str), 
                "members": ObjectId(user_id_str)
            }) > 0
        except Exception: return False

    @staticmethod
    def increment_post_count(community_id_obj, amount=1):
        # ... (same as the version from "GIVE FULL CODE IDIOT" response)
        Community.get_collection().update_one(
            {"_id": community_id_obj},
            {"$inc": {"postCount": amount}, "$set": {"updatedAt": datetime.now(timezone.utc)}}
        )