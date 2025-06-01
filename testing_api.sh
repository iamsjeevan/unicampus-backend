#!/bin/bash

# Script to test UniCampus API endpoints for communities, posts, and comments

# --- Configuration ---
BASE_URL="http://localhost:5000/api/v1"
USER_USN="1MS22CS118"
USER_DOB_DD="13"
USER_DOB_MM="04"
USER_DOB_YYYY="2004"

# --- Helper Functions ---
cleanup_json_files() {
  echo "Cleaning up temporary JSON response files..."
  rm -f login_response.json community_response.json post_response.json \
        comment1_response.json comment2_response.json vote_response.json \
        edit_comment_response.json delete_response.json
}

check_var() {
  local var_name="$1"
  local var_value="$2"
  local source_file="$3"
  if [ "$var_value" == "null" ] || [ -z "$var_value" ]; then
    echo "ERROR: Failed to get $var_name. Check $source_file and API response."
    cat "$source_file"
    cleanup_json_files
    exit 1
  fi
  echo "$var_name set: $var_value"
}

# Trap EXIT signal to ensure cleanup happens
trap cleanup_json_files EXIT

# --- Test Execution ---
echo "===== UniCampus API Test Script ====="
echo "Using Base URL: $BASE_URL"
echo ""

# 1. Login and Get Tokens
echo "--- 1. Logging in ---"
curl -s -X POST "$BASE_URL/auth/login/student" \
-H "Content-Type: application/json" \
--data "{
    \"usn\": \"$USER_USN\",
    \"dob_dd\": \"$USER_DOB_DD\",
    \"dob_mm\": \"$USER_DOB_MM\",
    \"dob_yyyy\": \"$USER_DOB_YYYY\"
}" \
| tee login_response.json > /dev/null # Tee to file, suppress stdout for cleaner script output

ACCESS_TOKEN=$(jq -r '.accessToken' login_response.json)
check_var "ACCESS_TOKEN" "$ACCESS_TOKEN" "login_response.json"
echo ""

# 2. Create a Community
echo "--- 2. Creating a Community ---"
curl -s -X POST "$BASE_URL/communities" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
--data '{
    "name": "API Test Community - Scripted",
    "description": "A community created by the API test script.",
    "tags": ["scripted-test", "api-testing"]
}' | tee community_response.json > /dev/null

COMMUNITY_ID=$(jq -r '.data.community.id' community_response.json)
check_var "COMMUNITY_ID" "$COMMUNITY_ID" "community_response.json"
echo ""

# 3. Create a Post in the Community
echo "--- 3. Creating a Post in Community ID: $COMMUNITY_ID ---"
curl -s -X POST "$BASE_URL/communities/$COMMUNITY_ID/posts" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
--data '{
    "title": "Scripted Test Post for Comments & Votes",
    "content_type": "text",
    "content_text": "This post was created by an automated script to test comments and voting.",
    "tags": ["automated", "testing"]
}' | tee post_response.json > /dev/null

POST_ID=$(jq -r '.data.post.id' post_response.json)
check_var "POST_ID" "$POST_ID" "post_response.json"
echo ""

# 4. Create a Parent Comment
echo "--- 4. Creating a Parent Comment on Post ID: $POST_ID ---"
curl -s -X POST "$BASE_URL/posts/$POST_ID/comments" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
--data '{
    "text": "This is the PARENT comment created by script."
}' | tee comment1_response.json > /dev/null

PARENT_COMMENT_ID=$(jq -r '.data.comment.id' comment1_response.json)
check_var "PARENT_COMMENT_ID" "$PARENT_COMMENT_ID" "comment1_response.json"
echo ""

# 5. Create a Reply to the Parent Comment
echo "--- 5. Creating a Reply to Parent Comment ID: $PARENT_COMMENT_ID ---"
curl -s -X POST "$BASE_URL/posts/$POST_ID/comments" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
--data '{
    "text": "This is a REPLY to the parent comment, created by script.",
    "parent_comment_id": "'"$PARENT_COMMENT_ID"'"
}' | tee comment2_response.json > /dev/null

REPLY_COMMENT_ID=$(jq -r '.data.comment.id' comment2_response.json)
check_var "REPLY_COMMENT_ID" "$REPLY_COMMENT_ID" "comment2_response.json"
echo ""

# 6. List Top-Level Comments for the Post (Parent should have reply_count > 0)
echo "--- 6. Listing Top-Level Comments for Post ID: $POST_ID ---"
curl -s "$BASE_URL/posts/$POST_ID/comments" \
-H "Authorization: Bearer $ACCESS_TOKEN" | jq .
echo ""

# 7. List Replies for the Parent Comment
echo "--- 7. Listing Replies for Parent Comment ID: $PARENT_COMMENT_ID ---"
curl -s "$BASE_URL/comments/$PARENT_COMMENT_ID/replies" \
-H "Authorization: Bearer $ACCESS_TOKEN" | jq .
echo ""

# 8. Edit the Reply Comment
echo "--- 8. Editing Reply Comment ID: $REPLY_COMMENT_ID ---"
curl -s -X PUT "$BASE_URL/comments/$REPLY_COMMENT_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
--data '{
    "text": "This is the EDITED reply to the parent comment."
}' | tee edit_comment_response.json > /dev/null
jq . edit_comment_response.json # Display edit response
echo ""

# 9. Vote on the Parent Comment (Upvote)
echo "--- 9. Upvoting Parent Comment ID: $PARENT_COMMENT_ID ---"
curl -s -X POST "$BASE_URL/comments/$PARENT_COMMENT_ID/vote" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
--data '{"direction": "up"}' | tee vote_response.json > /dev/null
jq . vote_response.json # Display vote response
echo ""

# 10. List Top-Level Comments Again (Parent should show user_vote: "up")
echo "--- 10. Listing Top-Level Comments for Post ID: $POST_ID (after voting on parent) ---"
curl -s "$BASE_URL/posts/$POST_ID/comments" \
-H "Authorization: Bearer $ACCESS_TOKEN" | jq '.data[] | select(.id == "'"$PARENT_COMMENT_ID"'")' # Filter for parent
echo ""

# 11. Delete the Reply Comment
echo "--- 11. Deleting Reply Comment ID: $REPLY_COMMENT_ID ---"
curl -s -X DELETE "$BASE_URL/comments/$REPLY_COMMENT_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN" | tee delete_response.json > /dev/null
jq . delete_response.json
echo ""

# 12. List Replies for Parent Comment (Reply should be gone)
echo "--- 12. Listing Replies for Parent Comment ID: $PARENT_COMMENT_ID (reply should be gone) ---"
curl -s "$BASE_URL/comments/$PARENT_COMMENT_ID/replies" \
-H "Authorization: Bearer $ACCESS_TOKEN" | jq .
echo ""

# 13. Delete the Parent Comment
echo "--- 13. Deleting Parent Comment ID: $PARENT_COMMENT_ID ---"
curl -s -X DELETE "$BASE_URL/comments/$PARENT_COMMENT_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN" | tee delete_response.json > /dev/null
jq . delete_response.json
echo ""

# 14. List Top-Level Comments (Parent should be gone, Post's comment_count should be 0)
echo "--- 14. Listing Top-Level Comments for Post ID: $POST_ID (parent should be gone) ---"
curl -s "$BASE_URL/posts/$POST_ID/comments" \
-H "Authorization: Bearer $ACCESS_TOKEN" | jq .
echo ""
echo "--- Checking Post's comment_count after all comment deletions ---"
curl -s "$BASE_URL/posts/$POST_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN" | jq '.data.post.comment_count'
echo ""


# 15. Delete the Post
echo "--- 15. Deleting Post ID: $POST_ID ---"
curl -s -X DELETE "$BASE_URL/posts/$POST_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN" | tee delete_response.json > /dev/null
jq . delete_response.json
echo ""

# 16. Verify Post is Deleted
echo "--- 16. Verifying Post ID: $POST_ID is deleted (expect 404) ---"
curl -s -i "$BASE_URL/posts/$POST_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN" # -i to show headers (and status code)
echo ""


echo "===== API Test Script Finished ====="
# Cleanup is handled by the trap