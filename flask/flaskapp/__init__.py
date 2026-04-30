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
    CORS(app=app)
    
    # URL rule for index
    app.add_url_rule('/', endpoint='index')

    from . import authjson
    app.register_blueprint(authjson.bp)

    from . import evaluationjson
    app.register_blueprint(evaluationjson.bp)

    # JSON server
    from . import dbjson
    app.cli.add_command(dbjson.create_new_database)
    app.cli.add_command(dbjson.reset_all_db)
    app.cli.add_command(dbjson.clear_all_answers)

    # SQLite
    from . import dbsql
    dbsql.init_app(app)

    return app

# Remember to run the app with --no-reload
# so the server doesn't reload when response.py changes