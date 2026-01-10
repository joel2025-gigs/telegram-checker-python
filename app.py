from flask import Flask, request, jsonify
from telethon.sync import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.errors import FloodWaitError
import asyncio
import time

app = Flask(__name__)

BATCH_SIZE = 50  # Process 50 contacts at a time
BATCH_DELAY = 2  # Wait 2 seconds between batches

async def check_phones_batch(client, phone_numbers):
    results = []
    
    for i in range(0, len(phone_numbers), BATCH_SIZE):
        batch = phone_numbers[i:i + BATCH_SIZE]
        print(f"Processing batch {i // BATCH_SIZE + 1}: {len(batch)} numbers")
        
        try:
            contacts = [
                InputPhoneContact(
                    client_id=idx,
                    phone=phone,
                    first_name=f"Check{idx}",
                    last_name=""
                )
                for idx, phone in enumerate(batch)
            ]
            
            result = await client(ImportContactsRequest(contacts))
            
            # Map imported users
            imported_phones = {}
            for user in result.users:
                if user.phone:
                    imported_phones[f"+{user.phone}"] = user
            
            # Build results for this batch
            for phone in batch:
                normalized = phone if phone.startswith('+') else f'+{phone}'
                if normalized in imported_phones or phone in imported_phones:
                    user = imported_phones.get(normalized) or imported_phones.get(phone)
                    results.append({
                        "phoneNumber": phone,
                        "status": "found",
                        "userId": str(user.id),
                        "username": user.username,
                        "displayName": f"{user.first_name or ''} {user.last_name or ''}".strip()
                    })
                else:
                    results.append({
                        "phoneNumber": phone,
                        "status": "not_found"
                    })
            
            # Delete contacts to clean up
            if result.users:
                await client(DeleteContactsRequest(id=[u.id for u in result.users]))
            
            # Delay between batches
            if i + BATCH_SIZE < len(phone_numbers):
                await asyncio.sleep(BATCH_DELAY)
                
        except FloodWaitError as e:
            print(f"Rate limited! Waiting {e.seconds} seconds...")
            # For remaining numbers in this batch, mark as rate-limited
            for phone in batch:
                if not any(r['phoneNumber'] == phone for r in results):
                    results.append({
                        "phoneNumber": phone,
                        "status": "error",
                        "error": f"Rate limited. Try again in {e.seconds} seconds."
                    })
            # Wait the required time, then continue
            await asyncio.sleep(min(e.seconds, 30))  # Cap at 30 seconds
            
        except Exception as e:
            print(f"Batch error: {e}")
            for phone in batch:
                if not any(r['phoneNumber'] == phone for r in results):
                    results.append({
                        "phoneNumber": phone,
                        "status": "error", 
                        "error": str(e)
                    })
    
    return results

@app.route('/check', methods=['POST'])
def check():
    data = request.json
    phone_numbers = data.get('phoneNumbers', [])
    api_id = data.get('apiId')
    api_hash = data.get('apiHash')
    session_string = data.get('sessionString')
    
    if not all([phone_numbers, api_id, api_hash, session_string]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        from telethon.sessions import StringSession
        
        async def run():
            client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                return {"error": "Session not authorized"}
            
            results = await check_phones_batch(client, phone_numbers)
            await client.disconnect()
            return {"results": results}
        
        result = asyncio.run(run())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
