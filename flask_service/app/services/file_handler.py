# app/services/file_handler.py
import base64
import os
import uuid
from flask import current_app, url_for

def save_base64_image(base64_string, upload_folder_name, filename_prefix="img"):
    if not base64_string or not base64_string.startswith('data:image'):
        raise ValueError("Invalid base64 image string format or empty string.")

    try:
        header, encoded_data = base64_string.split(',', 1)
        image_type = header.split(';')[0].split('/')[1]
        allowed_types = ['png', 'jpeg', 'jpg', 'gif', 'webp']
        if image_type.lower() not in allowed_types:
            raise ValueError(f"Unsupported image type: {image_type}. Allowed: {', '.join(allowed_types)}")
        image_data = base64.b64decode(encoded_data)
    except Exception as e:
        current_app.logger.error(f"Base64 decoding error: {e}", exc_info=True)
        raise ValueError(f"Could not decode base64 string: {str(e)}")

    base_upload_path_config = current_app.config.get('UPLOAD_FOLDER')
    if not base_upload_path_config:
        current_app.logger.error("UPLOAD_FOLDER is not configured in the Flask app.")
        raise EnvironmentError("UPLOAD_FOLDER not configured.")
    
    # Ensure UPLOAD_FOLDER is absolute
    if not os.path.isabs(base_upload_path_config):
        base_upload_path = os.path.join(current_app.instance_path, base_upload_path_config)
    else:
        base_upload_path = base_upload_path_config

    if not os.path.exists(base_upload_path):
        os.makedirs(base_upload_path, exist_ok=True)

    target_folder_path = os.path.join(base_upload_path, upload_folder_name)
    if not os.path.exists(target_folder_path):
        os.makedirs(target_folder_path, exist_ok=True)

    unique_id = uuid.uuid4().hex
    filename_with_ext = f"{filename_prefix}_{unique_id}.{image_type}"
    full_file_path = os.path.join(target_folder_path, filename_with_ext)

    try:
        with open(full_file_path, 'wb') as f:
            f.write(image_data)
        current_app.logger.info(f"Saved image to: {full_file_path}")
    except IOError as e:
        current_app.logger.error(f"IOError saving image to {full_file_path}: {e}", exc_info=True)
        raise IOError(f"Could not save image file: {str(e)}")

    # Path for URL generation, relative to the root of UPLOAD_FOLDER
    path_for_url = os.path.join(upload_folder_name, filename_with_ext)
    
    try:
        # Uses the 'serve_uploaded_file' route defined in __init__.py
        image_url = url_for('serve_uploaded_file', filename=path_for_url, _external=True)
        current_app.logger.info(f"Generated public URL for image: {image_url}")
        return image_url
    except RuntimeError as e:
        current_app.logger.error(f"RuntimeError generating URL (likely 'serve_uploaded_file' endpoint issue): {e}", exc_info=True)
        # Fallback to a relative path based on STATIC_UPLOAD_SUBPATH config
        static_subpath = current_app.config.get("STATIC_UPLOAD_SUBPATH", "uploads")
        return f"/{static_subpath}/{path_for_url}"
