#!/anaconda3/envs/cal/bin/python


##TODO handle EXDATE! (Exception Dates -- remove from recurrance) 

##TODO handle daylight savings crossings 
##https://webis.helpshift.com/a/pocket-informant/?s=general&f=recurring-events-and-daylight-saving-time

#%%
import os
import sys
import glob
import pickle
import pytz
import datetime

from tqdm import tqdm

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

sys.path.append("/Users/tahouse/git/python/icalevents")
from icalevents.icalparser import parse_events
# from icalevents.icalparser import parse_events

import argparse


tz = pytz.timezone('America/Los_Angeles')

parser = argparse.ArgumentParser(description="Flip a switch by setting a flag")
parser.add_argument('--cron', action='store_true')
args = parser.parse_args()

# if args.cron:
#     print("Cron called!")
# else:
#     print("Manually run")

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
    # if "Lunch" in e.summary:
    #     print(e, dir(e), )
    if e.description:
        e.description.replace("\n\n\n\n", "\n")
    else:
        e.description = ""

    try:
        organizer = e.organizer
    except:
        organizer = "n/a"
    try:
        attendee = e.attendee
    except:
        attendee = "n/a"

    e.description = e.description + "\n\nOrganizer:\n" + str(organizer) + "\n\nAttendees:\n" + str(attendee)

    ## Fix timezone/Daylight savings issue
    ## TODO still not working super well
    # if str(e.start.tzinfo) == "tzutc()":
    #     e.start = e.start.astimezone(pytz.utc)
    #     e.end = e.end.astimezone(pytz.utc)
    # else:
    #     tz = pytz.timezone(str(e.start.tzinfo))
    #     e.start = tz.localize(e.start.replace(tzinfo=None))
    #     e.end = tz.localize(e.end.replace(tzinfo=None))

    if e.status is None:
        color = None
    elif e.status == "TENTATIVE":
        color = 3
    elif e.status == "FREE":
        color = 5
    elif e.status == "BUSY":
        color = 4
    else:
        color = None

    event = dict(
        summary     = e.summary,
        location    = e.location,
        description = e.description,
        uid         = e.uid,
        start       = dict(dateTime = e.start.isoformat()),
        end         = dict(dateTime = e.end.isoformat()),
        colorId     = color,
        reminders   = {'useDefault': False}
    )

    if len(e.alarms) > 0:
        if color == 5:
            pass
            # print(e.summary, [alarm.total_seconds()/60 for alarm in e.alarms])
            # print(e.file)
            # event['reminders']['overrides']   = [ dict(
            #                                     method = 'popup',
            #                                     minutes = -alarm.total_seconds()/60 # assume alarm is BEFORE event, this will be weird otherwise
            #                                     ) for alarm in e.alarms ]
            #                     )
        else:
            event['reminders']['overrides']   = [ dict(
                                                method = 'popup',
                                                minutes = -alarm.total_seconds()/60 # assume alarm is BEFORE event, this will be weird otherwise
                                                ) for alarm in e.alarms ]
    return event


def check_recurrence_id(event):
    if event.recurrence_id is None:
        return event.start.astimezone(pytz.utc)
    else:
        return event.recurrence_id.astimezone(pytz.utc)

def check_modified_recurring_event(event, previous_events):
    duplicate = False
    if previous_events is not None:
        for uid, previous_event in previous_events.items():
            # recurring events generate underscored occurence vals: UUID_OCCURENCE
            if previous_event.uid.split("_")[0] == event.uid.split("_")[0]:
                # both recurrence_id are none so don't do anything
                if previous_event.recurrence_id == event.recurrence_id == None:
                    continue
                
                if check_recurrence_id(previous_event) == check_recurrence_id(event):
                    # print("Found match!", previous_event, "&&", event)
                    # given a UID, if same recurrence_id then sequence is final determiniation
                    if previous_event.sequence is not None and event.sequence is not None:
                        # print("Using sequence to determine which event to keep")
                        if previous_event.sequence > event.sequence:
                            #return previous event, no need to modifiy previous_events
                            duplicate = True
                            break
                        else:
                            # return current event
                            duplicate = True
                            previous_events.pop(key)
                            previous_events[event.uid] = event
                            break
                    else:
                        # print("At least one sequence is None, return one that isn't None unless both are.. then error")
                        # print(previous_event.recurrence_id, previous_event.sequence, check_recurrence_id(previous_event))
                        # print(event.recurrence_id, event.sequence, check_recurrence_id(event))
                        # return the event with sequence that isn't None
                        if previous_event.sequence is None:
                            # return current event
                            duplicate = True
                            previous_events[event.uid] = event
                            break
                        elif event.sequence is None:
                            #return previous event, no need to modifiy previous_events
                            duplicate = True
                            break
                        else:
                            # both are none??
                            raise Exception("Recurring events with same UID, different recurrence_ids, but neither have a Sequence! Don't know what to do..")

    return previous_events, duplicate

def check_duplicate_event(event, previous_events):
    duplicate = False
    if previous_events is not None:
        # TODO compare current event to existing events
        for previous_event in previous_events.values():
            if event.start == previous_event.start and event.end == previous_event.end and event.summary == previous_event.summary:
                duplicate = True
                break
    return duplicate

def check_duplicate_gcal_event(event, previous_events):
    duplicate = False
    if previous_events is not None:
        # TODO compare current event to existing events
        for previous_event in previous_events.values():
            if event['start']   == previous_event['start']   and \
               event['end']     == previous_event['end']     and \
               event['summary'] == previous_event['summary'] :
                duplicate = True
                break
    return duplicate


def get_ics_events(files=None, remove_duplicates=True, days=30):
    events_dict = {}
    for ics_file in tqdm(files, total=len(files)):

        # open the file and parse ics calendar to list of events
        try:
            with open(ics_file) as f:
                events_list = parse_events(f.read(), default_span=datetime.timedelta(days=days))
        except Exception as e:
            print(ics_file)
            raise e

        # loop through all events in calendar
        for new_event in events_list:
            # add file field
            new_event.file = ics_file

            # if "Lunch" in new_event.summary:
            #     print()
            #     print(new_event, new_event.file, new_event.status)
            #     print(dir(new_event))
            #     print(new_event.uid.split("_")[0])
            #     print(new_event.recurrence_id)

            # continue if uid already exists in dictionary
            if new_event.uid in events_dict:
                continue

            if remove_duplicates:
                # check if duplicate of event already exists (has different uid though)
                duplicate = check_duplicate_event(new_event, events_dict)
            
            events_dict, duplicate = check_modified_recurring_event(new_event, events_dict)

            if duplicate:
                continue

            # only add event uids that aren't duplicated
            events_dict[new_event.uid] = new_event

    return events_dict

if __name__ == "__main__":
    print("Starting:", datetime.datetime.now())


    # load the configuration file
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
    print("Got {} events from ics files".format(len(events)))
    if os.path.exists(os.path.join(local_path, "cal.pickle")):
        with open(os.path.join(local_path, "cal.pickle"), 'rb') as f:
            previous_events = pickle.load(f)
            print("Got {} events from last export/save".format(len(previous_events)))
    else:
        previous_events = None

    gcal_events = {}
    # any_new = False

    # loop through events
    for event in tqdm(events.values(), total=len(events)):

        try:
            # generate Google calendar event from ICS event
            gcal_event = generate_gcal_event(event)
        except Exception as e:
            print(event, event.file)
            raise e


        # duplicate = check_duplicate_gcal_event(gcal_event, previous_events)

        # # insert gcal event into the primary calendar
        # if not duplicate:
        #     # any_new = True
        #     # new_event_count += 1
        #     # gcal_events.append(gcal_event)
        gcal_events[gcal_event['uid']] = gcal_event

    # raise Exception()
    print("Found {} new events not in previous export".format(len(gcal_events)))

    # clear and update calendar if changes
    if len(gcal_events) > 0:
        # get the service object
        service = get_gcal_service()

        # clear the calendar
        if calendar_replace:
            print("Clearing your '{}' calendar!".format(calendarId))
            service.calendars().clear(calendarId=calendarId).execute()

        for gcal_event in tqdm(gcal_events.values(), total = len(gcal_events)):
            # print(gcal_event)
            result = service.events().insert(calendarId='primary', body=gcal_event).execute()

        # with open(os.path.join(local_path, "cal.pickle"), 'wb') as f:
        #     pickle.dump(gcal_events, f, protocol=pickle.HIGHEST_PROTOCOL)

    print("Finished:", datetime.datetime.now())
    print()
    print()
