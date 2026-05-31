import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, Response
)
from werkzeug.security import check_password_hash, generate_password_hash
from flaskapp.dbsql import get_db

from flask_cors import cross_origin

bp = Blueprint('auth', __name__, url_prefix="/auth")

cors_required_headers = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', '*'),
    ('Access-Control-Allow-Headers', 'Content-Type')
]

############# DUPLICATE CHECK FOR LEGACY FRONT-END CODE #####################
@cross_origin # Enables CORS
@bp.route('duplicatecheck/register/<username>', methods=['GET'])
def duplicate_check_register_link(username: str):
    print(f'Checking username duplicates: ')
    if request.method == 'GET':
        db = get_db()
        duplicate_username = db.execute(
            'SELECT * FROM ACCOUNT WHERE Username = ?', (username,)
        ).fetchone()

        if (duplicate_username is not None):
            return Response(status=403, headers=cors_required_headers, response='The username has already been picked.')
        return Response(status=200, headers=cors_required_headers, response="The username has not been picked.")
    return Response(status=403, headers=cors_required_headers, response='Inaccessible')

@cross_origin # Enables CORS
@bp.route('duplicatecheck/login/<username>', methods=['GET'])
def duplicate_check_login_link(username: str):
    print(username)
    if request.method == 'GET':
        db = get_db()
        duplicate_username = db.execute(
            'SELECT * FROM ACCOUNT WHERE Username = ?', (username,)
        ).fetchone()

        if (duplicate_username is not None):
            return Response(status=200, headers=cors_required_headers, response='The username has already been picked.')
        return Response(status=403, headers=cors_required_headers, response="The username has not been picked.")
    return Response(status=403, headers=cors_required_headers, response='Inaccessible')
###########################################################

@cross_origin # Enables CORS
@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        request_json = request.json # gets the body data
        username = request_json['username']
        password = request_json['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        
        if error is None:
            try:
                # This is a locally-run app, so only 1 admin is possible.
                admin_id = 1

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
            return Response(status=404, headers=cors_required_headers, response=error)
        return Response(status=200, headers=cors_required_headers)
    return Response(status=403, headers=cors_required_headers, response='Inaccessible')
    
@cross_origin # Enables CORS
@bp.route('login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        request_json = request.json # gets the body data
        username = request_json['username']
        password = request_json['password']
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
            return Response(status=200, headers=cors_required_headers, response=f'The user ID is: {user['AccountID']}')
        else:
            return Response(status=403, headers=cors_required_headers, response=error)
    return Response(status=403, headers=cors_required_headers, response='Inaccessible')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM ACCOUNT WHERE AccountID = ?', (user_id,)
        )

@cross_origin
@bp.route('/logout', methods=['GET'])
def logout():
    if request.method == 'GET':
        session.clear()
        # Redirect to the LOGIN page
        return Response(status=200, headers=cors_required_headers, response='The user has logged out.')
    return Response(status=403, headers=cors_required_headers, response='Inaccessible.')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            print(f'Unable to proceed to {view.__name__} view function as login is required.', flush=True)
            import os
            return redirect(os.getenv('LOGIN_REQUIRED_ENDPOINT'))
        
        return view(**kwargs)

    return wrapped_view