#!/bin/bash

OUTPUT_FILE="backend_username_debug.txt"

# Clear the output file if it exists
> "$OUTPUT_FILE"

echo "Concatenating backend files for 'username not coming' debugging into $OUTPUT_FILE..."
echo "" >> "$OUTPUT_FILE"

# --- Flask Service Models ---
echo "--- START: flask_service/app/models/user.py ---" >> "$OUTPUT_FILE"
cat ./flask_service/app/models/user.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or unreadable." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/models/user.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/models/post.py (focus on to_dict and author handling) ---" >> "$OUTPUT_FILE"
# We need the whole file to see how author_id is handled and if user details are fetched
cat ./flask_service/app/models/post.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or unreadable." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/models/post.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/models/comment.py (focus on to_dict and author handling) ---" >> "$OUTPUT_FILE"
cat ./flask_service/app/models/comment.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or unreadable." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/models/comment.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

# --- Flask Service Routes (focus on where user identity is retrieved/used and responses are built) ---
echo "--- START: flask_service/app/routes/auth_routes.py (Login response) ---" >> "$OUTPUT_FILE"
cat ./flask_service/app/routes/auth_routes.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or unreadable." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/routes/auth_routes.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/routes/user_routes.py (User profile endpoints) ---" >> "$OUTPUT_FILE"
cat ./flask_service/app/routes/user_routes.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or unreadable." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/routes/user_routes.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/routes/community_routes.py (GET /posts/:id, GET /posts/:id/comments parts) ---" >> "$OUTPUT_FILE"
# Grep for relevant functions to keep it shorter, but full file might be better if logic is complex
awk '/@community_bp.route\('\''\/posts\//,/\)\s*$/' ./flask_service/app/routes/community_routes.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or relevant sections not found." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "(Note: For community_routes.py, only sections related to /posts/... were attempted. Review full file if needed.)" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/routes/community_routes.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/__init__.py (JWT Configuration) ---" >> "$OUTPUT_FILE"
grep -E "JWTManager|jwt|USER_ID_KEY|user_lookup|user_identity_loader" ./flask_service/app/__init__.py >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or JWT config not found with grep." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "(Note: For __init__.py, only lines matching JWT keywords were included. Review full file if needed.)" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/__init__.py ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

# --- Node Service ---
echo "--- START: node_service/src/middleware/forwardAuthHeader.js ---" >> "$OUTPUT_FILE"
cat ./node_service/src/middleware/forwardAuthHeader.js >> "$OUTPUT_FILE" 2>/dev/null || echo "File not found or unreadable." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: node_service/src/middleware/forwardAuthHeader.js ---" >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

echo "Backend code gathering complete. Please copy the content of $OUTPUT_FILE"