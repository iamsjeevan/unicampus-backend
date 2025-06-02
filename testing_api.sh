#!/bin/bash

# Smoke Test Script for UniCampus Backend (Flask proxied via Node, and native Node APIs)

# --- Configuration ---
NODE_GATEWAY_BASE_URL="http://localhost:3001/api/v1" # All requests go through Node

USER_USN="1MS22CS118"
USER_DOB_DD="13"
USER_DOB_MM="04"
USER_DOB_YYYY="2004"

RUN_SUFFIX=$(date +%s%N | sha256sum | base64 | head -c 4 | sed 's/[^a-zA-Z0-9]//g')
TEMP_FILES=() # Array to store temp file names for cleanup

# --- Helper Functions ---
cleanup_temp_files() {
  echo ""
  echo "--- Cleaning up temporary JSON response files ---"
  for f in "${TEMP_FILES[@]}"; do
    rm -f "$f"
  done
}

check_var() {
  local var_name="$1"; local var_value="$2"; local source_file="$3"
  if [ "$var_value" == "null" ] || [ -z "$var_value" ]; then
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "ERROR: Failed to get or set '$var_name'."
    echo "Source file for ID/Token was: '$source_file'"
    echo "Content of '$source_file' (if it exists):"; cat "$source_file"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    cleanup_temp_files; exit 1
  fi
  echo "SUCCESS: $var_name set to: $var_value"
}

# Function to make a curl request and save response
# Usage: make_request METHOD URL FILENAME [DATA_JSON_STRING] [EXPECTED_STATUS]
make_request() {
    local method="$1"
    local url="$2"
    local output_file="$3"
    local data_json="$4" # Optional: JSON data string for POST/PUT
    local expected_status="${5:-200}" # Default expected status 200

    TEMP_FILES+=("$output_file") # Add to cleanup list

    echo "--- Requesting: $method $url ---"
    
    local curl_cmd="curl -s -w \"%{http_code}\" -X $method \"$url\" \
                    -H \"Content-Type: application/json\" \
                    -H \"Authorization: Bearer $ACCESS_TOKEN\""

    if [ -n "$data_json" ]; then
        curl_cmd="$curl_cmd --data '$data_json'"
    fi
    
    # Execute curl and capture HTTP status code and body separately
    response_and_status=$(eval "$curl_cmd -o $output_file")
    http_status_code=$(echo "$response_and_status" | tail -n1) # Get last line for status
    
    # Check if output file was created (curl -o writes body to file)
    if [ ! -f "$output_file" ] && [ "$http_status_code" -ne "204" ]; then # 204 No Content is ok with no body
        echo "ERROR: curl output file '$output_file' not created for $method $url. HTTP Status: $http_status_code"
        # Attempt to show response if status not as expected but file exists
        if [ -f "$output_file" ]; then cat "$output_file"; fi
        cleanup_temp_files; exit 1
    fi

    echo "Response (Status $http_status_code):"
    if [ -f "$output_file" ]; then
      jq . "$output_file" || cat "$output_file" # Try to pretty print, else cat
    else
      echo "(No response body for status $http_status_code)"
    fi
    echo ""

    # Basic status check
    if [ "$http_status_code" -ne "$expected_status" ]; then
        echo "ERROR: Expected status $expected_status but got $http_status_code for $method $url"
        cleanup_temp_files; exit 1
    fi
}


trap cleanup_temp_files EXIT INT TERM

echo "===== UniCampus API Smoke Test (via Node Gateway) ====="
echo "Node Gateway URL: $NODE_GATEWAY_BASE_URL"
echo ""

# 1. Login (Proxied to Flask)
echo "--- 1. Logging in ---"
LOGIN_PAYLOAD="{ \"usn\": \"$USER_USN\", \"dob_dd\": \"$USER_DOB_DD\", \"dob_mm\": \"$USER_DOB_MM\", \"dob_yyyy\": \"$USER_DOB_YYYY\" }"
# Login doesn't use ACCESS_TOKEN in header, it creates it
response_and_status_login=$(curl -s -w "%{http_code}" -X POST "$NODE_GATEWAY_BASE_URL/auth/login/student" \
                            -H "Content-Type: application/json" \
                            --data "$LOGIN_PAYLOAD" \
                            -o login_response.json)
HTTP_STATUS_LOGIN=$(echo "$response_and_status_login" | tail -n1)
TEMP_FILES+=("login_response.json")

if [ "$HTTP_STATUS_LOGIN" -ne "200" ]; then
    echo "ERROR: Login failed with status $HTTP_STATUS_LOGIN"; cat login_response.json; cleanup_temp_files; exit 1
fi
ACCESS_TOKEN=$(jq -r '.accessToken' login_response.json)
check_var "ACCESS_TOKEN" "$ACCESS_TOKEN" "login_response.json"; echo ""


# --- USER APIs (Proxied to Flask) ---
make_request "GET" "$NODE_GATEWAY_BASE_URL/users/me" "user_me_response.json" "" 200

# --- ACADEMIC APIs (Proxied to Flask) ---
make_request "GET" "$NODE_GATEWAY_BASE_URL/results/cie" "cie_response.json" "" 200

# --- CONTENT APIs (App Info - Proxied to Flask, Resources - Native Node) ---
make_request "GET" "$NODE_GATEWAY_BASE_URL/app/info" "app_info_response.json" "" 200 # Auth not strictly needed by Flask route

# --- RESOURCES (Native Node.js) ---
DUMMY_FILE_NAME="resource_smoke_test_$RUN_SUFFIX.pdf"
echo "Test content for $DUMMY_FILE_NAME" > "$DUMMY_FILE_NAME"
TEMP_FILES+=("$DUMMY_FILE_NAME") # Add to cleanup

echo "--- Creating FILE Resource (Native Node) ---"
# Curl for multipart/form-data is different
if ! curl -s -f -X POST "$NODE_GATEWAY_BASE_URL/resources" \
   -H "Authorization: Bearer $ACCESS_TOKEN" \
   -F "title=Smoke Test File ($RUN_SUFFIX)" \
   -F "resource_type=file" \
   -F "description=File for smoke test." \
   -F "category=smoke-test" \
   -F "resourceFile=@$DUMMY_FILE_NAME" \
   -o resource_file_res.json; then
    echo "ERROR: File resource upload failed."; cat resource_file_res.json; cleanup_temp_files; exit 1
fi
RESOURCE_FILE_ID=$(jq -r '.data.resource.id' resource_file_res.json)
check_var "RESOURCE_FILE_ID" "$RESOURCE_FILE_ID" "resource_file_res.json"
jq . resource_file_res.json; echo ""

make_request "GET" "$NODE_GATEWAY_BASE_URL/resources" "list_resources_response.json" "" 200
make_request "GET" "$NODE_GATEWAY_BASE_URL/resources/$RESOURCE_FILE_ID" "detail_resource_response.json" "" 200

# --- COMMUNITY, POST, COMMENT FLOW (Proxied to Flask) ---
COMMUNITY_NAME="Smoke Test Community ($RUN_SUFFIX)"
COMMUNITY_PAYLOAD="{ \"name\": \"$COMMUNITY_NAME\", \"description\": \"Smoke test community.\" }"
make_request "POST" "$NODE_GATEWAY_BASE_URL/communities" "community_res.json" "$COMMUNITY_PAYLOAD" 201
COMMUNITY_ID=$(jq -r '.data.community.id' community_res.json)
check_var "COMMUNITY_ID" "$COMMUNITY_ID" "community_res.json"

POST_TITLE="Smoke Test Post ($RUN_SUFFIX)"
POST_PAYLOAD="{ \"title\": \"$POST_TITLE\", \"content_type\": \"text\", \"content_text\": \"Smoke test post content.\" }"
make_request "POST" "$NODE_GATEWAY_BASE_URL/communities/$COMMUNITY_ID/posts" "post_res.json" "$POST_PAYLOAD" 201
POST_ID=$(jq -r '.data.post.id' post_res.json)
check_var "POST_ID" "$POST_ID" "post_res.json"

COMMENT_TEXT="Smoke test comment ($RUN_SUFFIX)."
COMMENT_PAYLOAD="{ \"text\": \"$COMMENT_TEXT\" }"
make_request "POST" "$NODE_GATEWAY_BASE_URL/posts/$POST_ID/comments" "comment_res.json" "$COMMENT_PAYLOAD" 201
COMMENT_ID=$(jq -r '.data.comment.id' comment_res.json)
check_var "COMMENT_ID" "$COMMENT_ID" "comment_res.json"

# Vote on comment
VOTE_PAYLOAD_COMMENT="{\"direction\": \"up\"}"
make_request "POST" "$NODE_GATEWAY_BASE_URL/comments/$COMMENT_ID/vote" "vote_comment_res.json" "$VOTE_PAYLOAD_COMMENT" 200

# Edit comment
EDIT_COMMENT_PAYLOAD="{ \"text\": \"$COMMENT_TEXT [Edited]\" }"
make_request "PUT" "$NODE_GATEWAY_BASE_URL/comments/$COMMENT_ID" "edit_comment_res.json" "$EDIT_COMMENT_PAYLOAD" 200

# Delete comment
make_request "DELETE" "$NODE_GATEWAY_BASE_URL/comments/$COMMENT_ID" "delete_comment_res.json" "" 200

# Delete post
make_request "DELETE" "$NODE_GATEWAY_BASE_URL/posts/$POST_ID" "delete_post_res.json" "" 200

# --- Clean up the dummy file for resource upload ---
# rm -f "$DUMMY_FILE_NAME" # Cleanup function will handle this if added to TEMP_FILES

echo "===== API Smoke Test Finished (Run Suffix: $RUN_SUFFIX) ====="
# Cleanup of .json files is handled by the trap