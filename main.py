import os
import subprocess
import traceback
import sys
import json
import asyncio
import socket
import psutil
import time
import datetime
import contextlib
import cryptg
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.functions.channels import EditAdminRequest, EditBannedRequest, LeaveChannelRequest
from telethon.tl.types import ChatAdminRights, ChatBannedRights
from telethon import types, functions

from config import string, api_id, api_hash, USER_ID

natsu = TelegramClient(StringSession(string), api_id, api_hash)
start_time = time.time()
message_info_file = 'message_info.json'

def is_authorized(user_id):
    return user_id == USER_ID

@natsu.on(events.NewMessage(pattern=r'^help$'))
async def help_command(event):
    if not is_authorized(event.sender_id):
        return

    help_message = """
- `ping`: Check the Natsu's response time.
- `systeminfo`: Get system information (network, disk, CPU, uptime).
- `reload`: Reload the Natsu.
- `speedtest`: Run internet speed test.
- `listgroups`: List all groups and channels the Natsu is in.
- `ban [username|ID]`: Ban a user from the chat.
- `unban [username|ID]`: Unban a user from the chat.
- `kick [username|ID]`: Kick a user from the chat.
- `kickme [group_id]`: Leave the current group or a specified group.
- `mute [username|ID] <duration>[mhd]`: Mute a user for a specified duration (m for minutes, h for hours, d for days) or indefinitely using 'forever'.
- `unmute [username|ID]`: Unmute a user.
- `promote [username|ID]`: Promote a user to admin.
- `demote [username|ID]`: Demote a user from admin.
- `admintitle [username|ID] <title>`: Set a custom admin title for a user.
- `whois [username|ID]`: Get user info.
- `pin`: Pin a message (requires a reply to the message you want to pin).
- `unpin`: Unpin the replied message.
- `del`: Delete the replied message.
- `purge [username|ID]`: Purge all messages from a user.
- `$ <command>`: Execute a shell command.
- `> <expression>`: Evaluate a Python expression.
- `exec <code>`: Execute Python code.
"""
    await event.reply(help_message, parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^\$'))
async def shell_command(event):
    if not is_authorized(event.sender_id):
        return
    command = event.raw_text[1:]
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.decode() or result.stderr.decode() or "Command executed successfully with no output."
    await event.reply(f"**Shell Output:**\n```{output}```", parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^>'))
async def eval_command(event):
    if not is_authorized(event.sender_id):
        return

    code = event.raw_text[1:].strip()

    if event.is_reply:
        reply_message = await event.get_reply_message()
        code = reply_message.message.strip()

    local_vars = {"natsu": natsu, "event": event}

    try:
        result = eval(code, globals(), local_vars)
        if asyncio.iscoroutine(result):
            result = await result
        await event.reply(f"**Eval Result:**\n```{result}```", parse_mode='markdown')
    except SyntaxError:
        try:
            exec(
                f"async def __eval_function():\n"
                + '\n'.join(f"    {line}" for line in code.splitlines()),
                globals(), local_vars
            )
            result = await local_vars['__eval_function']()
            await event.reply(f"**Exec Result:**\n```{result}```", parse_mode='markdown')
        except Exception as e:
            await event.reply(f"**Exec Error:**\n```{traceback.format_exception_only(type(e), e)[0]}```", parse_mode='markdown')
    except Exception as e:
        await event.reply(f"**Eval Error:**\n```{traceback.format_exception_only(type(e), e)[0]}```", parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^whois(?: (.+))?$'))
async def whois(event):
    if not is_authorized(event.sender_id):
        return
    
    input_data = event.pattern_match.group(1)
    user = None
    
    try:
        if event.is_reply:
            reply_message = await event.get_reply_message()
            user = await natsu.get_entity(reply_message.sender_id)
        elif input_data:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                username = input_data.lstrip('@')
                user = await natsu.get_entity(username)
        else:
            await event.reply("Please provide a valid username or ID.", parse_mode='markdown')
            return
        
        if user is None:
            await event.reply("Error: No user found.", parse_mode='markdown')
            return
        
        bot_status = "Yes" if user.bot else "No"

        user_id = user.id
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        username = f"@{user.username}" if user.username else "-"
        
        status = "Unknown"
        if isinstance(user.status, types.UserStatusOnline):
            status = "Online"
        elif isinstance(user.status, types.UserStatusOffline):
            status = f"Offline (Last seen: {user.status.was_online.strftime('%Y-%m-%d %H:%M:%S')})"
        elif isinstance(user.status, types.UserStatusRecently):
            status = "Recently"
        elif isinstance(user.status, types.UserStatusLastWeek):
            status = "Last week"
        elif isinstance(user.status, types.UserStatusLastMonth):
            status = "Last month"

        common_chats = await natsu(functions.messages.GetCommonChatsRequest(user_id=user.id, max_id=0, limit=100))
        common_chats_count = len(common_chats.chats)

        profile_photos_count = 0
        photos = await natsu(functions.photos.GetUserPhotosRequest(user_id=user.id, offset=0, max_id=0, limit=1))
        if isinstance(photos, types.photos.Photos):
            profile_photos_count = len(photos.photos)
        elif isinstance(photos, types.photos.PhotosSlice):
            profile_photos_count = photos.count

        verified = "Yes" if user.verified else "No"

        restricted = "Yes" if user.restricted else "No"

        user_info = f"""
**Detailed User Info:**
- ID: `{user_id}`
- First Name: {first_name}
- Last Name: {last_name}
- Username: {username}
- Status: {status}
- Bot: {bot_status}
- Verified: {verified}
- Restricted: {restricted}
- Common Chats: {common_chats_count}
- Profile Photos: {profile_photos_count}
- Permanent Link: [User Link](tg://user?id={user_id})
"""
        
        profile_pic_path = None
        try:
            profile_pic_path = await natsu.download_profile_photo(user.id, "profile_pic.jpg")
        except Exception:
            pass
        
        if profile_pic_path:
            await natsu.send_file(event.chat_id, profile_pic_path, caption=user_info, reply_to=event.id, parse_mode='markdown')
            os.remove(profile_pic_path)
        else:
            await event.reply(user_info, reply_to=event.id, parse_mode='markdown')
    
    except Exception as e:
        await event.reply(f"Error: {str(e)}", reply_to=event.id, parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^systeminfo$'))
async def system_info(event):
    if not is_authorized(event.sender_id):
        return

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    public_ip = subprocess.run(["curl", "ifconfig.me"], stdout=subprocess.PIPE).stdout.decode().strip()
    
    usage = psutil.disk_usage('/')
    disk_info = f"""
**Disk Usage:**
- Total: {usage.total // (1024 ** 3)} GB
- Used: {usage.used // (1024 ** 3)} GB
- Free: {usage.free // (1024 ** 3)} GB
- Percent Used: {usage.percent}%
"""
    
    cpu_count = psutil.cpu_count(logical=False)
    cpu_logical_count = psutil.cpu_count(logical=True)
    cpu_usage = psutil.cpu_percent(percpu=True)
    cpu_info = f"**CPU Info:**\n- Cores: {cpu_count} physical, {cpu_logical_count} logical\n"
    for i, perc in enumerate(cpu_usage):
        cpu_info += f"- Core {i + 1}: {perc}% usage"
    
    virtual_mem = psutil.virtual_memory()
    memory_info = f"""
**Memory Usage:**
- Total: {virtual_mem.total // (1024 ** 3)} GB
- Used: {virtual_mem.used // (1024 ** 3)} GB
- Free: {virtual_mem.available // (1024 ** 3)} GB
- Percent Used: {virtual_mem.percent}%
"""

    interfaces = psutil.net_if_addrs()
    net_info = "**Network Interfaces:**\n"
    for interface, addresses in interfaces.items():
        for address in addresses:
            if address.family == socket.AF_INET:
                net_info += f"  - {interface}: IP {address.address}\n"
            elif address.family == psutil.AF_LINK:
                net_info += f"  - {interface}: MAC {address.address}\n"

    current_time = time.time()
    uptime_seconds = round(current_time - start_time)
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    
    sys_info = f"""
**System Info:**
- Hostname: {hostname}
- Local IP: {local_ip}
- Public IP: {public_ip}
{disk_info}
{cpu_info}
{memory_info}
{net_info}
**Uptime:**
- Natsu Uptime: {uptime_str}
"""
    
    await event.reply(sys_info, parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^ping$'))
async def ping(event):
    if not is_authorized(event.sender_id):
        return
    
    start = time.time()
    message = await event.reply("Pinging...")
    end = time.time()
    
    ping_time = round((end - start) * 1000, 2)
    await message.edit(f"**Pong!**\nResponse time: {ping_time} ms")

@natsu.on(events.NewMessage(pattern=r'^exec (.+)$'))
async def exec_command(event):
    if not is_authorized(event.sender_id):
        return

    code = event.pattern_match.group(1)
    
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            exec(code, globals(), locals())
            exec_output = output.getvalue()
        except Exception as e:
            exec_output = f"**Exec Error:**\n{traceback.format_exception_only(type(e), e)[0]}"

    if not exec_output:
        exec_output = "Code executed successfully with no output."
        
    await event.reply(f"**Exec Result:**\n```{exec_output}```", parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^ban(?: (.+))?$'))
async def ban_user(event):
    if not is_authorized(event.sender_id):
        return
    
    input_data = event.pattern_match.group(1)
    user = None

    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            ban_rights = ChatBannedRights(until_date=None, view_messages=True)
            await natsu(EditBannedRequest(event.chat_id, user.id, ban_rights))
            await event.reply(f"User {user.first_name} has been banned.")
        except Exception as e:
            await event.reply(f"Failed to ban user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^unban(?: (.+))?$'))
async def unban_user(event):
    if not is_authorized(event.sender_id):
        return
    
    input_data = event.pattern_match.group(1)
    user = None
    
    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            unban_rights = ChatBannedRights(until_date=None, view_messages=False)
            await natsu(EditBannedRequest(event.chat_id, user.id, unban_rights))
            await event.reply(f"User {user.first_name} has been unbanned.")
        except Exception as e:
            await event.reply(f"Failed to unban user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^kick(?: (.+))?$'))
async def kick_user(event):
    if not is_authorized(event.sender_id):
        return
    
    input_data = event.pattern_match.group(1)
    user = None
    
    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            await natsu.kick_participant(event.chat_id, user.id)
            await event.reply(f"User {user.first_name} has been kicked.")
        except Exception as e:
            await event.reply(f"Failed to kick user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^kickme(?: (\d+))?$'))
async def kickme(event):
    group_id = event.pattern_match.group(1)
    if group_id:
        try:
            group_id = int(group_id)
        except ValueError:
            return
    else:
        group_id = event.chat_id
    
    try:
        await natsu(LeaveChannelRequest(group_id))
    except Exception as e:
        pass

@natsu.on(events.NewMessage(pattern=r'^mute(?: (.+))? (\d+|forever)([mhd])?$'))
async def mute_user(event):
    if not is_authorized(event.sender_id):
        return

    input_data = event.pattern_match.group(1)
    duration = event.pattern_match.group(2)
    unit = event.pattern_match.group(3)
    user = None

    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        if duration == 'forever':
            until_date = None
        elif unit:
            if unit == 'm':
                until_date = datetime.datetime.now() + datetime.timedelta(minutes=int(duration))
            elif unit == 'h':
                until_date = datetime.datetime.now() + datetime.timedelta(hours=int(duration))
            elif unit == 'd':
                until_date = datetime.datetime.now() + datetime.timedelta(days=int(duration))
            else:
                await event.reply("Invalid time format. Use m (minutes), h (hours), or d (days).")
                return
        else:
            await event.reply("No time unit specified. Use m (minutes), h (hours), or d (days).")
            return
        
        try:
            mute_rights = ChatBannedRights(until_date=until_date, send_messages=True)
            await natsu(EditBannedRequest(event.chat_id, user.id, mute_rights))
            if until_date:
                time_str = f"{duration} {unit}"
            else:
                time_str = "forever"
            await event.reply(f"User {user.first_name} has been muted for {time_str}.")
        except Exception as e:
            await event.reply(f"Failed to mute user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^unmute(?: (.+))?$'))
async def unmute_user(event):
    if not is_authorized(event.sender_id):
        return
    
    input_data = event.pattern_match.group(1)
    user = None
    
    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            unmute_rights = ChatBannedRights(until_date=None, send_messages=False)
            await natsu(EditBannedRequest(event.chat_id, user.id, unmute_rights))
            await event.reply(f"User {user.first_name} has been unmuted.")
        except Exception as e:
            await event.reply(f"Failed to unmute user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^pin$'))
async def pin_message(event):
    if not is_authorized(event.sender_id):
        return
    
    if event.is_reply:
        reply_message = await event.get_reply_message()
        try:
            await natsu(UpdatePinnedMessageRequest(event.chat_id, reply_message.id, silent=True))
        except Exception as e:
            print(f"Failed to pin message: {str(e)}")

@natsu.on(events.NewMessage(pattern=r'^unpin$'))
async def unpin_message(event):
    if not is_authorized(event.sender_id):
        return

    if event.is_reply:
        reply_message = await event.get_reply_message()
        try:
            await natsu(UpdatePinnedMessageRequest(event.chat_id, reply_message.id, unpin=True))
        except Exception as e:
            print(f"Failed to unpin message: {str(e)}")

@natsu.on(events.NewMessage(pattern=r'^speedtest$'))
async def speedtest_command(event):
    if not is_authorized(event.sender_id):
        return

    processing_message = await event.reply("Running speedtest... Please wait.")

    try:
        result = subprocess.run(['speedtest-cli', '--json'], capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        download_speed = data['download'] / 1_000_000
        upload_speed = data['upload'] / 1_000_000
        ping = data['ping']

        speedtest_result = f"""
**Speedtest Results:**
- Download Speed: {download_speed:.2f} Mbps
- Upload Speed: {upload_speed:.2f} Mbps
- Ping: {ping} ms
"""
        await processing_message.edit(speedtest_result, parse_mode='markdown')

    except Exception as e:
        await processing_message.edit(f"**Error running speedtest:**\n```{traceback.format_exc()}```", parse_mode='markdown')

@natsu.on(events.NewMessage(pattern=r'^promote(?: (.+))?$'))
async def promote_user(event):
    if not is_authorized(event.sender_id):
        return

    input_data = event.pattern_match.group(1)
    user = None
    
    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            admin_rights = ChatAdminRights(
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=False
            )
            await natsu(EditAdminRequest(event.chat_id, user.id, admin_rights, 'Admin'))
            await event.reply(f"User {user.first_name} has been promoted to admin.")
        except Exception as e:
            await event.reply(f"Failed to promote user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^demote(?: (.+))?$'))
async def demote_user(event):
    if not is_authorized(event.sender_id):
        return

    input_data = event.pattern_match.group(1)
    user = None
    
    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            no_rights = ChatAdminRights(
                change_info=False,
                post_messages=False,
                edit_messages=False,
                delete_messages=False,
                ban_users=False,
                invite_users=False,
                pin_messages=False,
                add_admins=False
            )
            await natsu(EditAdminRequest(event.chat_id, user.id, no_rights, ''))
            await event.reply(f"User {user.first_name} has been demoted.")
        except Exception as e:
            await event.reply(f"Failed to demote user: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^admintitle (.+?) (.+)$'))
async def admintitle(event):
    if not is_authorized(event.sender_id):
        return

    try:
        input_data = event.pattern_match.group(1)
        new_title = event.pattern_match.group(2)

        if input_data.isdigit():
            user = await natsu.get_entity(int(input_data))
        else:
            user = await natsu.get_entity(input_data.lstrip('@'))

        if user:
            try:
                admin_rights = ChatAdminRights(
                    change_info=True,
                    post_messages=True,
                    edit_messages=True,
                    delete_messages=True,
                    ban_users=True,
                    invite_users=True,
                    pin_messages=True,
                    add_admins=False
                )
                await natsu(EditAdminRequest(event.chat_id, user.id, admin_rights, new_title))
                await event.reply(f"Title for user {user.first_name} has been set to '{new_title}'.")
            except Exception as e:
                await event.reply(f"Failed to set title: {str(e)}")
        else:
            await event.reply("User not found.")
    except Exception as e:
        await event.reply(f"Error processing command: {str(e)}")

@natsu.on(events.NewMessage(pattern=r'^del$'))
async def delete_replied_message(event):
    if not is_authorized(event.sender_id):
        return

    if event.is_reply:
        reply_message = await event.get_reply_message()
        try:
            await reply_message.delete()
            await event.delete()
        except Exception as e:
            pass

@natsu.on(events.NewMessage(pattern=r'^purge(?: (.+))?$'))
async def purge_user_messages(event):
    if not is_authorized(event.sender_id):
        return

    input_data = event.pattern_match.group(1)
    user = None

    if event.is_reply:
        reply_message = await event.get_reply_message()
        user = await natsu.get_entity(reply_message.sender_id)
    elif input_data:
        try:
            if input_data.isdigit():
                user = await natsu.get_entity(int(input_data))
            else:
                user = await natsu.get_entity(input_data.lstrip('@'))
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            return

    if user:
        try:
            async for message in natsu.iter_messages(event.chat_id, from_user=user.id):
                await message.delete()
            await event.reply(f"Purged all messages from {user.first_name}.")
        except Exception as e:
            await event.reply(f"Failed to purge messages: {str(e)}")
    else:
        await event.reply("User not found.")

@natsu.on(events.NewMessage(pattern=r'^listgroups$'))
async def list_groups(event):
    if not is_authorized(event.sender_id):
        return

    processing_message = await event.reply("Processing... Please wait.")

    try:
        dialogs = await natsu.get_dialogs()
        group_list = []

        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                try:
                    participants = await natsu.get_participants(dialog)
                    total_members = len(participants)
                except Exception:
                    total_members = "Unknown"

                group_list.append(f"- **{dialog.name}** (ID: `{dialog.id}`, Members: {total_members})")

        if group_list:
            group_list_str = "\n".join(group_list)
            result_message = f"**Groups List:**\n{group_list_str}"
        else:
            result_message = "No groups found."

        await processing_message.edit(result_message, parse_mode='markdown')
    
    except Exception as e:
        await processing_message.edit(f"Error: {str(e)}")

@natsu.on(events.NewMessage(pattern=r'^reload$'))
async def reload_command(event):
    if not is_authorized(event.sender_id):
        return
    try:
        chat_entity = await event.get_chat()
        if os.path.exists(message_info_file):
            with open(message_info_file, 'r') as f:
                message_info = json.load(f)
            try:
                await natsu.delete_messages(chat_entity, message_info['message_id'])
            except Exception as e:
                print(f"Failed to delete previous reload message: {e}")
            os.remove(message_info_file)
        
        message = await natsu.send_message(chat_entity, "**Reloading...**", parse_mode='markdown')
        with open(message_info_file, 'w') as f:
            json.dump({'chat_id': event.chat_id, 'message_id': message.id, 'stage': 'reloading'}, f)
        
        await event.delete()

        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        await event.reply(f"**Error during reload:**\n```{traceback.format_exc()}```", parse_mode='markdown')

async def edit_reload_message():
    if os.path.exists(message_info_file):
        with open(message_info_file, 'r') as f:
            message_info = json.load(f)
        try:
            chat_entity = await natsu.get_input_entity(message_info['chat_id'])
            current_message = await natsu.get_messages(chat_entity, ids=message_info['message_id'])

            if message_info.get('stage') == 'reloading':
                new_text = "**Reload successful**"
                new_message = await natsu.edit_message(chat_entity, message_info['message_id'], text=new_text, parse_mode='markdown')
                
                message_info['stage'] = 'successful'
                with open(message_info_file, 'w') as f:
                    json.dump(message_info, f)
                
                natsu.loop.create_task(final_edit_reload_message(chat_entity, new_message.id))
            else:
                print("Reload message has already been updated.")

        except ValueError:
            await natsu.send_message(message_info['chat_id'], "Reload completed.")
        except Exception as e:
            print(f"Unexpected error occurred: {e}")

async def final_edit_reload_message(chat_entity, message_id):
    await asyncio.sleep(2)
    try:
        new_text = "**Reloaded!!**"
        new_message = await natsu.edit_message(chat_entity, message_id, text=new_text, parse_mode='markdown')
        await asyncio.sleep(5)
        await natsu.delete_messages(chat_entity, new_message.id)
        os.remove(message_info_file)
    except Exception as e:
        print(f"Error in final edit: {e}")

async def preload_entities():
    await natsu.get_dialogs()

with natsu:
    natsu.loop.run_until_complete(preload_entities())
    natsu.loop.run_until_complete(edit_reload_message())
    natsu.run_until_disconnected()