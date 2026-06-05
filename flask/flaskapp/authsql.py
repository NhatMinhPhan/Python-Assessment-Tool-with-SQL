import functools
import os

from flask import (
    Blueprint, g, request, session, Response, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from flaskapp.dbsql import get_db

from flask_cors import cross_origin

bp = Blueprint('auth', __name__, url_prefix="/auth")

# Fetch the frontend endpoint configuration safely
FRONTEND_ORIGIN = os.getenv('FRONTEND_ENDPOINT', 'http://localhost:5173')

# GLOBAL DECORATOR: Custom API-based login security check
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            print(f'Access denied to {view.__name__}: login required.', flush=True)
            # Use jsonify for clean cross-origin contract consistency
            return jsonify({"error": "Login required."}), 401
        return view(**kwargs)
    return wrapped_view


############# DUPLICATE CHECK FOR LEGACY FRONT-END CODE #####################

@bp.route('/duplicatecheck/register/<username>', methods=['GET'])
@cross_origin(origins=FRONTEND_ORIGIN, supports_credentials=True) # ROUTE DECORATOR GOES FIRST
def duplicate_check_register_link(username: str):
    db = get_db()
    duplicate_username = db.execute(
        'SELECT * FROM ACCOUNT WHERE Username = ?', (username,)
    ).fetchone()

    if duplicate_username is not None:
        return Response(status=403, response='The username has already been picked.')
    return Response(status=200, response="The username has not been picked.")


@bp.route('/duplicatecheck/login/<username>', methods=['GET'])
@cross_origin(origins=FRONTEND_ORIGIN, supports_credentials=True)
def duplicate_check_login_link(username: str):
    db = get_db()
    duplicate_username = db.execute(
        'SELECT * FROM ACCOUNT WHERE Username = ?', (username,)
    ).fetchone()

    if duplicate_username is not None:
        return Response(status=200, response='The username has already been picked.')
    return Response(status=403, response="The username has not been picked.")

#############################################################################


@bp.route('/register', methods=['POST']) # Flask-CORS automatically intercepts & handles OPTIONS!
@cross_origin(origins=FRONTEND_ORIGIN, supports_credentials=True)
def register():
    request_json = request.get_json() or {} # Safe JSON retrieval
    username = request_json.get('username')
    password = request_json.get('password')
    db = get_db()
    error = None

    if not username:
        error = 'Username is required.'
    elif not password:
        error = 'Password is required.'
    
    if error is None:
        try:
            admin_id = 1 # App restriction rule
            db.execute(
                '''
                INSERT INTO ACCOUNT (Username, PasswordHash, AdminID)
                VALUES (?, ?, ?)
                ''',
                (username, generate_password_hash(password), admin_id)
            )
            db.commit()
        except db.IntegrityError:
            error = f'User {username} is already registered.'
        
    if error:
        return Response(status=404, response=error)
    return Response(status=200)

    
@bp.route('/login', methods=['POST'])
@cross_origin(origins=FRONTEND_ORIGIN, supports_credentials=True)
def login():
    request_json = request.get_json() or {}
    username = request_json.get('username')
    password = request_json.get('password')
    db = get_db()
    error = None
    
    user = db.execute(
        'SELECT * FROM ACCOUNT WHERE Username = ?', (username,)
    ).fetchone()

    if user is None:
        error = 'Incorrect username.'
    elif not check_password_hash(user['PasswordHash'], password):
        error = 'Incorrect password.'

    if error is None:
        session.clear()
        session['user_id'] = user['AccountID']
        # Fixed quoting mismatch inside the f-string format blocks
        return Response(status=200, response=f"The user ID is: {user['AccountID']}")
    
    return Response(status=403, response=error)


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM ACCOUNT WHERE AccountID = ?', (user_id,)
        ).fetchone()


@bp.route('/logout', methods=['GET'])
@cross_origin(origins=FRONTEND_ORIGIN, supports_credentials=True)
def logout():
    session.clear()
    return Response(status=200, response='The user has logged out.')
