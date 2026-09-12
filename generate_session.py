from pyrogram import Client

api_id = int(input("Enter API_ID: ").strip())
api_hash = input("Enter API_HASH: ").strip()

with Client("session_gen", api_id=api_id, api_hash=api_hash, in_memory=True) as app:
    print("\nSESSION_STRING (keep it secret):\n")
    print(app.export_session_string())
