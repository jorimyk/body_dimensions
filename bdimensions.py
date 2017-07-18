from flask import Flask, request, abort, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Users, UserData
import json

engine = create_engine('sqlite:///bdimension.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

@app.route('/', methods = ['HEAD', 'GET']) # /
def hello_world():
    return 'Welcome to root!'


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE']) # /users
def users():
    if request.method == 'POST': # Add a new user
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return addNewUser(d)
            else:
                abort (400, 'No json in request content')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'GET': # List all users
       return getAllUsers()
    elif request.method == 'PUT': # Bulk update users
        abort(501, 'Bulk update users not imlemented')
    elif request.method == 'DELETE': # Delete all users
        abort(501, 'Delete all users not imlemented')


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>
def user(userId):
    if request.method == 'GET': # Show user with userId
        return getUser(userId)
    elif request.method == 'PUT': # Update user
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return updateUser(userId, d)
            else:
                abort (400, 'No json in request content')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'DELETE': # Delete user and all data for user
        return (deleteAllUserData(userId), deleteUser(userId))


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE']) # /users/<user>/data
def user_data(userId):
    if request.method == 'POST': # Add new measurement data
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return addNewData(userId, d)
            else:
                abort (400, 'No json in request content')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'GET': # Get all measurement data for user
        return getUserData(userId)
    elif request.method == 'DELETE': # Delete all measurement data for user
        return deleteAllUserData(userId)


@app.route('/users/<int:userId>/data/<int:dataId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>/data/<data>
def data(userId, dataId):
    if request.method == 'GET': # Get a measurement data item
        return getDataItem(userId, dataId)
    elif request.method == 'PUT': # Update a measurement data item
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return updateDataItem(userId, dataId, d)
            else:
                abort (400, 'No json in request content')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'DELETE': # Delete a measurement data item
        return deleteDataItem(userId, dataId)


def addNewUser(d):
    if 'firstName' in d and d.get('firstName') \
    and 'lastName' in d and d.get('lastName') \
    and 'genre' in d and d.get('genre') \
    and 'dateOfBirth' in d and d.get('dateOfBirth'):
        user = Users( \
        firstName = d.get('firstName'), \
        lastName = d.get('lastName'), \
        genre = d.get('lastName'), \
        dateOfBirth = d.get('dateOfBirth'))
        session.add(user)
        session.commit()
        return jsonify(Users=user.serialize)
    else:
        abort(400, 'Request must contain keywords firstName, lastName, genre and dateOfBirth with values')


def getAllUsers():
    users = session.query(Users).all()
    if users:
        return jsonify(Users=[i.serialize for i in users])
    else:
        abort(404, 'No users found')


def getUser(userId):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        return jsonify(Users=user.serialize)
    else:
        abort(404, 'User with id %s does not exist' % userId)


def updateUser(userId, d):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        validData = False
        if 'firstName' in d and d.get('firstName'):
            validData = True
            user.firstName = d.get('firstName')
        if 'lastName' in d and d.get('lastName'):
            validData = True
            user.lastName = d.get('lastName')
        if 'genre' in d and d.get('genre'):
            validData = True
            user.genre = d.get('genre')
        if 'dateOfBirth' in d and d.get('dateOfBirth'):
            validData = True
            user.dateOfBirth = d.get('dateOfBirth')
        if validData:
            session.add(user)
            session.commit()
            return jsonify(Users=user.serialize)
        else:
            abort(400, 'Request must contain firstName, lastName, genre or dateOfBirth keyword with values')
    else:
        abort(404, 'User with id %s does not exist' % userId)


def deleteUser(userId):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        session.delete(user)
        session.commit()
        return 'Removed user with id %s' % userId
    else:
        abort(404, 'User with id %s does not exist' % userId)


def addNewData(userId, d):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        if not 'measurementDate' in d or not d.get('measurementDate'):
            abort(400, 'Request must contain keyword measurementDate with valid date')
        elif not d.get('height') and not d.get('weight') and not d.get('waistline'):
            abort(400, 'Request must contain value for height, weight or waistline keyword')
        elif (d.get('fatTotal') or d.get('bodyMass') or d.get('fatVisceral')) and not d.get('weight'):
            abort(400, 'For fatTotal, bodyMass and fatVisceral request must contain weight')
        else:        
            data = UserData( \
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
            return jsonify(UserData=data.serialize)
    else:
        abort(404, 'User with id %s does not exist' % userId)


def getUserData(userId):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        data = session.query(UserData).filter_by(userId = userId).all()
        if data:
            return jsonify(UserData=[i.serialize for i in data])
        else:
            abort(404, 'No data for user with id %s' % userId)
    else:
        abort(404, 'User with id %s does not exist' % userId)


def deleteAllUserData(userId):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        data = session.query(UserData).filter_by(userId = userId).all()
        if data:
            for index in range(len(data)):
                session.delete(data[index])
                session.commit()
            return 'All %s data items removed for user with id %s' % (len(data), userId)
        else:
            abort(404, 'No data for user with id %s' % userId)            
    else:
        abort(404, 'User with id %s does not exist' % userId)


def getDataItem(userId, dataId):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        data = session.query(UserData).filter_by(userId = userId).filter_by(id = dataId).first()
        if data:
            return jsonify(UserData=data.serialize)
        else:
            abort(404, 'User with id %s does not have data with id %s' % (userId, dataId))
    else:
        abort(404, 'User with id %s does not exist' % userId)


def updateDataItem(userId, dataId, d):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        data = session.query(UserData).filter_by(userId = userId).filter_by(id = dataId).first()
        if data:
            validData = False
            if 'measurementDate' in d and d.get('measurementDate'):
                validData = True
                data.measurementDate = d.get('measurementDate')
            if 'height' in d and d.get('height'):
                validData = True
                data.height = d.get('height')
            if 'weight' in d and d.get('weight'):
                validData = True
                data.weight = d.get('weight')
            if 'waistline' in d and d.get('waistline'):
                validData = True
                data.waistline = d.get('waistline')
            if 'fatTotal' in d and d.get('fatTotal'):
                validData = True
                data.fatTotal = d.get('fatTotal')
            if 'fatVisceral' in d and d.get('fatVisceral'):
                validData = True
                data.fatVisceral = d.get('fatVisceral')
            if 'bodyMass' in d and d.get('bodyMass'):
                validData = True
                data.bodyMass = d.get('bodyMass')
            if not validData:
                abort(400, 'Request must contain valid keyword(s) with value(s)')
            elif (d.get('fatTotal') or d.get('fatVisceral') or d.get('bodyMass')) \
            and not data.weight and not d.get('weight'):
                abort(400, 'Weight needs to be defined for fatTotal, fatVisceral and bodyMass')
            else:
                session.add(user)
                session.commit()
                return jsonify(UserData=data.serialize)
        else:
            abort(404, 'User with id %s does not have data with id %s' % (userId, dataId))
    else:
        abort(404, 'User with id %s does not exist' % userId)


def deleteDataItem(userId, dataId):
    user = session.query(Users).filter_by(id = userId).first()
    if user:
        data = session.query(UserData).filter_by(userId = userId).filter_by(id = dataId).first()
        if data:
            session.delete(data)
            session.commit()
            return 'Removed data with id %s from user with id %s' % (dataId, userId)
        else:
            abort(404, 'User with id %s does not have data with id %s' % (userId, dataId))
    else:
        abort(404, 'User with id %s does not exist' % userId)


if __name__ == '__main__':
    app.debug = True
    app.run()
