from passlib.hash import argon2
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

from bd_api import app

def hashPassword(password):
    """Return argon2 hash created from string given as a argument"""
    try:
        passwordHash = argon2.hash(password)
    except TypeError:
        abort(make_response(jsonify(error='invalid password', password='string'), 400))
    return(passwordHash)

def verifyPassword(username, password):
    """Return true if password matches hashed password of user"""
    q = session.query(Users).add_columns('password').filter_by(username = username).first()
    if q:
        return argon2.verify(password, q[1])
    else:
        abort(make_response(jsonify(error='not found: %s' % username), 404))

def generateToken(userId, username, role, expiration):
    """Return token including user id and username, valid expiration time"""
    s = Serializer(app.secret_key, expires_in = expiration)
    token = s.dumps({'id': userId, 'username': username, 'role': role})
    return token

def verifyToken(token):
    """Return user id if valid token"""
    s = Serializer(app.secret_key)
    try:
        data = s.loads(token)
    except SignatureExpired:
        abort(make_response(jsonify(error='Session expired, login required'), 401))
    except BadSignature:
        abort(make_response(jsonify(error='Invalid signature, login required'), 401))
    userId = data['id']
    username = data['username']
    role = data['role']
    return userId, username, role

def authenticate(userId, auth):
    """Return True if token is valid or correct username & password"""
    if not auth.get('password'):
        return userId == verifyToken(auth.get('username'))[0]
    elif getUsername(userId) == auth.get('username'):
        return verifyPassword(auth.get('username'), auth.get('password'))
    else:
        return False
