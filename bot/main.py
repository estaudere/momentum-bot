from fastapi import FastAPI, Header
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from utils import SlackEvent
from router import router
from db import users, events, records

from multiprocessing import Process
import time

app = FastAPI(title="Momentum Slack Bot")

load_dotenv()

@app.get("/")
async def root():
    return 'Welcome to the official Texas Momentum Slack Bot!'

@app.post("/slack")
async def slack_event(event: SlackEvent, header: str = Header(None)):

    print(event, header)

    # on first run, Slack will send a challenge to verify the URL
    if event.type == 'url_verification':
        return f"HTTP 200 OK\nContent-type: application/x-www-form-urlencoded\nchallenge={event.challenge}"
    
    # check if the app is being rate limited
    if event.type == 'app_rate_limited':
        print("App rate limited")
        return "HTTP 200 OK"

    # if the event is a retry, don't retry
    if header == 'HTTP_X_SLACK_RETRY_NUM':
        print("App retried")
        return "HTTP 201 OK"
    

    # route the request to the appropriate handler in a new thread
    # NOTE: Lambda does not support multiprocessing
    # process = Process(target=router, args=(event.event,))
    # process.start()
    # st = time.time()
    router(event.event)
    # print(time.time() - st)

    return "HTTP 200 OK", 200

@app.get("/events")
async def get_events():
    """Get all events."""
    return events.fetch().items

@app.get("/admin/events")
async def get_admin_events(return_users: bool = False):
    """Get all events with list of users."""
    all_events = events.fetch().items # get all events
    for event in all_events:
        event['users'] = records.fetch({"event": event['key']}).items

    if not return_users:
        return all_events
    
    for event in all_events:
        for user in event['users']:
            user['info'] = users.fetch({"key": user['user']}).items[0]

    return all_events

@app.get("/admin/events/{event_id}")
async def get_events_by_id(event_id, formatted: bool = False):
    """Get the event with a list of users."""
    event = events.fetch({"key": event_id}).items[0]
    event['users'] = records.fetch({"event": event['key']}).items
    for user in event['users']:
        user['info'] = users.fetch({"key": user['user']}).items[0]

    if formatted:
        # return just the user's names in a list
        names = [u['info']['name'] for u in event['users']]
        count = len(names)
        names = "<br>".join(names)
        
        # format the message
        message = f"""
        <style>
            body {{
                font-family: sans-serif;
            }}
            h1 {{
                margin-bottom: 0.2em;
            }}
        </style>
        <h1>{event['name']}</h1>
        <code>{event['key']}</code>

        <p>{names}</p>
        <br>
        <p><strong>Total Attendees:</strong> {count}</p>
        """
        return HTMLResponse(content=message, status_code=200)

    return event

@app.get("/users/{user_email}")
async def get_user(user_email: str):
    """Get all events for a user by email address."""
    user_info =  users.fetch({"email": user_email}).items
    if len(user_info) == 0:
        return {"error": "User not found."}, 404
    
    user_info = user_info[0]
    user_info['events'] = records.fetch({"user": user_info['key']}).items

    # get info about the events
    for event in user_info['events']:
        event['info'] = events.fetch({"key": event['event']}).items[0]

    return user_info