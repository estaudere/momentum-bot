"""
Interact with the Google Sheets API to get and post data to the database.
"""
import pytz, asyncio, json, uuid
from aiogoogle import Aiogoogle
from datetime import datetime, date
import google_secrets

# EDIT THE FOLLOWING VALUES 
service_account_creds = {
    "scopes": [
        "https://www.googleapis.com/auth/spreadsheets"
    ],
    **json.load(open(google_secrets.service_account_creds))
}

SHEET_ID = google_secrets.sheet_id
TIMEZONE = "America/Chicago"

# register a user in the database
def register_user_handler(user_id, text):
    info = text.split(" ")
    if len(info) != 4:
        return {
            "body": "Please use the following format: `register Firstname Lastname email`",
            "header": "Error registering user: Invalid format"
        }
    return asyncio.run(register_user(user_id, info[1], info[2], info[3]))

async def register_user(user_id, first_name, last_name, email):
    async with Aiogoogle(service_account_creds=service_account_creds) as google:
        sheets_api = await google.discover("sheets", "v4")
        name_match = await find_all_column(google, sheets_api, 'Users', 'A', user_id)
        if name_match:
            return {
                'body': "You are already registered in the attendance system. Please notify an admin if you think this is a mistake.", 
                'header': "Error: User already exists"
            }
        else:
            email = email.split("|")[1][:-1]
            await insert_row(google, sheets_api, 'Users', [user_id, first_name, last_name, email])
            return {
                'body': f"Registered {first_name} into attendance system. You can now check into events.",
                'header': "Success"
            }

# create a new event and get a unique code (admin only)
def create_event_handler(user_id, text):
    info = text.split(" ")[1:]
    if len(info) < 2:
        return {
            "body": "Please use the following format: `newevent \"name\" type`",
            "header": "Error creating event: Invalid format"
        }
    info = ["", " ".join(info[:-1])[1:-1], info[-1]]
    if info[2] not in ["tech", "prof", "social", "other"]:
        return {
            "body": "Please use one of the following event types: tech, prof, social, other",
            "header": "Error creating event: Invalid type"
        }
    eid = str(uuid.uuid4()).split("-")[0].upper()
    return asyncio.run(create_event(user_id, info[1], info[2], eid))

async def create_event(user_id, event_name, event_type, event_id):
    async with Aiogoogle(service_account_creds=service_account_creds) as google:
        sheets_api = await google.discover("sheets", "v4")
        admin_match = await find_all_column(google, sheets_api, 'Admins', 'A', user_id)
        if not admin_match:
            return {
                'body': "Unable to create event, admin privileges required. Please contact an admin if you think this is a mistake.", 
                'header': "Error: User not admin"
            }
        await insert_row(google, sheets_api, 'Events', [event_name, event_type, event_id])
        return {
            'body': f"Created {event_type} event {event_name}. Use code {event_id} to check in.",
            'header': "Success"
        }

# check in to an event with a code
def checkin_handler(user_id, text):
    info = text.split(" ")
    if len(info) != 2:
        return {
            "body": "Please use the following format: `checkin code`",
            "header": "Error checking in: Invalid format"
        }
    return asyncio.run(checkin(user_id, info[1].upper()))

async def checkin(user_id, event_id):
    async with Aiogoogle(service_account_creds=service_account_creds) as google:
        sheets_api = await google.discover("sheets", "v4")
        event_match = await find_all(google, sheets_api, 'Events', 'C', event_id)
        if not event_match:
            return {
                'body': "Unable to check in, event not found.", 
                'header': "Error: Event not found"
            }
        event_name = event_match[0][0]
        event_type = event_match[0][1]
        event_id = event_match[0][2]
        checkin_time = datetime.now(pytz.timezone(TIMEZONE)).strftime("%m/%d/%Y %H:%M")
        attendance_match = await find_all(google, sheets_api, 'Attendance', 'A', user_id)
        for row in attendance_match:
            if row[3] == event_id:
                return {
                    'body': f"You have already checked into {event_name}.", 
                    'header': "Error: Already checked in"
                }
        await insert_row(google, sheets_api, 'Attendance', [user_id, event_name, event_type, event_id, checkin_time])
        return {
            'body': f"Checked in to event \"{event_name}\".",
            'header': "Success"
        }

# send a summary of events to a user
def update_user_handler(user_id):
    return asyncio.run(update_user(user_id))

async def update_user(user_id):
    async with Aiogoogle(service_account_creds=service_account_creds) as google:
        sheets_api = await google.discover("sheets", "v4")
        total_attendance = await google.as_service_account(sheets_api.spreadsheets.values.get(spreadsheetId=SHEET_ID, range=f"Summary!A2:G2", valueRenderOption='FORMATTED_VALUE', dateTimeRenderOption='FORMATTED_STRING'))
        total_attendance = total_attendance['values'][0]
        total_tech = total_attendance[2]
        total_prof = total_attendance[3]
        total_social = total_attendance[4]
        total_other = total_attendance[5]
        name_match = await find_all(google, sheets_api, 'Summary', 'A', user_id)
        if not name_match:
            return {
                'body': "You are not registered in the attendance system. Please use `register` to register.", 
                'header': "Error: User not registered"
            }
        else:
            tech = name_match[0][2]
            prof = name_match[0][3]
            social = name_match[0][4]
            other = name_match[0][5]
            total = name_match[0][6]
            return {
                'header': f"Congrats! You've been to {total} event(s).",
                'body': f"_Tech:_ {tech} out of {total_tech}\n_Professional:_ {prof} out of {total_prof}\n_Social:_ {social} out of {total_social}\n_Other:_ {other} out of {total_other}"
            }

# send a summary of the event to a user (admin only)
def event_status_handler(user_id, text):
    info = text.split(" ")
    if len(info) != 2:
        return {
            "body": "Please use the following format: `eventstatus code`",
            "header": "Error checking event status: Invalid format"
        }
    return asyncio.run(event_status(user_id, info[1].upper()))

async def event_status(user_id, event_id):
    async with Aiogoogle(service_account_creds=service_account_creds) as google:
        sheets_api = await google.discover("sheets", "v4")
        admin_match = await find_all_column(google, sheets_api, 'Admins', 'A', user_id)
        if not admin_match:
            return {
                'body': "Unable to see event status, admin privileges required. Please contact an admin if you think this is a mistake.", 
                'header': "Error: User not admin"
            }
        event_match = await find_all(google, sheets_api, 'Events', 'C', event_id)
        if not event_match:
            return {
                'body': "Unable to check event status, event not found.", 
                'header': "Error: Event not found"
            }
        event_name = event_match[0][0]
        event_type = event_match[0][1]
        attendance_match = await find_all(google, sheets_api, 'Attendance', 'D', event_id)
        if not attendance_match:
            return {
                'body': f"No one has checked into {event_name} yet. Use code {event_id} to check in.", 
                'header': "Error: Event not found"
            }
        if len(attendance_match) == 1:
            return {
                'body': f"1 person has checked into {event_type} event {event_name} (code: {event_id}): {attendance_match[0][5]}.", 
                'header': "Success"
            }
        people = ""
        for row in attendance_match:
            people += f"- {row[5]}\n"
        people = people[:-1]
        return {
            'body': f"{len(attendance_match)} people have checked into {event_type} event {event_name} (code: {event_id}).\n{people}",
            'header': "Success"
        }


''' HELPER FUNCTIONS '''
# gsheet post and get functions

# get a single column's matching values
async def find_all_column(google, sheets_api, sheet_name, column_letter, text):
    all_values_request = sheets_api.spreadsheets.values.get(spreadsheetId=SHEET_ID, range=f"{sheet_name}!{column_letter}2:{column_letter}", valueRenderOption='FORMATTED_VALUE', dateTimeRenderOption='FORMATTED_STRING')
    all_values = await google.as_service_account(all_values_request)
    matches = []
    if 'values' in all_values:
        for v in all_values['values']:
            if v[0] == text:
                matches.append(v[0])
    return matches

# get all rows with matching values
async def find_all(google, sheets_api, sheet_name, column_letter, text):
    all_values_request = sheets_api.spreadsheets.values.get(spreadsheetId=SHEET_ID, range=f"{sheet_name}", valueRenderOption='FORMATTED_VALUE', dateTimeRenderOption='FORMATTED_STRING')
    all_values = await google.as_service_account(all_values_request)
    value_index = ord(column_letter) - 65 # this will break if column letter is beyond Z
    matches = []
    if 'values' in all_values:
        for v in all_values['values']:
            if v[value_index] == text:
                matches.append(v)
    return matches

# insert a new row at the bottom of sheet
async def insert_row(google, sheets_api, sheet_name, data):
    value_range_body = {
        "range": sheet_name,
        "majorDimension": 'ROWS',
        "values": [data]
    }
    request = sheets_api.spreadsheets.values.append(range=sheet_name, spreadsheetId=SHEET_ID, valueInputOption='RAW', insertDataOption='OVERWRITE', json=value_range_body)
    return await google.as_service_account(request)