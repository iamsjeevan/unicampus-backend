    #!/bin/bash

    # Script to test UniCampus Node.js Resources API endpoints

    # --- Configuration ---
    NODE_BASE_URL="http://localhost:3001/api/v1" # Node.js service
    FLASK_BASE_URL="http://localhost:5000/api/v1" # Flask service (for login)

    USER_USN="1MS22CS118"
    USER_DOB_DD="13"
    USER_DOB_MM="04"
    USER_DOB_YYYY="2004"

    RUN_SUFFIX=$(date +%s%N | sha256sum | base64 | head -c 6 | sed 's/[^a-zA-Z0-9]//g')

    # --- Helper Functions ---
    cleanup_json_files() {
    echo ""
    echo "--- Cleaning up temporary JSON response files ---"
    rm -f login_res.json resource_file_res.json resource_link_res.json \
            list_res.json detail_res.json delete_res.json download_res.tmp
    }

    check_var() {
    local var_name="$1"; local var_value="$2"; local source_file="$3"
    if [ "$var_value" == "null" ] || [ -z "$var_value" ]; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "ERROR: Failed to get or set '$var_name'."
        echo "Source file for ID was: '$source_file'"
        echo "Content of '$source_file' (if it exists):"; cat "$source_file"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        cleanup_json_files; exit 1
    fi
    echo "SUCCESS: $var_name set to: $var_value"
    }

    trap cleanup_json_files EXIT

    echo "===== UniCampus Resources API Test Script (Run Suffix: $RUN_SUFFIX) ====="
    echo "Node Service URL: $NODE_BASE_URL"
    echo "Flask Service URL (for login): $FLASK_BASE_URL"
    echo ""

    # 1. Login (to Flask via Node proxy OR directly to Flask to get a token)
    # Assuming Node service has a proxy for login at /auth/login/student
    # If not, change LOGIN_TARGET_URL to $FLASK_BASE_URL
    LOGIN_TARGET_URL="$NODE_BASE_URL" # Change if Node doesn't proxy login

    echo "--- 1. Logging in (via ${LOGIN_TARGET_URL}) ---"
    if ! curl -s -f -X POST "$LOGIN_TARGET_URL/auth/login/student" \
    -H "Content-Type: application/json" \
    --data "{\"usn\":\"$USER_USN\",\"dob_dd\":\"$USER_DOB_DD\",\"dob_mm\":\"$USER_DOB_MM\",\"dob_yyyy\":\"$USER_DOB_YYYY\"}" \
    -o login_res.json; then
        echo "ERROR: Login curl command failed or server returned error."
        cat login_res.json; cleanup_json_files; exit 1
    fi
    ACCESS_TOKEN=$(jq -r '.accessToken' login_res.json)
    check_var "ACCESS_TOKEN" "$ACCESS_TOKEN" "login_res.json"; echo ""
    # Note: The uploaderId in resources will be mocked by tempAuthMiddleware in Node for now.

    # 2. Create a Dummy File for Upload
    DUMMY_FILE_NAME="test_resource_$RUN_SUFFIX.pdf"
    echo "This is a test PDF content for run $RUN_SUFFIX" > "$DUMMY_FILE_NAME"
    echo "Created dummy file: $DUMMY_FILE_NAME"
    echo ""

    # 3. Upload a File Resource
    echo "--- 3. Uploading a FILE Resource ---"
    # Note: $ACCESS_TOKEN is included for completeness, but tempAuthMiddleware might override user
    if ! curl -s -f -X POST "$NODE_BASE_URL/resources" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "title=Test File Resource ($RUN_SUFFIX)" \
    -F "resource_type=file" \
    -F "description=A test PDF file uploaded by script $RUN_SUFFIX." \
    -F "semester_tag=SemAll" \
    -F "category=test-notes" \
    -F "tags=test,pdf,$RUN_SUFFIX" \
    -F "resourceFile=@$DUMMY_FILE_NAME" \
    -o resource_file_res.json; then
        echo "ERROR: File resource upload curl command failed or server returned error."
        cat resource_file_res.json; cleanup_json_files; exit 1
    fi
    jq . resource_file_res.json # Display response
    RESOURCE_FILE_ID=$(jq -r '.data.resource.id' resource_file_res.json)
    check_var "RESOURCE_FILE_ID" "$RESOURCE_FILE_ID" "resource_file_res.json"; echo ""

    # 4. Create a Link Resource
    echo "--- 4. Creating a LINK Resource ---"
    if ! curl -s -f -X POST "$NODE_BASE_URL/resources" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "title=Node.js Official Docs ($RUN_SUFFIX)" \
    -F "resource_type=link" \
    -F "link_url=https://nodejs.org/en/docs/" \
    -F "description=Official Node.js documentation (run $RUN_SUFFIX)." \
    -F "category=documentation" \
    -F "semester_tag=Common" \
    -F "tags=node,docs,$RUN_SUFFIX" \
    -o resource_link_res.json; then
        echo "ERROR: Link resource creation curl command failed or server returned error."
        cat resource_link_res.json; cleanup_json_files; exit 1
    fi
    jq . resource_link_res.json
    RESOURCE_LINK_ID=$(jq -r '.data.resource.id' resource_link_res.json)
    check_var "RESOURCE_LINK_ID" "$RESOURCE_LINK_ID" "resource_link_res.json"; echo ""

    # 5. List All Resources
    echo "--- 5. Listing ALL Resources ---"
    curl -s "$NODE_BASE_URL/resources" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
    echo ""

    # 6. List Resources with Category Filter
    echo "--- 6. Listing Resources with filter: category=test-notes ---"
    curl -s "$NODE_BASE_URL/resources?category=test-notes" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
    echo ""

    # 7. List Resources with Semester Filter
    echo "--- 7. Listing Resources with filter: semester=SemAll ---"
    curl -s "$NODE_BASE_URL/resources?semester=SemAll" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
    echo ""

    # 8. List Resources with Search Query
    echo "--- 8. Listing Resources with search: searchQuery=$RUN_SUFFIX ---"
    curl -s "$NODE_BASE_URL/resources?searchQuery=$RUN_SUFFIX" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
    echo ""

    # 9. Get Specific File Resource Detail
    echo "--- 9. Getting details for File Resource ID: $RESOURCE_FILE_ID ---"
    curl -s "$NODE_BASE_URL/resources/$RESOURCE_FILE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
    echo ""

    # 10. Attempt to Download File Resource
    echo "--- 10. Attempting to download File Resource ID: $RESOURCE_FILE_ID ---"
    # This will save the file with a name like the resourceId if -J is not used with a proper Content-Disposition from server
    # Using -o to save to a specific temp file, and checking if it has content.
    curl -s -L "$NODE_BASE_URL/resources/$RESOURCE_FILE_ID/download" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -o download_res.tmp # Save to a temporary file

    if [ -s download_res.tmp ]; then # Check if file is not empty
        echo "SUCCESS: Download endpoint hit and received data. Saved to download_res.tmp"
        echo "Downloaded file content (first few lines):"
        head -n 3 download_res.tmp
    else
        echo "ERROR: Download endpoint failed or returned empty file."
        # If the server returned JSON error, download_res.tmp might contain it
        if jq -e . download_res.tmp > /dev/null 2>&1; then 
            echo "Response was JSON (likely an error):"
            jq . download_res.tmp
        else
            echo "Response was not JSON, content (if any):"
            cat download_res.tmp
        fi
    fi
    echo ""


    # 11. Delete the File Resource
    echo "--- 11. Deleting File Resource ID: $RESOURCE_FILE_ID ---"
    curl -s -X DELETE "$NODE_BASE_URL/resources/$RESOURCE_FILE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | tee delete_response.json > /dev/null
    jq . delete_response.json
    echo ""

    # 12. Verify File Resource is Deleted
    echo "--- 12. Verifying File Resource ID: $RESOURCE_FILE_ID is deleted (expect 404) ---"
    curl -s -i "$NODE_BASE_URL/resources/$RESOURCE_FILE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
    echo ""

    # 13. Delete the Link Resource
    echo "--- 13. Deleting Link Resource ID: $RESOURCE_LINK_ID ---"
    curl -s -X DELETE "$NODE_BASE_URL/resources/$RESOURCE_LINK_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | tee delete_response.json > /dev/null
    jq . delete_response.json
    echo ""


    echo "===== Resources API Test Script Finished (Run Suffix: $RUN_SUFFIX) ====="
    # Cleanup of .json files is handled by the trap
    rm -f "$DUMMY_FILE_NAME" download_res.tmp # Clean up specific test files