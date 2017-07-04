from flask import Flask, request
app = Flask(__name__)

users = [
    {
        'id': 1,
        'title': u'Jori',
        'genre': u'male',
        'date_of_birth': u'30.11.1978'
    },
    {
        'id': 2,
        'title': u'Osmi',
        'genre': u'female',
        'date_of_birth': u'3.5.1993'
    }
]

@app.route('/')
def hello_world():
    return 'Hello, World!'


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
        return 'Show user with id %s' % id
    elif request.method == 'PUT':
        return 'If exists update user with id %s' % id
    elif request.method == 'DELETE':
        return 'Delete user with id %s' % id

@app.route('/users/<int:user_id>/data', methods = ['POST', 'GET', 'PUT', 'DELETE'])
def hello_world4():
    return 'Hello, World!'


@app.route('/users/<int:user_id>/data/<int:data_id>', methods = ['GET', 'PUT', 'DELETE'])
def hello_world5():
    return 'Hello, World!'

if __name__ == '__main__':
    app.debug = True
    app.run()
