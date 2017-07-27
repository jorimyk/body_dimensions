from flask import Flask, request, abort, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Users, Measurements
from passlib.hash import argon2
import json, datetime

engine = create_engine('mysql://bdimensions:fatty@localhost/bdimensions')
#engine = create_engine('sqlite:///bdimension.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

limiter = Limiter(app, key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"])

@app.route('/', methods = ['HEAD', 'GET']) # /
def hello_world():
    return 'Welcome to root!'


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE']) # /users
def users():
    if request.method == 'POST': # Add a new user
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json(silent=True)
            return addNewUser(d)
        else:
            abort(400, 'Content Type must be application/json')
    elif request.method == 'GET': # List all users
       return getAllUsers()
    elif request.method == 'PUT': # Bulk update users
        abort(501, 'Bulk update users not implemented')
    elif request.method == 'DELETE': # Delete all users
        abort(501, 'Delete all users not implemented')


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>
def user(userId):
    if request.authorization:
        auth = request.authorization
    else:
        abort (401, 'Authorization required')
    if authenticate(userId, auth):
        if request.method == 'GET': # Show user with userId
            return getUser(userId)
        elif request.method == 'PUT': # Update user
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return updateUser(userId, d)
            else:
                abort(400, 'Content Type must be application/json')
        elif request.method == 'DELETE': # Delete user and all measurements for user
            if checkIfMeasurements(userId): deleteAllMeasurements(userId)
            return deleteUser(userId)
    else:
        abort (401, 'Wrong username / password')


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE']) # /users/<user>/data
def measurement(userId):
    if request.authorization:
        auth = request.authorization
    else:
        abort (401, 'Authorization required')
    if authenticate(userId, auth):
        if request.method == 'POST': # Add new measurement data
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return addNewMeasurement(userId, d)
            else:
                abort(400, 'Content Type must be application/json')
        elif request.method == 'GET': # Get all measurement data for user
            return getMeasurements(userId)
        elif request.method == 'DELETE': # Delete all measurement data for user
            return deleteAllMeasurements(userId)
    else:
        abort (401, 'Wrong username / password')


@app.route('/users/<int:userId>/data/<int:dataId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>/data/<data>
def data(userId, dataId):
    if request.authorization:
        auth = request.authorization
    else:
        abort (401, 'Authorization required')
    if authenticate(userId, auth):
        if request.method == 'GET': # Get a measurement data item
            return getMeasurementItem(userId, dataId)
        elif request.method == 'PUT': # Update a measurement data item
            if request.headers['Content-Type'] == 'application/json':
                d = request.get_json(silent=True)
                return updateMeasurementItem(userId, dataId, d)
            else:
                abort(400, 'Content Type must be application/json')
        elif request.method == 'DELETE': # Delete a measurement data item
            return deleteMeasurementItem(userId, dataId)
    else:
        abort (401, 'Wrong username / password')


def addNewUser(d):
    if d and checkUsername(d.get('username')):
        if 'username' in d and d.get('username') and 'password' in d and d.get('password'):
            user = Users( \
            firstName = d.get('firstName'), \
            lastName = d.get('lastName'), \
            genre = d.get('genre'), \
            dateOfBirth = d.get('dateOfBirth'), \
            username = d.get('username'), \
            password = createPassword(d.get('password')))
            session.add(user)
            session.commit()
            return jsonify(user.serialize), 201
    else:
        abort(make_response(jsonify(firstName='Optional', lastName='Optional', genre='Optional', dateOfBirth='Optional', username='Mandatory', password='Mandatory'), 400))


def getAllUsers():
    users = session.query(Users).all()
    if users:
        return jsonify([i.serialize for i in users])
    else:
        abort(404, 'No users found')


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
        if 'username' in d and d.get('username') and checkUsername(d.get('username')):
            validRequest = True
            user.username = d.get('username')
        if 'password' in d and d.get('password'):
            validRequest = True
            user.password = createPassword(d.get('password'))
        if validRequest:
            session.add(user)
            session.commit()
            return jsonify(user.serialize), 201
        else:
            abort(make_response(jsonify(firstName=d.get('firstName'), lastName=d.get('lastName'), genre=d.get('genre'), dateOfBirth=d.get('dateOfBirth'), username=d.get('username'), password=d.get('password')), 400))
    else:
        abort(make_response(jsonify(firstName='Optional', lastName='Optional', genre='Optional', dateOfBirth='Optional', username='Optional', password='Optional'), 400))


def deleteUser(userId):
    user = session.query(Users).filter_by(id = userId).first()
    session.delete(user)
    session.commit()
    return 'User %s (id %s) removed' % (user.username, userId)


def addNewMeasurement(userId, d):
    if not d or not 'measurementDate' in d or not d.get('measurementDate'):
        abort(make_response(jsonify(measurementDate='Mandatory', height='Optional', weight='Optional', waistline='Optional', fatTotal='Optional', bodyMass='Optional', fatVisceral='Optional'), 400))
    #elif not d.get('height') and not d.get('weight') and not d.get('waistline'):
        #abort(400, 'Request must contain value for height, weight or waistline keyword')
    elif (d.get('fatTotal') or d.get('bodyMass') or d.get('fatVisceral')) and not d.get('weight'):
        abort(make_response(jsonify(measurementDate=d.get('measurementDate'), weight='Mandatory', fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400))
    elif checkMeasurementDate(userId, d.get('measurementDate')):        
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
        abort(404, 'No measurements for user %s (id %s)' % (getUsername(userId), userId))


def deleteAllMeasurements(userId):
    data = session.query(Measurements).filter_by(userId = userId).all()
    if data:
        for index in range(len(data)):
            session.delete(data[index])
            session.commit()
        return 'All %s measurement items removed for user %s (id %s)' % (len(data), getUsername(userId), userId)
    else:
        abort(404, 'No measurements for user %s (id %s)' % (getUsername(userId), userId))


def getMeasurementItem(userId, dataId):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        return jsonify(data.serialize)
    else:
        abort(404, 'User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId))


def updateMeasurementItem(userId, dataId, d):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        if d:
            validRequest = False
            if 'measurementDate' in d and d.get('measurementDate') and checkMeasurementDate(userId, d.get('measurementDate')):
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
        abort(404, 'User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId))


def deleteMeasurementItem(userId, dataId):
    data = session.query(Measurements).filter_by(userId = userId).filter_by(id = dataId).first()
    if data:
        session.delete(data)
        session.commit()
        return 'Removed measurements with id %s from user %s (id %s)' % (dataId, getUsername(userId), userId)
    else:
        abort(404, 'User %s (id %s) does not have measurements with id %s' % (getUsername(userId), userId, dataId))


def createPassword(password):
    passwordHash = argon2.hash(password)
    return(passwordHash)

def authenticate(userId, auth):
    q = session.query(Users).add_columns('username', 'password').filter_by(id = userId).first()
    if q:
        return argon2.verify(auth['password'], q[2])
    else:
        abort(404, 'User with id %s does not exist' % userId)


def checkUsername(username):
    q = session.query(Users).filter_by(username = username).first()
    if q:
        abort(400, 'Username %s is in use' % username)
    else:
        return True

def getUsername(userId):
    q = session.query(Users).add_columns('username').filter_by(id = userId).first()
    if q:
        return q[1]
    else:
        abort(404, 'User with id %s does not exist' % userId)

def checkIfMeasurements(userId):
    q = session.query(Measurements).filter_by(userId = userId).first()
    return q

def checkMeasurementDate(userId, measurementDate):
    q = session.query(Measurements).add_columns('id').filter_by(userId = userId).filter_by(measurementDate = measurementDate).first()
    if q:
        abort(400, 'User %s already has an measurement item id %s for date %s' % (getUsername(userId), q[1], measurementDate))
    else:
        return True


if __name__ == '__main__':
    app.debug = True
    app.run()
