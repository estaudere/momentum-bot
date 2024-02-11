from utils import EventInfo, send_message, parse_command
from .user import handle_user
from .event import handle_event
from .committee import handle_committee
from .help_text import help_text

def router(event: EventInfo):
    text = parse_command(event.text)

    if 'user' in text[0].lower():
        return handle_user(event, text)
    
    elif 'event' in text[0].lower():
        return handle_event(event, text)
    
    elif 'committee' in text[0].lower():
        return handle_committee(event, text)
    
    else:
        # send some helpful text
        send_message(event, body=help_text)
        return "Error: invalid command", 400