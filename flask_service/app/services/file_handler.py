# Example: app/services/file_handler.py (or wherever save_base64_image is)
import os
import base64
import uuid
from flask import current_app # To access app.config

# Ensure this directory exists or is created when the app starts
# UPLOAD_FOLDER_BASE = current_app.config['UPLOAD_FOLDER'] # This will be an absolute path on the server

def save_base64_image(base64_string_with_prefix: str, subfolder_name: str, base_filename_prefix: str) -> str:
    """
    Saves a base64 encoded image to the specified subfolder within UPLOAD_FOLDER
    and returns the full public HTTPS URL.
    """
    if not base64_string_with_prefix or not base64_string_with_prefix.startswith('data:image'):
        raise ValueError("Invalid base64 image string")

    header, encoded_data = base64_string_with_prefix.split(',', 1)
    image_data = base64.b64decode(encoded_data)
    
    # Determine file extension
    # e.g., 'data:image/png;base64' -> 'png'
    try:
        file_extension = header.split('/')[1].split(';')[0]
        if not file_extension or file_extension not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            file_extension = 'png' # Default to png if unknown or invalid
    except IndexError:
        file_extension = 'png' # Default if parsing fails

    unique_id = uuid.uuid4().hex
    filename_on_disk = f"{base_filename_prefix}_{unique_id}.{file_extension}"

    # Get the absolute base upload directory from Flask config
    # This UPLOAD_FOLDER should be the root for all uploads, e.g., /path/to/your/project/instance/uploads
    base_upload_dir_on_server = current_app.config['UPLOAD_FOLDER'] 
    
    # Create the full path to the subfolder on the server
    target_subfolder_on_server = os.path.join(base_upload_dir_on_server, subfolder_name)
    os.makedirs(target_subfolder_on_server, exist_ok=True) # Create subfolder if it doesn't exist

    file_path_on_server = os.path.join(target_subfolder_on_server, filename_on_disk)

    with open(file_path_on_server, 'wb') as f:
        f.write(image_data)
    
    current_app.logger.info(f"Saved image to: {file_path_on_server}")

    # --- CONSTRUCT THE PUBLIC HTTPS URL ---
    backend_public_base_url = current_app.config['BACKEND_PUBLIC_BASE_URL'].rstrip('/')
    static_upload_url_segment = current_app.config['STATIC_UPLOAD_SUBPATH'].strip('/')
    
    # The public URL path will be /<STATIC_UPLOAD_SUBPATH>/<subfolder_name>/<filename_on_disk>
    # e.g., /uploads/community_icons/cicon_communityId_uuid.png
    public_url = f"{backend_public_base_url}/{static_upload_url_segment}/{subfolder_name}/{filename_on_disk}"
    
    current_app.logger.info(f"Generated public URL: {public_url}")
    return public_url