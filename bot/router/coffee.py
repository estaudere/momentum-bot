from dotenv import load_dotenv
import os
import requests
import random
from utils import send_message
from typing import List
from .user import check_admin, register_user
from db import users
from datetime import datetime as dt

load_dotenv()

CHANNEL = os.getenv("COFFEE_CHANNEL")
LIMIT_USERS = 40
COFFEE_TIME = "Friday 4 pm at Medici"
HELP_CONTACT = "U04LRHRBGHF" # Riya Kohli
BOT_ID = "U05L20ULXPY" # bot user id

def filter_users(users_list: List[str], filter_admins=True) -> List[str]:
    # remove admins
    ret = []
    if filter_admins:
        ret = [user for user in users_list if not check_admin(user)]
    else:
        ret = users_list

    # check if user has opted out of coffee within a week ago
    # as well as performing updates to the coffee field (expires if more than a week ago)
    ret_new = []
    for user in ret:
        user_item = users.get(user)

        if not user_item: # if the user doesn't exist in the database
            ret_new.append(user)
            continue

        coffee = user_item.get("coffee")
        if coffee:
            ret_new.append(user)
            continue
        else:
            out_time = user_item.get("coffee_out_time") 

            # if no out time exists, they should be signed up
            if not out_time: 
                users.update({"coffee": True}, user)
                ret_new.append(user)
                continue
            
            # otherwise, if the out time was more than a week ago, sign them up
            if dt.now().timestamp() - out_time > 604800:
                users.update({"coffee": True}, user)
                ret_new.append(user)

    return ret_new


def get_users(channel_id: str) -> List[str]:
    headers = {
        "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"
    }
    
    data = {
        "Content-Type": "application/json",
        "channel": channel_id,
        "limit": LIMIT_USERS
    }
    r = requests.get("https://slack.com/api/conversations.members", params=data, headers=headers)
    members = r.json()["members"]

    # remove bot user
    members.remove(BOT_ID)

    members = filter_users(members, filter_admins=False)
    return members # TODO add blacklist filtering

def make_pairs(users: List[str]) -> List[List[str]]:
    # make random pairs of users
    # if there is an odd number of users, make a group of 3
    random.shuffle(users)
    pairs = []
    while len(users) > 0:
        if len(users) == 3:
            pairs.append(users)
            break
        pairs.append(users[:2])
        users = users[2:]
    return pairs

def post_matches(channel_id: str, pairs: List[List[str]]):
    match_message = "*Matches for this week:*\n"
    for pair in pairs:
        if (len(pair) == 3):
            match_message += f"\n<@{pair[0]}>, <@{pair[1]}>, and <@{pair[2]}>"
            continue
        match_message += f"\n<@{pair[0]}> and <@{pair[1]}>"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": 'A new round of pairings are in! :coffee:\n'
                        f'Reach out to your coffee partner(s) and verify that you\'ll be there at *{COFFEE_TIME}*! '
                        'Otherwise, you should arrange to find another time to meet this week.'
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": match_message
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"That's {len(pairs)} matches for this round! If you have any questions or concerns, please reach out to <@{HELP_CONTACT}>."
            }
        }
    ]


    data = {
        "Content-Type": "application/json",
        "channel": channel_id,
        "text": ":coffee: Coffee matches for this week are in! :coffee:",
        "blocks": blocks
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"
    }
    r = requests.post("https://slack.com/api/chat.postMessage", json=data, headers=headers)
    if r.json().get('error'):
        raise Exception(r.json().get('error'))
    
def coffee_create(event, text):
    if not check_admin(event.user):
        send_message(event, body="You do not have permission to use this command.", error=True)
        return "Error: Unauthorized", 400

    channel_name, channel_id = CHANNEL.split(":")

    try:
        channel_users: List[str] = get_users(channel_id)
        print(f"Successfully fetched {len(channel_users)} users from {channel_name} channel")
    except ValueError:
        send_message(event, body=f"Sorry, I'm not invited to that channel.", error=True)
        return "Error: Invalid channel", 400

    if len(channel_users) < 2:
        send_message(event, body=f"Not enough users to make pairs in the channel <#{channel_id}>.")
        return

    pairs = make_pairs(channel_users)
    print(f"Successfully made {len(pairs)} pairs")
    post_matches(channel_id, pairs)

    send_message(event, body=f"Successfully made {len(pairs)} pairs in the channel <#{channel_id}>.")
    # TODO add functionality to send dms to users

    return "Success", 200

def coffee_out(event, text):
    # mark user as opting out of coffee and note the time
    user_id = event.user
    register_user(event, send_msg=False)
    users.update({"coffee": False, "coffee_out_time": dt.now().timestamp()}, user_id)
    send_message(event, body="You have opted out of coffee for this week.")
    return "Success", 200

def handle_coffee(event, text):
    subcommand = text[1].lower()
    if subcommand == "create":
        return coffee_create(event, text)
    elif subcommand == "out":
        return coffee_out(event, text)
    else:
        send_message(event, body="Invalid subcommand.", error=True)
        return "Error: Invalid subcommand", 400

