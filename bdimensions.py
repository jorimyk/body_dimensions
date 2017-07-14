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
                abort (400, 'No json in request')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'GET': # List all users
       return getAllUsers()
    elif request.method == 'PUT':
        abort(501, 'Bulk update users not imlemented')
    elif request.method == 'DELETE':
        abort(501, 'Delete all users not imlemented')


@app.route('/users/<int:user_id>', methods = ['GET', 'PUT', 'DELETE'])
def user(user_id):
    if request.method == 'GET': # Show user with user_id
        return getUser(user_id)
    elif request.method == 'PUT':
        if request.headers['Content-Type'] == 'application/json':
            if request.get_json(silent=True):
                d = request.get_json()
                return updateUser(user_id, d)
            else:
                abort (400, 'No json in request')
        else:
            abort(415, 'Content Type must be application/json')
    elif request.method == 'DELETE':
        return deleteUser(user_id)


@app.route('/users/<int:user_id>/data', methods = ['POST', 'GET', 'DELETE'])
def user_data(user_id):
    if request.method == 'POST':
        return 'Add a new data item for user with id %s' % user_id
    elif request.method == 'GET':
        return 'List data for user with id %s' % user_id
    elif request.method == 'DELETE':
        return 'Delete all data for user with id %s' % user_id


@app.route('/users/<int:user_id>/data/<int:data_id>', methods = ['GET', 'PUT', 'DELETE'])
def data(user_id, data_id):
    if request.method == 'GET':
        return 'Show data item with id %s for user with id %s' % (data_id, user_id)
    elif request.method == 'PUT':
        return 'If exists update data item with id %s for user with id %s' % (data_id, user_id)
    elif request.method == 'DELETE':
        return 'Delete data item with id %s for user with id %s' % (data_id, user_id)


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
    return jsonify(Users=[i.serialize for i in users])

def getUser(user_id):
    user = session.query(Users).filter_by(id = user_id).first()
    if user:
        return jsonify(Users=user.serialize)
    else:
        abort(404, 'User with id %s does not exist' % user_id)

def updateUser(user_id, d):
    user = session.query(Users).filter_by(id = user_id).first()
    if user:
        i = 0
        if 'firstName' in d and d['firstName']:
            i += 1
            user.firstName = d['firstName']
        if 'lastName' in d and d['lastName']:
            i += 1
            user.lastName = d['lastName']
        if 'genre' in d and d['genre']:
            i += 1
            user.genre = d['genre']
        if 'dateOfBirth' in d and d['dateOfBirth']:
            i += 1
            user.dateOfBirth = d['dateOfBirth']
        if (i > 0):
            session.add(user)
            session.commit()
            return jsonify(Users=user.serialize)
        else:
            abort(400, 'Request must contain firstName, lastName, genre or dateOfBirth keyword with values')
    else:
        abort(404, 'User with id %s does not exist' % user_id)


def deleteUser(user_id):
    user = session.query(Users).filter_by(id = user_id).first()
    if user:
        session.delete(user)
        session.commit()
        return 'Removed user with id %s' % user_id
    else:
        abort(404, 'User with id %s does not exist' % user_id)


if __name__ == '__main__':
    app.debug = True
    app.run()
