from db import users
from utils import EventInfo, send_message
from typing import List
import requests
import os


def handle_user(event: EventInfo, text: List[str]):
    """
    Handle user subcommands.
    Args:
        event (EventInfo): EventInfo object describing the event
        text (List[str]): List of parsed words in the command
    Returns:
        Error 400 or HTTP 200 OK
    """

    if len(text) == 1:
        return "Error: No subcommand provided", 400
    
    subcommand = text[1].lower()
    if subcommand == "makeadmin":

        if len(text) < 3 or text[2] != os.getenv('ADMIN_PW'):
            send_message(event, 
                         header="Incorrect password", 
                         body="Contact an admin for assistance.", 
                         error=True)
            return "Error: Incorrect password", 200
        
        # otherwise, correct password given
        make_admin(event)
        return "HTTP 200 OK", 200
    
    if subcommand == "register":
        register_user(event, send_msg=True)
        return "HTTP 200 OK", 200
        


def make_admin(event: EventInfo):
    """
    Make a user an admin in the database.
    Args:
        event (EventInfo): EventInfo object describing the event
    """
    user_id = event.user
    user = users.get(user_id) # find the user in the database

    if user: # if the user exists, update their admin status
        users.update({"admin": True}, user_id)
    else: # if the user doesn't exist in the db, create a new user
        user_info = get_user_info(user_id)
        if not user_info: # the user couldn't be found in the workspace
            send_message(event, 
                         header="Error: User not found", 
                         body="Contact an admin for assistance.", 
                         error=True)
            return "Error: User not found", 200
        
        users.put(
            {
                "admin": True, 
                "name": user_info.get('real_name'), 
                "email": user_info.get('email')
            }, 
            user_id)
    
    send_message(event,
                 header="Success!", 
                 body="You are now an admin! You can now create events using `event create <name>`.")        


def check_admin(user_id: str):
    """
    Helper function to check if a user is an admin. Useful for commands that
    require admin access.
    Args:
        user_id (str): Slack user ID
    """
    user = users.get(user_id)
    if user.get('admin') == True:
        return True
    return False


def get_user_info(user_id: str):
    """
    Get a user's info from Slack to put into a database.
    Args:
        user_id (str): Slack user ID
    Returns:
        user_info (dict): Dictionary of user info, or None if the user couldn't 
            be found
    """
    data = {
        "Content-Type": "application/json",
        "user": user_id
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"
    }
    user_info = requests.get("https://slack.com/api/users.profile.get", 
                                params=data, 
                                headers=headers)
    user_info = user_info.json().get('profile')
    return user_info


def register_user(event: EventInfo, send_msg: bool = False):
    """
    Register a user in the database.
    Args:
        event (EventInfo): EventInfo object describing the event
        send_msg (bool): True if a message should be sent to the user
            (typically used in response to a command, but should be False
            otherwise)
    """
    user_id = event.user
    user = users.get(user_id) # find the user in the database

    if user: # if the user exists, nothing needs to be done
        if send_msg:
            send_message(event, 
                         body="You are already registered.")
        return None
    else: # if the user doesn't exist in the db, create a new user
        user_info = get_user_info(user_id)
        if not user_info: # the user couldn't be found in the workspace
            if send_msg:
                send_message(event, 
                            header="Error: User not found", 
                            body="Contact an admin for assistance.", 
                            error=True)
            return None
        
        users.put(
            {
                "admin": False, 
                "name": user_info.get('real_name'), 
                "email": user_info.get('email')
            }, 
            user_id)
    
    if send_msg:
        send_message(event,
                 header="Success!", 
                 body="You are registered! You can now checkin for events using `event checkin <event code>`.")