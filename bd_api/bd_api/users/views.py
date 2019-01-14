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

    # Add a new user if Content-Type == application/json, else return 400
    if request.method == 'POST' and 'Content-Type' in headers and 'application/json' in headers.get('Content-Type'):
        d = request.get_json(silent=True)
        return addNewUser(d)
    elif request.method == 'POST':
        return jsonify(error='Content Type must be application/json'), 400
    # Read users that user is authorized to see
    elif request.method == 'GET':
        return getAllUsers(user)
    # Delete all users if role is admin, else return 403
    elif request.method == 'DELETE' and user[1] == Role.ADMIN:# Delete all users
        return deleteUsers()
    elif request.method == 'DELETE':
        return jsonify(error='Unauthorized'), 403
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
    elif request.method == 'PUT' and 'Content-Type' in headers and 'application/json' in headers.get('Content-Type') and (user[0] == userId or user[1] == Role.ADMIN):
        d = request.get_json(silent=True)
        return updateUser(userId, d)
    elif request.method == 'PUT' and (user[0] == userId or user[1] == Role.ADMIN):
        return jsonify(error='Content Type must be application/json'), 400
    # Delete user and all measurements for user if owner or admin
    elif request.method == 'DELETE' and user[0] == userId or user[1] == Role.ADMIN:
        return deleteUser(userId, user)
    # User not authenticated
    elif not user[0]:
        return jsonify(error='Authentication required'), 401
    # User is not authorized for resource
    elif user[0] != userId:
        return jsonify(error='Unauthorized'), 403
    else:
        return jsonify(error='HTTP method %s not allowed' % request.method), 405


def addNewUser(d):
    """Add new user to database if valid username/password and if optional values are valid in d"""
    errorResponse = {'firstName': 'string/null', 'lastName': 'string/null', 'gender': 'male/female/null', 'dateOfBirth': 'string YYYY-MM-DD/null', 'username': 'string (Mandatory)', 'password': 'string (Mandatory)', 'public': 'boolean/null'}
    if d:
        if  'username' in d and 'password' in d and 'email' in d:
            if UserUtils.validate_user_values(d):
                return jsonify(UserUtils.validate_user_values(d)), 400
            user = User( \
            firstName = d.get('firstName'), \
            lastName = d.get('lastName'), \
            email = d.get('email'), \
            gender = d.get('gender'), \
            dateOfBirth = CommonUtils.convertFromISODate(d.get('dateOfBirth')), \
            username = d.get('username'), \
            password = Password.hashPassword(d.get('password')), \
            public = d.get('public'))
            db.session.add(user)
            db.session.commit()
            user = user.serialize
            user['token'] = Token.generateToken(user['id'], d.get('username'), 'user', Config.expiration).decode('ascii')
            user['dateOfBirth'] = CommonUtils.convertToISODate(user['dateOfBirth'])
            response = jsonify(user)
            response.status_code = 201
            response.headers['Content-Location'] = '/users/' + str(user['id'])
            response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
            return response
        else:
            errorResponse['error'] = 'invalid JSON keys/values'
            return jsonify(errorResponse), 400
    else:
        errorResponse['error'] = 'no JSON in request'
        return jsonify(errorResponse), 400


def getAllUsers(user):
    """Return all users from database"""
    if user[1] == Role.ADMIN:
        q = User.query.all()
    else:
        q = User.query.filter((User.id == user[0]) | (User.public == True)).all()
    if q:
        q = [i.serialize for i in q]
        for index in q:
            index['numberOfMeasurements'] = CommonUtils.countNumberOfRows(index['id'])
            index['dateOfBirth'] = CommonUtils.convertToISODate(index['dateOfBirth'])
        return jsonify(q)
    else:
        return ('', 204)


def deleteUsers():
    """Delete all measurements and users with role user"""
    measurements_deleted = Measurement.query.delete()
    users_deleted = User.query.filter_by(role=Role.USER).delete()

    db.session.commit()
    return jsonify(nubmerOfUsersDeleted=users_deleted, numberOfMeasurementsDeleted=measurements_deleted)


def getUser(userId, user):
    """Query user based on userId"""
    q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    elif not user[0] and not q.public:
        return jsonify(error='Authentication required'), 401
    elif user[0] != userId and user[1] != Role.ADMIN and not q.public:
        return jsonify(error='Unauthorized'), 403
#    elif user[0] == userId or user[1] == Role.ADMIN or q.public:
    else:
        q = q.serialize
        q['numberOfMeasurements'] = CommonUtils.countNumberOfRows(userId)
        q['dateOfBirth'] = CommonUtils.convertToISODate(q['dateOfBirth'])
        return jsonify(q)


def updateUser(userId, d):
    """Update user details if valid keys/values in d"""
    errorResponse = {'firstName': 'string/null (if key exists)', 'lastName': 'string/null (if key exists)', 'gender': '(male/female/null) (if key exists)', 'dateOfBirth': 'string YYYY-MM-DD/null (if key exists)', 'username': 'string (if key exists)', 'password': 'string (if key exists)', 'public': 'boolean/null (if key exists'}
    if d:
        if any(key in d for key in User.user_keys):
            if not UserUtils.validate_user_values(d):
                user = User.query.filter_by(id = userId).first()
                if d.get('firstName'):
                    user.firstName = d.get('firstName')
                if d.get('lastName'):
                    user.lastName = d.get('lastName')
                if d.get('gender'):
                    user.gender = d.get('gender')
                if d.get('dateOfBirth'):
                    user.dateOfBirth = CommonUtils.convertFromISODate(d.get('dateOfBirth'))
                if d.get('username'):
                    user.username = d.get('username')
                if d.get('password'):
                    user.password = Password.hashPassword(d.get('password'))
                if d.get('public'):
                    user.public = d.get('public')
                db.session.add(user)
                db.session.commit()
                user = user.serialize
                user['dateOfBirth'] = CommonUtils.convertToISODate(user['dateOfBirth'])
                return jsonify(user), 200
            else:
                return jsonify(UserUtils.validate_user_values(d)), 400
        else:
            errorResponse['error'] = 'No valid keys'
            return jsonify(errorResponse), 400
    else:
        errorResponse['error'] = 'no valid JSON in request'
        return jsonify(errorResponse), 400


def deleteUser(userId, user):
    """Delete user from database based on userId"""
    q = User.query.filter_by(id = userId).first()

    if q:
        measurements_deleted = Measurement.query.filter_by(owner_id = userId).delete()
        db.session.delete(q)
        db.session.commit()
        return jsonify(result='user removed', userId=userId, username=user[2], numberOfMeasurementsDeleted=measurements_deleted)
    else:
        return jsonify(error='User not found', userId=userId), 404
