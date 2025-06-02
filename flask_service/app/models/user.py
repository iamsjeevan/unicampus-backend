from app import mongo
from datetime import datetime
from bson import ObjectId
# from werkzeug.security import generate_password_hash, check_password_hash # Not used for this student login flow

class User:
    @staticmethod
    def get_collection():
        return mongo.db.users

    @staticmethod
    def create_user_from_scraped_data(scraped_data, requested_usn):
        profile = scraped_data.get('studentProfile', {})
        exam_history_data = scraped_data.get('examHistory', {})
        
        usn_from_profile = profile.get('usn', requested_usn).upper() # Fallback to requested_usn if not in profile

        user_data = {
            "usn": usn_from_profile,
            "name": profile.get('name'),
            "email": f"{usn_from_profile.lower()}@unicampus.app",
            "role": "student",
            "password_hash": None,
            "college_profile": {
                "officialName": profile.get('name'),
                "department": profile.get('department'),
                "semester": profile.get('semester'),
                "section": profile.get('section'),
                "usn": usn_from_profile 
            },
            "academic_summaries": scraped_data.get('dashboardSummaries', []),
            "exam_history": exam_history_data.get('semesters', []),
            "most_recent_cgpa": exam_history_data.get('mostRecentCGPA'),
            "college_data_last_updated": datetime.utcnow(),
            "avatar": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        existing_user_usn = User.get_collection().find_one({"usn": user_data["usn"]})
        if existing_user_usn:
            raise ValueError(f"User with USN {user_data['usn']} already exists. Update logic should be used.")

        result = User.get_collection().insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return user_data

    @staticmethod
    def update_user_with_scraped_data(user_id, scraped_data):
        profile = scraped_data.get('studentProfile', {})
        exam_history_data = scraped_data.get('examHistory', {})
        usn_from_profile = profile.get('usn', '').upper()


        update_fields = {
            "name": profile.get('name'),
            "college_profile": {
                "officialName": profile.get('name'),
                "department": profile.get('department'),
                "semester": profile.get('semester'),
                "section": profile.get('section'),
            },
            "academic_summaries": scraped_data.get('dashboardSummaries', []),
            "exam_history": exam_history_data.get('semesters', []),
            "most_recent_cgpa": exam_history_data.get('mostRecentCGPA'),
            "college_data_last_updated": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        # Ensure USN is in college_profile if available from scrape
        if usn_from_profile:
            update_fields["college_profile"]["usn"] = usn_from_profile
        else: # If USN not in scraped profile, try to keep existing from DB doc
            existing_user = User.find_by_id(user_id)
            if existing_user and existing_user.get("college_profile", {}).get("usn"):
                 update_fields["college_profile"]["usn"] = existing_user["college_profile"]["usn"]


        User.get_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
        return User.find_by_id(user_id)

    @staticmethod
    def find_by_usn(usn):
        return User.get_collection().find_one({"usn": usn.upper()})

    @staticmethod
    def find_by_id(user_id):
        try:
            return User.get_collection().find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    @staticmethod
    def update_profile(user_id, data_to_update):
        allowed_updates = {"avatar", "name"} 
        update_data = {k: v for k, v in data_to_update.items() if k in allowed_updates}
        if not update_data:
            return False
        update_data["updated_at"] = datetime.utcnow()
        User.get_collection().update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        return True

    @staticmethod
    def to_dict(user_doc):
        if not user_doc:
            return None
        
        college_data_last_updated_iso = None
        if user_doc.get("college_data_last_updated") and isinstance(user_doc.get("college_data_last_updated"), datetime):
            college_data_last_updated_iso = user_doc.get("college_data_last_updated").isoformat()
        
        created_at_iso = None
        if user_doc.get("created_at") and isinstance(user_doc.get("created_at"), datetime):
            created_at_iso = user_doc.get("created_at").isoformat()

        updated_at_iso = None
        if user_doc.get("updated_at") and isinstance(user_doc.get("updated_at"), datetime):
            updated_at_iso = user_doc.get("updated_at").isoformat()
            
        return {
            "id": str(user_doc["_id"]),
            "usn": user_doc.get("usn"),
            "name": user_doc.get("name"),
            "email": user_doc.get("email"),
            "role": user_doc.get("role"),
            "collegeProfile": user_doc.get("college_profile"),
            "academicSummaries": user_doc.get("academic_summaries"),
            "examHistory": user_doc.get("exam_history"),
            "mostRecentCGPA": user_doc.get("most_recent_cgpa"),
            "collegeDataLastUpdated": college_data_last_updated_iso,
            "avatar": user_doc.get("avatar"),
            "createdAt": created_at_iso,
            "updatedAt": updated_at_iso,
        }