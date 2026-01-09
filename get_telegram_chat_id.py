#!/usr/bin/env python3
"""
Simple script to get your Telegram chat ID
Run this script and send a message to your bot to get the chat ID
"""

import requests
import sys
import json

def get_chat_id(bot_token):
    """Get chat ID by checking bot updates"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('ok'):
            print(f"Error: {data.get('description', 'Unknown error')}")
            return None

        updates = data.get('result', [])

        if not updates:
            print("\nNo messages found!")
            print("Please send a message to your bot and run this script again.")
            print(f"Bot username: @{get_bot_username(bot_token)}")
            return None

        # Get the most recent chat ID
        latest_update = updates[-1]
        chat_id = latest_update.get('message', {}).get('chat', {}).get('id')

        if chat_id:
            print(f"\n✅ Your Telegram Chat ID: {chat_id}")
            print(f"\nAdd this to your config.json:")
            print(f'  "telegram_chat_id": "{chat_id}",')
            return chat_id
        else:
            print("Could not extract chat ID from updates")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Telegram API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_bot_username(bot_token):
    """Get bot username"""
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data.get('result', {}).get('username', 'your_bot')
    except:
        return 'your_bot'

def main():
    # Check if config.json exists and try to read token from it
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            bot_token = config.get('telegram_bot_token', '')

            if bot_token and bot_token != "YOUR_BOT_TOKEN_HERE":
                print(f"Using bot token from config.json")
                get_chat_id(bot_token)
                return
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Warning: Could not read config.json: {e}")

    # Ask for token if not in config
    if len(sys.argv) > 1:
        bot_token = sys.argv[1]
    else:
        print("Usage: python get_telegram_chat_id.py [BOT_TOKEN]")
        print("\nOr add your bot token to config.json and run without arguments")
        sys.exit(1)

    get_chat_id(bot_token)

if __name__ == "__main__":
    main()
