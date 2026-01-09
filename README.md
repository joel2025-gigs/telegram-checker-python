# Telegram Phone Checker

## Setup

1. Get API credentials from https://my.telegram.org
2. Run `python generate_session.py` locally to get session string
3. Set environment variables on Railway:
   - `TELEGRAM_API_ID`
   - `TELEGRAM_API_HASH`
   - `TELEGRAM_SESSION_STRING`

## Deploy to Railway

Push this repo to GitHub, then deploy on Railway.
