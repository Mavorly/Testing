import json
import os
import schedule
import time as t 
import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, g
from slackeventsapi import SlackEventAdapter
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = Flask(__name__)

#Loading environment file
env_path = Path('.') / '.env' # SlackBot Token Key
load_dotenv(dotenv_path=env_path)

#Event adapter
slack_event_adapter = SlackEventAdapter(os.environ.get("SLACK_EVENTS_TOKEN"),'/slack/events',app)

# Initialize a WebClient with your bot token
slack_web_client = WebClient(token=os.environ.get("SLACKBOT_TOKEN"))

# Send Message into the Closing Checklist Channel once a day at 3:15pm
time = datetime.time()
today = datetime.date.today()
month = today.strftime("%B")
#Directory Info for emoji reactions
lines_and_ts = {}
ts_list = []

#Bot's User ID 
bot_id = client.auth_test()['user_id']



#Global Variables
first_message_ts = None
last_message_ts = None
checklistName = None
with open('checklists.json') as file:
    checklists = json.load(file)
with open('checklist_reactions.json') as file:
    checklist_reactions = json.load(file)
checkbox = ':white_large_square:'
who_checked_channel = 'checklist_confirms'

# You probably want to use a database to store any user information ;)
########################################
response = client.users_list()
users = response["members"]
users_dict = {user["id"]: user["name"] for user in users}
print(users_dict)
##################################################################
@app.route('/sendchecklist', methods=['POST'])
def send_check_list():
    global checklists
    payload = request.form
    checklistName = payload.get('text')
    channel_id = payload.get('channel_id')
    ts = payload.get('ts')
    checklist = checklists.get(checklistName)
    client.chat_postMessage(channel=channel_id, text="Checklist: " + checklistName)
    if checklist: 
        for item in checklist:
            response = client.chat_postMessage(channel=channel_id, text=checkbox + item)    
    t.sleep(1)
    return 'Checklist Sent!'

@app.route('/makechecklist', methods=['POST'])
def make_checklist_handler():
    global first_message_ts
    global checklistName
    payload = request.form
    checklistName = payload.get('text')
    channel_id = payload.get('channel_id')
    response = client.conversations_history(channel=channel_id)
    if response["ok"]:
        first_message_ts = response["messages"][0]["ts"]
    return 'Your checklist: ' + '"'+checklistName+'"' + ' Is ready to start. To add new points just\
 send messages below when your finished type /savechecklist! to save'


@app.route('/savechecklist', methods=['POST'])
def save_checklist_handler():
    global checklistName , first_message_ts, checklists
    listening = False
    payload = request.form
    channel_id = payload.get('channel_id')
    response = client.conversations_history(channel=channel_id)
    print(checklistName)
    print(checklists)
    if response["ok"]:
        last_message_ts = response["messages"][0]["ts"]
        print(first_message_ts)
        print(last_message_ts)
    print(client.conversations_history(channel=channel_id,oldest = first_message_ts, latest = last_message_ts))
    messages_in_range = client.conversations_history(channel=channel_id,oldest = first_message_ts)
    if messages_in_range["ok"]:
        messages = messages_in_range["messages"]
        for message in reversed(messages):
            message_text = message['text']
            try:
                checklists[checklistName].append(message_text)
            except:
                checklists[checklistName] = []
                checklists[checklistName].append(message_text)
    with open('checklists.json', 'w') as file:
        json.dump(checklists, file)
    file.close()
    return 'Finished Checklist: ' + '"'+checklistName+'"' + ' Use the command /sendchecklist [Name] to send it'

@slack_event_adapter.on('reaction_added')
def reaction(payload):
    event = payload.get('event', {})
    print (event)
    token = payload['token']
    print(token)
    ts = event['item']['ts']
    channel_id = event['item']['channel']
    original_user_id = event.get('item_user')
    react_user_id = event.get('user')
    react_name = users_dict[react_user_id]
    reaction = event.get('reaction')
    checkbox = ":"+reaction+":"
    ####Create A Range####
    start_timestamp = float(ts) - .00001
    end_timestamp = float(ts) + .00001
    message_in_range = client.conversations_history(channel=channel_id,oldest = str(start_timestamp), latest = str(end_timestamp))
    try:
        text = message_in_range['messages'][0]['blocks'][0]['elements'][0]['elements'][1]['text']   
    except:
        print("error")
        print(message_in_range)
    print(payload)
    if original_user_id == bot_id:
        client.chat_update(
        channel=channel_id,
        ts=ts,
        text= checkbox + text
        )
        try:
            checklist_reactions[text].append([str(today),str(time),text,checkbox,react_user_id])
        except:
            checklist_reactions[text] = []
            checklist_reactions[text].append([str(today),str(time),text,checkbox,react_user_id])
        with open('checklist_reactions.json', 'w') as file:
            json.dump(checklist_reactions, file)
            file.close()    
        response = client.chat_postMessage(channel='#checklist_confirms', text=react_name + " reacted to " + text + " with " + checkbox + "at " + str(today))
    return
    ######[DELETE REACTION]#########
    client.reactions_remove(token = token , name = checkbox)
    #########################
        #Send reaction user_id to a seperate channel including what the message they responded to was

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port=8080)
