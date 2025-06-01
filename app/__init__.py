# app/__init__.py
from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from .config import Config
import os

mongo = PyMongo()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    mongo.init_app(app)
    jwt.init_app(app)

    from .routes.auth_routes import auth_bp
    from .routes.user_routes import user_bp
    from .routes.content_routes import content_bp 
    from .routes.academic_routes import academic_bp
    from .routes.community_routes import community_bp # <-- Ensure this is imported

    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')
    app.register_blueprint(content_bp, url_prefix='/api/v1') 
    app.register_blueprint(academic_bp, url_prefix='/api/v1') 
    app.register_blueprint(community_bp, url_prefix='/api/v1') # <-- Ensure this is registered

    # ... (health_check and JWT error handlers) ...
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy"}), 200
    
    @jwt.unauthorized_loader
    def unauthorized_response(reason_for_error):
        return jsonify({"status": "error", "message": "Missing Authorization Header"}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(error_string):
        return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Token has expired"}), 401
        
    @jwt.needs_fresh_token_loader
    def token_not_fresh_response(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Fresh token required"}), 401
        
    return app