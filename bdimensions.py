from flask import Flask, request, abort, jsonify, make_response, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Users, Measurements
from passlib.hash import argon2
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
import json, random, string

engine = create_engine('mysql://bdimensions:fatty@localhost/bdimensions')
#engine = create_engine('sqlite:///bdimension.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

limiter = Limiter(app, key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"])

secret_key = secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))


@app.route('/login', methods = ['POST']) # /login page
def login():
    if request.method == 'POST':
        if request.authorization:
            auth = request.authorization
        else:
            abort(make_response(jsonify(error='Username/password required'), 401))
        userId = checkUserId(auth.get('username'))
        if not userId:
            abort(make_response(jsonify(error='User %s not found' % auth.get('username')), 401))
        elif not verifyPassword(userId, auth):
            abort(make_response(jsonify(error='Invalid password'), 401))
        else:
            return jsonify({'token': generateAuthToken(userId, 1800).decode('ascii')})


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE']) # /users
def users():
    if request.method == 'POST': # Add a new user
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json(silent=True)
            return addNewUser(d)
        else:
            abort(make_response(jsonify(error='Content Type must be application/json'), 400))
    elif request.method == 'GET': # List all users
       return getAllUsers()
    elif request.method == 'PUT': # Bulk update users
        abort(make_response(jsonify(error='Bulk update users not implemented'), 501))
    elif request.method == 'DELETE': # Delete all users
        abort(make_response(jsonify(error='Delete all users not implemented'), 501))


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>
def user(userId):
    if request.authorization:
        auth = request.authorization
    else:
        abort(make_response(jsonify(error='Authorization required'), 401))
    if authenticate(userId, auth):
        if request.method == 'GET': # Show user with userId
            return getUser(userId)
        elif request.method == 'PUT': # Update user
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return updateUser(userId, d)
            else:
                abort(make_response(jsonify(error='Content Type must be application/json'), 400))
        elif request.method == 'DELETE': # Delete user and all measurements for user
            if checkIfMeasurements(userId): deleteAllMeasurements(userId)
            return deleteUser(userId)
    else:
        abort(make_response(jsonify(error='Invalid credentials'), 401))


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE']) # /users/<user>/data
def measurement(userId):
    if request.authorization:
        auth = request.authorization
    else:
        abort(make_response(jsonify(error='Authorization required'), 401))
    if authenticate(userId, auth):
        if request.method == 'POST': # Add new measurement data
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return addNewMeasurement(userId, d)
            else:
                abort(make_response(jsonify(error='Content Type must be application/json'), 400))
        elif request.method == 'GET': # Get all measurement data for user
            return getMeasurements(userId)
        elif request.method == 'DELETE': # Delete all measurement data for user
            return deleteAllMeasurements(userId)
    else:
        abort(make_response(jsonify(error='Invalid credentials'), 401))


@app.route('/users/<int:userId>/data/<int:dataId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>/data/<data>
def data(userId, dataId):
    if request.authorization:
        auth = request.authorization
    else:
        abort(make_response(jsonify(error='Authorization required'), 401))
    if authenticate(userId, auth):
        if request.method == 'GET': # Get a measurement data item
            return getMeasurementItem(userId, dataId)
        elif request.method == 'PUT': # Update a measurement data item
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return updateMeasurementItem(userId, dataId, d)
            else:
                abort(make_response(jsonify(error='Content Type must be application/json'), 400))
        elif request.method == 'DELETE': # Delete a measurement data item
            return deleteMeasurementItem(userId, dataId)
    else:
        abort(make_response(jsonify(error='Invalid credentials'), 401))


def addNewUser(d):
    if d and 'username' in d and d.get('username') and checkUsername(d.get('username')) and 'password' in d and d.get('password'):
        user = Users( \
        firstName = d.get('firstName'), \
        lastName = d.get('lastName'), \
        genre = d.get('genre'), \
        dateOfBirth = d.get('dateOfBirth'), \
        username = d.get('username'), \
        password = hashPassword(d.get('password')))
        session.add(user)
        session.commit()
        return jsonify(user.serialize), 201
    else:
        error = {'error': 'Incomplete request'}
        example = {'firstName': 'Optional', 'lastName': 'Optional', 'genre': 'Optional', 'dateOfBirth': 'Optional', 'username': 'Mandatory', 'password': 'Mandatory'}
        abort(make_response(jsonify(error, example), 400))


def getAllUsers():
    users = session.query(Users).all()
    if users:
        return jsonify([i.serialize for i in users])
    else:
        abort(make_response(jsonify(error='No users found'), 404))


def getUser(userId):
    user = session.query(Users).filter_by(id = userId).first()
    return jsonify(user.serialize)


def updateUser(userId, d):
    if d:
        user = session.query(Users).filter_by(id = userId).first()
        validRequest = False
        if 'firstName' in d and d.get('firstName'):
            validRequest = True
            user.firstName = d.get('firstName')
        if 'lastName' in d and d.get('lastName'):
            validRequest = True
            user.lastName = d.get('lastName')
        if 'genre' in d and d.get('genre'):
            validRequest = True
            user.genre = d.get('genre')
        if 'dateOfBirth' in d and d.get('dateOfBirth'):
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
            error = {'error': 'No valid keywords or nothing to be updated'}
            example = {'firstName': d.get('firstName'), 'lastName': d.get('lastName'), 'genre': d.get('genre'), 'dateOfBirth': d.get('dateOfBirth'), 'username': d.get('username'), 'password': d.get('password')}
            abort(make_response(jsonify(error, example), 400))
    else:
        error = {'error': 'No valid JSON in request'}
        example = {'firstName': 'Optional', 'lastName': 'Optional', 'genre': 'Optional', 'dateOfBirth': 'Optional', 'username': 'Optional', 'password': 'Optional'}
        abort(make_response(jsonify(error, example), 400))


def deleteUser(userId):
    user = session.query(Users).filter_by(id = userId).first()
    session.delete(user)
    session.commit()
    return jsonify(result='User %s (id %s) removed' % (user.username, userId))


def addNewMeasurement(userId, d):
    if d:
        checkMeasurementDate(userId, d.get('measurementDate'))
    else:
        error = {'error': 'Incomple request'}
        example = {'measurementDate': 'Mandatory', 'height': 'Optional', 'weight': 'Optional', 'waistline': 'Optional', 'fatTotal': 'Optional', 'bodyMass': 'Optional', 'fatVisceral': 'Optional'}
        abort(make_response(jsonify(error, example), 400))
    #elif not d.get('height') and not d.get('weight') and not d.get('waistline'):
        #abort(400, 'Request must contain value for height, weight or waistline keyword')
    if (d.get('fatTotal') or d.get('bodyMass') or d.get('fatVisceral')) and not d.get('weight'):
        error = {'error': 'fatTotal, bodymass or fatVisceral needs value for weight'}
        example = {'measurementDate': d.get('measurementDate'), 'weight': 'Mandatory', 'fatTotal': d.get('fatTotal'), 'bodyMass': d.get('bodyMass'), 'fatVisceral': d.get('fatVisceral')}
        abort(make_response(jsonify(error, example), 400))
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
        return jsonify(data.serialize), 201


def getMeasurements(userId):
    data = session.query(Measurements).filter_by(userId = userId).all()
    if data:
        return jsonify([i.serialize for i in data])
    else:
        abort(make_response(jsonify(error='No measurements for user %s (id %s)' % (getUsername(userId), userId)), 404))


def deleteAllMeasurements(userId):
    data = session.query(Measurements).filter_by(userId = userId).all()
    if data:
        for index in range(len(data)):
            session.delete(data[index])
            session.commit()
        return jsonify(result='All %s measurement items removed for user %s (id %s)' % (len(data), getUsername(userId), userId))
    else:
        abort(make_response(jsonify(error='No measurements for user %s (id %s)' % (getUsername(userId), userId)), 404))


def getMeasurementItem(userId, dataId):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        return jsonify(data.serialize)
    else:
        abort(make_response(jsonify(error='User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId)), 404))


def updateMeasurementItem(userId, dataId, d):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        if d:
            validRequest = False
            if 'measurementDate' in d and checkMeasurementDate(userId, d.get('measurementDate')):
                validRequest = True
                data.measurementDate = d.get('measurementDate')
            if 'height' in d and d.get('height'):
                validRequest = True
                data.height = d.get('height')
            if 'weight' in d and d.get('weight'):
                validRequest = True
                data.weight = d.get('weight')
            if 'waistline' in d and d.get('waistline'):
                validRequest = True
                data.waistline = d.get('waistline')
            if 'fatTotal' in d and d.get('fatTotal'):
                validRequest = True
                data.fatTotal = d.get('fatTotal')
            if 'fatVisceral' in d and d.get('fatVisceral'):
                validRequest = True
                data.fatVisceral = d.get('fatVisceral')
            if 'bodyMass' in d and d.get('bodyMass'):
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
            abort(make_response(jsonify(measurementDate='Optional', height='Optional', weight='Optional', waistline='Optional', fatTotal='Optional', bodyMass='Optional', fatVisceral='Optional'), 400))
    else:
        abort(make_response(jsonify(error='User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId)), 404))


def deleteMeasurementItem(userId, dataId):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        session.delete(data)
        session.commit()
        return jsonify(result='Removed measurements with id %s from user %s (id %s)' % (dataId, getUsername(userId), userId))
    else:
        abort(404, 'User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId))


def hashPassword(password):
    passwordHash = argon2.hash(password)
    return(passwordHash)

def verifyPassword(userId, auth):
    q = session.query(Users).add_columns('password').filter_by(id = userId).first()
    if q:
        return argon2.verify(auth.get('password'), q[1])
    else:
        abort(make_response(jsonify(error='No user with id %s' % userId), 404))

def generateAuthToken(userId, expiration):
    s = Serializer(secret_key, expires_in = expiration)
    token = s.dumps({"id": userId })
    return token

def verifyToken(token):
    s = Serializer(secret_key)
    try:
        data = s.loads(token)
    except SignatureExpired:
        abort(make_response(jsonify(error='Session expired, login required'), 401))
        #abort(401, 'Token expired, login required')
    except BadSignature:
        abort(make_response(jsonify(error='Invalid signarure, login required'), 401))
        abort(401, 'Invalid token, login required')
    userId = data['id']
    return userId

def authenticate(userId, auth):
    q = session.query(Users).add_columns('username', 'password').filter_by(id = userId).first()
    if q:
        return userId == verifyToken(auth.get('username'))
    else:
        abort(make_response(jsonify(error='No user with id %s' % userId), 404))


def checkUserId(username):
    q = session.query(Users).add_columns('id').filter_by(username = username).first()
    if q:
        return q[1]
    else:
        return None

def checkUsername(username):
    q = session.query(Users).filter_by(username = username).first()
    if not username:
        abort(make_response(jsonify(error='Username cannot be empty'), 400))
    elif q:
        abort(make_response(jsonify(error='Username %s is in use' % username), 400))
    else:
        return True

def getUsername(userId):
    q = session.query(Users).add_columns('username').filter_by(id = userId).first()
    if q:
        return q[1]
    else:
        abort(make_response(jsonify(error='No user with id %s' % userId), 404))


def checkIfMeasurements(userId):
    q = session.query(Measurements).filter_by(userId = userId).first()
    return q

def checkMeasurementDate(userId, measurementDate):
    q = session.query(Measurements).add_columns('id').filter_by(userId = userId).filter_by(measurementDate = measurementDate).first()
    if q:
        abort(make_response(jsonify(error='User %s already has an measurement item id %s for date %s' % (getUsername(userId), q[1], measurementDate)), 400))
    elif not measurementDate:
        abort(make_response(jsonify(error='Measurement item must have date'), 400))
    else:
        return True


if __name__ == '__main__':
    app.debug = True
    app.run()
