from app import create_app

application = create_app() # Gunicorn typically looks for 'application'

if __name__ == '__main__':
    application.run(debug=True)