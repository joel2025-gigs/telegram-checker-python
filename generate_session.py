from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = input("Enter your API ID: ")
api_hash = input("Enter your API Hash: ")

with TelegramClient(StringSession(), int(api_id), api_hash) as client:
    print("\nYour session string (save this!):\n")
    print(client.session.save())
