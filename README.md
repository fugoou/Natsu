## Prerequisites

- Python 3.7+
- Telethon library
- Other dependencies (see `requirements.txt`)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/fugoou/Natsu.git
   cd Natsu
   ```

2. Install the required dependencies:
   ```
   pip3 install -r requirements.txt
   ```

3. Set up config.py
   - Obtain your `api_id` and `api_hash` from https://my.telegram.org
   - Obtain your `string` from [String Session](https://telegram.tools/session-string-generator#telethon)
   - `USER_ID` your telegram ID

4. Run the Natsu:
   ```
   python3 main.py
   ```

## Usage

Once the Natsu is running, you can use the following commands in any Telegram chat:

| Command | Description |
| --- | --- |
| `ping` | Check the Natsu's response time. |
| `systeminfo` | Get system information (network, disk, CPU, uptime). |
| `reload` | Reload the Natsu. |
| `speedtest` | Run internet speed test. |
| `listgroups` | List all groups and channels the Natsu is in. |
| `ban [username or ID]` | Ban a user from the chat. |
| `unban [username or ID]` | Unban a user from the chat. |
| `kick [username or ID]` | Kick a user from the chat. |
| `kickme [group_id]` | Leave the current group or a specified group. |
| `mute [username or ID] <duration>[mhd]` | Mute a user for a specified duration (m for minutes, h for hours, d for days) or indefinitely using 'forever'. |
| `unmute [username or ID]` | Unmute a user. |
| `promote [username or ID]` | Promote a user to admin. |
| `demote [username or ID]` | Demote a user from admin. |
| `admintitle [username or ID] <title>` | Set a custom admin title for a user. |
| `whois [username or ID]` | Get user info. |
| `pin` | Pin a message (requires a reply to the message you want to pin). |
| `unpin` | Unpin the replied message. |
| `del` | Delete the replied message. |
| `purge [username or ID]` | Purge all messages from a user. |
| `$ <command>` | Execute a shell command. |
| `> <expression>` | Evaluate a Python expression. |
| `exec <code>` | Execute Python code. |

## Disclaimer

This userbot is meant for educational and personal use only. Misuse of this bot may violate Telegram's Terms of Service. Use responsibly and at your own risk.
