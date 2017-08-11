from flask import Flask, request, abort, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Users, Measurements
from passlib.hash import argon2
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
#from OpenSSL import SSL
import json, random, string, datetime

engine = create_engine('mysql://bdimensions:fatty@localhost/bdimensions')
#engine = create_engine('sqlite:///bdimension.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

limiter = Limiter(app, key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"])

secret_key = secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))


@app.route('/login')
def index():
    if request.authorization:
        auth = request.authorization
    else:
        return jsonify(error='Authorization required'), 401
    if verifyPassword(auth.get('username'), auth.get('password')):
#        return jsonify({'token': generateToken(checkUserId(auth.get('username')), auth.get('username'), 600).decode('ascii')})
        response = jsonify({'token': generateToken(checkUserId(auth.get('username')), auth.get('username'), 600).decode('ascii')})
        response.headers['location'] = '/users/' + str(checkUserId(auth.get('username')))
        return response
    else:
        return jsonify(error='Invalid username/password'), 403


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE']) # /users
def users():
    if request.method == 'POST': # Add a new user
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json(silent=True)
            return addNewUser(d)
        else:
            return jsonify(error='Content Type must be application/json'), 400
    elif request.method == 'GET': # List all users
       return getAllUsers()
    elif request.method == 'PUT': # Bulk update users
        return jsonify(error='Bulk update users not implemented'), 501
    elif request.method == 'DELETE': # Delete all users
        return jsonify(error='Delete all users not implemented'), 501


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>
def user(userId):
    if request.authorization:
        auth = request.authorization
    else:
        return jsonify(error='Authorization required'), 401
    if authenticate(userId, auth):
        if request.method == 'GET': # Show user with userId
            return getUser(userId)
        elif request.method == 'PUT': # Update user
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return updateUser(userId, d)
            else:
                return jsonify(error='Content Type must be application/json'), 400
        elif request.method == 'DELETE': # Delete user and all measurements for user
            if checkIfMeasurements(userId): deleteAllMeasurements(userId)
            return deleteUser(userId)
    else:
        return jsonify(error='Invalid credentials'), 403


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE']) # /users/<user>/data
def measurement(userId):
    if request.authorization:
        auth = request.authorization
    else:
        return jsonify(error='Authorization required'), 401
    if authenticate(userId, auth):
        if request.method == 'POST': # Add new measurement data
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return addNewMeasurement(userId, d)
            else:
                return jsonify(error='Content Type must be application/json'), 400
        elif request.method == 'GET': # Get all measurement data for user
            return getMeasurements(userId)
        elif request.method == 'DELETE': # Delete all measurement data for user
            return deleteAllMeasurements(userId)
    else:
        return jsonify(error='Invalid credentials'), 403


@app.route('/users/<int:userId>/data/<int:dataId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>/data/<data>
def data(userId, dataId):
    if request.authorization:
        auth = request.authorization
    else:
        return jsonify(error='Authorization required'), 401
    if authenticate(userId, auth):
        if request.method == 'GET': # Get a measurement data item
            return getMeasurementItem(userId, dataId)
        elif request.method == 'PUT': # Update a measurement data item
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return updateMeasurementItem(userId, dataId, d)
            else:
                return jsonify(error='Content Type must be application/json'), 400
        elif request.method == 'DELETE': # Delete a measurement data item
            return deleteMeasurementItem(userId, dataId)
    else:
        return jsonify(error='Invalid credentials'), 403


def addNewUser(d):
    """Create new user if valid username/password and if optional values are valid"""
    example = {'firstName': 'string/null', 'lastName': 'string/null', 'genre': 'male/female/null', 'dateOfBirth': 'string(YYYY-MM-DD)/null', 'username': 'string (Mandatory)', 'password': 'string (Mandatory)'}
    if d:
        if  'username' in d and 'password' in d:
            checkUsername(d.get('username'))
            validateString('firstName', d.get('firstName'), 80)
            validateString('lastName', d.get('lastName'), 80)
            validateGenre(d.get('genre'))
            validateDate(None, 'dateOfBirth', d.get('dateOfBirth'))
            user = Users( \
            firstName = d.get('firstName'), \
            lastName = d.get('lastName'), \
            genre = d.get('genre'), \
            dateOfBirth = d.get('dateOfBirth'), \
            username = d.get('username'), \
            password = hashPassword(d.get('password')))
            session.add(user)
            session.commit()
            response = jsonify(user.serialize)
            response.status_code = 201
            response.headers['location'] = '/users/' + str(user.id)
            return response
        else:
            error = {'error': 'invalid JSON keys/values'}
            return jsonify(error, example), 400
    else:
        error = {'error': 'no valid JSON'}
        return jsonify(error, example), 400


def getAllUsers():
    """Return all users in database"""
    users = session.query(Users).all()
    if users:
        return jsonify([i.serialize for i in users])
    else:
        return jsonify(error='No users found'), 404


def getUser(userId):
    """Return user details based on id"""
    user = session.query(Users).filter_by(id = userId).first()
    return jsonify(user.serialize)


def updateUser(userId, d):
    example = {'firstName': 'string/null (if key exists)', 'lastName': 'string/null (if key exists)', 'genre': '(male/female/null) (if key exists)', 'dateOfBirth': 'YYYY-MM-DD/null (if key exists)', 'username': 'string (if key exists)', 'password': 'string (if key exists)'}
    if d:
        user = session.query(Users).filter_by(id = userId).first()
        validRequest = False
        if 'firstName' in d and validateString('firstName', d.get('firstName'), 80):
            validRequest = True
            user.firstName = d.get('firstName')
        if 'lastName' in d and validateString('lastName', d.get('lastName'), 80):
            validRequest = True
            user.lastName = d.get('lastName')
        if 'genre' in d and validateGenre(d.get('genre')):
            validRequest = True
            user.genre = d.get('genre')
        if 'dateOfBirth' in d and validateDate(userId, 'dateOfBirth', d.get('dateOfBirth')):
            validRequest = True
            user.dateOfBirth = d.get('dateOfBirth')
        if 'username' in d and checkUsername(d.get('username')):
            validRequest = True
            user.username = d.get('username')
        if 'password' in d and d.get('password'):
            validRequest = True
            user.password = hashPassword(d.get('password'))
        if validRequest:
            session.add(user)
            session.commit()
            return jsonify(user.serialize), 201
        else:
            error = {'error': 'No valid keys or nothing to be updated'}
            return jsonify(error, example), 400
    else:
        error = {'error': 'no valid JSON'}
        return jsonify(error, example), 400


def deleteUser(userId):
    user = session.query(Users).filter_by(id = userId).first()
    session.delete(user)
    session.commit()
    response = jsonify(result='user removed', userId=userId, username=user.username)
    response.status_code = 200
    return response


def addNewMeasurement(userId, d):
    if d:
        validateDate(userId, 'measurementDate', d.get('measurementDate'))
    else:
        error = {'error': 'no valid JSON'}
        example = {'measurementDate': 'Mandatory, YYYY-MM-DD', 'height': 'number/null', 'weight': 'number/null', 'waistline': 'number/null', 'fatTotal': 'number/null', 'bodyMass': 'number/null', 'fatVisceral': 'number/null'}
        return jsonify(error, example), 400
    validateNumber('height', d.get('height'))
    validateNumber('weight', d.get('weight'))
    validateNumber('waistline', d.get('waistline'))
    validateNumber('fatTotal', d.get('fatTotal'))
    validateNumber('bodyMass', d.get('bodyMass'))
    validateNumber('fatVisceral', d.get('fatVisceral'))
    if (d.get('fatTotal') or d.get('bodyMass') or d.get('fatVisceral')) and not d.get('weight'):
        error = {'error': 'fatTotal, bodymass or fatVisceral needs value for weight'}
        example = {'measurementDate': d.get('measurementDate'), 'weight': 'Mandatory', 'fatTotal': d.get('fatTotal'), 'bodyMass': d.get('bodyMass'), 'fatVisceral': d.get('fatVisceral')}
        return jsonify(error, example), 400
    else:
        data = Measurements( \
        userId = userId, \
        measurementDate = d.get('measurementDate'), \
        height = d.get('height'), \
        weight = d.get('weight'), \
        waistline = d.get('waistline'), \
        fatTotal = d.get('fatTotal'), \
        bodyMass = d.get('bodyMass'), \
        fatVisceral = d.get('fatVisceral'))
        session.add(data)
        session.commit()
        response = jsonify(data.serialize)
        response.status_code = 201
        response.headers['location'] = '/users/' + str(userId) + '/data/' + str(data.id)
        return response


def getMeasurements(userId):
    data = session.query(Measurements).filter_by(userId = userId).all()
    if data:
        return jsonify([i.serialize for i in data])
    else:
        return jsonify(error='measurements not found', userId=userId, username=getUsername(userId)), 404


def deleteAllMeasurements(userId):
    data = session.query(Measurements).filter_by(userId=userId).all()
    for index in range(len(data)):
        session.delete(data[index])
        session.commit()
    return jsonify(result='%s measurements removed' % len(data), userId=userId, username=getUsername(userId))


def getMeasurementItem(userId, dataId):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        return jsonify(data.serialize)
    else:
        return jsonify(error='not found', userId=userId, username=getUsername(userId), dataId=dataId), 404


def updateMeasurementItem(userId, dataId, d):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        if d:
            validRequest = False
            if 'measurementDate' in d and validateDate(userId, 'measurementDate', d.get('measurementDate')):
                validRequest = True
                data.measurementDate = d.get('measurementDate')
            if 'height' in d and validateNumber('height', d.get('height')):
                validRequest = True
                data.height = d.get('height')
            if 'weight' in d and validateNumber('weight', d.get('weight')):
                validRequest = True
                data.weight = d.get('weight')
            if 'waistline' in d and validateNumber('waistline', d.get('waistline')):
                validRequest = True
                data.waistline = d.get('waistline')
            if 'fatTotal' in d and validateNumber('fatTotal', d.get('fatTotal')):
                validRequest = True
                data.fatTotal = d.get('fatTotal')
            if 'fatVisceral' in d and validateNumber('fatVisceral', d.get('fatVisceral')):
                validRequest = True
                data.fatVisceral = d.get('fatVisceral')
            if 'bodyMass' in d and validateNumber('bodyMass', d.get('bodyMass')):
                validRequest = True
                data.bodyMass = d.get('bodyMass')
            if not validRequest:
                abort(make_response(jsonify(measurementDate=d.get('measurementDate'), height=d.get('height'), weight=d.get('weight'), waistline=d.get('waistline'), fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400))
            elif (d.get('fatTotal') or d.get('fatVisceral') or d.get('bodyMass')) and not data.weight and not d.get('weight'):
                abort(make_response(jsonify(weight='Mandatory', fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400))
            else:
                session.add(data)
                session.commit()
                return jsonify(data.serialize), 201
        else:
            error = {'error': 'no valid JSON'}
            example = {'measurementDate': 'YYYY-MM-DD', 'height': 'number/null', 'weight': 'number/null', 'waistline': 'number/null', 'fatTotal': 'number/null', 'bodyMass': 'number/null', 'fatVisceral': 'number/null'}
            abort(make_response(jsonify(error, example), 400))
            #abort(make_response(jsonify(measurementDate='Optional', height='Optional', weight='Optional', waistline='Optional', fatTotal='Optional', bodyMass='Optional', fatVisceral='Optional'), 400))
    else:
        abort(make_response(jsonify(error='User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId)), 404))


def deleteMeasurementItem(userId, dataId):
    """Delete measurement item if owned by user"""
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        session.delete(data)
        session.commit()
        return jsonify(result='Removed measurements with id %s from user %s (id %s)' % (dataId, getUsername(userId), userId))
    else:
#        error = {'error': 'No measurement found'}
        response = jsonify(error='not found', userId=userId, username=getUsername(userId), dataId=dataId)
        response.status_code = 404
        return response
#        abort(404, 'User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId))


def hashPassword(password):
    """Return argon2 hash created from string given as a argument"""
    try:
        passwordHash = argon2.hash(password)
    except TypeError:
#        abort(make_response(jsonify(error='Password cannot be null nor int'), 400))
        abort(make_response(jsonify(error='invalid password', password='string'), 400))
    return(passwordHash)

def verifyPassword(username, password):
    """Return true if password matches hashed password of user"""
    q = session.query(Users).add_columns('password').filter_by(username = username).first()
    if q:
        return argon2.verify(password, q[1])
    else:
        abort(make_response(jsonify(error='not found: %s' % username), 404))

def generateToken(userId, username, expiration):
    """Return token including user id and username, valid expiration time"""
    s = Serializer(secret_key, expires_in = expiration)
    token = s.dumps({'id': userId, 'username': username })
    return token

def verifyToken(token):
    """Return user id if valid token"""
    s = Serializer(secret_key)
    try:
        data = s.loads(token)
    except SignatureExpired:
        abort(make_response(jsonify(error='Session expired, login required'), 401))
    except BadSignature:
        abort(make_response(jsonify(error='Invalid signature, login required'), 401))
    userId = data['id']
    username = data['username']
    return userId

def authenticate(userId, auth):
    """Return True if token is valid or correct username & password"""
    if not auth.get('password'):
        return userId == verifyToken(auth.get('username'))
    elif getUsername(userId) == auth.get('username'):
        return verifyPassword(auth.get('username'), auth.get('password'))
    else:
        return False

def checkUserId(username):
    """Return user Id linked to username"""
    q = session.query(Users).add_columns('id').filter_by(username = username).first()
    return q[1]

def checkUsername(username):
    """Return True if username is string 1 to 80 characters and username is not in use"""
    if not username or not isinstance(username, str) or len(username) > 80:
        abort(make_response(jsonify(error= 'invalid username: %s (%s)' % (username, pythonTypeToJSONType(username)), username= 'string (not empty)'), 400))
    q = session.query(Users).filter_by(username = username).first()
    if q:
        abort(make_response(jsonify(error='username %s is in use' % username), 400))
    else:
        return True

def getUsername(userId):
    """Return username linked to user Id"""
    q = session.query(Users).add_columns('username').filter_by(id = userId).first()
    if q:
        return q[1]
    else:
        abort(make_response(jsonify(error='not found', userId=userId), 404))

def checkIfMeasurements(userId):
    """Return None if user has no measurements"""
    q = session.query(Measurements).filter_by(userId = userId).first()
    return q

def validateString(key, value, maxLenght):
    """Return True if value is None or string including 1 to 80 characters"""
    if value is None or isinstance(value, str) and len(value) <= maxLenght and len(value) > 0:
        return True
    else:
        abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'string (not empty)/null'}), 400))

def validateDate(userId, key, date):
    """Return True if date is in YYYY-MM-DD format and user doesn't already have measurements with that date"""
    if key == 'dateOfBirth' and date == None:
        return True
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        abort(make_response(jsonify({'error': 'invalid value: %s' % date, key: 'YYYY-MM-DD (string)'}), 400))
    except TypeError:
        abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (date, pythonTypeToJSONType(date)), key: 'YYYY-MM-DD (string)'}), 400))
    if userId:
        q = session.query(Measurements).add_columns('id').filter_by(userId = userId).filter_by(measurementDate = date).first()
        if q:
            abort(make_response(jsonify(error='duplicate value found: %s' % date, dataId=q[1], userId=userId, username=getUsername(userId)), 400))
    return True

def validateGenre(genre):
    """Return True if genre equals 'male', 'female' or None"""
    if genre == "male" or genre == "female" or genre == None:
        return True
    else:
        abort(make_response(jsonify(error='invalid value: %s (%s)' % (genre, pythonTypeToJSONType(genre)), genre='male/female/null'), 400))

def validateNumber(key, value):
    """Return True if value data type is None, Int or Float"""
    if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    else:
        abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'number/null'}), 400))

def pythonTypeToJSONType(value):
    if isinstance(value, dict): return 'object'
    elif isinstance(value, (list, tuple)): return 'array'
    elif isinstance(value, str): return 'string'
    elif isinstance(value, bool): return 'boolean'
    elif isinstance(value, (int, float)): return 'number'
    elif value is None: return 'null'
    else: return 'unknown'


#if __name__ == "__main__":
#    context = ('cert.crt', 'key.key')
#    app.run(host='127.0.0.1', port=5000, ssl_context=context, threaded=True, debug=True)

if __name__ == '__main__':
    app.debug = True
    app.run()
