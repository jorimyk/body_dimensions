import datetime

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
#            abort(make_response(jsonify(error='not found', userId=userId), 404))



    def validateDate(userId, key, date):
        """Return True if date is in ISO 8601 format and user doesn't already have measurements with that date"""
        if key == 'dateOfBirth' and date == None:
            return True

        if not isinstance(date, str):
            return {'error': 'invalid value: %s (%s)' % (date, pythonTypeToJSONType(date)), key: 'date in ISO 8601 format'}

        if 'T' in date:
            try:
                datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
            except TypeError:
#                abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (date, pythonTypeToJSONType(date)), key: 'date in ISO 8601 format'}), 400))
                return {'error': 'invalid value: %s (%s)' % (date, pythonTypeToJSONType(date)), key: 'date in ISO 8601 format'}
            except ValueError:
#                abort(make_response(jsonify({'error': 'invalid value: %s' % date, key: 'date in ISO 8601 format'}), 400))
                return {'error': 'invalid value: %s' % date, key: 'date in ISO 8601 format'}
        else:
            try:
                datetime.datetime.strptime(date, '%Y-%m-%d')
            except TypeError:
#                abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (date, pythonTypeToJSONType(date)), key: 'date in ISO 8601 format'}), 400))
                return {'error': 'invalid value: %s (%s)' % (date, pythonTypeToJSONType(date)), key: 'date in ISO 8601 format'}
            except ValueError:
#                abort(make_response(jsonify({'error': 'invalid value: %s' % date, key: 'date in ISO 8601 format'}), 400))
                return {'error': 'invalid value: %s' % date, key: 'date in ISOOO 8601 format'}

        if userId:
#            q = session.query(Measurements).add_columns('id').filter_by(userId = userId).filter_by(measurementDate = date).first()
            q = Measurement.query.add_columns('id').filter_by(userId = userId).filter_by(measurementDate = date).first()
            if q:
#                abort(make_response(jsonify(error='duplicate value found: %s' % date, dataId=q[1], userId=userId, username=getUsername(userId)), 400))
                return {'error': 'duplicate value found: %s' % date, 'dataId': q[1], 'userId': userId, 'username': getUsername(userId)}
            else:
                return True


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

    def userExists(userId):
        return User.query.filter_by(id = userId).first()


    def getUserIdAndRole(username):
        """Return user Id linked to username"""
        q = User.query.add_columns('id').add_columns('role').filter_by(username=username).first()
        if q:
            return q[1], q[2]
        else:
            return False
#            return {'error': 'user %s not found' % username}
#            abort(make_response(jsonify(error='user %s not found' % username), 404))


    def checkUsername(username):
        """Return True if username is string 1 to 80 characters and username is not in use"""
        if not username or not isinstance(username, str) or len(username) > 80:
            return {'error': 'invalid username: %s (%s)' % (username, pythonTypeToJSONType(username)), 'username': 'string (not empty)'}
#            abort(make_response(jsonify(error= 'invalid username: %s (%s)' % (username, pythonTypeToJSONType(username)), username= 'string (not empty)'), 400))
        q = User.query.filter_by(username = username).first()
        if q:
            return {'error': 'username %s is in use' % username}
#            abort(make_response(jsonify(error='username %s is in use' % username), 400))
        else:
            return True


    def checkIfPublicUser(userId):
        """Return None if user with userId is not public"""
        return User.query.filter_by(public = True).filter_by(id = userId).first()


    def validateString(key, value, maxLenght):
        """Return True if value is None or string including 1 to 80 characters"""
        if value is None or isinstance(value, str) and len(value) <= maxLenght and len(value) > 0:
            return True
        else:
#            abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'string (not empty)/null'}), 400))
            return {'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'string (not empty)/null'}


    def validateGender(gender):
        """Return True if gender equals 'male', 'female' or None"""
        if gender == "male" or gender == "female" or gender == None:
            return True
        else:
#            abort(make_response(jsonify(error='invalid value: %s (%s)' % (gender, pythonTypeToJSONType(gender)), gender='male/female/null'), 400))
            return {'error': 'invalid value: %s (%s)' % (gender, pythonTypeToJSONType(gender)), 'gender': 'male/female/null'}


    def validateBoolean(key, value):
        """Return True if value data type is None or boolean"""
        if value is None or isinstance(value, bool):
            return True
        else:
#            abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'boolean/null'}), 400))
            return {'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'boolean/null'}


class MeasurementUtils:

    def validateNumber(key, value):
        """Return True if value data type is None, Int or Float"""
        if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        else:
            return {'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'number/null'}
#            abort(make_response(jsonify({'error': 'invalid value: %s (%s)' % (value, pythonTypeToJSONType(value)), key: 'number/null'}), 400)),


def pythonTypeToJSONType(value):
    """Convert Python data type to JSON data type"""
    if isinstance(value, dict): return 'object'
    elif isinstance(value, (list, tuple)): return 'array'
    elif isinstance(value, str): return 'string'
    elif isinstance(value, bool): return 'boolean'
    elif isinstance(value, (int, float)): return 'number'
    elif value is None: return 'null'
    else: return 'unknown'
