### this file is quickstart.py from google's examples modified by Ali Nuri SEKER
### the original could be found at https://developers.google.com/calendar/quickstart/python
### comments made by me will be marked with triple hash(#)
### this method of access can be used in any other type of google api's also


from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
### this import is for service account. install api page -> https://developers.google.com/api-client-library/python/apis/calendar/v3
### $ pip install --upgrade google-api-python-client
from google.oauth2 import service_account

import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
### this is the path to the JSON file you provided -> https://console.developers.google.com/iam-admin/serviceaccounts/
SERVICE_ACCOUNT_FILE = 'config/service.json'

### this function is used for service account credentials
def get_service_credentials():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[SCOPES])
    return credentials

def get_all_events():
    credentials = get_service_credentials()
    service = discovery.build('calendar', 'v3', credentials=credentials)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    eventsResult = service.events().list(calendarId='2k1tq4bc5nnqsoso02c7tkv7gc@group.calendar.google.com', timeMin=now,
                                         singleEvents=True, orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    if not events:
        print('No upcoming events found, returning empty arrays')
        return [], [], []
    startArray = []
    endArray = []
    summaryArray = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        startArray.append(start)
        endArray.append(end)
        summaryArray.append(event['summary'])
    return startArray, endArray, summaryArray

def get_next_week_events():
    credentials = get_service_credentials()
    service = discovery.build('calendar', 'v3', credentials=credentials)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    nextWeek = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    nextWeek = nextWeek.isoformat() + 'Z'
    eventsResult = service.events().list(calendarId='2k1tq4bc5nnqsoso02c7tkv7gc@group.calendar.google.com', timeMin=now,
                                         timeMax=nextWeek, singleEvents=True, orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    if not events:
        print('No upcoming events found, returning empty arrays')
        return [], [], []
    startArray = []
    endArray = []
    summaryArray = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        startArray.append(start)
        endArray.append(end)
        summaryArray.append(event['summary'])
    return startArray, endArray, summaryArray


