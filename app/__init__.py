# app/__init__.py
from flask import Flask, jsonify # Added jsonify here as it's used in error handlers
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
    from .routes.content_routes import content_bp # <-- UNCOMMENT THIS IMPORT
    from .routes.academic_routes import academic_bp

    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')
    app.register_blueprint(content_bp, url_prefix='/api/v1') # <-- UNCOMMENT THIS REGISTRATION
    app.register_blueprint(academic_bp, url_prefix='/api/v1') 

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy"}), 200 # Added jsonify call
    
    @jwt.unauthorized_loader
    def unauthorized_response(reason_for_error): # Changed 'callback' to a more descriptive name
        return jsonify({"status": "error", "message": "Missing Authorization Header"}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(error_string): # Changed 'callback'
        return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Token has expired"}), 401
        
    @jwt.needs_fresh_token_loader
    def token_not_fresh_response(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Fresh token required"}), 401

    return app