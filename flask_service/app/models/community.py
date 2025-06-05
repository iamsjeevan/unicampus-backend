# flask_service/app/models/community.py
from app import mongo
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors
import re
from flask import current_app

# UserModelPlaceholder (keep as is or replace with your actual User model interactions)

class Community:
    @staticmethod
    def get_collection():
        return mongo.db.communities

    @staticmethod
    def to_dict(community_doc, current_user_id_str=None):
        if not community_doc: return None
        community_id_str = str(community_doc["_id"])
        is_member_status = False
        if current_user_id_str and ObjectId.is_valid(current_user_id_str):
            user_obj_id_for_check = ObjectId(current_user_id_str)
            if user_obj_id_for_check in community_doc.get("members", []):
                is_member_status = True
        return {
            "id": community_id_str,
            "_id": community_id_str, 
            "name": community_doc.get("name"),
            "slug": community_doc.get("slug"),
            "description": community_doc.get("description"),
            "rules": community_doc.get("rules", []),
            "icon": community_doc.get("iconUrl"), # DB: iconUrl -> JSON: icon
            "bannerImage": community_doc.get("bannerImage"), # DB: bannerImage -> JSON: bannerImage
            "createdBy": str(community_doc.get("createdBy")) if community_doc.get("createdBy") else None,
            "createdAt": community_doc.get("createdAt").isoformat() if community_doc.get("createdAt") else None,
            "updatedAt": community_doc.get("updatedAt").isoformat() if community_doc.get("updatedAt") else None,
            "memberCount": community_doc.get("memberCount", 0),
            "postCount": community_doc.get("postCount", 0),
            "tags": community_doc.get("tags", []),
            "is_member": is_member_status
        }

    @staticmethod
    def create_community(name, description, created_by_id_str, rules=None, icon_url=None, banner_image_url=None, tags=None):
        if not name or len(name.strip()) < 3: raise ValueError("Name required (min 3 chars).")
        if not description or len(description.strip()) < 10 : raise ValueError("Description required (min 10 chars).")
        if not created_by_id_str: raise ValueError("Creator ID required.")
        try: creator_obj_id = ObjectId(created_by_id_str)
        except bson_errors.InvalidId: raise ValueError("Invalid creator ID format.")

        name_clean = name.strip()
        slug = re.sub(r'[^\w\s-]', '', name_clean.lower()).strip()
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        if not slug: slug = str(ObjectId())[:12] # Fallback slug

        name_regex = f"^{re.escape(name_clean)}$"
        if Community.get_collection().find_one({"name": {"$regex": name_regex, "$options": "i"}}):
            raise ValueError(f"Community name '{name_clean}' already exists.")
        
        temp_slug, counter = slug, 1
        while Community.get_collection().find_one({"slug": temp_slug}):
            temp_slug = f"{slug}-{counter}"; counter += 1
        slug = temp_slug

        community_data = {
            "name": name_clean, "slug": slug, "description": description.strip(),
            "rules": rules or [], "iconUrl": icon_url, "bannerImage": banner_image_url, # Stored as iconUrl, bannerImage
            "createdBy": creator_obj_id, "createdAt": datetime.now(timezone.utc), 
            "updatedAt": datetime.now(timezone.utc), "memberCount": 1,
            "members": [creator_obj_id], "postCount": 0,
            "tags": [tag.strip().lower() for tag in tags if isinstance(tag, str) and tag.strip()] if tags else []
        }
        result = Community.get_collection().insert_one(community_data)
        inserted_doc = Community.get_collection().find_one({"_id": result.inserted_id})
        return Community.to_dict(inserted_doc, current_user_id_str=created_by_id_str)

    @staticmethod
    def update_community(community_id_str, user_id_str, update_data):
        try:
            community_id_obj = ObjectId(community_id_str)
            user_id_obj = ObjectId(user_id_str)
        except bson_errors.InvalidId:
            raise ValueError("Invalid Community or User ID format.")

        community_doc = Community.get_collection().find_one({"_id": community_id_obj})
        if not community_doc:
            raise ValueError("Community not found.")

        if community_doc.get("createdBy") != user_id_obj: # Simple permission
            raise PermissionError("You are not authorized to update this community.")

        set_payload = {}
        if "name" in update_data:
            name_clean = str(update_data["name"]).strip()
            if len(name_clean) < 3: raise ValueError("Updated name too short (min 3 chars).")
            name_regex = f"^{re.escape(name_clean)}$"
            if Community.get_collection().find_one({"name": {"$regex": name_regex, "$options": "i"}, "_id": {"$ne": community_id_obj}}):
                raise ValueError(f"Community name '{name_clean}' already exists.")
            set_payload["name"] = name_clean
        
        if "description" in update_data:
            desc_clean = str(update_data["description"]).strip()
            if len(desc_clean) < 10: raise ValueError("Updated description too short (min 10 chars).")
            set_payload["description"] = desc_clean
        
        if "rules" in update_data and isinstance(update_data["rules"], list):
            set_payload["rules"] = [str(rule).strip() for rule in update_data["rules"] if str(rule).strip()]
        
        if "tags" in update_data and isinstance(update_data["tags"], list):
            set_payload["tags"] = list(set([tag.strip().lower() for tag in update_data["tags"] if isinstance(tag, str) and tag.strip()]))

        # These expect URLs from the route, or None to clear
        if "iconUrl" in update_data: # Key from route is 'iconUrl'
            set_payload["iconUrl"] = update_data["iconUrl"] 
        if "bannerImage" in update_data: # Key from route is 'bannerImage'
            set_payload["bannerImage"] = update_data["bannerImage"]

        if not set_payload:
            current_app.logger.info(f"No valid fields to update for community {community_id_str}.")
            return Community.to_dict(community_doc, user_id_str) # Return current if no changes

        set_payload["updatedAt"] = datetime.now(timezone.utc)
        
        Community.get_collection().update_one({"_id": community_id_obj}, {"$set": set_payload})
        
        updated_community_doc = Community.get_collection().find_one({"_id": community_id_obj})
        return Community.to_dict(updated_community_doc, user_id_str)

    # ... (find_by_id_or_slug, get_all_communities, _update_membership, join_community, leave_community, is_user_member, increment_post_count remain as you provided) ...
    @staticmethod
    def find_by_id_or_slug(id_or_slug_str, current_user_id_str=None):
        community_doc = None
        if ObjectId.is_valid(id_or_slug_str):
            try: community_doc = Community.get_collection().find_one({"_id": ObjectId(id_or_slug_str)})
            except bson_errors.InvalidId: pass # Will try slug search next
        if not community_doc: # If not found by ID or ID was invalid
            community_doc = Community.get_collection().find_one({"slug": id_or_slug_str})
        return Community.to_dict(community_doc, current_user_id_str)

    @staticmethod
    def get_all_communities(page=1, per_page=10, search_query=None, current_user_id_str=None):
        query = {}
        if search_query:
            search_regex = re.escape(search_query) # Escape special characters
            query["$or"] = [
                {"name": {"$regex": search_regex, "$options": "i"}},
                {"description": {"$regex": search_regex, "$options": "i"}},
                {"tags": {"$regex": search_regex, "$options": "i"}}
            ]
        
        skip_count = (page - 1) * per_page
        communities_cursor = Community.get_collection().find(query).sort([("memberCount", -1), ("createdAt", -1)]).skip(skip_count).limit(per_page)
        
        communities_list = []
        for community_doc_item in communities_cursor:
            community_dict = Community.to_dict(community_doc_item, current_user_id_str)
            if community_dict: # Ensure to_dict didn't return None
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
        if not ObjectId.is_valid(community_id_str) or not ObjectId.is_valid(user_id_str):
            raise ValueError("Invalid community or user ID format.")
        community_id_obj, user_id_obj = ObjectId(community_id_str), ObjectId(user_id_str)

        community = Community.get_collection().find_one({"_id": community_id_obj})
        if not community: raise ValueError("Community not found.")

        is_current_member = user_id_obj in community.get("members", [])
        update_op_main = {} # Use a main update operator dictionary
        member_count_change = 0

        if action == "join" and not is_current_member:
            update_op_main["$addToSet"] = {"members": user_id_obj}
            member_count_change = 1
        elif action == "leave" and is_current_member:
            update_op_main["$pull"] = {"members": user_id_obj}
            member_count_change = -1
        
        if update_op_main: # Check if there are any operations to perform
            new_member_count = max(0, community.get("memberCount", 0) + member_count_change)
            # Add $set operations to the main update_op_main dictionary
            update_op_main.setdefault("$set", {}).update({
                "memberCount": new_member_count, 
                "updatedAt": datetime.now(timezone.utc)
            })
            result = Community.get_collection().update_one({"_id": community_id_obj}, update_op_main)
            return result.modified_count > 0
        return False # No action taken

    @staticmethod
    def join_community(community_id_str, user_id_str):
        try:
            if Community.is_user_member(community_id_str, user_id_str):
                 return {"message": "Already a member.", "already_member": True, "modified": False}
            if Community._update_membership(community_id_str, user_id_str, "join"):
                return {"message": "Successfully joined community.", "modified": True}
            # If _update_membership returned False without an exception (e.g. already member, though checked above)
            return {"message": "Could not join community (no change made).", "modified": False} 
        except ValueError as ve: 
            current_app.logger.warning(f"Join community ValueError: {ve}")
            raise ve 
        except Exception as e:
            current_app.logger.error(f"Unexpected error joining community {community_id_str} by {user_id_str}: {e}", exc_info=True)
            raise ValueError("Could not join community due to an unexpected error.")


    @staticmethod
    def leave_community(community_id_str, user_id_str):
        try:
            if not Community.is_user_member(community_id_str, user_id_str):
                return {"message": "Not a member of this community.", "not_member": True, "modified": False}
            if Community._update_membership(community_id_str, user_id_str, "leave"):
                return {"message": "Successfully left community.", "modified": True}
            return {"message": "Could not leave community (no change made).", "modified": False}
        except ValueError as ve: 
            current_app.logger.warning(f"Leave community ValueError: {ve}")
            raise ve
        except Exception as e:
            current_app.logger.error(f"Unexpected error leaving community {community_id_str} by {user_id_str}: {e}", exc_info=True)
            raise ValueError("Could not leave community due to an unexpected error.")


    @staticmethod
    def is_user_member(community_id_str, user_id_str):
        if not community_id_str or not user_id_str or \
           not ObjectId.is_valid(community_id_str) or not ObjectId.is_valid(user_id_str):
            # current_app.logger.debug(f"is_user_member: Invalid ID format. C_ID: {community_id_str}, U_ID: {user_id_str}")
            return False
        try:
            return Community.get_collection().count_documents({
                "_id": ObjectId(community_id_str), 
                "members": ObjectId(user_id_str)
            }) > 0
        except Exception as e: 
            current_app.logger.error(f"is_user_member: DB error for C_ID {community_id_str}, U_ID {user_id_str}: {e}", exc_info=True)
            return False

    @staticmethod
    def increment_post_count(community_id_obj, amount=1):
        if not isinstance(community_id_obj, ObjectId):
            current_app.logger.error(f"increment_post_count: Expected ObjectId, got {type(community_id_obj)}")
            return # Or raise error
            
        Community.get_collection().update_one(
            {"_id": community_id_obj},
            {"$inc": {"postCount": amount}, "$set": {"updatedAt": datetime.now(timezone.utc)}}
        )
