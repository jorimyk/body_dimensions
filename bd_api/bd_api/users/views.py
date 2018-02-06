from flask import request, jsonify, make_response

from bd_api import app, db, limiter, auth
from . models import User, Role
from bd_api import Config
from bd_api.utils import CommonUtils, UserUtils
from bd_api.auth import Authenticate, Password, Token


@app.route('/hello')
def hello():
    return 'Hello, World'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.authorization:
        auth = request.authorization
    elif request.form['username'] and request.form['password']:
        auth = {'username': request.form['username'], 'password': request.form['password']}
    else:
        return jsonify(error='username/password required'), 400
    if UserUtils.getUserIdAndRole(auth.get('username')):
        if Password.verifyPassword(auth.get('username'), auth.get('password')):
            userId, role = UserUtils.getUserIdAndRole(auth.get('username'))
            response = jsonify({'token': Token.generateToken(userId, auth.get('username'), role, Config.expiration).decode('ascii')})
            response.headers['Content-Location'] = '/users/%s' % str(userId)
            response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
            return response
        else:
            return jsonify(error='Invalid username/password'), 401
    else:
        return  jsonify(error='user %s not found' % auth.get('username')), 400


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE']) # /users
def users():
    headers = request.headers
    if request.authorization:
        auth = request.authorization
        if isinstance(Authenticate.authenticate(auth), dict):
            return jsonify(Authenticate.authenticate(auth)), 401
        else:
            userId, role, username = Authenticate.authenticate(auth)
    else:
        role = Role.USER
        userId = None
    if request.method == 'POST': # Add a new user
        if 'Content-Type' in headers and 'application/json' in headers.get('Content-Type'):
            d = request.get_json(silent=True)
            return addNewUser(d)
        else:
            return jsonify(error='Content Type must be application/json'), 400
    elif request.method == 'GET': # List all users
        if role == Role.ADMIN:
            return getAllUsers()
        else:
            return getAllPublicUsers(userId)
#    elif request.method == 'PUT': # Bulk update users
#        return jsonify(error='Bulk update users not implemented'), 501
    elif request.method == 'DELETE': # Delete all users
        if role == Role.ADMIN:
            return deleteUsers()
        else:
            return jsonify(error='Insufficient privileges'), 403
    else:
        return jsonify(error='HTTP method %s not allowed' % request.method), 405


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>
def user(userId):
    headers = request.headers
    if not UserUtils.userExists(userId):
        return jsonify(error='No user with id %s' % userId), 404
    elif request.method == 'GET' and UserUtils.checkIfPublicUser(userId):
        return getUser(userId)
    elif request.authorization:
        auth = request.authorization
        if isinstance(Authenticate.authenticate(auth), dict):
            return jsonify(Authenticate.authenticate(auth)), 401
        elif Authenticate.authenticate(auth)[0] == userId or Authenticate.authenticate(auth)[1] == Role.ADMIN:
            if request.method == 'GET': # Show user with userId
                return getUser(userId)
            elif request.method == 'PUT': # Update user
                if 'Content-Type' in headers and 'application/json' in headers.get('Content-Type'):
                    d = request.get_json(silent=True)
                    return updateUser(userId, d)
                else:
                    return jsonify(error='Content Type must be application/json'), 400
            elif request.method == 'DELETE': # Delete user and all measurements for user
                return deleteUser(userId)
            else:
                return jsonify(error='HTTP method %s not allowed' % request.method), 405
        else:
            return jsonify(error='Insufficient privileges'), 403
    else:
        return jsonify(error='Authorization required'), 401


def addNewUser(d):
    """Add new user to database if valid username/password and if optional values are valid in d"""
    errorResponse = {'firstName': 'string/null', 'lastName': 'string/null', 'gender': 'male/female/null', 'dateOfBirth': 'string YYYY-MM-DD/null', 'username': 'string (Mandatory)', 'password': 'string (Mandatory)', 'public': 'boolean/null'}
    if d:
        if  'username' in d and 'password' in d and 'email' in d:
            if isinstance(UserUtils.checkUsername(d.get('username')), dict):
                return jsonify(UserUtils.checkUsername(d.get('username'))), 400
            if isinstance(UserUtils.validateString('email', d.get('email'), 120), dict):
                return jsonify(UserUtils.validateString('email', d.get('email'), 120)), 400
            if isinstance(UserUtils.validateString('firstName', d.get('firstName'), 80), dict):
                return jsonify(UserUtils.validateString('firstName', d.get('firstName'), 80)), 400
            if isinstance(UserUtils.validateString('lastName', d.get('lastName'), 80), dict):
                return jsonify(UserUtils.validateString('lastName', d.get('lastName'), 80)), 400
            if isinstance(UserUtils.validateGender(d.get('gender')), dict):
                return jsonify(UserUtils.validateGender(d.get('gender'))), 400
            if isinstance(CommonUtils.validateDate(None, 'dateOfBirth', d.get('dateOfBirth')), dict):
                return jsonify(CommonUtils.validateDate(None, 'dateOfBirth', d.get('dateOfBirth'))), 400
            if isinstance(UserUtils.validateBoolean('public', d.get('public')), dict):
                return jsonify(UserUtils.validateBoolean('public', d.get('public'))), 400
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


def getAllUsers():
    """Return all users from database"""
    users = User.query.all()
    if users:
        users = [i.serialize for i in users]
        for index in users:
            index['numberOfMeasurements'] = CommonUtils.countNumberOfRows(index['id'])
            index['dateOfBirth'] = CommonUtils.convertToISODate(index['dateOfBirth'])
        return jsonify(users)
    else:
        return ('', 204)


def getAllPublicUsers(userId):
    """Return all users that user has privileges to view"""
    users = User.query.filter((User.public == True) | (User.id == userId)).all()
    if users:
        users = [i.serialize for i in users]
        for index in users:
            index['numberOfMeasurements'] = CommonUtils.countNumberOfRows(index['id'])
            index['dateOfBirth'] = CommonUtils.convertToISODate(index['dateOfBirth'])
        return jsonify(users)
    else:
        return ('', 204)


def deleteUsers():
    """Delete all users with role user and their data"""
    users = User.query.filter_by(role=1).all()
    numberOfMeasurementsDeleted = 0
    for index in range(len(users)):
        numberOfMeasurementsDeleted += deleteAllMeasurements(users[index].id, True)
        session.delete(users[index])
        session.commit()
    return jsonify(nubmerOfUsersDeleted=len(users), numberOfMeasurementsDeleted=numberOfMeasurementsDeleted)


def getUser(userId):
    """Return user from database based on userId"""
    user = User.query.filter_by(id = userId).first()
    user = user.serialize
    user['numberOfMeasurements'] = CommonUtils.countNumberOfRows(userId)
    user['dateOfBirth'] = CommonUtils.convertToISODate(user['dateOfBirth'])
    return jsonify(user)


def updateUser(userId, d):
    """Update user details if valid keys/values in d"""
    errorResponse = {'firstName': 'string/null (if key exists)', 'lastName': 'string/null (if key exists)', 'gender': '(male/female/null) (if key exists)', 'dateOfBirth': 'string YYYY-MM-DD/null (if key exists)', 'username': 'string (if key exists)', 'password': 'string (if key exists)', 'public': 'boolean/null (if key exists'}
    if d:
        user = User.query.filter_by(id = userId).first()
        validRequest = False
        if 'firstName' in d and UserUtils.validateString('firstName', d.get('firstName'), 80):
            validRequest = True
            user.firstName = d.get('firstName')
        if 'lastName' in d and UserUtils.validateString('lastName', d.get('lastName'), 80):
            validRequest = True
            user.lastName = d.get('lastName')
        if 'gender' in d and UserUtils.validateGender(d.get('gender')):
            validRequest = True
            user.gender = d.get('gender')
        if 'dateOfBirth' in d and CommonUtils.validateDate(userId, 'dateOfBirth', d.get('dateOfBirth')):
            validRequest = True
            user.dateOfBirth = CommonUtils.convertFromISODate(d.get('dateOfBirth'))
        if 'username' in d and checkUsername(d.get('username')):
            validRequest = True
            user.username = d.get('username')
        if 'password' in d and d.get('password'):
            validRequest = True
            user.password = Password.hashPassword(d.get('password'))
        if 'public' in d and UserUtils.validateBoolean('public', d.get('public')):
            validRequest = True
            user.public = d.get('public')
        if validRequest:
            session.add(user)
            session.commit()
            user = user.serialize
            user['dateOfBirth'] = convertToISODate(user['dateOfBirth'])
            return jsonify(user), 201
        else:
            errorResponse['error'] = 'No valid keys or nothing to be updated'
            return jsonify(errorResponse), 400
    else:
        errorResponse['error'] = 'no valid JSON in request'
        return jsonify(errorResponse), 400


def deleteUser(userId):
    """Delete user from database based on userId"""
    numberOfMeasurementsDeleted = deleteAllMeasurements(userId, True)
    user = User.query.filter_by(id = userId).first()
    session.delete(user)
    session.commit()
    return jsonify(result='user removed', numberOfMeasurementsDeleted=numberOfMeasurementsDeleted, userId=userId, username=user.username)
