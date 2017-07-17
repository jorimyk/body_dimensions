from flask import Flask, request, abort, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, deferred
from models import Base, Users, UserData
import json

engine = create_engine('sqlite:///bdimension.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

@app.route('/', methods = ['HEAD', 'GET'])
def hello_world():
    return 'Welcome to root!'


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE'])
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
    elif request.method == 'PUT':
        abort(501, 'Bulk update users not imlemented')
    elif request.method == 'DELETE':
        abort(501, 'Delete all users not imlemented')


@app.route('/users/<int:userId>', methods = ['GET', 'PUT', 'DELETE'])
def user(userId):
    if request.method == 'GET': # Show user with userId
        return getUser(userId)
    elif request.method == 'PUT':
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return updateUser(userId, d)
            else:
                abort (400, 'No json in request content')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'DELETE':
        return deleteUser(userId)


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE'])
def user_data(userId):
    if request.method == 'POST':
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return addNewData(userId, d)
            else:
                abort (400, 'No json in request content')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'GET':
        return getUserData(userId)
    elif request.method == 'DELETE':
        return deleteAllUserData(userId)


@app.route('/users/<int:userId>/data/<int:data_id>', methods = ['GET', 'PUT', 'DELETE'])
def data(userId, data_id):
    if request.method == 'GET':
        return 'Show data item with id %s for user with id %s' % (data_id, userId)
    elif request.method == 'PUT':
        return 'If exists update data item with id %s for user with id %s' % (data_id, userId)
    elif request.method == 'DELETE':
        return 'Delete data item with id %s for user with id %s' % (data_id, userId)


def addNewUser(d):
    if 'firstName' in d and d['firstName'] \
    and 'lastName' in d and d['lastName'] \
    and 'genre' in d and d['genre'] \
    and 'dateOfBirth' in d and d['dateOfBirth']:
        user = Users( \
        firstName = d['firstName'], \
        lastName = d['lastName'], \
        genre = d['lastName'], \
        dateOfBirth = d['dateOfBirth'])
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
        if 'firstName' in d and d['firstName']:
            validData = True
            user.firstName = d['firstName']
        if 'lastName' in d and d['lastName']:
            validData = True
            user.lastName = d['lastName']
        if 'genre' in d and d['genre']:
            validData = True
            user.genre = d['genre']
        if 'dateOfBirth' in d and d['dateOfBirth']:
            validData = True
            user.dateOfBirth = d['dateOfBirth']
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
        if not 'height' in d: d['height'] = ''
        if not 'weight' in d: d['weight'] = ''
        if not 'waistline' in d: d['waistline'] = ''
        if not 'fatTotal' in d: d['fatTotal'] = ''
        if not 'bodyMass' in d: d['bodyMass'] = ''
        if not 'fatVisceral' in d: d['fatVisceral'] = ''
        if not 'measurementDate' in d or not d['measurementDate']:
            abort(400, 'Request must contain keyword measurementDate with valid date')
        #elif not 'height' in d and not 'weight' in d and not 'waistline' in d:
            #abort(400, 'Request must contain height, weight or waistline keyword')
        elif not d['height'] and not d['weight'] and not d['waistline']:
            abort(400, 'Request must contain value for height, weight or waistline keyword')
        elif (d['fatTotal'] or d['bodyMass'] or d['fatVisceral']) and not d['weight']:
            abort(400, 'For fatTotal, bodyMass and fatVisceral request must also contain weight')
        else:        
            data = UserData( \
            userId = userId, \
            measurementDate = d['measurementDate'], \
            height = d['height'], \
            weight = d['weight'], \
            waistline = d['waistline'], \
            fatTotal = d['fatTotal'], \
            bodyMass = d['bodyMass'], \
            fatVisceral = d['fatVisceral'])
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


if __name__ == '__main__':
    app.debug = True
    app.run()
