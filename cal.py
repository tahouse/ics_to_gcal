#!/anaconda3/envs/cal/bin/python

#%%
import os
import sys
import glob
import pickle

from dateutil.tz import tzlocal
import datetime
from tqdm import tqdm

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from icalevents.icalparser import parse_events

local_path = os.path.dirname(os.path.realpath(__file__))

def get_gcal_service():
    """Create a Google Calendar service object.
    copied from https://developers.google.com/calendar/quickstart/python
    """

    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(os.path.join(local_path, 'token.pickle')):
        with open(os.path.join(local_path, 'token.pickle'), 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(local_path,'credentials.json'), SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(os.path.join(local_path, 'token.pickle'), 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    return service

def generate_gcal_event(e):
    e.description.replace("\n\n\n\n", "\n")
    try:
        organizer = e.organizer
    except:
        organizer = "n/a"
    try:
        attendee = e.attendee
    except:
        attendee = "n/a"
    

    e.description = e.description + "\n\nOrganizer:\n" + str(organizer) + "\n\nAttendees:\n" + str(attendee)
    event = dict(
        summary= e.summary,
        description= e.description,
        uid = e.uid,
        location= e.location,
        start = dict(dateTime = e.start.isoformat()),
        end = dict(dateTime = e.end.isoformat()),
    )
    return event

def check_duplicate_event(event, previous_events):
    duplicate = False
    if previous_events is not None:
        # TODO compare current event to existing events
        for previous_event in previous_events.values():
            if event.start == previous_event.start and event.end == previous_event.end and event.summary == previous_event.summary:
                    duplicate = True
                    break
    return duplicate

def get_ics_events(files=None, remove_duplicates=True):
    events_dict = {}
    for ics_file in tqdm(files, total=len(files)):
        # open the file and parse ics calendar to list of events
        with open(ics_file) as f:
            events_list = parse_events(f.read(), default_span=datetime.timedelta(days=30))

        # loop through all events in calendar
        for new_event in events_list:

            # conintue if uid already exists in dictionary
            if new_event.uid in events_dict:
                continue

            if remove_duplicates:
                # check if duplicate of event already exists (has different uid though)
                duplicate = check_duplicate_event(new_event, events_dict)

            if duplicate:
                continue

            # only add event uids that aren't duplicated
            events_dict[new_event.uid] = new_event

    return events_dict

if __name__ == "__main__":
    print("Starting:", datetime.datetime.now())

    # load the configuration file
    # path_to_config = os.path.join(, "config.json")
    path_to_config = os.path.join(local_path, "config.json")

    print("Config location:", path_to_config)
    if os.path.exists(path_to_config):
        import json
        with open(path_to_config, "r") as f:
            config = json.loads(f.read())
    else:
        config = {}

    path = config.get('path', None)
    if path is None:
        path = input("Enter a path to load *.ics files from: ")

    calendarId = config.get('calendarId', 'primary')

    calendar_replace = config.get('calendar_replace', False)

    # parse the ics files from path into an event dictionary (key values are UIDs)
    files = glob.glob(os.path.expanduser(os.path.expandvars(os.path.join(path,"*.ics"))))

    events = get_ics_events(files)

    if os.path.exists(os.path.join(local_path, "cal.pickle")):
        with open(os.path.join(local_path, "cal.pickle"), 'rb') as f:
            previous_events = pickle.load(f)
    else:
        previous_events = None

    gcal_events = []
    any_new = False
    # loop through events
    for event in tqdm(events.values(), total=len(events)):

        duplicate = check_duplicate_event(event, previous_events)

        if not duplicate:
            any_new = True

        # generate Google calendar event from ICS event
        gcal_event = generate_gcal_event(event)

        # insert gcal event into the primary calendar
        gcal_events.append(gcal_event)

    # clear and update calendar if changes
    if any_new:
        # get the service object
        service = get_gcal_service()

        # clear the calendar
        if calendar_replace:
            print("Clearing your '{}' calendar!".format(calendarId))
            service.calendars().clear(calendarId=calendarId).execute()

        for gcal_event in tqdm(gcal_events, total = len(gcal_events)):
            result = service.events().insert(calendarId='primary', body=gcal_event).execute()

    with open(os.path.join(local_path, "cal.pickle"), 'wb') as f:
            pickle.dump(events, f, protocol=pickle.HIGHEST_PROTOCOL)


    print("Finished:", datetime.datetime.now())
    print()
    print()
