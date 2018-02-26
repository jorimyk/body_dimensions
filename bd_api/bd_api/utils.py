import datetime

from validate_email import validate_email

from bd_api import db
from bd_api.users.models import User
from bd_api.users.measurements.models import Measurement

class CommonUtils:

    def getUsername(userId):
        """Return username linked to user Id"""
        q = User.query.add_columns('username').filter_by(id = userId).first()
        if q:
            return q[1]
        else:
            return {'error': 'not found', 'userId': userId}


    def convertFromISODate(date):
        """Convert long ISO date to short if exists, else return None"""
        if date:
            try:
                datetime_object = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                return date
            else:
                return datetime_object.strftime('%Y-%m-%d')
        else:
            return None


    def convertToISODate(date):
        if date:
            return date.isoformat()
        else:
            return None


    def countNumberOfRows(userId):
        numberOfMeasurements = Measurement.query.filter_by(user_id=userId).count()
        return(numberOfMeasurements)


class UserUtils:

    def validate_user_values(user_request):
        user_validation = {}
        if user_request.get('username'):
            if validate_username(user_request.get('username')):
                user_validation['username'] = validate_username(user_request.get('username'))['error']
        if user_request.get('password'):
            if validateString('password', user_request.get('password'), 80):
                user_validation['password'] = validateString('password', user_request.get('password'), 120)['error']
        if user_request.get('email'):
            if isinstance(user_request.get('email'), str):
                if not validate_email(user_request.get('email')):
                    user_validation['email'] = 'invalid email %s' % user_request.get('email')
            else:
                user_validation['email'] = 'invalid email %s (%s)' % (user_request.get('email'), pythonTypeToJSONType(user_request.get('email')))
        if user_request.get('firstName'):
            if validateString('firstName', user_request.get('firstName'), 80):
                user_validation['firstName'] = validateString('firstName', user_request.get('firstName'), 80)['error']
        if user_request.get('lastName'):
            if validateString('lastName', user_request.get('lastName'), 80):
                user_validation['lastName'] = validateString('lastName', user_request.get('lastName'), 80)['error']
        if user_request.get('gender'):
            if validateGender(user_request.get('gender')):
                user_validation['gender'] = validateGender(user_request.get('gender'))['error']
        if user_request.get('dateOfBirth'):
            if validateDate(None, 'dateOfBirth', user_request.get('dateOfBirth')):
                user_validation['dateOfBirth'] = validateDate(None, 'dateOfBirth', user_request.get('dateOfBirth'))['error']
        if user_request.get('public'):
            if validateBoolean('public', user_request.get('public')):
                user_validation['public'] = validateBoolean('public', user_request.get('public'))['error']
        if user_validation:
            user_validation['error'] = 'Invalid value(s)'
        return user_validation


    def userExists(userId):
        return User.query.filter_by(id = userId).first()


    def getUserIdAndRole(username):
        """Return user Id linked to username"""
        q = User.query.add_columns('id').add_columns('role').filter_by(username=username).first()
        if q:
            return q[1], q[2]
        else:
            return False


    def checkIfPublicUser(userId):
        """Return None if user with userId is not public"""
        return User.query.filter_by(public = True).filter_by(id = userId).first()


class MeasurementUtils:

    def validate_measurement_values(userId, measurement_request):
        measurement_validation = {}


def validate_username(username):
    """Return None if username is string 1 to 80 characters and username is not in use"""
    if not username or not isinstance(username, str) or len(username) > 80:
        return {'error': 'invalid username: %s (%s), valid value string 1 to 80 characters, mandatory' % (username, pythonTypeToJSONType(username))}
    q = User.query.filter_by(username = username).first()
    if q:
        return {'error': 'username %s is in use' % username}
    else:
        return None


def validateNumber(key, value):
    """Return None if value data type is None, Int or Float"""
    if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
        return None
    else:
        return {'error': 'invalid value: %s (%s), valid values number/null' % (value, pythonTypeToJSONType(value))}


def validateString(key, value, maxLenght):
    """Return None if value is None or string including 1 to 80 characters"""
    if value is None or isinstance(value, str) and len(value) <= maxLenght and len(value) > 0:
        return None
    else:
        return {'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value))}


def validateGender(gender):
    """Return True if gender equals 'male', 'female' or None"""
    if gender == "male" or gender == "female" or gender == None:
        return None
    else:
        return {'error': 'invalid value: %s (%s), valid values male/female/null' % (gender, pythonTypeToJSONType(gender))}


def validateBoolean(key, value):
    """Return None if value data type is None or boolean"""
    if value is None or isinstance(value, bool):
        return None
    else:
        return {'error': 'invalid value: %s (%s), valid values boolean/null' % (value, pythonTypeToJSONType(value))}


def validateDate(userId, key, date):
    """Return None if date is in ISO 8601 format and user doesn't already have measurements with that date"""
    if key == 'dateOfBirth' and date == None:
        return None

    if not isinstance(date, str):
        return {'error': 'invalid value: %s (%s), valid value date in ISO 8601 format' % (date, pythonTypeToJSONType(date))}

    if 'T' in date:
        try:
            datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
        except TypeError:
            return {'error': 'invalid value: %s (%s), valid value date in ISO 8601 format' % (date, pythonTypeToJSONType(date))}
        except ValueError:
            return {'error': 'invalid value: %s, valid value date in ISO 8601 format' % date}
    else:
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except TypeError:
            return {'error': 'invalid value: %s (%s), valid value date in ISO 8601 format' % (date, pythonTypeToJSONType(date))}
        except ValueError:
            return {'error': 'invalid value: %s, valid value date in ISO 8601 format' % date}

    if userId:
        q = Measurement.query.add_columns('id').filter_by(userId = userId).filter_by(measurementDate = date).first()
        if q:
            return {'error': 'duplicate value found for date %s (dataId %s)' % (date, q[1])}
        else:
            return None


def pythonTypeToJSONType(value):
    """Convert Python data type to JSON data type"""
    if isinstance(value, dict): return 'object'
    elif isinstance(value, (list, tuple)): return 'array'
    elif isinstance(value, str): return 'string'
    elif isinstance(value, bool): return 'boolean'
    elif isinstance(value, (int, float)): return 'number'
    elif value is None: return 'null'
    else: return 'unknown'
