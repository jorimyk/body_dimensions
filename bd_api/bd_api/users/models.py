from bd_api import db

from datetime import datetime

class Role:
    ADMIN = 0
    USER = 1

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(80), nullable=True)
    lastName = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.Integer, default = 1, nullable=False)
    gender = db.Column(db.String(6), nullable=True)
    dateOfBirth = db.Column(db.Date, nullable=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable = False)
    public = db.Column(db.Boolean, nullable = False)
    dateJoined = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    measurements = db.relationship('Measurement', backref='owner', lazy=True)


    @property
    def serialize(self):
        if self.dateOfBirth:
            self.dateOfBirth = self.dateOfBirth.isoformat()
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'public': self.public,
            'username': self.username,
            'firstName': self.firstName,
            'lastName' : self.lastName,
            'gender' : self.gender,
            'dateOfBirth' : self.dateOfBirth,
            'dateJoined' : self.dateJoined.isoformat()
        }


    user_keys = ['firstName',
                'lastName',
                'email',
                'role',
                'gender',
                'dateOfBirth',
                'username',
                'password',
                'public']
