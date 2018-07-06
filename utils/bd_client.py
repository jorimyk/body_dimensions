import json, sys, re, time
import datetime
import requests

print('Running Endpoint Tester....\n')
address = input('Enter the address of the server you want to access, \n If left blank the connection will be set to "http://localhost:5000": ')
if address == '':
    address = 'http://localhost:5000'


def topMenu():
    action = True
    while action:
        print ('1. New user\n2. Existing user\n3. Unregistered user\n4. Exit/Quit')
        action = input('Your choice:\n')
        if action == '1':
            print('Create new user')
        elif action == '2':
            username = input('Enter username:')
            password = input('Enter password:')
            token, location = login(username, password)
            return userMenu(token, location)
        elif action == '3':
            return userMenu(None, None)
        elif action == '4':
            print('Bye bye!')
            sys.exit()
        else:
            print('Not valid choise')


def login(username, password):
    try:
        r = requests.get('%s/login' % address, auth=(username, password))
        jsonData = r.json()
        headers = r.headers
        if jsonData.get('token'):
            print('Login success!\n')
            return jsonData.get('token'), headers.get('Content-Location')
        else:
            raise Exception('Could not login: %s' % jsonData.get('error'))
    except Exception as err:
        print(err.args)
        sys.exit()


def userMenu(token, location):
    action = True
    while action:
        print ('1. View users\n2. View user info\n3. View all measurements\n4. View single measurement\n5. Delete user\n6. Add measurements\n7. Exit/Quit')
        action = input('Your choice:\n')
        if action == '1':
            print(getUsers(token))
        elif action == '2':
            print(getUser(token, location))
        elif action == '3':
            data = getMeasurements(token, location)
            for index in range(len(data)):
                print(data[index])
        elif action == '4':
            dataId = input('Enter measurement id:')
            print(getMeasurement(token, location, dataId))
        elif action == '5':
            print('Delete user not implemented')
        elif action == '6':
            print(postMeasurements(token, location))
        elif action == '7':
            topMenu()
        else:
            print('Not valid choise')


def getUsers(token):
    try:
        r = requests.get('%s/users' % (address), auth=(token, ''))
        jsonData = r.json()
        if isinstance(jsonData, list):
            return jsonData
        else:
            raise Exception('Error: %s' % jsonData.get('error'))
    except Exception as err:
        return err.args

def getUser(token, location):
    try:
        r = requests.get('%s%s' % (address, location), auth=(token, ''))
        jsonData = r.json()
        if not jsonData.get('error'):
            return jsonData
        else:
            raise Exception('Could not view user: %s' % jsonData.get('error'))
    except Exception as err:
        return err.args


def getMeasurements(token, location):
    try:
        r = requests.get('%s%s/data' % (address, location), auth=(token, ''))
        jsonData = r.json()
        if isinstance(jsonData, list):
            return jsonData
        else:
            raise Exception('Error: %s' % jsonData.get('error'))
    except Exception as err:
        return err.args


def getMeasurement(token, location, dataId):
    """Return single measurement item based on location and dataId"""
    try:
        r = requests.get('%s%s/data/%s' % (address, location, dataId), auth=(token, ''))
        jsonData = r.json()
        if not jsonData.get('error'):
            return jsonData
        else:
            raise Exception('Error: %s' % jsonData.get('error'))
    except Exception as err:
        return err.args

def postMeasurements(token, location):
    """Read white-space separated values from file in order
    measurementDate (d.m.yy(yy)), weight, fatTotal, bodyMass, fatVisceral, waistline
    and POST line by line"""
    measurementFile = input('Enter filename:')
    pattern = re.compile(r'''
    ^           # beginning of string
    (\d{1,2})   # day number 1 to 2 digits
    .           # date separator
    (\d{1,2})   # month number 1 to 2 digits
    .           # date separator
    (\d{2,4})   # year 2 to 4 digits
    \D+         # any number of non-digits
    (\d+.\d+)   # weight any number of digits
    \D+         #  any number of non-digits
    (\d+.\d+)   # fatTotal any number of digits
    \D+         # any number of non-digits
    (\d+.\d+)   # bodyMass any number of digits
    \D*         # any number of non-digits, optional
    (\d*)       # fatVisceral any number of digits, optional
    \D*         # any number of non-digits, optional
    (\d*.\d*)?  # waistline as floating point number, optional
    \D*         # any number of non-digits, optional
    $           # end of string
    ''', re.VERBOSE)
    try:
        with open(measurementFile) as inputData:
            counter = 0;
            for line in inputData:
#                print('Round %s' % counter)
                output = pattern.search(line).groups()
                weight = float(output[3])
                fatTotal = float(output[4])
                bodyMass = float(output[5])
#                print('%s.%s.%s fatVisceral: %s, waistline: %s' % (output[0], output[1], output[2], output[6], output[7]))
                if output[6]:
#                    print('fatVisceral löytyy')
                    fatVisceral = int(output[6])
                else:
#                    print('fatVisceral ei löydy')
                    fatVisceral = None
                if output[7]:
                    try:
                        waistline = int(output[7])
                    except ValueError:
                        waistline = float(output[7])
                else:
                    waistline = None
                if len(output[2]) == 2:
                    measurementDate = datetime.datetime.strptime('%s.%s.%s' % (output[0], output[1], output[2]), '%d.%m.%y').date()
                elif len(output[2]) == 4:
                    measurementDate = datetime.datetime.strptime('%s.%s.%s' % (output[0], output[1], output[2]), '%d.%m.%Y').date()
                jsonOutput = {'measurementDate': measurementDate.strftime('%Y-%m-%d'), 'weight': weight, 'fatTotal': fatTotal, 'bodyMass': bodyMass, 'fatVisceral': fatVisceral, 'waistline': waistline}
                r = requests.post('%s%s/data' % (address, location), auth=(token, ''), json=jsonOutput)
                if r.status_code == 401:
                    jsonData = r.json()
                    print('Status code: %s, error: %s' % (r.status_code, jsonData.get('error')))
                    while (r.status_code == 401): # Token gets old during file reading
                        username = input('Enter username:')
                        password = input('Enter password:')
                        token, location = login(username, password)
                        r = requests.post('%s%s/data' % (address, location), auth=(token, ''), json=jsonOutput)
                if r.status_code == 201: # Successful POST
                    counter += 1;
                    print('Status code: 201')
                elif r.status_code == 429: # Too many connections reached
                    while (r.status_code == 429):
                        print('Too many connections, trying again after 60 seconds...')
                        for remaining in range(60, 0, -1):
                            sys.stdout.write("\r")
                            sys.stdout.write("{:2d} seconds remaining...".format(remaining))
                            sys.stdout.flush()
                            time.sleep(1)
                        r = requests.post('%s%s/data' % (address, location), auth=(token, ''), json=jsonOutput)
                    if r.status_code != 201: #
                        jsonData = r.json()
                        print('Status code: %s, error: %s' % (r.status_code, jsonData.get('error')))
                        if r.status_code == 401: # Token gets old after 60 seconds dalay
                            while (r.status_code == 401):
                                username = input('Enter username:')
                                password = input('Enter password:')
                                token, location = login(username, password)
                                r = requests.post('%s%s/data' % (address, location), auth=(token, ''), json=jsonOutput)
                                if r.status_code == 201: # Successful POST after relogin
                                    counter += 1;
                                    print('Status code: 201')
                                else: # Unsuccessful POST after relogin
                                    print('Status code: %s, error: %s' % (r.status_code, jsonData.get('error')))
                    else: # Successful POST after 60 seconds delay
                        counter += 1;
                        print('Status code: 201')
                else: # Valid token, not too many connections but other error
                    jsonData = r.json()
                    print('Status code: %s, error: %s' % (r.status_code, jsonData.get('error')))
            print('Number of measurements posted: %s' %counter)
    except Exception as err:
        print(err.args)


topMenu()
