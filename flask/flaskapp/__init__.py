import os
from flask import Flask

import dotenv
dotenv.load_dotenv(dotenv_path='flask/instance/.env')

def create_app(test_config = None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE = os.path.join(app.instance_path, 'flaskapp.sqlite')
    )

    if test_config is None:
        # Load the instance config 'config.py' if it exists
        # silent = True so failures will not be brought up in the console if config doesn't exist
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure that the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError: # Cannot make the directory since it already exists
        pass
    
    # Enable Cross-Origin Resource Sharing (CORS)
    from flask_cors import CORS
    CORS(app=app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], supports_credentials=True)

    IS_DEV = os.getenv('FLASK_ENV') == 'development' or True  # Force True for local

    app.config.update(
        # On HTTP localhost, SameSite must be 'Lax' and Secure must be False for cookies to work
        SESSION_COOKIE_SAMESITE="Lax" if IS_DEV else "None",
        SESSION_COOKIE_SECURE=False if IS_DEV else True
    )
    
    # URL rule for index
    app.add_url_rule('/', endpoint='index')
    
    from . import authsql
    app.register_blueprint(authsql.bp)

    from . import evaluationsql
    app.register_blueprint(evaluationsql.bp)

    # SQLite
    from . import dbsql
    dbsql.init_app(app)

    return app

# Remember to run the app with --no-reload
# so the server doesn't reload when response.py changes