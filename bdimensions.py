from flask import Flask, request
app = Flask(__name__)

users = [
    {
        'id': 1,
        'name': u'Jori',
        'genre': u'male',
        'date_of_birth': u'7.11.1930'
    },
    {
        'id': 2,
        'name': u'Osmi',
        'genre': u'female',
        'date_of_birth': u'5.3.1995'
    }
]

@app.route('/')
def hello_world():
    return 'Welcome to root!'


@app.route('/users', methods = ['POST', 'GET', 'PUT', 'DELETE'])
def users():
    if request.method == 'POST':
        return 'Add a new user'
    elif request.method == 'GET':
        return 'List users'
    elif request.method == 'PUT':
        return 'Bulk update users'
    elif request.method == 'DELETE':
        return 'Delete all users'


@app.route('/users/<int:user_id>', methods = ['GET', 'PUT', 'DELETE'])
def user(user_id):
#    user = [user for user in users if user['id'] == user_id]
    if request.method == 'GET':
        return 'Show user with id %s' % user_id
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
