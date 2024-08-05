### Apology

I apologize that I didn't push the code to github from the start. I had done several improvements to sshJarvis from the initial code that I had submitted. I have updated the README.md file to reflect the changes that I have made to sshJarvis. I will start making regular optimization to sshJarvis and push the code to github. I hope I can consider the code that I have pushed to github. Thank you.

# sshjarvis

sshJarivs is a shift picking automation for telegram that has optimized algorithm based on the location/time/urgency with flexibility to adjust the shift picking according to your peference

# Shift Picker

## Overview

sshJarvis is an automated bot designed to streamline the process of picking up available shifts in fast-paced group chats. It monitors messages in specified Telegram chats, identifies shift availability announcements, and automatically responds to claim the longest available shift.

## Features

- Monitors multiple Telegram chats simultaneously
- Parses shift information from unstructured text messages
- Identifies shifts based on configurable keywords and locations
- Prioritizes urgent and ASAP shifts
- Automatically responds to claim the longest available shift
- Customizable response delay to mimic human behavior
- Easy activation/deactivation through chat commands

## Technologies Used

- Python 3.x
- Telethon: Telegram client library
- asyncio: For asynchronous programming
- fuzzywuzzy: For fuzzy string matching
- zoneinfo: For handling time zones

## How It Works

1. **Chat Monitoring**: The bot connects to specified Telegram chats using the Telethon library.

2. **Message Parsing**: When a new message is received, the bot checks for inclusion keywords that indicate shift availability.

3. **Information Extraction**: If a relevant message is found, the bot parses the message to extract:

   - Date of the shift
   - Venue/Location
   - Available shift times
   - Urgency status

4. **Shift Selection**: The bot identifies the longest available shift from the parsed information.

5. **Response Generation**: A response message is crafted based on the extracted information, following a predefined format.

6. **Automated Reply**: The bot sends the response message to the chat, effectively claiming the shift.

## Key Components

- `parse_shift_message()`: Extracts shift information from raw message text.
- `format_response()`: Generates a properly formatted response for shift claiming.
- `calculate_shift_duration()`: Determines the duration of a given shift.
- `get_longest_shift()`: Identifies the longest shift from a list of available shifts.
- `fuzzy_match()`: Performs fuzzy string matching to identify locations despite potential typos or variations.

## Configuration

The bot can be customized through several variables:

- `inclusion_keywords`: List of phrases that indicate shift availability.
- `inclusion_locations`: List of venues where shifts are accepted.
- `exclusion_locations`: List of venues to ignore.
- `relevant_roles`: List of job roles the bot should respond to.
- `chat_names`: List of Telegram chat names to monitor.
- `RESPONSE_DELAY`: Time delay before sending a response (to mimic human behavior).

## Usage

1. Set up the required API credentials (`api_id` and `api_hash`) for Telegram.
2. Configure the bot settings (keywords, locations, etc.) as needed.
3. Run the script to start the bot.
4. In the configured "state" chat, send "namaste" to activate the bot or "bye" to deactivate it.

## Future Improvements

- Implement a database to store shift history and prevent duplicate responses.
- Add more sophisticated natural language processing for better message parsing.
- Develop a web interface for easy configuration and monitoring.
- Implement multi-user support with individual preferences.

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/sshresthh/sshjarvis.git
   cd sshjarvis
   ```

2. Create a virtual environment:

   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```python
   pip install python-dotenv telethon fuzzywuzzy python-dateutil
   ```

## Configuration

1. Create a `.env.local` file in the project root with your Telegram API credentials:

   ```
   TELEGRAM_API_ID=your_api_id_here
   TELEGRAM_API_HASH=your_api_hash_here
   ```

2. Customize the bot settings in the script:
   - `inclusion_keywords`: List of phrases that indicate shift availability
   - `inclusion_locations`: List of venues where shifts are accepted
   - `exclusion_locations`: List of venues to ignore
   - `relevant_roles`: List of job roles the bot should respond to
   - `chat_names`: List of Telegram chat names to monitor

## Usage

1. Activate the virtual environment:

   ```
   source venv/bin/activate
   ```

2. Run the script:
   ```
   python3 sshjarvis.py
   ```

---

# Running SSHJarvis 24/7 on Google Cloud Platform

This guide explains how to run your SSHJarvis bot continuously on a Google Cloud Platform (GCP) VM instance using `tmux`.

## Initial Setup

### 1. Set up your GCP VM Instance

- Create a new VM instance in GCP if you haven't already.
- Ensure Python 3.x is installed on your instance.

### 2. Install Required Packages

SSH into your VM instance and run:

```bash
sudo apt update
sudo apt install tmux python3-pip
pip3 install python-dotenv telethon fuzzywuzzy python-Levenshtein
```

---

## Running SSHJarvis Using `tmux`

### 1. Create a New `tmux` Session

```bash
tmux new -s sshjarvis
```

### 2. Run Your Bot

Inside the `tmux` session:

```bash
python3 sshjarvis.py
```

### 3. Detach from the `tmux` Session

Press `Ctrl + B`, then `D`. Your bot will continue running in the background.

### 4. Exit SSH (Optional)

You can now safely exit your SSH session. The bot will keep running.

---

## Managing Your Bot

### Checking Bot Status

1. SSH into your VM instance
2. List `tmux` sessions:
   ```bash
   tmux ls
   ```
3. Reattach to your session:
   ```bash
   tmux attach -t sshjarvis
   ```

### Stopping the Bot

1. Reattach to the `tmux` session
2. Stop the Python script (Ctrl + C)
3. Exit the `tmux` session:
   ```bash
   exit
   ```

### Killing the `tmux` Session

If needed, you can forcefully terminate the session:

```bash
tmux kill-session -t sshjarvis
```

---

## Best Practices

1. **Logging**: Implement comprehensive logging in your bot script to track its activities and any errors.

2. **Monitoring**: Set up monitoring alerts in GCP to notify you of high CPU usage or other issues.

3. **Updates**: Regularly update your bot script and dependencies. When updating:

   - Reattach to the `tmux` session
   - Stop the current bot instance
   - Pull the latest code (if using version control)
   - Restart the bot

4. **Security**:

   - Keep your `.env.rosana` file secure and never commit it to version control.
   - Regularly update your VM instance and all installed packages.

5. **Backup**: Regularly backup your bot script and any important data.

## Troubleshooting

- If the bot crashes, reattach to the `tmux` session and check the output for error messages.
- Ensure your GCP firewall settings allow necessary outbound connections for the bot to function.
- If `tmux` sessions persist after reboots, causing issues, you can clear all sessions with:
  ```bash
  tmux kill-server
  ```

Remember to monitor your GCP usage to stay within free tier limits or your budget if using paid services.

---

## Conclusion

##### sshJarvis demonstrates the power of automation in solving real-world scheduling challenges. By leveraging asyncio for efficient chat monitoring and employing clever parsing techniques, this bot significantly reduces the manual effort required in the shift-picking process.
