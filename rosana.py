import asyncio
import logging
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo
import os
import random

# Try to import optional libraries
try:
    from fuzzywuzzy import fuzz
except ImportError:
    print("fuzzywuzzy library not found. Please install it using 'pip install fuzzywuzzy python-Levenshtein'")
    fuzz = None

try:
    from telethon import TelegramClient, events, utils
except ImportError:
    print("telethon library not found. Please install it using 'pip install telethon'")
    TelegramClient = events = utils = None

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv library not found. Please install it using 'pip install python-dotenv'")
    load_dotenv = lambda x: None

# Load environment variables
load_dotenv('.env.local')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\nStarting SSHJarvis...")

# Get API credentials from environment variables
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')

# Configurable settings
inclusion_keywords = ["SHIFT AVAILABLE", "MULTIPLE SHIFTS AVAILABLE", "URGENT SHIFT AVAILABLE"]
inclusion_locations = ["Calvary Oakland", "Calvary Brighton", "Calvary Kingswood", "Helping Hand North Adelaide", "Helping Hand", "HH"]
exclusion_locations = ["SNOWTOWN", "ELIZABETH"]
relevant_roles = ["PCW", "PCA"]

chat_names = ["WorkforceXS Carers (PCA, PCW,CWK) chat", "test", "state"]
chat_ids = {}
bot_active = False  # Initial state of the bot
RESPONSE_DELAY = 0  # Default delay
ADELAIDE_TZ = ZoneInfo("Australia/Adelaide")

async def get_chat_ids(client):
    global chat_ids
    async for dialog in client.iter_dialogs():
        if dialog.name in chat_names:
            chat_ids[dialog.name] = dialog.id
    logger.info(f"Chat IDs: {chat_ids}")

def fuzzy_match(target, choices, threshold=80):
    best_match = None
    best_ratio = 0
    for choice in choices:
        ratio = fuzz.ratio(target.lower(), choice.lower())
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = choice
    return best_match

def parse_shift_message(message):
    lines = message.split('\n')
    date = None
    venue = None
    shifts = []
    is_urgent = False
    
    for line in lines:
        if any(keyword in line.upper() for keyword in inclusion_keywords):
            if "URGENT" in line.upper():
                is_urgent = True
            if "TODAY" in line.upper():
                date = "TODAY"
            elif "TOMORROW" in line.upper():
                date = "TOMORROW"
            continue
        
        if not date and re.match(r'\w{3}\s+\d{1,2}/\d{1,2}', line):
            date = line.strip()
            continue
        
        if not venue:
            possible_venue = fuzzy_match(line, inclusion_locations)
            if possible_venue:
                venue = possible_venue
                continue
        
        shift_match = re.match(r'(?:(\w+)\s+)?(\d{4})-(\d{4})(?:\s*x\s*(\d+))?', line)
        if shift_match:
            role, start_time, end_time, multiplier = shift_match.groups()
            if not role or role.upper() in (r.upper() for r in relevant_roles):
                shift_time = f"{start_time}-{end_time}"
                multiplier = int(multiplier) if multiplier else 1
                shifts.extend([shift_time] * multiplier)
        elif "ASAP" in line.upper():
            asap_match = re.search(r'ASAP-(\d{4})', line.upper())
            if asap_match:
                end_time = asap_match.group(1)
                shifts.append(f"ASAP-{end_time}")
            else:
                shifts.append("ASAP-2359")  # Default end time if not specified
            is_urgent = True
    
    logger.info(f"Parsed message - Date: {date}, Venue: {venue}, Shifts: {shifts}, Urgent: {is_urgent}")
    return date, venue, shifts, is_urgent

def format_date(date_str):
    if not date_str:
        return datetime.now(ADELAIDE_TZ).strftime("%d %B")
    if date_str == "TODAY":
        return datetime.now(ADELAIDE_TZ).strftime("%d %B")
    if date_str == "TOMORROW":
        tomorrow = datetime.now(ADELAIDE_TZ) + timedelta(days=1)
        return tomorrow.strftime("%d %B")
    else:
        try:
            day, month = map(int, date_str.split('/'))
            current_year = datetime.now(ADELAIDE_TZ).year
            date_obj = datetime(current_year, month, day, tzinfo=ADELAIDE_TZ)
            return date_obj.strftime("%d %B")
        except ValueError:
            return datetime.now(ADELAIDE_TZ).strftime("%d %B")

def format_response(venue, date, time, is_urgent):
    formatted_date = format_date(date)
    if is_urgent and time.startswith("ASAP"):
        return f"I can in 20 minutes {venue}/{formatted_date}/{time}"
    else:
        start_time, end_time = time.split('-')
        formatted_time = f"{start_time[:2]}{start_time[2:] or ''}-{end_time[:2]}{end_time[2:] or ''}"
        return f"I can {venue}/{formatted_date}/{formatted_time}"

def calculate_shift_duration(shift):
    start, end = shift.split('-')
    if start.upper() == "ASAP":
        return float('inf')  # Prioritize ASAP shifts
    start_minutes = int(start[:2]) * 60 + int(start[2:] or '0')
    end_minutes = int(end[:2]) * 60 + int(end[2:] or '0')
    duration = end_minutes - start_minutes
    if duration < 0:
        duration += 24 * 60
    return duration

def get_longest_shift(shifts):
    return max(shifts, key=calculate_shift_duration)

async def main():
    if not api_id or not api_hash:
        logger.error("API credentials not found. Please check your .env.local file.")
        return

    client = TelegramClient('sshjarvis_session', api_id, api_hash)

    async with client:
        await get_chat_ids(client)

        @client.on(events.NewMessage(chats=list(chat_ids.values())))
        async def my_event_handler(event):
            global bot_active, RESPONSE_DELAY
            message = event.raw_text
            sender = await event.get_sender()
            sender_name = utils.get_display_name(sender)
            chat_name = next((name for name, id in chat_ids.items() if id == event.chat_id), None)

            logger.info(f"Message from {sender_name} in {chat_name}: {message}")

            if chat_name == "state":
                command_parts = message.strip().lower().split()
                if command_parts[0] == "namaste":
                    if len(command_parts) == 2 and command_parts[1].isdigit():
                        delay = int(command_parts[1])
                        if 0 <= delay <= 4:
                            RESPONSE_DELAY = delay
                            bot_active = True
                            logger.info(f"Bot activated with delay {RESPONSE_DELAY}")
                            await client.send_message(event.chat_id, f'\n--------------------\nTURNED ON.\nShift Pick Gardinchu Hai!\nDelay set to {RESPONSE_DELAY} seconds.\n--------------------')
                        else:
                            await client.send_message(event.chat_id, "Invalid delay. Please use a number between 0 and 4.")
                    else:
                        await client.send_message(event.chat_id, "Please specify a delay between 0 and 4 seconds. Example: 'namaste 2'")
                elif message.strip().lower() == "bye":
                    bot_active = False
                    logger.info("Bot deactivated.")
                    await client.send_message(event.chat_id, '\n--------------------\nTURNED OFF!\nMa Sutna Gaye!\n--------------------')
                print("\n-------------------------\n")
                return

            if bot_active and any(keyword in message.upper() for keyword in inclusion_keywords):
                try:
                    date, venue, shifts, is_urgent = parse_shift_message(message)
                    
                    if venue and shifts and venue not in exclusion_locations:
                        longest_shift = get_longest_shift(shifts)
                        response = format_response(venue, date, longest_shift, is_urgent)
                        logger.info(f"Preparing to send response: {response}")
                        await asyncio.sleep(RESPONSE_DELAY)
                        await client.send_message(event.chat_id, response)
                        logger.info(f"Response sent after {RESPONSE_DELAY} seconds delay.")
                    else:
                        logger.info("Invalid shift information or excluded location, not responding.")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
            else:
                logger.info("Bot is inactive or no inclusion keyword found, not processing message.")

        await client.run_until_disconnected()

if __name__ == "__main__":
    if None in (fuzz, TelegramClient, load_dotenv):
        print("Error: Some required libraries are missing. Please install them and try again.")
    else:
        print("SSHJarvis is now running!")
        asyncio.run(main())
        print("SSHJarvis has stopped.")