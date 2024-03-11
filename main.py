import json
import time

import telebot
from apscheduler.schedulers.background import BackgroundScheduler
from requests import ReadTimeout
from telebot import types
from telebot.types import Message
from telebot.util import update_types

api_key = "6329679818:AAFSyk6qEc-Gut9sIS7kIBC5rQ4lgXofGEI"
bot = telebot.TeleBot(token=api_key)
ref_data = dict()
channel = "-1001868675721"
final_channel = "-1002003338835"
file_path = "ref.json"
next_update = time.time()
"""
tg_id = {
link = "invite_link"
accepted = [id,id,id]
verified = 0 (int of number of ppl who accepted)
username = ""
}
"""


def load_dict_from_json():
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        # If the file doesn't exist, return an empty dictionary
        return {"invited": []}


def save_dict_to_json():
    with open(file_path, 'w') as file:
        json.dump(ref_data, file, indent=2)


@bot.chat_member_handler()
def chat_member_update(cmu: types.ChatMemberUpdated):
    global  next_update
    if cmu.invite_link is None:
        return
    if cmu.from_user.id in ref_data["invited"]:
        return
    for i in ref_data.keys():
        if i == "invited":
            continue
        if cmu.invite_link.invite_link == ref_data[i]['link']:
            ref_data[i]["accepted"].append(cmu.from_user.id)
            ref_data[i]["verified"] += 1
            next_update = time.time() + 600
    ref_data["invited"].append(cmu.from_user.id)


@bot.message_handler(commands=["start"])
def handle_start(message: Message):
    if str(message.chat.id) == channel:
        return
    if not str(message.from_user.id) in ref_data:
        ref_data[str(message.from_user.id)] = {
            "link": bot.create_chat_invite_link(chat_id=channel).invite_link,
            "accepted": [],
            "verified": 0,
            "username": message.from_user.username if message.from_user.username is not None else message.from_user.first_name
        }
    msg = """
Welcome to the referral bot. Please send your invite link to your friends.

{}

Make sure that the person stays in the channel in order to count. 
            """.format(ref_data[str(message.from_user.id)]["link"])
    bot.send_message(message.chat.id, msg, parse_mode="MARKDOWN", reply_to_message_id=message.message_id)


def verify_users():
    global next_update
    if next_update < time.time():
        return
    for i in ref_data.keys():
        if i == "invited":
            continue
        copy_inv = ref_data[i]["accepted"].copy()
        for tg_id in copy_inv:
            while True:
                try:
                    chat_member = bot.get_chat_member(final_channel, tg_id)
                    if chat_member.is_member:
                        continue
                    else:
                        ref_data[i]["accepted"].remove(tg_id)
                        ref_data[i]["verified"] -= 1
                except Exception as e:
                    print(e)
                    time.sleep(3)


@bot.message_handler(commands=["ranking"])
def handle_ranking(message: Message):
    to_send = ""
    unsorted = []
    for i in ref_data.keys():
        if i == "invited":
            continue
        unsorted.append((i, ref_data[i]["verified"]))
    sort = sorted(unsorted, key=lambda tup: tup[1], reverse=True)
    rank = 1
    for i in sort:
        to_send += "{}° @{} ==>\t{} invitation \n".format(rank, str(ref_data[i[0]]["username"]).replace("_","\_"), i[1])
        rank += 1
    if to_send == "":
        bot.reply_to(message, "No participation yet. Check back later")
    else:
        to_send = "Invite ranking\n================\n\n" + to_send
        bot.reply_to(message, to_send, parse_mode="Markdown")


ref_data = load_dict_from_json()
scheduler = BackgroundScheduler()
# Schedule the function to run every minute
scheduler.add_job(save_dict_to_json, 'interval', minutes=1)
scheduler.add_job(verify_users, "interval", minutes=1)
scheduler.start()

while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=update_types)
        while True:
            time.sleep(100)
    except (ConnectionError, ReadTimeout) as e:
        time.sleep(5)
