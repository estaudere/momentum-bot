from db import users, committees
from utils import EventInfo, send_message
from typing import List
from .user import register_user

COMMITTEES = {
    "comms": 10,
    "special": 10,
    "partners": 5
}

def handle_committee(event: EventInfo, text: List[str]):
    """
    Handle committee subcommand.
    Args:
        event (EventInfo): EventInfo object describing the event
        text (List[str]): List of parsed words in the command
    Returns:
        Error 400 or HTTP 200 OK
    """

    if len(text) == 1:
        return "Error: No subcommand provided", 400
    
    c = text[1].lower()

    if c not in COMMITTEES.keys():
        send_message(event, 
                     header="Invalid committee name",
                     body="Try a different committee name or contact an admin.", 
                     error=True)
        return "Error: Invalid committee", 400
    
    register_user(event, send_msg=False)
    user_id = event.user
    user = users.get(user_id) # get user info from db

    # check if the user is already in the current committee
    u = committees.get(user_id)
    if u is not None and u.get("committee") == c:
        send_message(event, 
                     body="You are already in this committee.")
        return "Already in committee", 200
    
    # check the number of committee c that already exist in the db
    num_c = committees.fetch({"committee": c}).count
    if num_c >= COMMITTEES[c]:
        send_message(event, 
                     header="Committee full",
                     body=f"Sorry, the maximum number of members for that committee has been reached.",
                     error=True)
        return "Committee full", 200
    else:
        # update the user's committee in the db
        committees.put({"committee": c, "name": user.get("name")}, user_id)
        send_message(event, 
                     header="Success!",
                     body=f"You have been added to the {c} committee.")
        return "HTTP 200 OK", 200