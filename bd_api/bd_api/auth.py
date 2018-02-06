from passlib.hash import argon2
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

from bd_api import app
from bd_api.users.models import User
from bd_api.utils import UserUtils


class Authenticate:

    def authenticate(auth):
        """Return True if token is valid or correct username & password"""
        if auth.get('username') and not auth.get('password'):
            return Token.verifyToken(auth.get('username'))
        elif auth.get('username') and auth.get('password'):
            if Password.verifyPassword(auth.get('username'), auth.get('password')):
                userId, role = UserUtils.getUserIdAndRole(auth.get('username'))
                return userId, role, auth.get('username')
            else:
                return {'error': 'invalid password'}
        else:
            return {'error': 'authorization required'}


class Password:

    def hashPassword(password):
        """Return argon2 hash created from string given as a argument"""
        try:
            passwordHash = argon2.hash(password)
        except TypeError:
            return {'error': 'invalid password', 'password': 'string'}
        return(passwordHash)


    def verifyPassword(username, password):
        """Return true if password matches hashed password of user"""
        q = User.query.add_columns('password').filter_by(username = username).first()
        if q:
            return argon2.verify(password, q[1])
#        else:
#            return {'error': 'not found: %s' % username}


class Token:

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
            return {'error': 'Session expired, login required'}
        except BadSignature:
            return {'error': 'Invalid signature, login required'}
        userId = data['id']
        username = data['username']
        role = data['role']
        return userId, role, username
