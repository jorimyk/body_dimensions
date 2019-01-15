from flask import request, jsonify, make_response

from bd_api import app, db, limiter, auth
from . models import Measurement
from bd_api.users.models import Role, User
from bd_api import Config
from bd_api.utils import CommonUtils, UserUtils, MeasurementUtils
from bd_api.auth import Authenticate, Token


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE']) # /users/<user>/data
# @limiter.limit("100/day")
def measurements(userId):
    headers = request.headers
    auth = request.authorization

    if not auth:
        user = (None, Role.USER, None)
    elif 'error' in Token.verifyToken(auth.get('username')):
        return jsonify(Token.verifyToken(auth.get('username'))), 401
    else:
        user = Token.verifyToken(auth.get('username'))

    # Add new measurement data if owner
    if request.method == 'POST':
        d = request.get_json(silent=True)
        return addNewMeasurement(headers, userId, user, d)
    # Get all measurement data for user
    elif request.method == 'GET':
        return getMeasurements(userId, user)
    # Delete all measurement data for user
    elif request.method == 'DELETE' and user[0] == userId or user[1] == Role.ADMIN:
        return deleteAllMeasurements(userId, user)
    # User not authenticated
#    elif not user[0]:
#        return jsonify(error='Authentication required'), 401
    # User is not authorized for resource
#    elif user[0] != userId:
#        return jsonify(error='Unauthorized'), 403
    else:
        return jsonify(error='HTTP method %s not allowed' % request.method), 405


@app.route('/users/<int:userId>/data/<int:dataId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>/data/<data>
def measurement(userId, dataId):
    headers = request.headers
    auth = request.authorization

    if not auth:
        user = (None, Role.USER, None)
    elif 'error' in Token.verifyToken(auth.get('username')):
        return jsonify(Token.verifyToken(auth.get('username'))), 401
    else:
        user = Token.verifyToken(auth.get('username'))

    if not MeasurementUtils.measurement_exists(userId, dataId):
        return jsonify(error='No data %s for user %s' % (dataId, userId)), 404
    elif request.method == 'GET' and UserUtils.checkIfPublicUser(userId):
        return getMeasurementItem(userId, dataId)
    elif request.authorization:
        auth = request.authorization
        if isinstance(Authenticate.authenticate(auth), dict):
            return jsonify(Authenticate.authenticate(auth)), 401
        elif Authenticate.authenticate(auth)[0] == userId or Authenticate.authenticate(auth)[1] == Role.ADMIN:
            if request.method == 'GET': # Get a measurement data item
                return getMeasurementItem(userId, dataId)
            elif request.method == 'PUT': # Update a measurement data item
                if 'Content-Type' in headers and 'application/json' in headers.get('Content-Type'):
                    d = request.get_json(silent=True)
                    return updateMeasurementItem(userId, dataId, d)
                else:
                    return jsonify(error='Content Type must be application/json'), 400
            elif request.method == 'DELETE': # Delete a measurement data item
                return deleteMeasurementItem(userId, dataId)
        else:
            return jsonify(error='Insufficient privileges'), 403
    else:
        return jsonify(error='Authorization required'), 401


def addNewMeasurement(headers, userId, user, d):
    """Add new measurement item to database if valid JSON with valid keys/values in d"""

    if user[0] != userId:
        return jsonify(error='Unauthorized'), 403
    elif not 'Content-Type' in headers or not 'application/json' in headers.get('Content-Type'):
        return jsonify(error='Content Type must be application/json'), 400
    elif not d:
        return jsonify(error='no JSON in request'), 400
    elif not 'measurementDate' in d or not any(key in d for key in Measurement.measurement_keys):
        return jsonify(error='Measurement must have measurement date and at least one measurement value'), 400
    elif MeasurementUtils.validate_measurement_values(userId, d):
        return jsonify(MeasurementUtils.validate_measurement_values(userId, d)), 400
    elif (d.get('fatTotal') or d.get('bodyMass') or d.get('fatVisceral')) and not d.get('weight'):
        return jsonify(error='fatTotal, bodyMass or fatVisceral needs value for weight'), 400
    else:
        q = Measurement( \
        owner_id = userId, \
        measurementDate = CommonUtils.convertFromISODate(d.get('measurementDate')), \
        height = d.get('height'), \
        weight = d.get('weight'), \
        waistline = d.get('waistline'), \
        fatTotal = d.get('fatTotal'), \
        bodyMass = d.get('bodyMass'), \
        fatVisceral = d.get('fatVisceral'))
        db.session.add(q)
        db.session.commit()
        data = q.serialize
        response = jsonify(data)
        response.status_code = 201
        response.headers['Content-Location'] = '/users/' + str(userId) + '/data/' + str(data['id'])
        response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
        return response


def getMeasurements(userId, user):
    """Query user measurements from database based ownid"""
    q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    elif not user[0] and not q.public:
        return jsonify(error='Authentication required'), 401
    elif user[0] != userId and not q.public:
        return jsonify(error='Unauthorized'), 403
    elif q.measurements:
        measurements = [i.serialize for i in q.measurements]
        for index in measurements:
            index['measurementDate'] = CommonUtils.convertToISODate(index['measurementDate'])
            index['timestamp'] = CommonUtils.convertToISODate(index['timestamp']);
            return jsonify(measurements)
    else:
        return ('', 204)


def deleteAllMeasurements(userId, user):
    """Delete all user measurement items in qbase based on user id"""
    q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    elif not user[0]:
        return jsonify(error='Authentication required'), 401
    elif user[0] != userId:
        return jsonify(error='Unauthorized'), 403
    else:
        numberOfMeasurementsDeleted = Measurement.query.filter_by(owner_id = userId).delete()
        db.session.commit()
        return jsonify(numberOfMeasurementsDeleted=numberOfMeasurementsDeleted, userId=userId, username=user[2])


def getMeasurementItem(userId, dataId):
    """"Return single measurement item from database based on user id and data id"""
    data = Measurement.query.filter_by(owner_id = userId).filter_by(id = dataId).first()
    data = data.serialize
    data['measurementDate'] = CommonUtils.convertToISODate(data['measurementDate'])
    data['timestamp'] = CommonUtils.convertToISODate(data['timestamp'])
    return jsonify(data)


def updateMeasurementItem(userId, dataId, d):
    """Update user changes to database if valid values in d"""
    errorResponse = {'measurementDate': 'string YYYY-MM-DD (if key exists)', 'height': 'number/null (if key exists)', 'weight': 'number/null (if key exists)', 'waistline': 'number/null (if key exists)', 'fatTotal': 'number/null (if key exists)', 'bodyMass': 'number/null (if key exists)', 'fatVisceral': 'number/null (if key exists)'}
    if d:
        if any(key in d for key in Measurement.measurement_keys):
            if not MeasurementUtils.validate_measurement_values(userId, d):
                data = Measurement.query.filter_by(owner_id = userId).filter_by(id = dataId).first()
                if 'measurementDate' in d:
                    data.measurementDate = CommonUtils.convertFromISODate(d.get('measurementDate'))
                if 'height' in d:
                    data.height = d.get('height')
                if 'weight' in d:
                    data.weight = d.get('weight')
                if 'waistline' in d:
                    data.waistline = d.get('waistline')
                if 'fatTotal' in d:
                    data.fatTotal = d.get('fatTotal')
                if 'fatVisceral' in d:
                    data.fatVisceral = d.get('fatVisceral')
                if 'bodyMass' in d:
                    data.bodyMass = d.get('bodyMass')
                if (d.get('fatTotal') or d.get('fatVisceral') or d.get('bodyMass')) and not data.weight and not d.get('weight'):
                    return jsonify(error='fatTotal, bodyMass and fatVisceral need value for weight', weight='Mandatory', fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400
                else:
                    db.session.add(data)
                    db.session.commit()
                    data = data.serialize
                    data['measurementDate'] = CommonUtils.convertToISODate(data['measurementDate'])
                    data['timestamp'] = CommonUtils.convertToISODate(data['timestamp'])
                    response = jsonify(data)
                    response.status_code = 200
                    response.headers['Content-Location'] = '/users/' + str(userId) + '/data/' + str(data['id'])
                    response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
                    return response
            else:
                return jsonify(MeasurementUtils.validate_measurement_values(userId, d)), 400
        else:
            errorResponse['error'] = 'no valid keys or nothing to be updated'
            return jsonify(errorResponse), 400
    else:
        errorResponse['error'] = 'no valid JSON in request'
        return jsonify(errorResponse), 400


def deleteMeasurementItem(userId, dataId):
    """Delete measurement item from database if user id and data id matches"""
    data = Measurement.query.filter_by(owner_id = userId).filter_by(id = dataId).first()
    db.session.delete(data)
    db.session.commit()
    return jsonify(result='measurement removed', userId=userId, username=CommonUtils.getUsername(userId), dataId=dataId)
