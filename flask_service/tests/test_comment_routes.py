# tests/test_comment_routes.py
import json
import pytest

# --- Test Comment Creation ---
def test_create_comment_success(client, auth_tokens):
    if not hasattr(pytest, 'POST_ID'):
        pytest.skip("POST_ID not set, skipping comment creation test.")
    
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    comment_data = {"text": "A pytest comment on a post."}
    
    response = client.post(f'/api/v1/posts/{pytest.POST_ID}/comments', headers=headers, json=comment_data)
    assert response.status_code == 201
    data = response.get_json()["data"]["comment"]
    assert data["text"] == comment_data["text"]
    assert data["author_id"] == auth_tokens["user_id"]
    assert data["post_id"] == pytest.POST_ID
    pytest.COMMENT_ID = data["id"] # Save for later tests

    # Verify post's comment_count increased
    response_post = client.get(f'/api/v1/posts/{pytest.POST_ID}', headers=headers)
    assert response_post.status_code == 200
    post_data = response_post.get_json()["data"]["post"]
    assert post_data["comment_count"] >= 1 # Should be at least 1

# --- Test Listing Comments ---
def test_list_comments_for_post(client, auth_tokens):
    if not hasattr(pytest, 'POST_ID') or not hasattr(pytest, 'COMMENT_ID'):
        pytest.skip("POST_ID or COMMENT_ID not set, skipping list comments test.")
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    response = client.get(f'/api/v1/posts/{pytest.POST_ID}/comments', headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 1
    assert any(comment['id'] == pytest.COMMENT_ID for comment in data['data'])

# --- Test Creating a Reply ---
def test_create_reply_comment(client, auth_tokens):
    if not hasattr(pytest, 'POST_ID') or not hasattr(pytest, 'COMMENT_ID'):
        pytest.skip("POST_ID or COMMENT_ID (for parent) not set, skipping reply test.")
    
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    reply_data = {
        "text": "This is a pytest reply.",
        "parent_comment_id": pytest.COMMENT_ID
    }
    response = client.post(f'/api/v1/posts/{pytest.POST_ID}/comments', headers=headers, json=reply_data)
    assert response.status_code == 201
    data = response.get_json()["data"]["comment"]
    assert data["text"] == reply_data["text"]
    assert data["parent_comment_id"] == pytest.COMMENT_ID
    pytest.REPLY_ID = data["id"]

    # Verify parent comment's reply_count increased (if model supports this accurately)
    # and post's comment_count increased
    response_parent_comment_list = client.get(f'/api/v1/posts/{pytest.POST_ID}/comments', headers=headers)
    parent_comment_data = next(c for c in response_parent_comment_list.get_json()['data'] if c['id'] == pytest.COMMENT_ID)
    assert parent_comment_data['reply_count'] >= 1


# --- Test Listing Replies ---
def test_list_replies_for_comment(client, auth_tokens):
    if not hasattr(pytest, 'COMMENT_ID') or not hasattr(pytest, 'REPLY_ID'):
        pytest.skip("COMMENT_ID or REPLY_ID not set, skipping list replies test.")
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    response = client.get(f'/api/v1/comments/{pytest.COMMENT_ID}/replies', headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 1
    assert any(reply['id'] == pytest.REPLY_ID for reply in data['data'])

# --- Test Voting on Comment ---
def test_vote_on_comment(client, auth_tokens):
    if not hasattr(pytest, 'COMMENT_ID'):
        pytest.skip("COMMENT_ID not set, skipping vote on comment test.")
    comment_id = pytest.COMMENT_ID
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}

    # Upvote
    response_up = client.post(f'/api/v1/comments/{comment_id}/vote', headers=headers, json={"direction": "up"})
    assert response_up.status_code == 200
    data_up = response_up.get_json()["data"]
    assert data_up["upvotes"] == 1
    assert data_up["user_vote"] == "up"

# --- Test Editing Own Comment ---
def test_edit_own_comment(client, auth_tokens):
    if not hasattr(pytest, 'COMMENT_ID'):
        pytest.skip("COMMENT_ID not set, skipping edit comment test.")
    comment_id = pytest.COMMENT_ID
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    update_data = {"text": "Pytest comment [Edited by test]."}
    
    response = client.put(f'/api/v1/comments/{comment_id}', headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.get_json()["data"]["comment"]
    assert data["text"] == update_data["text"]

# --- Test Deleting Own Comment ---
# This should run after other comment tests for a specific comment
@pytest.mark.run(order=-1) 
def test_delete_own_comment(client, auth_tokens):
    # Create a comment specifically for this delete test
    headers = {'Authorization': f'Bearer {auth_tokens["access_token"]}'}
    post_id = getattr(pytest, 'POST_ID', None)
    if not post_id: pytest.skip("POST_ID not available for creating comment to delete.")

    comment_data = {"text": "This comment will be deleted by pytest."}
    response_create = client.post(f'/api/v1/posts/{post_id}/comments', headers=headers, json=comment_data)
    assert response_create.status_code == 201
    comment_to_delete_id = response_create.get_json()["data"]["comment"]["id"]

    # Delete it
    response_delete = client.delete(f'/api/v1/comments/{comment_to_delete_id}', headers=headers)
    assert response_delete.status_code == 200
    assert "Comment deleted successfully" in response_delete.get_json()["message"]

    # Verify it's gone (by trying to list comments or get it directly)
    response_list = client.get(f'/api/v1/posts/{post_id}/comments', headers=headers)
    assert not any(c['id'] == comment_to_delete_id for c in response_list.get_json()['data'])