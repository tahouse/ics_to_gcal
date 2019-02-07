# ics_to_gcal
Read in iCalendar (ics) files and export Google Calendar (gcal) events

## Clone
```
cd <desired_storage_location>
git clone https://github.com/tahouse/ics_to_gcal.git
```
or

```
git@github.com:tahouse/ics_to_gcal.git
```

## Installation

```
cd <ics_to_gcal path>
pip install -r requirements.txt
```

Create a file `config.json` and add the following path to the Apple Calendar storage location for imported Exchange calendar
```
{
    "path":
        "$HOME/Library/Calendars/XXXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX.exchange/XXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX.calendar/Events",
    "calendarId":
        "primary",
    "calendar_replace":
        true
}
```

Alternatively, enter if the config.json is not found in the root folder, the user will be prompted to enter a directory for the ics files.

## Run manually

***Note: this is currently setup to clear the calendar!***
Setting calendar_replace to false above will append new events.

Run the script with `python cal.py`

Follow prompts for granting Calendar API access and storing your access token (stored as `token.pickle`).

Confirm calendar is updated correctly on http://calendar.google.com

## Install in crontab for routine syncronization

```
cd <ics_to_gcal path>
pip install -r requirements.txt
```

Run `crontab -e` and add the following line for running every 30 minutes:
```
30 * * * *  <ics_to_gcal path>/script.sh 2>&1 >> <ics_to_gcal path>/out.log &
```
replacing `<ics_to_gcal path>` with the location of the cloned repository.
