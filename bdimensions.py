from flask import Flask, request, abort, jsonify
import json
app = Flask(__name__)

def load_json():
    with open('users.json') as users_file:
        users_list = json.load(users_file)
    return(users_list)

def write_json(data):
    with open('users_.json', 'w') as users_file:
        json.dump(data, users_file)

@app.route('/', methods = ['HEAD', 'GET'])
def hello_world():
    return 'Welcome to root!'


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE'])
def users():
    if request.method == 'POST': # Add a new user
        if request.headers['Content-Type'] == 'application/json':
            return "JSON Message: " + json.dumps(request.json)
        else:
            abort(415)
    elif request.method == 'GET': # List all users
        users_list = load_json()
        return jsonify(users_list)
    elif request.method == 'PUT':
        return 'Bulk update users'
    elif request.method == 'DELETE':
        return 'Delete all users'


@app.route('/users/<int:user_id>', methods = ['GET', 'PUT', 'DELETE'])
def user(user_id):
    if request.method == 'GET': # Show user with user_id
        users_list = load_json()
        user = [user for user in users_list if user['user_id'] == user_id]
        if len(user) == 0:
            abort(404)
        return jsonify({'user': user[0]})
    elif request.method == 'PUT':
        return 'If exists update user with id %s' % user_id
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

if __name__ == '__main__':
    app.debug = True
    app.run()
