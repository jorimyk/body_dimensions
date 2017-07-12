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
            d = request.get_json()
            return addNewUser(d['firstName'],d['lastName'],d['genre'],d['dateOfBirth'])
        else:
            abort(415)
    elif request.method == 'GET': # List all users
       return getAllUsers()
    elif request.method == 'PUT':
        return 'Bulk update users'
    elif request.method == 'DELETE':
        return 'Delete all users'


@app.route('/users/<int:user_id>', methods = ['GET', 'PUT', 'DELETE'])
def user(user_id):
    if request.method == 'GET': # Show user with user_id
        return getUser(user_id)
    elif request.method == 'PUT':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            return updateUser(user_id, d)
        else:
            abort(415)
        #return 'If exists update user with id %s' % user_id
    elif request.method == 'DELETE':
        return 'Delete user with id %s' % user_id


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


def addNewUser(firstName,lastName,genre,dateOfBirth):
    user = Users(firstName = firstName, lastName = lastName, genre = genre, dateOfBirth = dateOfBirth)
    session.add(user)
    session.commit()
    return jsonify(Users=user.serialize)

def getAllUsers():
    users = session.query(Users).all()
    return jsonify(Users=[i.serialize for i in users])

def getUser(user_id):
    user = session.query(Users).filter_by(id = user_id).one()
    return jsonify(Users=user.serialize)

def updateUser(user_id, d):
    user = session.query(Users).filter_by(id = user_id).one()
    if 'firstName' in d:
        user.firstName = d['firstName']
    if 'lastName' in d:
        user.lastName = d['lastName']
    if 'genre' in d:
        user.genre = d['genre']
    if 'dateOfBirth' in d:
        user.dateOfBirth = d['dateOfBirth']
    session.add(user)
    session.commit()
    return jsonify(Users=user.serialize)


def deleteUser(user_id):
    user = session.query(Users).filter_by(id = user_id).one()
    session.delete(user)
    session.commit()
    return 'Removed user with id %s' % user_id


if __name__ == '__main__':
    app.debug = True
    app.run()
