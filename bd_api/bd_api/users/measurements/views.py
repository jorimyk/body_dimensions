from flask import request, jsonify, make_response

from bd_api import app, db, limiter, auth
from . models import Measurement
from bd_api import Config
from bd_api.utils import CommonUtils, UserUtils, MeasurementUtils
from bd_api.auth import Authenticate, Password, Token


@app.route('/users/<int:userId>/data', methods = ['POST', 'GET', 'DELETE']) # /users/<user>/data
@limiter.limit("100/day")
def measurements(userId):
    headers = request.headers
    if not UserUtils.userExists(userId):
        return jsonify(error='No user with id %s' % userId), 404
    elif request.method == 'GET' and UserUtils.checkIfPublicUser(userId):
        return getMeasurements(userId)
    elif request.authorization:
        auth = request.authorization
        if isinstance(Authenticate.authenticate(auth), dict):
            return jsonify(Authenticate.authenticate(auth)), 401
        elif Authenticate.authenticate(auth)[0] == userId or Authenticate.authenticate(auth)[1] == Role.ADMIN:
            if request.method == 'POST': # Add new measurement data
                if 'Content-Type' in headers and 'application/json' in headers.get('Content-Type'):
                    d = request.get_json(silent=True)
                    return addNewMeasurement(userId, d)
                else:
                    return jsonify(error='Content Type must be application/json'), 400
            elif request.method == 'GET': # Get all measurement data for user
                return getMeasurements(userId)
            elif request.method == 'DELETE': # Delete all measurement data for user
                return deleteAllMeasurements(userId, False)
        else:
            return jsonify(error='Insufficient privileges'), 403
    else:
        return jsonify(error='Authorization required'), 401


@app.route('/users/<int:userId>/data/<int:dataId>', methods = ['GET', 'PUT', 'DELETE']) # /users/<user>/data/<data>
def measurement(userId, dataId):
    headers = request.headers
    if not UserUtils.userExists(userId):
        return jsonify(error='No user with id %s' % userId), 404
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


def addNewMeasurement(userId, d):
    """Add new measurement item to database if valid JSON with valid keys/values in d"""
    if d and 'measurementDate' in d:
        if MeasurementUtils.validate_measurement_values(userId, d):
            return jsonify(MeasurementUtils.validate_measurement_values(userId, d)), 400
    else:
        return jsonify(error='no valid JSON in request', measurementDate='Mandatory, string YYYY-MM-DD', height='number/null', weight='number/null', waistline='number/null', fatTotal='number/null', bodyMass='number/null', fatVisceral='number/null'), 400
    if (d.get('fatTotal') or d.get('bodyMass') or d.get('fatVisceral')) and not d.get('weight'):
        return jsonify(error='fatTotal, bodyMass or fatVisceral needs value for weight', measurementDate=d.get('measurementDate'), weight='Mandatory', fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400
    else:
        data = Measurement( \
        user_id = userId, \
        measurementDate = CommonUtils.convertFromISODate(d.get('measurementDate')), \
        height = d.get('height'), \
        weight = d.get('weight'), \
        waistline = d.get('waistline'), \
        fatTotal = d.get('fatTotal'), \
        bodyMass = d.get('bodyMass'), \
        fatVisceral = d.get('fatVisceral'))
        db.session.add(data)
        db.session.commit()
        data = data.serialize
        data['measurementDate'] = CommonUtils.convertToISODate(data['measurementDate'])
        data['timestamp'] = CommonUtils.convertToISODate(data['timestamp'])
        response = jsonify(data)
        response.status_code = 201
        response.headers['Content-Location'] = '/users/' + str(userId) + '/data/' + str(data['id'])
        response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
        return response


def getMeasurements(userId):
    """Return all user measurements from database based on user id"""

    data = Measurement.query.filter_by(user_id = userId).all()
    if data:
        data = [i.serialize for i in data]
        for index in data:
            index['measurementDate'] = CommonUtils.convertToISODate(index['measurementDate'])
            index['timestamp'] = CommonUtils.convertToISODate(index['timestamp'])
        return jsonify(data)
    else:
        return ('', 204)


def deleteAllMeasurements(userId, internalCall):
    """Delete all user measurement items in database based on user id"""
    data = Measurement.query.filter_by(user_id = userId).all()
    for index in range(len(data)):
        db.session.delete(data[index])
        db.session.commit()
    if internalCall:
        return len(data)
    else:
        return jsonify(result='measurement(s) deleted', numberOfMeasurementsDeleted='%s' % len(data), userId=userId, username=getUsername(userId))


def getMeasurementItem(userId, dataId):
    """"Return single measurement item from database based on user id and data id"""
    data = Measurement.query.filter_by(user_id = userId).filter_by(id = dataId).first()
    if data:
        data = data.serialize
        data['measurementDate'] = CommonUtils.convertToISODate(data['measurementDate'])
        data['timestamp'] = CommonUtils.convertToISODate(data['timestamp'])
        return jsonify(data)
    else:
        return jsonify(error='not found', userId=userId, username=getUsername(userId), dataId=dataId), 404


def updateMeasurementItem(userId, dataId, d):
    """Update user changes to database if valid values in d"""
    errorResponse = {'measurementDate': 'string YYYY-MM-DD (if key exists)', 'height': 'number/null (if key exists)', 'weight': 'number/null (if key exists)', 'waistline': 'number/null (if key exists)', 'fatTotal': 'number/null (if key exists)', 'bodyMass': 'number/null (if key exists)', 'fatVisceral': 'number/null (if key exists)'}
    data = Measurement.query.filter_by(user_id = userId).filter_by(id = dataId).first()
    if data:
        if d:
            validRequest = False
            if 'measurementDate' in d and validateDate(userId, 'measurementDate', d.get('measurementDate')):
                validRequest = True
                data.measurementDate = CommonUtils.convertFromISODate(d.get('measurementDate'))
            if 'height' in d and validateNumber('height', d.get('height')):
                validRequest = True
                data.height = d.get('height')
            if 'weight' in d and validateNumber('weight', d.get('weight')):
                validRequest = True
                data.weight = d.get('weight')
            if 'waistline' in d and validateNumber('waistline', d.get('waistline')):
                validRequest = True
                data.waistline = d.get('waistline')
            if 'fatTotal' in d and validateNumber('fatTotal', d.get('fatTotal')):
                validRequest = True
                data.fatTotal = d.get('fatTotal')
            if 'fatVisceral' in d and validateNumber('fatVisceral', d.get('fatVisceral')):
                validRequest = True
                data.fatVisceral = d.get('fatVisceral')
            if 'bodyMass' in d and validateNumber('bodyMass', d.get('bodyMass')):
                validRequest = True
                data.bodyMass = d.get('bodyMass')
            if not validRequest:
                errorResponse['error'] = 'no valid keys or nothing to be updated'
                return jsonify(errorResponse), 400
            elif (d.get('fatTotal') or d.get('fatVisceral') or d.get('bodyMass')) and not data.weight and not d.get('weight'):
                return jsonify(error='fatTotal, bodyMass and fatVisceral need value for weight', weight='Mandatory', fatTotal=d.get('fatTotal'), bodyMass=d.get('bodyMass'), fatVisceral=d.get('fatVisceral')), 400
            else:
                db.session.add(data)
                db.session.commit()
                data = data.serialize
                data['measurementDate'] = CommonUtils.convertToISODate(data['measurementDate'])
                data['timestamp'] = CommonUtils.convertToISODate(data['timestamp'])
                response = jsonify(data)
                response.status_code = 201
                response.headers['Content-Location'] = '/users/' + str(userId) + '/data/' + str(data['id'])
                response.headers['Access-Control-Expose-Headers'] = 'Content-Location'
                return response
        else:
            errorResponse['error'] = 'no valid JSON in request'
            return jsonify(errorResponse), 400
    else:
        return jsonify(error='measurement not found', dataId=dataId, userId=userId, username=getUsername(userId)), 404


def deleteMeasurementItem(userId, dataId):
    """Delete measurement item from database if user id and data id matches"""
    data = Measurement.query.filter_by(user_id = userId).filter_by(id = dataId).first()
    if data:
        db.session.delete(data)
        db.session.commit()
        return jsonify(result='measurement removed', userId=userId, username=getUsername(userId), dataId=dataId)
    else:
        return jsonify(error='not found', userId=userId, username=getUsername(userId), dataId=dataId), 404
