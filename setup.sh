#!/bin/bash

OUTPUT_FILE="backend_post_creation_code.txt"

# Clear the output file if it exists
> "$OUTPUT_FILE"

echo "Concatenating backend files for post creation debugging into $OUTPUT_FILE..."
echo "" >> "$OUTPUT_FILE"

# --- Flask Service ---
echo "--- START: flask_service/app/routes/community_routes.py ---" >> "$OUTPUT_FILE"
cat ./flask_service/app/routes/community_routes.py >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/routes/community_routes.py ---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/models/post.py ---" >> "$OUTPUT_FILE"
cat ./flask_service/app/models/post.py >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/models/post.py ---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "--- START: flask_service/app/__init__.py (relevant parts for request parsing if any) ---" >> "$OUTPUT_FILE"
# You might need to manually copy relevant app factory configuration if it's not obvious
# This cat command might get too much, but let's try.
# Look for lines like app.json_encoder or middleware related to request parsing.
grep -E "app\.json_encoder|app\.json_decoder|request\.get_json|Request|jsonify|Blueprint|CORS" ./flask_service/app/__init__.py >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "(Note: For __init__.py, only lines matching certain keywords were included to keep it concise. Review the full file if needed.)" >> "$OUTPUT_FILE"
echo "--- END: flask_service/app/__init__.py ---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"


# --- Node Service ---
echo "--- START: node_service/src/routes/proxyCommunityRoutes.js ---" >> "$OUTPUT_FILE"
cat ./node_service/src/routes/proxyCommunityRoutes.js >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: node_service/src/routes/proxyCommunityRoutes.js ---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "--- START: node_service/src/app.js ---" >> "$OUTPUT_FILE"
cat ./node_service/src/app.js >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- END: node_service/src/app.js ---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Optional: Docker Compose if service names/ports are relevant
echo "--- START: docker-compose.yml (relevant service definitions) ---" >> "$OUTPUT_FILE"
# Show services to understand network communication if needed
grep -E "service:|image:|ports:|environment:|FLASK_APP_URL|NODE_APP_URL" ./docker-compose.yml >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "(Note: For docker-compose.yml, only lines matching certain keywords were included.)" >> "$OUTPUT_FILE"
echo "--- END: docker-compose.yml ---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"


echo "Done. Please copy the content of $OUTPUT_FILE"