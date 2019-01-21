from flask import request, jsonify, make_response

from bd_api import app, db, limiter, auth, CORS
from . models import User, Role
from bd_api.users.measurements.models import Measurement
from bd_api import Config
from bd_api.utils import CommonUtils, UserUtils
from bd_api.auth import Password, Token


# Creeate admin account if no users in database
if not User.query.all():
    admin = User(username='admin', email=Config.admin_email , password=Password.hashPassword(Config.admin_password), role=Role.ADMIN, public=False)
    db.session.add(admin)
    db.session.commit()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.authorization:
        auth = request.authorization
    elif request.form['username'] and request.form['password']:
        auth = {'username': request.form['username'], 'password': request.form['password']}
    else:
        return jsonify(error='username/password required'), 400

    q = User.query.filter_by(username=auth.get('username')).first()

    if q and Password.verifyPassword(auth.get('username'), auth.get('password')):
        response = jsonify({'token': Token.generateToken(q.id, q.username, q.role, Config.expiration).decode('ascii')})
        response.headers['Content-Location'] = '/users/%s' % str(q.id)
        response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
        return response
    else:
        return jsonify(error='Invalid username/password'), 401


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE']) # /users
def users():
    headers = request.headers
    auth = request.authorization

    if not auth:
        user = (None, Role.USER, None)
    elif 'error' in Token.verifyToken(auth.get('username')):
        return jsonify(Token.verifyToken(auth.get('username'))), 401
    else:
        user = Token.verifyToken(auth.get('username'))

    # Add a new user
    if request.method == 'POST':
        d = request.get_json(silent=True)
        return addNewUser(headers, d)
    # Read users
    elif request.method == 'GET':
        return getAllUsers(user)
    # Delete all users
    elif request.method == 'DELETE':
        return deleteUsers(user)
    # Return 405 if method not POST, GET or DELETE
    else:
        return jsonify(error='HTTP method %s not allowed' % request.method), 405


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>
def user(userId):
    headers = request.headers
    auth = request.authorization

    if not auth:
        user = (None, Role.USER, None)
    elif 'error' in Token.verifyToken(auth.get('username')):
        return jsonify(Token.verifyToken(auth.get('username'))), 401
    else:
        user = Token.verifyToken(auth.get('username'))

    # Read user
    if request.method == 'GET':
        return getUser(userId, user)
    # Update user if owner or admin
    elif request.method == 'PUT':
        d = request.get_json(silent=True)
        return updateUser(headers, userId, user, d)
    # Delete user and all measurements for user if owner or admin
    elif request.method == 'DELETE':
        return deleteUser(userId, user)
    # Return 405 if method not GET, PUT or DELETE
    else:
        return jsonify(error='HTTP method %s not allowed' % request.method), 405


def addNewUser(headers, d):
    """Add new user to database if valid username/password and if optional values are valid in d"""

    if not 'Content-Type' in headers or not 'application/json' in headers.get('Content-Type'):
        return jsonify(error='Content Type must be application/json'), 400
    elif not d:
        return jsonify(error='no JSON in request'), 400
    elif not 'username' in d or not 'password' in d or not 'email' in d:
        return jsonify(error='username, password and email required'), 400
    elif UserUtils.validate_user_values(d):
        return jsonify(UserUtils.validate_user_values(d)), 400
    else:
        q = User( \
        firstName = d.get('firstName'), \
        lastName = d.get('lastName'), \
        email = d.get('email'), \
        gender = d.get('gender'), \
        dateOfBirth = CommonUtils.convertFromISODate(d.get('dateOfBirth')), \
        username = d.get('username'), \
        password = Password.hashPassword(d.get('password')), \
        public = d.get('public'))
        db.session.add(q)
        db.session.commit()
        user = q.serialize
        user['token'] = Token.generateToken(user['id'], d.get('username'), 'user', Config.expiration).decode('ascii')
        response = jsonify(user)
        response.status_code = 201
        response.headers['Content-Location'] = '/users/' + str(user['id'])
        response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
        return response


def getAllUsers(user):
    """Return all users from database"""
    if user[1] == Role.ADMIN:
        q = User.query.all()
    else:
        q = User.query.filter((User.id == user[0]) | (User.public == True)).all()
    if q:
        q = [i.serialize for i in q]
        for index in q:
            index['measurements'] = CommonUtils.countNumberOfRows(index['id'])
        return jsonify(q)
    else:
        return ('', 204)


def deleteUsers(user):
    """Delete all measurements and users with role user"""

    if user[1] == Role.ADMIN:
        measurements_deleted = Measurement.query.delete()
        users_deleted = User.query.filter_by(role=Role.USER).delete()
        db.session.commit()
        return jsonify(usersDeleted=users_deleted, measurementsDeleted=measurements_deleted)
    else:
        return jsonify(error='Unauthorized'), 403


def getUser(userId, user):
    """Query user based on userId"""
    q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    elif not user[0] and not q.public:
        return jsonify(error='Authentication required'), 401
    elif user[0] != userId and user[1] != Role.ADMIN and not q.public:
        return jsonify(error='Unauthorized'), 403
    else:
        q = q.serialize
        q['measurements'] = CommonUtils.countNumberOfRows(userId)
        return jsonify(q)


def updateUser(headers, userId, user, d):
    """Update user details if valid keys/values in d"""
    q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    if user[0] != userId and user[1] != Role.ADMIN:
        return jsonify(error='Unauthorized'), 403
    if not 'Content-Type' in headers or not 'application/json' in headers.get('Content-Type'):
        return jsonify(error='Content Type must be application/json'), 400
    if not d:
        return jsonify(error='no JSON in request'), 400
    if not any(key in d for key in User.user_keys):
        return jsonify(error='No valid keys'), 400
    if UserUtils.validate_user_values(d):
        return jsonify(UserUtils.validate_user_values(d)), 400

    if d.get('firstName'):
        q.firstName = d.get('firstName')
    if d.get('lastName'):
        q.lastName = d.get('lastName')
    if d.get('gender'):
        q.gender = d.get('gender')
    if d.get('dateOfBirth'):
        q.dateOfBirth = CommonUtils.convertFromISODate(d.get('dateOfBirth'))
    if d.get('username'):
        q.username = d.get('username')
    if d.get('password'):
        q.password = Password.hashPassword(d.get('password'))
    if d.get('public'):
        q.public = d.get('public')

    db.session.add(q)
    db.session.commit()
    user = q.serialize
    return jsonify(user), 200


def deleteUser(userId, user):
    """Delete user from database based on userId"""
    q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    elif user[0] != userId and user[1] != Role.ADMIN:
        return jsonify(error='Unauthorized'), 403
    else:
        measurements_deleted = Measurement.query.filter_by(owner_id = userId).delete()
        db.session.delete(q)
        db.session.commit()
        return jsonify(result='user removed', userId=userId, username=user[2], measurementsDeleted=measurements_deleted)
