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
    elif request.method == 'DELETE':
        return deleteAllMeasurements(userId, user)
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

    if request.method == 'GET':
        return getMeasurementItem(userId, dataId, user)
    elif request.method == 'PUT': # Update a measurement data item
        d = request.get_json(silent=True)
        return updateMeasurementItem(headers, userId, dataId, user, d)
    elif request.method == 'DELETE': # Delete a measurement data item
        return deleteMeasurementItem(userId, dataId, user)
    else:
        return jsonify(error='HTTP method %s not allowed' % request.method), 405


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
        return jsonify(measurements)
    else:
        return ('', 204)


def deleteAllMeasurements(userId, user):
    """Delete all user measurement items in database based on user id"""

    if user[0] != userId and user[1] != Role.ADMIN:
        return jsonify(error='Unauthorized'), 403
    else:
        q = User.query.filter_by(id = userId).first()

    if not q:
        return jsonify(error='User not found', userId=userId), 404
    else:
        measurements_deleted = Measurement.query.filter_by(owner_id = userId).delete()
        db.session.commit()
        return jsonify(measurementsDeleted=measurements_deleted, userId=userId, username=user[2])


def getMeasurementItem(userId, dataId, user):
    """"Return single measurement item from database based on user id and data id"""

    q = Measurement.query.filter_by(owner_id = userId).filter_by(id = dataId).first()

    if not q:
        return jsonify(error='Measurement not found', userId=userId, dataId=dataId), 404
    elif not user[0] and not q.owner.public:
        return jsonify(error='Authentication required'), 401
    elif user[0] != userId and not q.owner.public:
        return jsonify(error='Unauthorized'), 403
    else:
        data = q.serialize
        return jsonify(data)


def updateMeasurementItem(headers, userId, dataId, user, d):
    """Update user changes to database if valid values in d"""

    if user[0] != userId:
        return jsonify(error='Unauthorized'), 403
    else:
        q = Measurement.query.filter_by(owner_id = userId).filter_by(id = dataId).first()

    if not q:
        return jsonify(error='Measurement not found', userId=userId, dataId=dataId), 404
    if not 'Content-Type' in headers or not 'application/json' in headers.get('Content-Type'):
        return jsonify(error='Content Type must be application/json'), 400
    if not d:
        return jsonify(error='no JSON in request'), 400
    if not 'measurementDate' in d and not any(key in d for key in Measurement.measurement_keys):
        return jsonify(error='No valid keys found'), 400
    if MeasurementUtils.validate_measurement_values(userId, d):
        return jsonify(MeasurementUtils.validate_measurement_values(userId, d)), 400
    if (d.get('fatTotal') or d.get('fatVisceral') or d.get('bodyMass')) and not q.weight and not d.get('weight'):
        return jsonify(error='fatTotal, bodyMass and fatVisceral need value for weight', weight='Mandatory', fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400

    if 'measurementDate' in d:
        q.measurementDate = CommonUtils.convertFromISODate(d.get('measurementDate'))
    if 'height' in d:
        q.height = d.get('height')
    if 'weight' in d:
        q.weight = d.get('weight')
    if 'waistline' in d:
        q.waistline = d.get('waistline')
    if 'fatTotal' in d:
        q.fatTotal = d.get('fatTotal')
    if 'fatVisceral' in d:
        q.fatVisceral = d.get('fatVisceral')
    if 'bodyMass' in d:
        q.bodyMass = d.get('bodyMass')

    db.session.add(q)
    db.session.commit()
    data = q.serialize
    response = jsonify(data)
    response.status_code = 200
    response.headers['Content-Location'] = '/users/' + str(userId) + '/data/' + str(data['id'])
    response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
    return response


def deleteMeasurementItem(userId, dataId, user):
    """Delete measurement item from database if authorized and if user id and data id matches"""

    if user[0] != userId and user[1] != Role.ADMIN:
        return jsonify(error='Unauthorized'), 403
    else:
        q = Measurement.query.filter_by(owner_id = userId).filter_by(id = dataId).first()

    if not q:
        return jsonify(error='Measurement not found', userId=userId, dataId=dataId), 404
    else:
        db.session.delete(q)
        db.session.commit()
        return jsonify(result='measurement removed', userId=userId, username=user[2], dataId=dataId)
