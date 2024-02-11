from pydantic import BaseModel
import requests
import random
from dotenv import load_dotenv
import os

load_dotenv()

class EventInfo(BaseModel):
    text: str = ""
    channel: str = None
    user: str = None

class SlackEvent(BaseModel):
    token: str = None
    type: str = None
    challenge: str = None
    event: EventInfo = None

def send_message(event: EventInfo, 
                 error: bool = False, 
                 header: str = None, 
                 body: str = None):
    """
    Sends a message to the user in the channel where the command was invoked,
    i.e. in the channel & user that EventInfo describes.
    Args:
        event (EventInfo): EventInfo object describing the event
        error (bool): True if the message is an error message
        header (str): Header text for the message
        body (str): Body text for the message
    Returns:
        None
    """
    
    if not event.channel or not event.user:
        return "Error: No channel or user provided", 400
    
    
    # compose message
    slack_emojis = ["partying_face", "white_check_mark", "tada", "rocket", 
                    "money_mouth_face", "champagne", "confetti_ball", "guitar", 
                    "bulb", "ok", "checkered_flag", "smile"]
    
    message = ""
    if header:
        message += f"*{header}*"
        decorator = "warning" if error else random.choice(slack_emojis)
        message += f" :{decorator}:\n\n"
    message += body

    # send message
    data = {
        "Content-Type": "application/json",
        "token": os.getenv('SLACK_BOT_TOKEN'),
        "channel": event.channel,
        "user": event.user,
        "text": message
    }
    r = requests.post("https://slack.com/api/chat.postEphemeral", data=data)
    print(r.text)

def parse_command(text: str):
    """
    Parses a command from the text of a Slack message. Text inside quotes is
    treated as a single argument.
    Args:
        text (str): Text of the Slack message
    Returns:
        command (str): The command, i.e. the first word of the message
        args (list): The arguments to the command, i.e. the rest of the message
    """
    text = text.replace(u"“", '"').replace(u"”", '"')
    # split by spaces
    words = text.split()

    # parse words in quotes
    args = []
    in_quote = False
    for word in words:
        if word[0] == '"' and word[-1] != '"':
            in_quote = True
            args.append(word[1:])
        elif word[-1] == '"' and word[0] != '"':
            in_quote = False
            args[-1] += " " + word[:-1]
        elif in_quote:
            args[-1] += " " + word
        else:
            args.append(word)
    
    return args