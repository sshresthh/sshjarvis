import asyncio
import logging
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo
import os
import json
from dateutil import parser as date_parser

# Try to import optional libraries
try:
    from fuzzywuzzy import fuzz, process
except ImportError:
    print("fuzzywuzzy library not found. Please install it using 'pip install fuzzywuzzy python-Levenshtein'")
    fuzz = process = None

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

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("\nStarting SSHJarvis...")

# Get API credentials from environment variables
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')

# Configurable settings from config file
inclusion_keywords = config['inclusion_keywords']
inclusion_locations = config['inclusion_locations']
exclusion_locations = config['exclusion_locations']
relevant_roles = config['relevant_roles']
facility_wards = config['facility_wards']
chat_names = config['chat_names']
FUZZY_MATCH_THRESHOLD = config['fuzzy_match_threshold']
ASAP_RESPONSE_TIME = config['asap_response_time']
MAX_MESSAGES_PER_MINUTE = config['max_messages_per_minute']

chat_ids = {}
bot_active = False  # Initial state of the bot
RESPONSE_DELAY = 0  # Default delay
ADELAIDE_TZ = ZoneInfo("Australia/Adelaide")

message_count = 0
last_reset_time = datetime.now()

async def get_chat_ids(client):
    global chat_ids
    async for dialog in client.iter_dialogs():
        if dialog.name in chat_names:
            chat_ids[dialog.name] = dialog.id
    logger.info(f"Chat IDs: {chat_ids}")

def fuzzy_match(target, choices, threshold=FUZZY_MATCH_THRESHOLD):
    best_match, score = process.extractOne(target, choices)
    if score >= threshold:
        return best_match
    return None

def parse_shift_message(message):
    lines = message.split('\n')
    date = None
    current_venue = None
    current_ward = None
    shifts = []
    is_urgent = False
    
    for line in lines:
        if any(keyword in line.upper() for keyword in inclusion_keywords):
            if "URGENT" in line.upper():
                is_urgent = True
            continue
        
        if not date:
            try:
                parsed_date = date_parser.parse(line, fuzzy=True)
                if parsed_date:
                    date = parsed_date.strftime("%d/%m")
                    continue
            except ValueError:
                logger.warning(f"Could not parse date from line: {line}")
        
        possible_venue = fuzzy_match(line, inclusion_locations)
        if possible_venue:
            current_venue = possible_venue
            # Check for ward information in the same line
            ward_match = re.search(r'(?:in|IN)\s+(.+)$', line)
            if ward_match:
                current_ward = ward_match.group(1).strip().title()
            else:
                current_ward = None
            continue
        
        shift_match = re.match(r'(?:(\w+)\s+)?(\d{4})-(\d{4})(?:\s+IN\s+(.+?))?(?:\s*x\s*(\d+))?$', line)
        if shift_match:
            role, start_time, end_time, ward, multiplier = shift_match.groups()
            if not role or role.upper() in (r.upper() for r in relevant_roles):
                shift_time = f"{start_time}-{end_time}"
                ward = ward.strip().title() if ward else current_ward
                multiplier = int(multiplier) if multiplier else 1
                shifts.extend([(shift_time, ward, current_venue)] * multiplier)
        elif "ASAP" in line.upper():
            asap_match = re.search(r'ASAP-(\d{4})(?:\s+IN\s+(.+))?$', line.upper())
            if asap_match:
                end_time, ward = asap_match.groups()
                shift_time = f"ASAP-{end_time}"
                ward = ward.strip().title() if ward else current_ward
                shifts.append((shift_time, ward, current_venue))
            else:
                shifts.append(("ASAP-2359", current_ward, current_venue))  # Default end time if not specified
            is_urgent = True
    
    logger.info(f"Parsed message - Date: {date}, Shifts: {shifts}, Urgent: {is_urgent}")
    return date, shifts, is_urgent

def format_date(date_str):
    today = datetime.now(ADELAIDE_TZ)
    if not date_str:
        return today.strftime("%d/%m")
    try:
        date_obj = date_parser.parse(date_str, fuzzy=True)
        if date_obj < today:
            date_obj = date_obj.replace(year=today.year + 1)
        return date_obj.strftime("%d/%m")
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}")
        return today.strftime("%d/%m")

def format_response(venue, date, shift, is_urgent):
    time, ward, _ = shift
    formatted_date = format_date(date)
    
    if is_urgent and time.startswith("ASAP"):
        response = f"I can {ASAP_RESPONSE_TIME} mins in {venue},"
    else:
        response = f"I can in {venue},"
    
    if ward:
        response += f" {ward},"
    response += f" {formatted_date}, {time}"
    return response

def calculate_shift_duration(shift):
    time, _, _ = shift
    start, end = time.split('-')
    if start.upper() == "ASAP":
        return float('inf')  # Prioritize ASAP shifts
    start_minutes = int(start[:2]) * 60 + int(start[2:] or '0')
    end_minutes = int(end[:2]) * 60 + int(end[2:] or '0')
    duration = end_minutes - start_minutes
    if duration < 0:
        duration += 24 * 60
    return duration

async def main():
    if not api_id or not api_hash:
        logger.error("API credentials not found. Please check your .env.local file.")
        return

    client = TelegramClient('sshjarvis_session', api_id, api_hash)

    async with client:
        await get_chat_ids(client)

        @client.on(events.NewMessage(chats=list(chat_ids.values())))
        async def my_event_handler(event):
            global bot_active, RESPONSE_DELAY, message_count, last_reset_time
            
            # Rate limiting
            current_time = datetime.now()
            if (current_time - last_reset_time).total_seconds() >= 60:
                message_count = 0
                last_reset_time = current_time
            
            if message_count >= MAX_MESSAGES_PER_MINUTE:
                logger.warning("Rate limit exceeded. Skipping message.")
                return

            try:
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
                    date, shifts, is_urgent = parse_shift_message(message)
                    
                    if shifts:
                        longest_shift = max(shifts, key=calculate_shift_duration)
                        time, ward, venue = longest_shift
                        if venue not in exclusion_locations:
                            response = format_response(venue, date, longest_shift, is_urgent)
                            logger.info(f"Preparing to send response: {response}")
                            await asyncio.sleep(RESPONSE_DELAY)
                            await client.send_message(event.chat_id, response)
                            logger.info(f"Response sent after {RESPONSE_DELAY} seconds delay.")
                            message_count += 1
                        else:
                            logger.info("Excluded location, not responding.")
                    else:
                        logger.info("No valid shifts found, not responding.")
                else:
                    logger.info("Bot is inactive or no inclusion keyword found, not processing message.")
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

        await client.run_until_disconnected()

if __name__ == "__main__":
    if None in (fuzz, process, TelegramClient, load_dotenv):
        print("Error: Some required libraries are missing. Please install them and try again.")
    else:
        print("SSHJarvis is now running!")
        asyncio.run(main())
        print("SSHJarvis has stopped.")