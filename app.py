from flask import Flask, request, jsonify
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import functions
import os

app = Flask(__name__)

@app.route('/check', methods=['POST', 'OPTIONS'])
def check_phones():
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    data = request.get_json()
    phone_numbers = data.get('phoneNumbers', [])
    
    api_id = data.get('apiId') or os.environ.get('TELEGRAM_API_ID')
    api_hash = data.get('apiHash') or os.environ.get('TELEGRAM_API_HASH')
    session_string = data.get('sessionString') or os.environ.get('TELEGRAM_SESSION_STRING')
    
    if not all([api_id, api_hash, session_string]):
        return jsonify({'error': 'Missing Telegram credentials'}), 400
    
    results = []
    
    try:
        client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
        client.connect()
        
        for phone in phone_numbers:
            try:
                contact = functions.contacts.ImportContactsRequest(
                    contacts=[functions.contacts.InputPhoneContact(
                        client_id=0,
                        phone=phone,
                        first_name="Check",
                        last_name=""
                    )]
                )
                result = client(contact)
                
                if result.users:
                    user = result.users[0]
                    last_seen = "unknown"
                    last_seen_days = None
                    
                    if hasattr(user, 'status') and user.status:
                        status_type = type(user.status).__name__
                        if 'Recently' in status_type:
                            last_seen = "recently"
                            last_seen_days = 0
                        elif 'Week' in status_type:
                            last_seen = "within_week"
                            last_seen_days = 5
                        elif 'Month' in status_type:
                            last_seen = "within_month"
                            last_seen_days = 20
                        elif 'Long' in status_type:
                            last_seen = "long_ago"
                            last_seen_days = 90
                    
                    results.append({
                        'phoneNumber': phone,
                        'status': 'found',
                        'username': user.username,
                        'displayName': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                        'userId': str(user.id),
                        'lastSeen': last_seen,
                        'lastSeenDays': last_seen_days
                    })
                    
                    # Clean up - delete the contact
                    client(functions.contacts.DeleteContactsRequest(id=[user.id]))
                else:
                    results.append({
                        'phoneNumber': phone,
                        'status': 'not_found'
                    })
            except Exception as e:
                results.append({
                    'phoneNumber': phone,
                    'status': 'error',
                    'error': str(e)
                })
        
        client.disconnect()
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    response = jsonify({'results': results})
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
