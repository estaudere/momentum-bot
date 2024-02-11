from db import events, records
from utils import EventInfo, send_message
from typing import List
from datetime import datetime as dt
from .user import check_admin, register_user
import random


def handle_event(event: EventInfo, text: List[str]):
    """
    Handle event subcommands.
    Args:
        event (EventInfo): EventInfo object describing the event
        text (List[str]): List of parsed words in the command
    Returns:
        Error 400 or HTTP 200 OK
    """
    if len(text) == 1:
        return "Error: No subcommand provided", 400
    
    subcommand = text[1].lower()

    if subcommand == "checkin":
        if len(text) < 3:
            send_message(event, body="Please provide an event code.", error=True)
            return "Error: No code provided", 200
        event_checkin(event, text[2].strip())

    if subcommand == "create":
        if len(text) < 3:
            send_message(event, body="Please provide an event name.", error=True)
            return "Error: No name provided", 200
        
        event_create(event, text[2])

    if subcommand == "open" or subcommand == "close":
        if len(text) < 3:
            send_message(event, body="Please provide an event code.", error=True)
            return "Error: No code provided", 200
        
        event_toggle(event, text[2].strip(), subcommand)

    return "HTTP 200 OK", 200

def event_checkin(event: EventInfo, code: str):
    """
    Handle event checkins.
    Args:
        event (EventInfo): EventInfo object describing the event
        code (str): The event code
    """
    user_id = event.user
    event_info_momentum = events.get(code)

    if event_info_momentum == None:
        send_message(event, 
                     header="Invalid event code",
                     body="Try again or contact an admin.", 
                     error=True)
        return "Error: Invalid event code", 400
    
    if not event_info_momentum.get('open', False):
        send_message(event, 
                     header="Event closed",
                     body="Try again later or contact an admin.", 
                     error=True)
        return "Error: Event not open", 400
    
    n = event_info_momentum['name']

    # check if user already checked in
    if records.get(f"{code}{user_id}"):
        send_message(event, 
                     body=f'You have already checked in to the event "{n}".')
        return "User already checked in", 200
    
    # register user if not already registered
    register_user(event, send_msg=False)

    records.put(
        {
            "user": user_id, 
            "event": code, 
            "time": dt.now().timestamp()
        }, 
        f"{code}{user_id}")
    send_message(event, 
                 header="Congrats!", 
                 body=f'You have successfully checked in to the event "{n}".')
    
    return "HTTP 200 OK", 200


def event_create(event: EventInfo, name: str):
    """
    Handle event creation.
    Args:
        event (EventInfo): EventInfo object describing the event
        name (str): The name of the event
    """
    user_id = event.user

    # check if user is an admin
    if not check_admin(user_id):
        send_message(event, 
                     header="Admin access required", 
                     body="You must be an admin to create events.", 
                     error=True)
        return "Error: User not admin", 400
    
    # generate new event code from random line in codes.txt
    with open('codes.txt') as f:
        codes = f.readlines()
        code = random.choice(codes).strip()

    try: 
        events.insert(
            {
                "name": name, 
                "created_by": user_id, 
                "created_at": dt.now().timestamp(),
                "open": False
            }, code)
    except Exception as e:
        send_message(
            event, 
            header="Error creating event",
            body="Sorry, an error occurred while creating the event. Try again.", 
            error=True)
        return "Error: Event creation failed", 400
    
    send_message(event, 
                 header="Congrats!", 
                 body=f'You have successfully created the event "{name}". Checkin using code `{code}`.')
    

def event_toggle(event: EventInfo, code: str, subcommand: str):
    """
    Handle event opening and closing.
    Args:
        event (EventInfo): EventInfo object describing the event
        code (str): The event code
        subcommand (str): Either "open" or "close"
    """
    user_id = event.user

    # check if user is an admin
    if not check_admin(user_id):
        send_message(event, 
                     header="Admin access required", 
                     body="You must be an admin to open/close events.", 
                     error=True)
        return "Error: User not admin", 400
    
    event_info_momentum = events.get(code)

    if event_info_momentum == None:
        send_message(event, 
                     header="Invalid event code",
                     body="This event does not exist. Try a different code.", 
                     error=True)
        return "Error: Invalid event code", 400
    

    name = event_info_momentum.get('name', "")

    if subcommand == "open":
        events.update({"open": True}, code)
        send_message(event, 
                     header="Event opened",
                     body=f'Users can now check in to event "{name}".', 
                     error=False)
        return "HTTP 200 OK", 200
    
    if subcommand == "close":
        events.update({"open": False}, code)
        send_message(event, 
                     header="Event closed",
                     body=f'Users can no longer check in to event "{name}".', 
                     error=False)
        return "HTTP 200 OK", 200