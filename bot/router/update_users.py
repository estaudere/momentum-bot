import requests
from deta import Deta
import os

deta = Deta(os.getenv('DETA_PROJECT_KEY'))
users = deta.Base("users")

SLACK_BOT_TOKEN='xoxb-2873829479361-5682028711814-pXNOqWPP6btCNiW4kbj4zEag'

def fill_in_user(user_id):
    data = {
        "Content-Type": "application/json",
        "user": user_id
    }
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    user_info = requests.get("https://slack.com/api/users.profile.get", 
                                params=data, 
                                headers=headers)
    user_info = user_info.json().get('profile')
    
    users.update(
        {
            "name": user_info.get('real_name'), 
            "email": user_info.get('email')
        }, 
        user_id)
    

def update_users():
    # get all users from the db
    res = users.fetch()
    all_items = res.items

    while res.last:
        res = users.fetch(last=res.last)
        all_items += res.items

    # print(all_items)

    for user in all_items:
        if user.get('name') == None or user.get('email') == None:
            fill_in_user(user.get('key'))
            print(f"Updated {user.get('key')}")
        else:
            print(f"Skipping {user.get('key')}")

if __name__ == "__main__":
    update_users()