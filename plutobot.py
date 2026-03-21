
import logging
from colorama import Fore, Style
import discord
from discord.ext import commands
import asyncio
import random
import os
import re
from datetime import datetime
import queue
import threading
import aiohttp
import sys
import requests
import signal

# ==================== CONFIGURATION ====================
TOKEN = ""  
PREFIX = "."

# Setup logging
logging.basicConfig(level=logging.INFO)

# Bot intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.presences = True
intents.message_content = True  # Required for reading message content
bot = commands.Bot(command_prefix=PREFIX, intents=intents, self_bot=True)

# ==================== GLOBAL VARIABLES ====================
deleted_messages = {}
edited_messages = {}
auto_reply_target_id = None
auto_reply_message = None
autoreact_enabled = False
autoreact_targets = set() 
autoreact_emoji = "👍"
autoreact_emoji_list = ["👍", "❤️", "😂", "😮", "😢", "😡"]
autoreact_emoji_rotation = False
autoreact_emoji_index = 0
superreact_enabled = False
superreact_targets = set()
superreact_emoji_list = ["👍", "❤️", "😂", "😮", "😢", "😡", "🔥", "💯", "⭐", "🎉"]
superreact_emoji_rotation = False
superreact_emoji_index = 0
chatpack_running = False
chatpack_task = None
chatpack_messages = []
chatpack_paused = False
afk_response_pending = False
spam_running = False
spam_task = None
user_note = ""
custom_status = None  
antiafk_enabled = True  
antiafk_secure_mode = True
killgc_running = False
killgc_task = None
killgc_names = []
antigc_enabled = False
antigc_message = "nah im good"
processed_antigc_channels = set()
status_task = None

# Command queue for thread communication
command_queue = queue.Queue()
command_responses = {}

# ========== PAGE SYSTEM HEADERS ==========
HEADERS = {
    "page1": """\u001b[2;31m
╔═════════════════════════════╗
║     REACTION COMMANDS       ║
╚═════════════════════════════╝\u001b[0m""",
    "page2": """\u001b[2;32m
╔═════════════════════════════╗
║     STATUS & PRESENCE       ║
╚═════════════════════════════╝\u001b[0m""",
    "page3": """\u001b[2;34m
╔═════════════════════════════╗
║    AUTOMATION & SPAM        ║
╚═════════════════════════════╝\u001b[0m""",
    "page4": """\u001b[2;35m
╔═════════════════════════════╗
║     UTILITY & TOOLS         ║
╚═════════════════════════════╝\u001b[0m""",
    "page5": """\u001b[2;36m
╔═════════════════════════════╗
║    INFORMATION COMMANDS     ║
╚═════════════════════════════╝\u001b[0m""",
    "page6": """\u001b[2;33m
╔═════════════════════════════╗
║    FUN & ENTERTAINMENT      ║
╚═════════════════════════════╝\u001b[0m""",
    "page7": """\u001b[2;91m
╔═════════════════════════════╗
║   DESTRUCTIVE & WEBHOOKS    ║
╚═════════════════════════════╝\u001b[0m""",
}

PAGES = {
    "page1": f"""{HEADERS['page1']}
\u001b[2;31m`.autoreact [@user] <emoji>`\u001b[0m – Auto-react to messages  
\u001b[2;31m`.addreact @user <emoji>`\u001b[0m – Add user to targets  
\u001b[2;31m`.removereact @user`\u001b[0m – Remove user from targets  
\u001b[2;31m`.stopreact`\u001b[0m – Stop auto-reacting  
\u001b[2;31m`.reactlist`\u001b[0m – Show current targets  
\u001b[2;31m`.reactrotate [on/off]`\u001b[0m – Toggle emoji rotation  
\u001b[2;31m`.reactemojis <emojis>`\u001b[0m – Set custom emoji list  
\u001b[2;31m`.superreact [@user]`\u001b[0m – Enable super-react (Nitro)  
\u001b[2;31m`.superreactlist`\u001b[0m – Show super-react targets  
\u001b[2;31m`.reactstatus`\u001b[0m – Show both systems status  
""",
    "page2": f"""{HEADERS['page2']}
\u001b[2;32m`.stream on/off <content>`\u001b[0m – Set streaming status  
\u001b[2;32m`.playing <text>`\u001b[0m – Set "Playing..." status  
\u001b[2;32m`.watching <text>`\u001b[0m – Set "Watching..." status  
\u001b[2;32m`.listening <text>`\u001b[0m – Set "Listening to..." status  
\u001b[2;32m`.customstatus <emoji> <text>`\u001b[0m – Set custom status  
\u001b[2;32m`.fakegame <text>`\u001b[0m – Set fake game status  
\u001b[2;32m`.clearstatus`\u001b[0m – Clear all status  
\u001b[2;32m`.statuscycle`\u001b[0m – Start status cycling from status.txt  
\u001b[2;32m`.statusstop`\u001b[0m – Stop status cycling  
""",
    "page3": f"""{HEADERS['page3']}
\u001b[2;34m`.ar @user <msg>`\u001b[0m – Auto-reply to user  
\u001b[2;34m`.arstop`\u001b[0m – Stop auto-replying  
\u001b[2;34m`.stam <msg>`\u001b[0m – Spam messages with counter  
\u001b[2;34m`.stamstop`\u001b[0m – Stop spamming  
\u001b[2;34m`.kill [channel_id]`\u001b[0m – Start chatpack  
\u001b[2;34m`.turbo [channel_id]`\u001b[0m – Ultra fast chatpack  
\u001b[2;34m`.stopkill [channel_id]`\u001b[0m – Stop chatpack  
\u001b[2;34m`.killgc [channel_id]`\u001b[0m – Group chat name changing  
\u001b[2;34m`.antiafk on/off`\u001b[0m – Toggle anti-AFK system  
\u001b[2;34m`.antigc <message>`\u001b[0m – Enable anti-GC  
""",
    "page4": f"""{HEADERS['page4']}
\u001b[2;35m`.snipe`\u001b[0m – Show last deleted message  
\u001b[2;35m`.editsnipe`\u001b[0m – Show last edited message  
\u001b[2;35m`.purge <amount>`\u001b[0m – Delete your messages  
\u001b[2;35m`.remind <sec> <msg>`\u001b[0m – Set a reminder  
\u001b[2;35m`.note <text>`\u001b[0m – Save a note  
\u001b[2;35m`.getnote`\u001b[0m – Get your saved note  
\u001b[2;35m`.prefix <new>`\u001b[0m – Change command prefix  
""",
    "page5": f"""{HEADERS['page5']}
\u001b[2;36m`.pfp <@user/user_id>`\u001b[0m – Show user's avatar  
\u001b[2;36m`.userinfo [@user]`\u001b[0m – Show user information  
\u001b[2;36m`.serverinfo`\u001b[0m – Show server info  
\u001b[2;36m`.ping`\u001b[0m – Show bot latency  
""",
    "page6": f"""{HEADERS['page6']}
\u001b[2;33m`.gayrate @user`\u001b[0m – Rate gayness (0-100%)  
\u001b[2;33m`.ppsize @user`\u001b[0m – Check pp size  
\u001b[2;33m`.simp @user`\u001b[0m – Check simp level  
""",
    "page7": f"""{HEADERS['page7']}
\u001b[2;91m`.nuke`\u001b[0m – Nuke entire server (DANGEROUS)  
\u001b[2;91m`.spamchannels <name>`\u001b[0m – Spam create channels  
\u001b[2;91m`.spamroles <name>`\u001b[0m – Spam create roles  
\u001b[2;91m`.deleteroles`\u001b[0m – Delete all server roles  
\u001b[2;91m`.deletechannels`\u001b[0m – Delete all channels  
\u001b[2;91m`.deletemojis`\u001b[0m – Delete all server emojis  
\u001b[2;91m`.deletewebhooks`\u001b[0m – Delete all webhooks  
\u001b[2;91m`.massban`\u001b[0m – Ban all server members  
\u001b[2;91m`.masskick`\u001b[0m – Kick all server members  
\u001b[2;91m`.dmall <msg>`\u001b[0m – DM all server members  
\u001b[2;91m`.whspam <url> <msg>`\u001b[0m – Spam webhook 20 times  
\u001b[2;91m`.whnuke <url> <msg>`\u001b[0m – Nuke webhook 50 times  
\u001b[2;91m`.whflood <url>`\u001b[0m – Flood webhook infinitely  
\u001b[2;91m`.whdelete <url>`\u001b[0m – Delete a webhook  
\u001b[2;91m`.whhook <name> <msg>`\u001b[0m – Send styled webhook message  
""",
}

bot.remove_command('help')

# ==================== HELPER FUNCTIONS ====================
def ensure_file_exists(filename, default_content=""):
    """Create file with default content if it doesn't exist"""
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(default_content)
        return True
    return False

# Create default files
ensure_file_exists("vanishwl.txt", "hello world\nthis is a test\npluto bot is cool\nrandom message here")
ensure_file_exists("killgc.txt", "PLUTO BOT\nDESTROYED\nBY PLUTO\nGET REKT\nLMAO")
ensure_file_exists("status.txt", "Playing PlutoBot\nWatching you\nListening to music\nStreaming Pluto")

# ==================== COMMAND QUEUE PROCESSOR ====================
async def process_command_queue():
    global chatpack_running, chatpack_task, chatpack_messages
    global killgc_running, killgc_task, killgc_names
    
    while True:
        try:
            if not command_queue.empty():
                cmd_data = command_queue.get_nowait()
                cmd_type = cmd_data['type']
                cmd_id = cmd_data['id']
                
                try:
                    if cmd_type == 'start_chatpack':
                        channel_id = cmd_data['channel_id']
                        filename = cmd_data['filename']
                        mode = cmd_data['mode']
                        
                        target_channel = bot.get_channel(channel_id)
                        if not target_channel:
                            command_responses[cmd_id] = f"❌ Channel {channel_id} not found!"
                            continue
                        
                        if not os.path.exists(filename):
                            ensure_file_exists(filename, "default message 1\ndefault message 2")
                        
                        with open(filename, 'r', encoding='utf-8') as f:
                            chatpack_messages = [line.strip() for line in f.readlines() if line.strip()]
                        
                        chatpack_running = True
                        chatpack_task = asyncio.create_task(chatpack_loop(target_channel, mode))
                        command_responses[cmd_id] = f"🔥 Chatpack started in {target_channel.name if hasattr(target_channel, 'name') else 'Unknown'}"
                        
                    elif cmd_type == 'start_killgc':
                        channel_id = cmd_data['channel_id']
                        filename = cmd_data['filename']
                        
                        target_channel = bot.get_channel(channel_id)
                        if not target_channel:
                            command_responses[cmd_id] = f"❌ Channel {channel_id} not found!"
                            continue
                        
                        if not (hasattr(target_channel, 'type') and str(target_channel.type) == 'group'):
                            command_responses[cmd_id] = f"❌ Channel {channel_id} is not a group chat!"
                            continue
                        
                        if not os.path.exists(filename):
                            ensure_file_exists(filename, "PLUTO\nDESTROYED\nBY PLUTO")
                        
                        with open(filename, 'r', encoding='utf-8') as f:
                            killgc_names = [line.strip() for line in f.readlines() if line.strip()]
                        
                        killgc_running = True
                        killgc_task = asyncio.create_task(killgc_loop(target_channel))
                        command_responses[cmd_id] = f"💀 Kill GC started in group chat (ID: {channel_id})"
                        
                except Exception as e:
                    command_responses[cmd_id] = f"❌ Error: {e}"
            
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Error in command queue processor: {e}")
            await asyncio.sleep(1)

# ==================== EVENTS ====================
@bot.event
async def on_ready():
    print('='*50)
    print(f"{Fore.MAGENTA}[+]PlutoBot successfully logged in as {Style.RESET_ALL} {bot.user}")
    print(f"{Fore.MAGENTA}[+]Guilds: {Style.RESET_ALL} {[g.name for g in bot.guilds]}")
    print(f'{Fore.MAGENTA}[+]User ID: {Style.RESET_ALL} {bot.user.id}')
    print(f'{Fore.MAGENTA}[+]Bot Status: {Style.RESET_ALL} Online')
    print(f'{Fore.MAGENTA}[+]Command Prefix: {Style.RESET_ALL} {bot.command_prefix}')
    print('='*50)
    
    # Start command queue processor
    asyncio.create_task(process_command_queue())

@bot.event
async def on_group_join(channel, user):
    global antigc_enabled, antigc_message, processed_antigc_channels
    
    if user.id != bot.user.id:
        return
    
    print(f"🔔 Group join detected! Channel ID: {channel.id}")
    
    if channel.id in processed_antigc_channels:
        print(f"⏭️ Skipping existing group chat: {channel.id}")
        return
    
    if antigc_enabled:
        try:
            processed_antigc_channels.add(channel.id)
            await channel.send(antigc_message)
            await asyncio.sleep(1.0)
            await channel.leave()
            print(f"✅ Left group chat: {channel.id}")
        except Exception as e:
            print(f"❌ Error in anti-GC: {e}")

@bot.event
async def on_private_channel_create(channel):
    global antigc_enabled, antigc_message, processed_antigc_channels
    
    if hasattr(channel, 'recipients') and len(channel.recipients) > 1:
        print(f"🔔 Private group channel detected! ID: {channel.id}")
        
        if channel.id in processed_antigc_channels:
            print(f"⏭️ Skipping existing group chat: {channel.id}")
            return
        
        if antigc_enabled:
            await asyncio.sleep(0.5)
            try:
                processed_antigc_channels.add(channel.id)
                await channel.send(antigc_message)
                await asyncio.sleep(1.0)
                await channel.leave()
                print(f"✅ Left private group chat: {channel.id}")
            except Exception as e:
                print(f"❌ Error in private channel anti-GC: {e}")

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    deleted_messages[channel_id] = {
        'content': message.content,
        'author': message.author,
        'timestamp': datetime.now(),
        'attachments': [att.url for att in message.attachments] if message.attachments else []
    }

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = before.channel.id
    edited_messages[channel_id] = {
        'before': before.content,
        'after': after.content,
        'author': before.author,
        'timestamp': datetime.now()
    }

@bot.event
async def on_message(message):
    global autoreact_enabled, autoreact_targets, autoreact_emoji, autoreact_emoji_index
    global superreact_enabled, superreact_targets, superreact_emoji_index
    global auto_reply_target_id, auto_reply_message
    global antiafk_enabled, antiafk_secure_mode
    global chatpack_paused, afk_response_pending, chatpack_running
    global antigc_enabled
    
    if message.author.bot and message.author != bot.user:
        return
    
    # Auto-react
    if autoreact_enabled and autoreact_targets and message.author.id in autoreact_targets:
        try:
            emoji_to_use = autoreact_emoji
            
            if autoreact_emoji_rotation:
                emoji_to_use = autoreact_emoji_list[autoreact_emoji_index]
                autoreact_emoji_index = (autoreact_emoji_index + 1) % len(autoreact_emoji_list)
            
            if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                emoji_id = emoji_to_use.split(':')[-1][:-1]
                emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                if emoji_obj:
                    await message.add_reaction(emoji_obj)
                else:
                    await message.add_reaction(emoji_to_use)
            else:
                await message.add_reaction(emoji_to_use)
        except:
            pass
    
    # Super-react
    if superreact_enabled and superreact_targets and message.author.id in superreact_targets:
        try:
            emoji_to_use = superreact_emoji_list[0]
            
            if superreact_emoji_rotation:
                emoji_to_use = superreact_emoji_list[superreact_emoji_index]
                superreact_emoji_index = (superreact_emoji_index + 1) % len(superreact_emoji_list)
            
            try:
                if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                    emoji_id = emoji_to_use.split(':')[-1][:-1]
                    emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                    if emoji_obj:
                        await message.add_reaction(emoji_obj, burst=True)
                    else:
                        await message.add_reaction(emoji_to_use, burst=True)
                else:
                    await message.add_reaction(emoji_to_use, burst=True)
            except:
                if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                    emoji_id = emoji_to_use.split(':')[-1][:-1]
                    emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                    if emoji_obj:
                        await message.add_reaction(emoji_obj)
                    else:
                        await message.add_reaction(emoji_to_use)
                else:
                    await message.add_reaction(emoji_to_use)
        except:
            pass
    
    # Auto-reply
    if auto_reply_target_id and message.author.id == auto_reply_target_id:
        await message.reply(auto_reply_message)
    
    # Anti-AFK
    if antiafk_enabled and message.author != bot.user:
        content = message.content.lower()
        original_content = message.content
        response_message = None
        
        is_mentioned = bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        content_mentions_us = (f'<@{bot.user.id}>' in message.content or 
                             f'<@!{bot.user.id}>' in message.content)
        
        if antiafk_secure_mode and not (is_mentioned or is_dm or content_mentions_us):
            return
        
        patterns = [
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+say\s+\[(.+?)\]', lambda m: m.group(1).strip().upper()),
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+say\s+([a-zA-Z0-9\s\'\"]+?)(?:\s*$)', lambda m: m.group(1).strip().upper()),
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+type\s+(.+?)(?:\s*$)', lambda m: m.group(1).strip()),
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+respond\s+(.+?)(?:\s*$)', lambda m: m.group(1).strip()),
            (r'(?:are\s+you\s+|u\s+)?(?:still\s+)?(?:here|active|awake|alive|present)\s*\?', 
             lambda m: random.choice(["yes", "here", "yep", "yeah", "yup", "present"])),
            (r'(?:type|say|send|write)\s+(.+?)\s+(?:if\s+)?(?:you\'?re\s+|ur\s+)?(?:here|active|awake|not\s+afk)', 
             lambda m: m.group(1).strip()),
            (r'respond\s+with\s+(.+?)(?:\s*$|\s+if)', lambda m: m.group(1).strip()),
            (r'if\s+(?:you\'?re\s+|ur\s+)?(?:not\s+)?(?:afk|here|active|awake),?\s+(?:type|say|send)\s+(.+?)(?:\s*$)', 
             lambda m: m.group(1).strip()),
            (r'(?:prove|show)\s+(?:you\'?re\s+|ur\s+)?(?:not\s+)?(?:afk|here|active|awake)(?:\s+(?:by\s+)?(?:typing|saying|sending)\s+(.+?))?(?:\s*$)', 
             lambda m: m.group(1).strip() if m.group(1) else random.choice(["HERE", "IM HERE", "YES IM HERE"])),
            (r'(?:(?:<@!?\d+>\s+)?\bafk\s+check\b(?!\s+(?:say|type|respond)))', 
             lambda m: random.choice(["HERE", "IM HERE", "not afk", "present"])),
        ]
        
        for pattern, response_func in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    response_message = response_func(match)
                    
                    suspicious_words = ["owner", "slave", "owns me", "my owner", "vanish", "daddy", "master"]
                    if any(word in response_message.lower() for word in suspicious_words) or len(response_message) > 100:
                        response_message = random.choice(["HERE", "IM HERE", "not afk"])
                    
                    break
                except:
                    continue
        
        if response_message:
            if chatpack_running:
                chatpack_paused = True
                afk_response_pending = True
            
            await asyncio.sleep(2.0)
            await message.channel.send(response_message)
            
            if chatpack_running and chatpack_paused:
                await asyncio.sleep(0.5)
                chatpack_paused = False
                afk_response_pending = False
    
    await bot.process_commands(message)

# ==================== UTILITY COMMANDS ====================
@bot.command()
async def snipe(ctx):
    if ctx.channel.id in deleted_messages:
        msg_data = deleted_messages[ctx.channel.id]
        content = msg_data['content']
        author = msg_data['author']
        await ctx.send(f"```Last deleted message:```\n{author}: {content}")
    else:
        await ctx.send("```No deleted messages to snipe```")
    await ctx.message.delete()

@bot.command()
async def editsnipe(ctx):
    if ctx.channel.id in edited_messages:
        msg_data = edited_messages[ctx.channel.id]
        old_content = msg_data['before']
        new_content = msg_data['after']
        author = msg_data['author']
        await ctx.send(f"```Last edited message:```\n{author}:\nBefore: {old_content}\nAfter: {new_content}")
    else:
        await ctx.send("```No edited messages to snipe.```")
    await ctx.message.delete()

# ==================== REACTION COMMANDS ====================
@bot.command()
async def autoreact(ctx, user: discord.User = None, *, emoji="👍"):
    global autoreact_enabled, autoreact_emoji, autoreact_targets
    
    if user is None:
        user = ctx.author
    
    if emoji.startswith('<') and emoji.endswith('>'):
        autoreact_emoji = emoji
    else:
        autoreact_emoji = emoji
    
    autoreact_targets.add(user.id)
    autoreact_enabled = True
    
    if user.id == ctx.author.id:
        await ctx.send(f"Auto-react enabled for your messages with {emoji} in all channels", delete_after=5)
    else:
        await ctx.send(f"Auto-react enabled for {user.display_name}'s messages with {emoji} in all channels", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def addreact(ctx, user: discord.User, *, emoji="👍"):
    global autoreact_targets, autoreact_emoji
    
    if emoji != "👍":
        autoreact_emoji = emoji
    
    autoreact_targets.add(user.id)
    await ctx.send(f"Added {user.display_name} to auto-react targets with {emoji}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def removereact(ctx, user: discord.User):
    global autoreact_targets
    
    if user.id in autoreact_targets:
        autoreact_targets.remove(user.id)
        await ctx.send(f"Removed {user.display_name} from auto-react targets", delete_after=5)
    else:
        await ctx.send(f"{user.display_name} is not in auto-react targets", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopreact(ctx):
    global autoreact_enabled, autoreact_targets
    autoreact_enabled = False
    autoreact_targets.clear()
    await ctx.send("Auto-react disabled and all targets cleared", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def reactlist(ctx):
    global autoreact_targets, autoreact_enabled, autoreact_emoji
    
    if not autoreact_enabled:
        await ctx.send("Auto-react is disabled", delete_after=5)
        await ctx.message.delete()
        return
    
    if not autoreact_targets:
        await ctx.send("No auto-react targets set", delete_after=5)
        await ctx.message.delete()
        return
    
    target_names = []
    for user_id in autoreact_targets:
        user = bot.get_user(user_id)
        if user:
            target_names.append(user.display_name)
        else:
            target_names.append(f"Unknown User ({user_id})")
    
    embed = discord.Embed(
        title="Auto-React Status",
        color=0x00ff00,
        description=f"**Emoji:** {autoreact_emoji}\n**Targets:** {', '.join(target_names)}"
    )
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

@bot.command()
async def reactrotate(ctx, action="toggle"):
    global autoreact_emoji_rotation
    
    if action.lower() == "on":
        autoreact_emoji_rotation = True
    elif action.lower() == "off":
        autoreact_emoji_rotation = False
    else:
        autoreact_emoji_rotation = not autoreact_emoji_rotation
    
    status = "enabled" if autoreact_emoji_rotation else "disabled"
    await ctx.send(f"Auto-react emoji rotation {status}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def reactemojis(ctx, *emojis):
    global autoreact_emoji_list
    
    if not emojis:
        current_emojis = " ".join(autoreact_emoji_list)
        await ctx.send(f"Current auto-react emojis: {current_emojis}", delete_after=10)
        await ctx.message.delete()
        return
    
    autoreact_emoji_list = list(emojis)
    emoji_display = " ".join(autoreact_emoji_list)
    await ctx.send(f"Auto-react emoji list updated: {emoji_display}", delete_after=5)
    await ctx.message.delete()

# ==================== SUPER-REACT COMMANDS ====================
@bot.command()
async def superreact(ctx, user: discord.User = None):
    global superreact_enabled, superreact_targets
    
    if user is None:
        user = ctx.author
    
    superreact_targets.add(user.id)
    superreact_enabled = True
    
    if user.id == ctx.author.id:
        await ctx.send(f"Super-react enabled for your messages with burst effect", delete_after=7)
    else:
        await ctx.send(f"Super-react enabled for {user.display_name}'s messages with burst effect", delete_after=7)
    await ctx.message.delete()

@bot.command()
async def addsuperreact(ctx, user: discord.User):
    global superreact_targets
    
    superreact_targets.add(user.id)
    await ctx.send(f"Added {user.display_name} to super-react targets", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def removesuperreact(ctx, user: discord.User):
    global superreact_targets
    
    if user.id in superreact_targets:
        superreact_targets.remove(user.id)
        await ctx.send(f"Removed {user.display_name} from super-react targets", delete_after=5)
    else:
        await ctx.send(f"{user.display_name} is not in super-react targets", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopsuperreact(ctx):
    global superreact_enabled, superreact_targets
    superreact_enabled = False
    superreact_targets.clear()
    await ctx.send("Super-react disabled and all targets cleared", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def superreactrotate(ctx, action="toggle"):
    global superreact_emoji_rotation
    
    if action.lower() == "on":
        superreact_emoji_rotation = True
    elif action.lower() == "off":
        superreact_emoji_rotation = False
    else:
        superreact_emoji_rotation = not superreact_emoji_rotation
    
    status = "enabled" if superreact_emoji_rotation else "disabled"
    await ctx.send(f"Super-react emoji rotation {status}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def superreactemojis(ctx, *emojis):
    global superreact_emoji_list
    
    if not emojis:
        current_emojis = " ".join(superreact_emoji_list)
        await ctx.send(f"Current super-react emojis: {current_emojis}", delete_after=10)
        await ctx.message.delete()
        return
    
    superreact_emoji_list = list(emojis)
    emoji_display = " ".join(superreact_emoji_list)
    await ctx.send(f"Super-react emoji list updated: {emoji_display}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def superreactlist(ctx):
    global superreact_targets, superreact_enabled, superreact_emoji_list, superreact_emoji_rotation
    
    if not superreact_enabled:
        await ctx.send("Super-react is disabled", delete_after=5)
        await ctx.message.delete()
        return
    
    if not superreact_targets:
        await ctx.send("No super-react targets set", delete_after=5)
        await ctx.message.delete()
        return
    
    target_names = []
    for user_id in superreact_targets:
        user = bot.get_user(user_id)
        if user:
            target_names.append(user.display_name)
        else:
            target_names.append(f"Unknown User ({user_id})")
    
    rotation_status = "On" if superreact_emoji_rotation else "Off"
    emoji_display = " ".join(superreact_emoji_list[:5])
    
    embed = discord.Embed(
        title="Super-React Status",
        color=0xff6600,
        description=f"**Emojis:** {emoji_display}\n**Rotation:** {rotation_status}\n**Targets:** {', '.join(target_names)}"
    )
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

@bot.command()
async def reactstatus(ctx):
    global autoreact_enabled, autoreact_targets, autoreact_emoji_rotation
    global superreact_enabled, superreact_targets, superreact_emoji_rotation
    
    autoreact_status = "✅ Enabled" if autoreact_enabled else "❌ Disabled"
    superreact_status = "✅ Enabled" if superreact_enabled else "❌ Disabled"
    
    embed = discord.Embed(
        title="React System Status",
        color=0x00ffff,
        description=f"""
        **Auto-React:**
        Status: {autoreact_status}
        Targets: {len(autoreact_targets)}
        
        **Super-React:**
        Status: {superreact_status}
        Targets: {len(superreact_targets)}
        """
    )
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

# ==================== AUTO-REPLY COMMANDS ====================
@bot.command()
async def ar(ctx, user: discord.User, *, message: str):
    global auto_reply_target_id, auto_reply_message
    auto_reply_target_id = user.id
    auto_reply_message = message
    await ctx.send(f"Auto-reply set for {user.mention}.", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def arstop(ctx):
    global auto_reply_target_id, auto_reply_message
    auto_reply_target_id = None
    auto_reply_message = None
    await ctx.send("Auto-reply stopped.", delete_after=3)
    await ctx.message.delete()

# ==================== AFK COMMANDS ====================
@bot.command()
async def afksecurity(ctx, mode: str = None):
    global antiafk_secure_mode, antiafk_enabled
    
    if mode is None:
        status = "SECURE" if antiafk_secure_mode else "OPEN"
        enabled_status = "ENABLED" if antiafk_enabled else "DISABLED"
        
        embed = discord.Embed(
            title="AFK Security Status", 
            color=0x00ff00 if antiafk_secure_mode else 0xff6600,
            description=f"**AFK System:** {enabled_status}\n**Security Mode:** {status}\n\n"
                       f"**Secure Mode:** Only responds when mentioned/DMed\n"
                       f"**Open Mode:** Responds to any AFK check\n\n"
                       f"Use `.afksecurity secure` or `.afksecurity open`"
        )
        await ctx.send(embed=embed, delete_after=15)
    
    elif mode.lower() == "secure":
        antiafk_secure_mode = True
        await ctx.send("🔒 AFK security set to SECURE mode", delete_after=5)
    
    elif mode.lower() == "open":
        antiafk_secure_mode = False
        await ctx.send("AFK security set to OPEN mode", delete_after=5)
    
    else:
        await ctx.send("Invalid mode. Use 'secure' or 'open'", delete_after=5)
    
    await ctx.message.delete()

@bot.command()
async def antiafk(ctx, toggle: str = None):
    global antiafk_enabled
    
    if toggle is None:
        status = "enabled" if antiafk_enabled else "disabled"
        await ctx.send(f"Anti-AFK is currently {status}. Use `.antiafk on` or `.antiafk off`", delete_after=5)
        await ctx.message.delete()
        return
    
    toggle = toggle.lower()
    if toggle == "on":
        antiafk_enabled = True
        await ctx.send("✅ Anti-AFK enabled", delete_after=5)
    elif toggle == "off":
        antiafk_enabled = False
        await ctx.send("❌ Anti-AFK disabled", delete_after=5)
    else:
        await ctx.send("Use `.antiafk on` or `.antiafk off`", delete_after=5)
    
    await ctx.message.delete()

# ==================== CHATPACK COMMANDS ====================
async def chatpack_loop(channel, mode="fast"):
    global chatpack_running, chatpack_messages, chatpack_paused, afk_response_pending
    
    if mode.lower() == "turbo":
        base_delay = 0.3
    elif mode.lower() == "safe":
        base_delay = 1.2
    else:
        base_delay = 0.6
    current_delay = base_delay
    consecutive_successes = 0
    rate_limit_hits = 0
    
    while chatpack_running and chatpack_messages:
        while chatpack_paused and afk_response_pending:
            await asyncio.sleep(0.1)
        
        if not chatpack_running:
            break
            
        try:
            message = random.choice(chatpack_messages)
            await channel.send(message)
            
            consecutive_successes += 1
            
            if consecutive_successes >= 5:
                current_delay = max(0.4, current_delay * 0.95)
                consecutive_successes = 0
            
            if rate_limit_hits > 0:
                rate_limit_hits -= 1
            
            await asyncio.sleep(current_delay + random.uniform(0.1, 0.3))
            
        except discord.HTTPException as e:
            consecutive_successes = 0
            
            if e.status == 429:
                rate_limit_hits += 1
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    await asyncio.sleep(retry_after + random.uniform(0.2, 0.8))
                else:
                    backoff_time = min(30, 2 ** rate_limit_hits + random.uniform(1, 3))
                    await asyncio.sleep(backoff_time)
                
                current_delay = min(3.0, base_delay * (1.5 ** rate_limit_hits))
            else:
                await asyncio.sleep(random.uniform(1, 2))
                
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(3)

@bot.command()
async def kill(ctx, target=None, filename="vanishwl.txt", mode="fast"):
    global chatpack_running, chatpack_task, chatpack_messages
    
    if chatpack_running:
        await ctx.send("already hoeing this nigga use .stopkill to stop it first", delete_after=5)
        await ctx.message.delete()
        return
    
    target_channel = None
    if target is None:
        target_channel = ctx.channel
    else:
        try:
            if target.isdigit():
                target_channel = bot.get_channel(int(target))
                if not target_channel:
                    await ctx.send(f"Channel with ID {target} not found!", delete_after=5)
                    await ctx.message.delete()
                    return
            else:
                filename = target
                target_channel = ctx.channel
        except:
            filename = target
            target_channel = ctx.channel
    
    if not os.path.exists(filename):
        ensure_file_exists(filename, "default message 1\ndefault message 2\npluto bot is here")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            chatpack_messages = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        await ctx.send(f"Error reading file: {e}", delete_after=5)
        await ctx.message.delete()
        return
    
    if not chatpack_messages:
        await ctx.send("No messages found in the file", delete_after=5)
        await ctx.message.delete()
        return
    
    chatpack_running = True
    chatpack_task = asyncio.create_task(chatpack_loop(target_channel, mode))
    await ctx.send(f"Chatpack started in {target_channel.name if hasattr(target_channel, 'name') else 'DM'} with {len(chatpack_messages)} messages (Mode: {mode})", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def turbo(ctx, target=None, filename="vanishwl.txt"):
    await kill(ctx, target, filename, "turbo")

@bot.command()
async def stopkill(ctx, target=None):
    global chatpack_running, chatpack_task
    
    if not chatpack_running:
        await ctx.send("Killing is not running", delete_after=5)
        await ctx.message.delete()
        return
    
    chatpack_running = False
    if chatpack_task:
        chatpack_task.cancel()
    
    await ctx.send("stopped hoeing this low tier faggot", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def unpause(ctx):
    global chatpack_paused, afk_response_pending, chatpack_running
    
    if not chatpack_running:
        await ctx.send("Chatpack is not running", delete_after=5)
        await ctx.message.delete()
        return
    
    if chatpack_paused:
        chatpack_paused = False
        afk_response_pending = False
        await ctx.send("✅ Chatpack unpaused and resumed", delete_after=5)
    else:
        await ctx.send("Chatpack is not paused", delete_after=5)
    
    await ctx.message.delete()

@bot.command()
async def killstatus(ctx):
    global chatpack_running, chatpack_paused, afk_response_pending, chatpack_messages
    
    if not chatpack_running:
        await ctx.send("❌ Chatpack is not running", delete_after=10)
        await ctx.message.delete()
        return
    
    status = "🔄 Running"
    if chatpack_paused:
        status = "⏸️ PAUSED"
    
    message_count = len(chatpack_messages) if chatpack_messages else 0
    
    embed = discord.Embed(
        title="Chatpack Status",
        color=0x00ff00 if not chatpack_paused else 0xffaa00,
        description=f"**Status:** {status}\n**Messages loaded:** {message_count}\n**Anti-AFK enabled:** {'✅' if antiafk_enabled else '❌'}"
    )
    
    if chatpack_paused:
        embed.add_field(name="Tip", value="Use `.unpause` to manually resume", inline=False)
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

# ==================== KILL GC COMMANDS ====================
async def killgc_loop(channel):
    global killgc_running, killgc_names
    
    while killgc_running and killgc_names:
        try:
            new_name = random.choice(killgc_names)
            await channel.edit(name=new_name)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    await asyncio.sleep(retry_after + random.uniform(0.1, 0.5))
                else:
                    await asyncio.sleep(random.uniform(3, 6))
            elif e.status == 403:
                break
            elif e.status == 400:
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(random.uniform(1, 3))
        except discord.NotFound:
            break
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(random.uniform(1, 3))

@bot.command()
async def killgc(ctx, target=None, filename="killgc.txt"):
    global killgc_running, killgc_task, killgc_names
    
    if killgc_running:
        await ctx.send("Kill GC is already running! Use .stopkillgc to stop it first.", delete_after=5)
        await ctx.message.delete()
        return
    
    target_channel = None
    if target is None:
        target_channel = ctx.channel
        if not (hasattr(ctx.channel, 'type') and str(ctx.channel.type) == 'group'):
            await ctx.send("❌ Current channel is not a group chat!", delete_after=5)
            await ctx.message.delete()
            return
    else:
        try:
            if target.isdigit():
                target_channel = bot.get_channel(int(target))
                if not target_channel:
                    await ctx.send(f"❌ Channel with ID {target} not found!", delete_after=5)
                    await ctx.message.delete()
                    return
                if not (hasattr(target_channel, 'type') and str(target_channel.type) == 'group'):
                    await ctx.send(f"❌ Channel {target} is not a group chat!", delete_after=5)
                    await ctx.message.delete()
                    return
            else:
                filename = target
                target_channel = ctx.channel
                if not (hasattr(ctx.channel, 'type') and str(ctx.channel.type) == 'group'):
                    await ctx.send("❌ Current channel is not a group chat!", delete_after=5)
                    await ctx.message.delete()
                    return
        except:
            filename = target
            target_channel = ctx.channel
            if not (hasattr(ctx.channel, 'type') and str(ctx.channel.type) == 'group'):
                await ctx.send("❌ Current channel is not a group chat!", delete_after=5)
                await ctx.message.delete()
                return
    
    if not os.path.exists(filename):
        ensure_file_exists(filename, "PLUTO\nDESTROYED\nBY PLUTO\nGET REKT\nLMAO")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            killgc_names = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        await ctx.send(f"Error reading file: {e}", delete_after=5)
        await ctx.message.delete()
        return
    
    if not killgc_names:
        await ctx.send("No names found in the file!", delete_after=5)
        await ctx.message.delete()
        return
    
    killgc_running = True
    killgc_task = asyncio.create_task(killgc_loop(target_channel))
    await ctx.send(f"✅ Kill GC started in group chat (ID: {target_channel.id}) with {len(killgc_names)} names", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopkillgc(ctx, target=None):
    global killgc_running, killgc_task
    
    if not killgc_running:
        await ctx.send("Kill GC is not running!", delete_after=5)
        await ctx.message.delete()
        return
    
    killgc_running = False
    if killgc_task:
        killgc_task.cancel()
    
    await ctx.send("Kill GC stopped", delete_after=5)
    await ctx.message.delete()

# ==================== ANTI-GC COMMANDS ====================
@bot.command()
async def antigc(ctx, *, message: str = "nah im good"):
    global antigc_enabled, antigc_message, processed_antigc_channels
    
    antigc_enabled = True
    antigc_message = message
    
    existing_groups = []
    for channel in bot.private_channels:
        if hasattr(channel, 'type') and str(channel.type) == 'group':
            processed_antigc_channels.add(channel.id)
            existing_groups.append(channel.id)
    
    await ctx.send(f"✅ Anti-GC enabled! Message: '{message}' (Ignoring {len(existing_groups)} existing group chats)", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopantigc(ctx):
    global antigc_enabled
    
    antigc_enabled = False
    await ctx.send("❌ Anti-GC disabled", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def testafk(ctx):
    global antiafk_enabled
    
    embed = discord.Embed(title="Anti-AFK Test & Info", color=0x00ff00 if antiafk_enabled else 0xff0000)
    
    status = "Enabled" if antiafk_enabled else "Disabled"
    embed.add_field(name="Status", value=status, inline=True)
    
    patterns = "`AFK CHECK SAY BANANA` → BANANA\n`AFK CHECK SAY [APPLE]` → APPLE\n`AFK CHECK` → random response\n`afk check say word` → WORD"
    embed.add_field(name="Supported Patterns", value=patterns, inline=False)
    
    embed.add_field(name="How it works", value="Bot detects AFK checks and responds automatically with the specified word or a random response", inline=False)
    
    if not antiafk_enabled:
        embed.add_field(name="⚠️ Note", value="Anti-AFK is currently disabled. Use `.antiafk on` to enable it.", inline=False)
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def testantigc(ctx):
    global antigc_enabled, antigc_message
    
    status = "✅ Enabled" if antigc_enabled else "❌ Disabled"
    
    is_group = False
    if hasattr(ctx.channel, 'type'):
        if str(ctx.channel.type) == 'group':
            is_group = True
    
    embed = discord.Embed(title="Anti-GC Status", color=0x00ff00 if antigc_enabled else 0xff0000)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Message", value=f"'{antigc_message}'" if antigc_enabled else "N/A", inline=True)
    embed.add_field(name="Current Channel Type", value=str(ctx.channel.type), inline=True)
    embed.add_field(name="Is Group Chat", value="Yes" if is_group else "No", inline=True)
    
    if hasattr(ctx.channel, 'recipients'):
        embed.add_field(name="Recipients Count", value=str(len(ctx.channel.recipients)), inline=True)
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

# ==================== SPAM COMMANDS ====================
@bot.command()
async def stam(ctx, *, message: str):
    global spam_running, spam_task
    
    if spam_running:
        await ctx.send("Spam is already running! Use .stamstop to stop it first.", delete_after=5)
        await ctx.message.delete()
        return
    
    spam_running = True
    spam_task = asyncio.create_task(spam_loop(ctx.channel, message))
    await ctx.send(f"Spam started with message: {message}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stamstop(ctx):
    global spam_running, spam_task
    
    if not spam_running:
        await ctx.send("Spam is not running!", delete_after=5)
        await ctx.message.delete()
        return
    
    spam_running = False
    if spam_task:
        spam_task.cancel()
    
    await ctx.send("Spam stopped", delete_after=5)
    await ctx.message.delete()

async def spam_loop(channel, message):
    global spam_running
    counter = 1
    
    while spam_running:
        try:
            await channel.send(f"{message} [{counter}]")
            counter += 1
            await asyncio.sleep(random.uniform(1.5, 3.0))
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    await asyncio.sleep(retry_after + 2)
                else:
                    await asyncio.sleep(10)
            else:
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(3)

# ==================== INFO COMMANDS ====================
@bot.command(name='pfp', aliases=['avatar'])
async def avatarUrl(ctx, user_info=None):
    if ctx.message.mentions:
        user = ctx.message.mentions[0]
    elif user_info and user_info.isdigit():
        try:
            user_id = int(user_info)
            user = await bot.fetch_user(user_id)
        except ValueError:
            await ctx.send("Please provide a valid user ID.")
            await ctx.message.delete()
            return
        except discord.NotFound:
            await ctx.send("User not found. Please provide a valid user ID.")
            await ctx.message.delete()
            return
    else:
        user = ctx.author

    if user:
        await ctx.send(user.display_avatar.url)
    else:
        await ctx.send("User not found.")
    
    await ctx.message.delete()

@bot.command()
async def userinfo(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    
    try:
        display_name = user.display_name
    except AttributeError:
        display_name = user.name
    
    try:
        thumbnail_url = user.display_avatar.url
    except AttributeError:
        thumbnail_url = "https://cdn.discordapp.com/embed/avatars/0.png"
    
    embed = discord.Embed(
        title=f"{display_name}'s Information",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    
    await ctx.send(embed=embed, delete_after=30)
    await ctx.message.delete()

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    if not guild:
        await ctx.send("This command can only be used in servers", delete_after=5)
        await ctx.message.delete()
        return
    
    embed = discord.Embed(
        title=f"{guild.name} Information",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    
    await ctx.send(embed=embed, delete_after=30)
    await ctx.message.delete()

@bot.command()
async def ping(ctx):
    try:
        latency = round(bot.latency * 1000)
        channel_type = "Server" if ctx.guild else "DM"
        guild_name = ctx.guild.name if ctx.guild else "Direct Message"
        
        await ctx.send(f"```🏓 Pong! {latency}ms\n📍 {channel_type}: {guild_name}\n✅ Commands working!```", delete_after=10)
        await ctx.message.delete()
    except Exception as e:
        print(f"❌ Ping failed: {e}")

# ==================== STATUS COMMANDS ====================
@bot.command()
async def stream(ctx, action: str = None, *, stream_content: str = None):
    try:
        if action == 'off':
            await bot.change_presence(activity=None)
            await ctx.send("```Stream turned off.```", delete_after=10)
        elif action == 'on' and stream_content:
            await bot.change_presence(activity=discord.Streaming(name=stream_content, url='https://twitch.tv/pluto'))
            await ctx.send(f"```Streaming status set to: {stream_content}```", delete_after=10)
        else:
            await ctx.send("```Invalid command. Use `.stream on <content>` or `.stream off`.```", delete_after=10)
    except Exception as e:
        await ctx.send(f"```An error occurred: {e}```", delete_after=10)
    finally:
        await ctx.message.delete()

@bot.command()
async def playing(ctx, *, text):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"Playing status set to: **{text}**")
    await ctx.message.delete()

@bot.command()
async def watching(ctx, *, text):
    activity = discord.Activity(type=discord.ActivityType.watching, name=text)
    await bot.change_presence(activity=activity)
    await ctx.send(f"Watching status set to: **{text}**")
    await ctx.message.delete()

@bot.command()
async def listening(ctx, *, text):
    activity = discord.Activity(type=discord.ActivityType.listening, name=text)
    await bot.change_presence(activity=activity)
    await ctx.send(f"Listening to: **{text}**")
    await ctx.message.delete()

@bot.command()
async def clearstatus(ctx):
    await bot.change_presence(activity=None)
    await ctx.send("Status cleared.")
    await ctx.message.delete()

@bot.command()
async def statuscycle(ctx):
    global status_task
    if status_task:
        await ctx.send("Status cycling already running.")
        await ctx.message.delete()
        return

    async def cycle():
        global status_task
        try:
            while True:
                if os.path.exists("status.txt"):
                    with open("status.txt", "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                await bot.change_presence(activity=discord.Game(name=line))
                                await asyncio.sleep(10)
                await asyncio.sleep(1)
        except:
            pass

    status_task = bot.loop.create_task(cycle())
    await ctx.send("Status cycling started from `status.txt`.")
    await ctx.message.delete()

@bot.command()
async def statusstop(ctx):
    global status_task
    if status_task:
        status_task.cancel()
        status_task = None
        await ctx.send("Status cycling stopped")
    else:
        await ctx.send("No status cycling running.")
    await ctx.message.delete()

@bot.command()
async def customstatus(ctx, emoji, *, text):
    try:
        await bot.change_presence(activity=discord.CustomActivity(name=text, emoji=emoji))
        await ctx.send(f"Custom status set to: {emoji} {text}")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def fakegame(ctx, *, text):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"Fake game status set: **{text}**")
    await ctx.message.delete()

# ==================== DESTRUCTIVE COMMANDS ====================
@bot.command()
async def nuke(ctx):
    await ctx.send("Pluto is now nuking this server...")
    try:
        for ch in ctx.guild.channels:
            try:
                await ch.delete()
                await asyncio.sleep(0.3)
            except: pass
        for r in ctx.guild.roles:
            try:
                await r.delete()
                await asyncio.sleep(0.3)
            except: pass
        for i in range(10):
            await ctx.guild.create_text_channel(f"pluto-{random.randint(100,999)}")
        await ctx.send("Pluto nuke finished.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def spamchannels(ctx, *, name="pluto"):
    await ctx.send(f"Spamming channels with name: `{name}`")
    try:
        for _ in range(20):
            await ctx.guild.create_text_channel(name)
            await asyncio.sleep(0.2)
        await ctx.send("done")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def spamroles(ctx, *, name="pluto"):
    await ctx.send(f"Spamming roles: `{name}`")
    try:
        for _ in range(20):
            await ctx.guild.create_role(name=name)
            await asyncio.sleep(0.2)
        await ctx.send("Roles created.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def deleteroles(ctx):
    await ctx.send("Deleting all roles...")
    try:
        for role in ctx.guild.roles:
            if role != ctx.guild.default_role:
                try:
                    await role.delete()
                    await asyncio.sleep(0.2)
                except: pass
        await ctx.send("Roles wiped.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def deletechannels(ctx):
    await ctx.send("Deleting all channels...")
    try:
        for ch in ctx.guild.channels:
            try:
                await ch.delete()
                await asyncio.sleep(0.2)
            except: pass
        await ctx.send("Channels deleted.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def deletemojis(ctx):
    await ctx.send("Deleting all emojis...")
    try:
        for emoji in ctx.guild.emojis:
            try:
                await emoji.delete()
                await asyncio.sleep(0.2)
            except: pass
        await ctx.send("Emojis wiped.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def deletewebhooks(ctx):
    await ctx.send("Deleting all webhooks...")
    try:
        for channel in ctx.guild.text_channels:
            try:
                hooks = await channel.webhooks()
                for hook in hooks:
                    await hook.delete()
                    await asyncio.sleep(0.1)
            except: pass
        await ctx.send("Webhooks deleted.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def massban(ctx):
    await ctx.send("Banning all users...")
    try:
        for member in ctx.guild.members:
            try:
                await member.ban(reason="pluto")
                await asyncio.sleep(0.3)
            except: pass
        await ctx.send("Mass ban finished.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def masskick(ctx):
    await ctx.send("Kicking everyone...")
    try:
        for member in ctx.guild.members:
            try:
                await member.kick(reason="pluto")
                await asyncio.sleep(0.3)
            except: pass
        await ctx.send("Everyone kicked.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def dmall(ctx, *, msg):
    await ctx.send("DMing everyone in the server...")
    try:
        for member in ctx.guild.members:
            if not member.bot:
                try:
                    await member.send(msg)
                    await asyncio.sleep(1)
                except: pass
        await ctx.send("DMs sent.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

# ==================== WEBHOOK COMMANDS ====================
@bot.command()
async def whspam(ctx, url, *, msg):
    await ctx.send(f"Spamming webhook with: `{msg}`")
    try:
        for _ in range(20):
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"content": msg})
            await asyncio.sleep(0.3)
        await ctx.send("Webhook spam done.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def whdelete(ctx, url):
    try:
        async with aiohttp.ClientSession() as session:
            await session.delete(url)
        await ctx.send("Webhook deleted.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def whnuke(ctx, url, *, msg):
    await ctx.send(f"Nuking webhook with `{msg}`...")
    try:
        for _ in range(50):
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"content": msg})
            await asyncio.sleep(0.1)
        await ctx.send("Webhook nuked.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    await ctx.message.delete()

@bot.command()
async def whflood(ctx, url):
    await ctx.send("Webhook flooding started.")
    try:
        while True:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"content": "pluto flooding"})
            await asyncio.sleep(0.1)
    except:
        pass

@bot.command()
async def whhook(ctx, name, *, msg):
    embed = discord.Embed(title=name, description=msg, color=0x00ffcc)
    async with aiohttp.ClientSession() as session:
        await session.post("YOUR_WEBHOOK_HERE", json={
            "username": name,
            "embeds": [embed.to_dict()]
        })
    await ctx.message.delete()

# ==================== FUN COMMANDS ====================
@bot.command()
async def gayrate(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{user.mention} is **{percent}%** gay 🌈")
    await ctx.message.delete()

@bot.command()
async def ppsize(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    length = random.randint(0, 15)
    bar = "8" + "=" * length + "D"
    await ctx.send(f"{user.mention}'s PP size:\n`{bar}`")
    await ctx.message.delete()

@bot.command()
async def simp(ctx, user: discord.User = None):
    if user is None:
        user = ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{user.mention} is **{percent}%** simp 💀")
    await ctx.message.delete()

# ==================== UTILITY COMMANDS ====================
@bot.command()
async def purge(ctx, amount: int):
    if amount <= 0:
        await ctx.send("Please provide a valid number!", delete_after=5)
        await ctx.message.delete()
        return
    
    deleted = 0
    async for message in ctx.channel.history(limit=amount * 2):
        if message.author == bot.user and deleted < amount:
            try:
                await message.delete()
                deleted += 1
                await asyncio.sleep(0.5)
            except: pass
    
    await ctx.send(f"Deleted {deleted} of your messages", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def remind(ctx, seconds: int, *, message: str):
    if seconds <= 0:
        await ctx.send("Please provide a valid number of seconds!", delete_after=5)
        await ctx.message.delete()
        return
    
    await ctx.send(f"Reminder set for {seconds} seconds: {message}", delete_after=5)
    await ctx.message.delete()
    
    await asyncio.sleep(seconds)
    embed = discord.Embed(
        title="⏰ Reminder",
        description=message,
        color=0xffff00,
        timestamp=datetime.now()
    )
    await ctx.send(embed=embed)

@bot.command()
async def note(ctx, *, text: str):
    global user_note
    user_note = text
    await ctx.send(f"Note saved: {text}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def getnote(ctx):
    global user_note
    if not user_note:
        await ctx.send("No note saved!", delete_after=5)
    else:
        embed = discord.Embed(
            title="📝 Your Note",
            description=user_note,
            color=0x00ff00
        )
        await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def prefix(ctx, new_prefix: str = None):
    global PREFIX, bot
    
    if new_prefix is None:
        await ctx.send(f"Current prefix: `{bot.command_prefix}`", delete_after=5)
        await ctx.message.delete()
        return
    
    if len(new_prefix) > 3:
        await ctx.send("Prefix must be 3 characters or less!", delete_after=5)
        await ctx.message.delete()
        return
    
    old_prefix = bot.command_prefix
    bot.command_prefix = new_prefix
    await ctx.send(f"Prefix changed from `{old_prefix}` to `{new_prefix}`", delete_after=5)
    await ctx.message.delete()

# ==================== HELP COMMANDS ====================
@bot.command()
async def help(ctx):
    await menu(ctx)

@bot.command()
async def menu(ctx):
    try:
        menu_text = """```ansi
 _   _  ___   _   _ _____ _____ _   _        
| | | |/ _ \ | \ | |_   _/  ___| | | |       
| | | / /_\ \|  \| | | | \ `--.| |_| |       
| | | |  _  || . ` | | |  `--. \  _  |       
\ \_/ / | | || |\  |_| |_/\__/ / | | |       
 \___/\_| |_/\_| \_/\___/\____/\_| |_/                                                                                               
 _____ _____ _     ____________  _____ _____ 
/  ___|  ___| |    |  ___| ___ \|  _  |_   _|
\ `--.| |__ | |    | |_  | |_/ /| | | | | |  
 `--. \  __|| |    |  _| | ___ \| | | | | |  
/\__/ / |___| |____| |   | |_/ /\ \_/ / | |  
\____/\____/\_____/\_|   \____/  \___/  \_/  
\u001b[2;31m Page 1 — Reaction Commands
\u001b[2;32m Page 2 — Status & Presence
\u001b[2;33m Page 3 — Chatpacking & Spamming
\u001b[2;34m Page 4 — Utility & Tools
\u001b[2;35m Page 5 — Information Commands
\u001b[2;36m Page 6 — Fun & Entertainment
\u001b[2;91m Page 7 — Destructive & Webhooks
\u001b[2;37mType .page<number> to open a section.
\u001b[2;36mExample: .page1 or .page7
```"""
        
        if ctx.guild:
            await asyncio.sleep(1.5)
            
        await ctx.send(menu_text, delete_after=45)
        
        if ctx.guild:
            await asyncio.sleep(0.8)
            
        await ctx.message.delete()
        
    except Exception as e:
        print(f"Error in menu command: {e}")
        try:
            await ctx.send("**PlutoBot Commands**\n\n"
                          "Use `.page1` through `.page7` for command categories", 
                          delete_after=15)
            await ctx.message.delete()
        except:
            pass

# ==================== PAGE COMMANDS ====================
@bot.command()
async def page1(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page1']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 1: {e}")
    await ctx.message.delete()

@bot.command()
async def page2(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page2']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 2: {e}")
    await ctx.message.delete()

@bot.command()
async def page3(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page3']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 3: {e}")
    await ctx.message.delete()

@bot.command()
async def page4(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page4']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 4: {e}")
    await ctx.message.delete()

@bot.command()
async def page5(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page5']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 5: {e}")
    await ctx.message.delete()

@bot.command()
async def page6(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page6']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 6: {e}")
    await ctx.message.delete()

@bot.command()
async def page7(ctx):
    try:
        await ctx.send(f"```ansi\n{PAGES['page7']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 7: {e}")
    await ctx.message.delete()

@bot.command()
async def allcommands(ctx):
    try:
        part1 = """```PlutoBot - All Commands (Part 1/4):
.autoreact <emoji>         - Auto-react to your messages
.addreact @user <emoji>    - Add user to auto-react targets
.removereact @user         - Remove user from auto-react targets
.stopreact                 - Stop auto-reacting
.reactlist                 - Show current auto-react targets
.reactrotate [on/off]      - Toggle emoji rotation
.reactemojis <emojis>      - Set custom emoji list
.superreact [@user]        - Enable super-react
.addsuperreact @user       - Add user to super-react targets
.removesuperreact @user    - Remove from super-react targets
.stopsuperreact            - Stop super-reacting
.superreactlist            - Show current super-react targets
.superreactrotate [on/off] - Toggle emoji rotation
.superreactemojis <emojis> - Set custom emoji list
.reactstatus               - Show status of both react systems
.ar @user <msg>            - Auto-reply to a user
.arstop                    - Stop auto-replying```"""

        part2 = """```PlutoBot - All Commands (Part 2/4):
.stam <msg>                - Spam a message with a counter
.stamstop                  - Stop spamming
.kill [channel_id]         - Start chatpack in channel
.turbo [channel_id]        - Ultra fast chatpack
.stopkill [channel_id]     - Stop chatpack
.killgc [channel_id]       - Start group chat name changing
.stopkillgc                - Stop GC name changing
.snipe                     - Show last deleted message
.editsnipe                 - Show last edited message```"""

        part3 = """```PlutoBot - All Commands (Part 3/4):
.nuke                      - Nuke entire server
.spamchannels [name]       - Spam create channels
.spamroles [name]          - Spam create roles
.deletechannels            - Delete all channels
.deleteroles               - Delete all roles
.deletemojis               - Delete all emojis
.deletewebhooks            - Delete all webhooks
.massban                   - Ban all members
.masskick                  - Kick all members
.dmall <msg>               - DM all members```"""

        part4 = """```PlutoBot - All Commands (Part 4/4):
.gayrate @user             - Rate how gay someone is
.ppsize @user              - Check someone's pp size
.simp @user                - Check simp level
.ping                      - Show bot latency
.pfp <@user/user_id>       - Show user's avatar
.userinfo [@user]          - Show user info
.serverinfo                - Show server info
.purge <amount>            - Delete your messages
.remind <sec> <msg>        - Set a reminder
.note <text>               - Save a note
.getnote                   - Get your note
.antiafk on/off            - Toggle anti-AFK system
.afksecurity [secure/open] - Toggle AFK security mode
.testafk                   - Test anti-AFK patterns
.antigc <message>          - Enable anti-GC with message
.stopantigc                - Disable anti-GC
.testantigc                - Test anti-GC status
.prefix <new>              - Change command prefix
.stream on/off <content>   - Set streaming status
.playing <text>            - Set playing status
.watching <text>           - Set watching status
.listening <text>          - Set listening status
.customstatus <status>     - Set custom status
.clearstatus               - Clear custom status
.statuscycle               - Start status cycling
.statusstop                - Stop status cycling```"""

        await ctx.send(part1, delete_after=45)
        await asyncio.sleep(0.5)
        await ctx.send(part2, delete_after=45)
        await asyncio.sleep(0.5)
        await ctx.send(part3, delete_after=45)
        await asyncio.sleep(0.5)
        await ctx.send(part4, delete_after=45)
        
        await ctx.message.delete()
        
    except Exception as e:
        print(f"Error in allcommands: {e}")
        await ctx.send("Command list temporarily unavailable. Use .menu instead.", delete_after=10)
        await ctx.message.delete()

# ==================== SYSTEM COMMANDS ====================
@bot.command()
async def restart(ctx):
    await ctx.send("🔄 Restarting bot...", delete_after=3)
    await ctx.message.delete()
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.command()
async def shutdown(ctx):
    await ctx.send("💀 Shutting down...", delete_after=2)
    await ctx.message.delete()
    sys.exit(0)

# ==================== COMMAND PROMPT INTERFACE ====================
def command_prompt_interface():
    global antiafk_enabled, antiafk_secure_mode, chatpack_running, chatpack_messages
    global killgc_running, killgc_names, antigc_enabled, autoreact_targets
    global auto_reply_target_id, auto_reply_message, user_note
    
    print("\n" + "="*50)
    print("🖥️  COMMAND PROMPT INTERFACE ACTIVE")
    print("📝 Type 'help' for available commands")
    print("="*50)
    
    while True:
        try:
            cmd = input("\n[SELFBOT]> ").strip().lower()
            
            if cmd == "help":
                print("""
🖥️ COMMAND PROMPT COMMANDS:
├── status                    - Show bot status and info
├── afk on/off                - Toggle anti-AFK system
├── security                  - Toggle AFK security mode
├── kill <channel_id> [file]  - Start chatpack in specific channel
├── turbo <channel_id> [file] - Start turbo chatpack
├── kill stop                 - Stop chatpack
├── killgc <channel_id> [file] - Start GC name killing
├── killgc stop               - Stop GC name killing
├── antigc on/off             - Toggle anti-GC system  
├── stats                     - Show running statistics
├── restart                   - Restart the bot
├── exit                      - Close the bot
└── help                      - Show this menu
                """)
                
            elif cmd == "status":
                print(f"""
📊 BOT STATUS:
├── Bot User: {bot.user if bot.user else 'Not logged in'}
├── Anti-AFK: {'✅ Enabled' if antiafk_enabled else '❌ Disabled'}
├── AFK Security: {'🔒 Secure' if antiafk_secure_mode else '⚠️ Open'}
├── Chatpack: {'🔥 Running' if chatpack_running else '💤 Stopped'}
├── Anti-GC: {'✅ Enabled' if antigc_enabled else '❌ Disabled'}
└── Prefix: {bot.command_prefix}
                """)
                
            elif cmd == "afk on":
                antiafk_enabled = True
                print("✅ Anti-AFK enabled via command prompt")
                
            elif cmd == "afk off":
                antiafk_enabled = False
                print("❌ Anti-AFK disabled via command prompt")
                
            elif cmd == "security":
                antiafk_secure_mode = not antiafk_secure_mode
                mode = "🔒 Secure" if antiafk_secure_mode else "⚠️ Open"
                print(f"🔄 AFK security mode: {mode}")
                
            elif cmd.startswith("kill ") and not cmd.endswith("stop"):
                parts = cmd.split()
                if len(parts) >= 2:
                    try:
                        channel_id = int(parts[1])
                        filename = parts[2] if len(parts) > 2 else "vanishwl.txt"
                        mode = "turbo" if cmd.startswith("turbo") else "fast"
                        
                        if chatpack_running:
                            print("⚠️ Chatpack already running! Stop it first.")
                            continue
                        
                        if not os.path.exists(filename):
                            ensure_file_exists(filename, "default message 1\ndefault message 2")
                        
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        command_queue.put({
                            'type': 'start_chatpack',
                            'id': cmd_id,
                            'channel_id': channel_id,
                            'filename': filename,
                            'mode': mode
                        })
                        
                        import time
                        start_time = time.time()
                        while cmd_id not in command_responses and time.time() - start_time < 5:
                            time.sleep(0.1)
                        
                        if cmd_id in command_responses:
                            response = command_responses.pop(cmd_id)
                            print(response)
                        else:
                            print("❌ Timeout waiting for response")
                        
                    except ValueError:
                        print("❌ Invalid channel ID! Use: kill <channel_id> [filename]")
                    except Exception as e:
                        print(f"❌ Error starting chatpack: {e}")
                else:
                    print("❌ Usage: kill <channel_id> [filename]")
            
            elif cmd.startswith("turbo "):
                parts = cmd.split()
                if len(parts) >= 2:
                    try:
                        channel_id = int(parts[1])
                        filename = parts[2] if len(parts) > 2 else "vanishwl.txt"
                        
                        if chatpack_running:
                            print("⚠️ Chatpack already running! Stop it first.")
                            continue
                        
                        if not os.path.exists(filename):
                            ensure_file_exists(filename, "default message 1\ndefault message 2")
                        
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        command_queue.put({
                            'type': 'start_chatpack',
                            'id': cmd_id,
                            'channel_id': channel_id,
                            'filename': filename,
                            'mode': 'turbo'
                        })
                        
                        import time
                        start_time = time.time()
                        while cmd_id not in command_responses and time.time() - start_time < 5:
                            time.sleep(0.1)
                        
                        if cmd_id in command_responses:
                            response = command_responses.pop(cmd_id)
                            print(f"🚀 {response}")
                        else:
                            print("❌ Timeout waiting for response")
                        
                    except ValueError:
                        print("❌ Invalid channel ID! Use: turbo <channel_id> [filename]")
                    except Exception as e:
                        print(f"❌ Error starting turbo chatpack: {e}")
                else:
                    print("❌ Usage: turbo <channel_id> [filename]")
                    
            elif cmd == "kill stop":
                if chatpack_running:
                    chatpack_running = False
                    if chatpack_task:
                        chatpack_task.cancel()
                    print("🛑 Chatpack stopped")
                else:
                    print("💤 Chatpack is not running")
            
            elif cmd.startswith("killgc ") and not cmd.endswith("stop"):
                parts = cmd.split()
                if len(parts) >= 2:
                    try:
                        channel_id = int(parts[1])
                        filename = parts[2] if len(parts) > 2 else "killgc.txt"
                        
                        if killgc_running:
                            print("⚠️ Kill GC already running! Stop it first.")
                            continue
                        
                        target_channel = bot.get_channel(channel_id)
                        if not target_channel:
                            print(f"❌ Channel {channel_id} not found!")
                            continue
                        
                        if not (hasattr(target_channel, 'type') and str(target_channel.type) == 'group'):
                            print(f"❌ Channel {channel_id} is not a group chat!")
                            continue
                        
                        if not os.path.exists(filename):
                            ensure_file_exists(filename, "PLUTO\nDESTROYED\nBY PLUTO")
                        
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        command_queue.put({
                            'type': 'start_killgc',
                            'id': cmd_id,
                            'channel_id': channel_id,
                            'filename': filename
                        })
                        
                        import time
                        start_time = time.time()
                        while cmd_id not in command_responses and time.time() - start_time < 5:
                            time.sleep(0.1)
                        
                        if cmd_id in command_responses:
                            response = command_responses.pop(cmd_id)
                            print(response)
                        else:
                            print("❌ Timeout waiting for response")
                        
                    except ValueError:
                        print("❌ Invalid channel ID! Use: killgc <channel_id> [filename]")
                    except Exception as e:
                        print(f"❌ Error starting Kill GC: {e}")
                else:
                    print("❌ Usage: killgc <channel_id> [filename]")
            
            elif cmd == "killgc stop":
                if killgc_running:
                    killgc_running = False
                    if killgc_task:
                        killgc_task.cancel()
                    print("🛑 Kill GC stopped")
                else:
                    print("💤 Kill GC is not running")
                    
            elif cmd == "antigc on":
                antigc_enabled = True
                print("✅ Anti-GC enabled")
                
            elif cmd == "antigc off":
                antigc_enabled = False
                print("❌ Anti-GC disabled")
                
            elif cmd == "stats":
                autoreply_status = f"User ID: {auto_reply_target_id}" if auto_reply_target_id else "None"
                print(f"""
📈 STATISTICS:
├── Autoreact Targets: {len(autoreact_targets)}
├── Autoreply Target: {autoreply_status}
├── Chatpack Messages: {len(chatpack_messages)}
├── Kill GC Names: {len(killgc_names)}
└── Current Note: {user_note if user_note else 'None'}
                """)
                
            elif cmd == "restart":
                print("🔄 Restarting bot...")
                os.execl(sys.executable, sys.executable, *sys.argv)
                
            elif cmd == "exit":
                print("👋 Shutting down...")
                sys.exit(0)
                
            elif cmd == "":
                continue
                
            else:
                print("❓ Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n👋 Command prompt closed")
            break
        except Exception as e:
            print(f"❌ Error in command prompt: {e}")

# ==================== RUN THE BOT ====================
if __name__ == "__main__":
    try:
        # Get token from environment variable
        TOKEN = os.environ.get('DISCORD_TOKEN', '')
        
        if not TOKEN:
            print("❌ ERROR: No token found! Please set DISCORD_TOKEN environment variable.")
            print("🔧 For Discord Bot Hosting.net, add DISCORD_TOKEN in Environment Variables")
            sys.exit(1)
        
        # Start command prompt interface in separate thread
        cmd_thread = threading.Thread(target=command_prompt_interface, daemon=True)
        cmd_thread.start()
        
        bot.run(TOKEN, bot=False)
        
    except discord.LoginFailure:
        print("❌ ERROR: Invalid token! Please check your Discord token.")
        sys.exit(1)
    except discord.HTTPException as e:
        print(f"❌ HTTP Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
