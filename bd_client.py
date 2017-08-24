import json
import sys
import requests

print('Running Endpoint Tester....\n')
address = input('Enter the address of the server you want to access, \n If left blank the connection will be set to "http://localhost:5000": ')
if address == '':
    address = 'http://localhost:5000'


def topMenu():
    action = True
    while action:
        print ('1. New user\n2. Existing user\n3.Exit/Quit')
        action = input('Your choice:\n')
        if action == '1':
            print('Create new user')
        elif action == '2':
            username = input('Enter username:')
            password = input('Enter password:')
            token, location = login(username, password)
            return userMenu(token, location)
        elif action == '3':
            print('Bye bye!')
            sys.exit()
        else:
            print('Not valid choise')


def login(username, password):
    try:
        response = requests.get('%s/login' % address, auth=(username, password))
        data = response.json()
        headers = response.headers
        if data.get('token'):
            print('Login success!\n')
            return data.get('token'), headers.get('Content-Location')
        else:
            raise Exception('Could not login: %s' % data.get('error'))
    except Exception as err:
        print(err.args)
        sys.exit()


def userMenu(token, location):
    action = True
    while action:
        print ('1. View user info\n2. View all measurements\n3. View single measurement\n4. Delete user\n5.Exit/Quit')
        action = input('Your choice:\n')
        if action == '1':
            print(getUser(token, location))
        elif action == '2':
            data = getMeasurements(token, location)
            for index in range(len(data)):
                print(data[index])
        elif action == '3':
            dataId = input('Enter measurement id:')
            print(getMeasurement(token, location, dataId))
        elif action == '4':
            print('Delete user not implemented')
        elif action == '5':
            print('Bye bye!')
            sys.exit()
        else:
            print('Not valid choise')


def getUser(token, location):
    try:
        response = requests.get('%s%s' % (address, location), auth=(token, ''))
        data = response.json()
        if not data.get('error'):
            return data
        else:
            raise Exception('Could not view user: %s' % data.get('error'))
    except Exception as err:
        return err.args


def getMeasurements(token, location):
    try:
        response = requests.get('%s%s/data' % (address, location), auth=(token, ''))
        data = response.json()
        if isinstance(data, list):
            return data
        else:
            raise Exception('Error: %s' % data.get('error'))
    except Exception as err:
        return err.args


def getMeasurement(token, location, dataId):
    try:
        response = requests.get('%s%s/data/%s' % (address, location, dataId), auth=(token, ''))
        data = response.json()
        if not data.get('error'):
            return data
        else:
            raise Exception('Error: %s' % data.get('error'))
    except Exception as err:
        return err.args


topMenu()

