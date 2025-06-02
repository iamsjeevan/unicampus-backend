# tests/test_post_routes.py
import json
import pytest # For pytest.COMMUNITY_ID and pytest.POST_ID

def test_create_post_unauthorized(client):
    # Assuming pytest.COMMUNITY_ID is set by community tests if run in order
    community_id = getattr(pytest, 'COMMUNITY_ID', 'somefakecommunityid') 
    response = client.post(f'/api/v1/communities/{community_id}/posts', json={
        "title": "Unauthorized Post", "content_type": "text", "content_text": "..."
    })
    assert response.status_code == 401

def test_create_post_success(client, auth_tokens):
    if not hasattr(pytest, 'COMMUNITY_ID'):
        pytest.skip("COMMUNITY_ID not set, skipping post creation test.")
    
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    post_data = {
        "title": "Pytest Post Title",
        "content_type": "text",
        "content_text": "This is a test post created by pytest.",
        "tags": ["pytest-post"]
    }
    response = client.post(f'/api/v1/communities/{pytest.COMMUNITY_ID}/posts', headers=headers, json=post_data)
    assert response.status_code == 201
    data = response.get_json()["data"]["post"]
    assert data["title"] == post_data["title"]
    assert data["author_id"] == auth_tokens["user_id"]
    assert data["community_id"] == pytest.COMMUNITY_ID
    pytest.POST_ID = data["id"] # Save for later tests

# --- Test Listing Posts ---
def test_list_posts_for_community(client, auth_tokens):
    if not hasattr(pytest, 'COMMUNITY_ID') or not hasattr(pytest, 'POST_ID'):
        pytest.skip("COMMUNITY_ID or POST_ID not set, skipping list posts test.")
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    response = client.get(f'/api/v1/communities/{pytest.COMMUNITY_ID}/posts', headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 1
    assert any(post['id'] == pytest.POST_ID for post in data['data'])

# --- Test Get Post Detail ---
def test_get_post_detail(client, auth_tokens):
    if not hasattr(pytest, 'POST_ID'):
        pytest.skip("POST_ID not set, skipping get post detail test.")
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    response = client.get(f'/api/v1/posts/{pytest.POST_ID}', headers=headers)
    assert response.status_code == 200
    data = response.get_json()["data"]["post"]
    assert data["id"] == pytest.POST_ID
    assert data["title"] == "Pytest Post Title" # Or whatever was last set

# --- Test Voting on Post ---
def test_vote_on_post(client, auth_tokens):
    if not hasattr(pytest, 'POST_ID'):
        pytest.skip("POST_ID not set, skipping vote on post test.")
    post_id = pytest.POST_ID
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}

    # Upvote
    response_up = client.post(f'/api/v1/posts/{post_id}/vote', headers=headers, json={"direction": "up"})
    assert response_up.status_code == 200
    data_up = response_up.get_json()["data"]
    assert data_up["upvotes"] == 1
    assert data_up["user_vote"] == "up"

    # Remove upvote (upvote again)
    response_remove_up = client.post(f'/api/v1/posts/{post_id}/vote', headers=headers, json={"direction": "up"})
    assert response_remove_up.status_code == 200
    data_remove_up = response_remove_up.get_json()["data"]
    assert data_remove_up["upvotes"] == 0
    assert data_remove_up["user_vote"] is None

    # Downvote
    response_down = client.post(f'/api/v1/posts/{post_id}/vote', headers=headers, json={"direction": "down"})
    assert response_down.status_code == 200
    data_down = response_down.get_json()["data"]
    assert data_down["downvotes"] == 1
    assert data_down["user_vote"] == "down"

# --- Test Editing Own Post ---
def test_edit_own_post(client, auth_tokens):
    if not hasattr(pytest, 'POST_ID'):
        pytest.skip("POST_ID not set, skipping edit post test.")
    post_id = pytest.POST_ID
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    update_data = {"title": "Pytest Post Title [Edited]", "content_text": "Updated content by pytest."}
    
    response = client.put(f'/api/v1/posts/{post_id}', headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.get_json()["data"]["post"]
    assert data["title"] == update_data["title"]
    assert data["content_text"] == update_data["content_text"]

# --- Test Deleting Own Post ---
# Note: This test should ideally run last or use a unique post for deletion testing
# as it removes data used by other tests if they depend on pytest.POST_ID
@pytest.mark.run(order=-1) # Try to run this later if possible, or manage test data better
def test_delete_own_post(client, auth_tokens):
    # Create a new post just for this delete test to avoid interfering with other tests
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    community_id = getattr(pytest, 'COMMUNITY_ID', None)
    if not community_id: # Create a temp community if needed
        comm_resp = client.post('/api/v1/communities', headers=headers, json={"name": "Temp Comm for Del", "description": "..."})
        community_id = comm_resp.get_json()["data"]["community"]["id"]

    post_data = {"title": "Post To Be Deleted by Pytest", "content_type": "text", "content_text": "Delete me."}
    response_create = client.post(f'/api/v1/communities/{community_id}/posts', headers=headers, json=post_data)
    assert response_create.status_code == 201
    post_to_delete_id = response_create.get_json()["data"]["post"]["id"]

    response_delete = client.delete(f'/api/v1/posts/{post_to_delete_id}', headers=headers)
    assert response_delete.status_code == 200
    assert "Post and associated comments deleted successfully" in response_delete.get_json()["message"]

    # Verify it's gone
    response_get = client.get(f'/api/v1/posts/{post_to_delete_id}', headers=headers)
    assert response_get.status_code == 404