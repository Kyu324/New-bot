import discord
from discord.ext import commands
import asyncio
import os
import json
from datetime import datetime, timedelta
import uuid
from pymongo import MongoClient
import logging
import re
import random
from typing import Optional, List, Dict, Any
import aiohttp
import httpx
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.environ.get('DISCORD_BOT_TOKEN', 'MTE2MjA1MzM3OTMxMzM4MTUyOA.Gqbogw.-VgCiUDpRBRHYRj6LOON2HIRcDfXKu7CorjqYw')
APPLICATION_ID = os.environ.get('DISCORD_APP_ID', '1162053379313381528')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '8ebf508a6ce04f47821b7fd21e7ae5e4')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'discord_bot_db')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
servers_collection = db.servers
commands_collection = db.commands
users_collection = db.users
warnings_collection = db.warnings
economy_collection = db.economy

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.presences = True

def get_prefix(bot, message):
    """Get server prefix"""
    if not message.guild:
        return "!"
    
    server_data = servers_collection.find_one({"server_id": str(message.guild.id)})
    if server_data:
        return server_data.get("prefix", "!")
    return "!"

# Bot setup
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    application_id=APPLICATION_ID,
    help_command=None
)

async def log_command(ctx, command_name, success=True, error=None):
    """Log command execution"""
    log_data = {
        "command_id": str(uuid.uuid4()),
        "server_id": str(ctx.guild.id) if ctx.guild else None,
        "user_id": str(ctx.author.id),
        "command_name": command_name,
        "parameters": {},
        "timestamp": datetime.utcnow(),
        "success": success,
        "error_message": str(error) if error else None
    }
    
    commands_collection.insert_one(log_data)

# Events
@bot.event
async def on_ready():
    """Bot ready event"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.watching, name="your server | !help")
    await bot.change_presence(activity=activity)
    
    # Initialize server data
    for guild in bot.guilds:
        server_data = {
            "server_id": str(guild.id),
            "server_name": guild.name,
            "prefix": "!",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        servers_collection.update_one(
            {"server_id": str(guild.id)},
            {"$set": server_data},
            upsert=True
        )

@bot.event
async def on_guild_join(guild):
    """Bot joins a guild"""
    logger.info(f'Joined guild: {guild.name} (ID: {guild.id})')
    
    # Initialize server data
    server_data = {
        "server_id": str(guild.id),
        "server_name": guild.name,
        "prefix": "!",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    servers_collection.update_one(
        {"server_id": str(guild.id)},
        {"$set": server_data},
        upsert=True
    )

@bot.event
async def on_guild_remove(guild):
    """Bot leaves a guild"""
    logger.info(f'Left guild: {guild.name} (ID: {guild.id})')

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    await log_command(ctx, ctx.command.name if ctx.command else "unknown", False, error)
    
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have permission to perform this action!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        logger.error(f"Command error: {error}")

# Helper functions
def has_permission(permission):
    """Check if user has permission"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.__getattribute__(permission):
            return True
        raise commands.MissingPermissions([permission])
    return commands.check(predicate)

def format_time(seconds):
    """Format time duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    elif seconds < 86400:
        return f"{seconds//3600}h {(seconds%3600)//60}m"
    else:
        return f"{seconds//86400}d {(seconds%86400)//3600}h"

# MODERATION COMMANDS
@bot.command(name='ban')
@has_permission('ban_members')
async def ban_user(ctx, user: discord.Member, *, reason="No reason provided"):
    """Ban a user from the server"""
    try:
        await user.ban(reason=reason)
        await ctx.send(f"✅ {user.mention} has been banned. Reason: {reason}")
        await log_command(ctx, "ban", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to ban user: {str(e)}")
        await log_command(ctx, "ban", False, e)

@bot.command(name='kick')
@has_permission('kick_members')
async def kick_user(ctx, user: discord.Member, *, reason="No reason provided"):
    """Kick a user from the server"""
    try:
        await user.kick(reason=reason)
        await ctx.send(f"✅ {user.mention} has been kicked. Reason: {reason}")
        await log_command(ctx, "kick", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to kick user: {str(e)}")
        await log_command(ctx, "kick", False, e)

@bot.command(name='timeout')
@has_permission('moderate_members')
async def timeout_user(ctx, user: discord.Member, duration: int, *, reason="No reason provided"):
    """Timeout a user"""
    try:
        timeout_until = datetime.utcnow() + timedelta(minutes=duration)
        await user.timeout(timeout_until, reason=reason)
        await ctx.send(f"✅ {user.mention} has been timed out for {duration} minutes. Reason: {reason}")
        await log_command(ctx, "timeout", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to timeout user: {str(e)}")
        await log_command(ctx, "timeout", False, e)

@bot.command(name='warn')
@has_permission('kick_members')
async def warn_user(ctx, user: discord.Member, *, reason="No reason provided"):
    """Warn a user"""
    try:
        warning_data = {
            "warning_id": str(uuid.uuid4()),
            "server_id": str(ctx.guild.id),
            "user_id": str(user.id),
            "moderator_id": str(ctx.author.id),
            "reason": reason,
            "timestamp": datetime.utcnow()
        }
        
        warnings_collection.insert_one(warning_data)
        
        # Count warnings
        warning_count = warnings_collection.count_documents({
            "server_id": str(ctx.guild.id),
            "user_id": str(user.id)
        })
        
        await ctx.send(f"⚠️ {user.mention} has been warned. Reason: {reason}\nTotal warnings: {warning_count}")
        await log_command(ctx, "warn", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to warn user: {str(e)}")
        await log_command(ctx, "warn", False, e)

@bot.command(name='clear')
@has_permission('manage_messages')
async def clear_messages(ctx, amount: int = 10):
    """Clear messages"""
    try:
        if amount > 100:
            amount = 100
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"✅ Cleared {len(deleted) - 1} messages.", delete_after=5)
        await log_command(ctx, "clear", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to clear messages: {str(e)}")
        await log_command(ctx, "clear", False, e)

@bot.command(name='slowmode')
@has_permission('manage_channels')
async def set_slowmode(ctx, seconds: int = 0):
    """Set channel slowmode"""
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled.")
        else:
            await ctx.send(f"✅ Slowmode set to {seconds} seconds.")
        await log_command(ctx, "slowmode", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to set slowmode: {str(e)}")
        await log_command(ctx, "slowmode", False, e)

@bot.command(name='lock')
@has_permission('manage_channels')
async def lock_channel(ctx):
    """Lock a channel"""
    try:
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("🔒 Channel locked.")
        await log_command(ctx, "lock", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to lock channel: {str(e)}")
        await log_command(ctx, "lock", False, e)

@bot.command(name='unlock')
@has_permission('manage_channels')
async def unlock_channel(ctx):
    """Unlock a channel"""
    try:
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("🔓 Channel unlocked.")
        await log_command(ctx, "unlock", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to unlock channel: {str(e)}")
        await log_command(ctx, "unlock", False, e)

# SERVER MANAGEMENT COMMANDS
@bot.command(name='serverinfo')
async def server_info(ctx):
    """Get server information"""
    try:
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"Server Information - {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Boosts", value=guild.premium_subscription_count, inline=True)
        
        await ctx.send(embed=embed)
        await log_command(ctx, "serverinfo", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to get server info: {str(e)}")
        await log_command(ctx, "serverinfo", False, e)

@bot.command(name='prefix')
@has_permission('manage_guild')
async def set_prefix(ctx, new_prefix: str):
    """Set bot prefix"""
    try:
        servers_collection.update_one(
            {"server_id": str(ctx.guild.id)},
            {"$set": {"prefix": new_prefix, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        await ctx.send(f"✅ Prefix changed to `{new_prefix}`")
        await log_command(ctx, "prefix", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to set prefix: {str(e)}")
        await log_command(ctx, "prefix", False, e)

# ROLE MANAGEMENT COMMANDS
@bot.command(name='createrole')
@has_permission('manage_roles')
async def create_role(ctx, *, name: str):
    """Create a new role"""
    try:
        role = await ctx.guild.create_role(name=name)
        await ctx.send(f"✅ Role `{name}` created successfully!")
        await log_command(ctx, "createrole", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to create role: {str(e)}")
        await log_command(ctx, "createrole", False, e)

@bot.command(name='assignrole')
@has_permission('manage_roles')
async def assign_role(ctx, user: discord.Member, *, role: discord.Role):
    """Assign role to user"""
    try:
        await user.add_roles(role)
        await ctx.send(f"✅ {role.name} assigned to {user.mention}")
        await log_command(ctx, "assignrole", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to assign role: {str(e)}")
        await log_command(ctx, "assignrole", False, e)

@bot.command(name='removerole')
@has_permission('manage_roles')
async def remove_role(ctx, user: discord.Member, *, role: discord.Role):
    """Remove role from user"""
    try:
        await user.remove_roles(role)
        await ctx.send(f"✅ {role.name} removed from {user.mention}")
        await log_command(ctx, "removerole", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to remove role: {str(e)}")
        await log_command(ctx, "removerole", False, e)

# CHANNEL MANAGEMENT COMMANDS
@bot.command(name='createchannel')
@has_permission('manage_channels')
async def create_channel(ctx, channel_type: str, *, name: str):
    """Create a new channel"""
    try:
        if channel_type.lower() == "text":
            channel = await ctx.guild.create_text_channel(name)
        elif channel_type.lower() == "voice":
            channel = await ctx.guild.create_voice_channel(name)
        else:
            await ctx.send("❌ Invalid channel type. Use 'text' or 'voice'")
            return
        
        await ctx.send(f"✅ {channel_type.capitalize()} channel `{name}` created successfully!")
        await log_command(ctx, "createchannel", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to create channel: {str(e)}")
        await log_command(ctx, "createchannel", False, e)

# USER MANAGEMENT COMMANDS
@bot.command(name='userinfo')
async def user_info(ctx, user: discord.Member = None):
    """Get user information"""
    try:
        if user is None:
            user = ctx.author
        
        embed = discord.Embed(
            title=f"User Information - {user.display_name}",
            color=user.color,
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
        embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Status", value=str(user.status), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=len(user.roles) - 1, inline=True)
        
        await ctx.send(embed=embed)
        await log_command(ctx, "userinfo", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to get user info: {str(e)}")
        await log_command(ctx, "userinfo", False, e)

@bot.command(name='nickname')
@has_permission('manage_nicknames')
async def change_nickname(ctx, user: discord.Member, *, nickname: str = None):
    """Change user nickname"""
    try:
        await user.edit(nick=nickname)
        if nickname:
            await ctx.send(f"✅ Changed {user.mention}'s nickname to `{nickname}`")
        else:
            await ctx.send(f"✅ Cleared {user.mention}'s nickname")
        await log_command(ctx, "nickname", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to change nickname: {str(e)}")
        await log_command(ctx, "nickname", False, e)

# UTILITY COMMANDS
@bot.command(name='poll')
async def create_poll(ctx, *, question: str):
    """Create a poll"""
    try:
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        
        await log_command(ctx, "poll", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to create poll: {str(e)}")
        await log_command(ctx, "poll", False, e)

@bot.command(name='embed')
@has_permission('manage_messages')
async def create_embed(ctx, title: str, *, description: str):
    """Create custom embed"""
    try:
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Created by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        await log_command(ctx, "embed", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to create embed: {str(e)}")
        await log_command(ctx, "embed", False, e)

# FUN COMMANDS
@bot.command(name='8ball')
async def magic_8ball(ctx, *, question: str):
    """Magic 8 ball"""
    try:
        responses = [
            "It is certain", "It is decidedly so", "Without a doubt",
            "Yes definitely", "You may rely on it", "As I see it, yes",
            "Most likely", "Outlook good", "Yes", "Signs point to yes",
            "Reply hazy, try again", "Ask again later", "Better not tell you now",
            "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no",
            "Outlook not so good", "Very doubtful"
        ]
        
        response = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 Magic 8 Ball",
            color=discord.Color.blue()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        
        await ctx.send(embed=embed)
        await log_command(ctx, "8ball", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to use 8ball: {str(e)}")
        await log_command(ctx, "8ball", False, e)

@bot.command(name='dice')
async def roll_dice(ctx, sides: int = 6):
    """Roll dice"""
    try:
        if sides < 2 or sides > 100:
            await ctx.send("❌ Dice must have between 2 and 100 sides!")
            return
        
        result = random.randint(1, sides)
        await ctx.send(f"🎲 You rolled a {result} (d{sides})")
        await log_command(ctx, "dice", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to roll dice: {str(e)}")
        await log_command(ctx, "dice", False, e)

# ECONOMY COMMANDS
@bot.command(name='balance')
async def check_balance(ctx, user: discord.Member = None):
    """Check balance"""
    try:
        if user is None:
            user = ctx.author
        
        user_data = economy_collection.find_one({
            "server_id": str(ctx.guild.id),
            "user_id": str(user.id)
        })
        
        if not user_data:
            balance = 0
        else:
            balance = user_data.get("balance", 0)
        
        embed = discord.Embed(
            title=f"💰 {user.display_name}'s Balance",
            description=f"**{balance:,}** coins",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        await log_command(ctx, "balance", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to check balance: {str(e)}")
        await log_command(ctx, "balance", False, e)

@bot.command(name='daily')
async def daily_reward(ctx):
    """Get daily reward"""
    try:
        user_data = economy_collection.find_one({
            "server_id": str(ctx.guild.id),
            "user_id": str(ctx.author.id)
        })
        
        now = datetime.utcnow()
        
        if user_data and user_data.get("last_daily"):
            last_daily = user_data["last_daily"]
            if (now - last_daily).days < 1:
                time_left = 24 - (now - last_daily).seconds // 3600
                await ctx.send(f"❌ You can claim your daily reward in {time_left} hours!")
                return
        
        reward = random.randint(100, 500)
        
        economy_collection.update_one(
            {"server_id": str(ctx.guild.id), "user_id": str(ctx.author.id)},
            {
                "$inc": {"balance": reward},
                "$set": {"last_daily": now}
            },
            upsert=True
        )
        
        await ctx.send(f"✅ You claimed your daily reward of **{reward:,}** coins!")
        await log_command(ctx, "daily", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to claim daily reward: {str(e)}")
        await log_command(ctx, "daily", False, e)

# HELP COMMAND
@bot.command(name='help')
async def help_command(ctx, category: str = None):
    """Show help information"""
    try:
        if category is None:
            embed = discord.Embed(
                title="🤖 Bot Commands",
                description="Here are all available command categories:",
                color=discord.Color.blue()
            )
            
            categories = {
                "moderation": "Moderation commands (ban, kick, warn, etc.)",
                "server": "Server management commands",
                "roles": "Role management commands",
                "channels": "Channel management commands",
                "users": "User management commands",
                "utility": "Utility commands",
                "fun": "Fun commands",
                "economy": "Economy commands"
            }
            
            for cat, desc in categories.items():
                embed.add_field(name=f"!help {cat}", value=desc, inline=False)
            
            embed.set_footer(text="Use !help <category> for specific commands")
            
        else:
            # Category-specific help would go here
            embed = discord.Embed(
                title=f"🤖 {category.title()} Commands",
                description=f"Commands for {category} category",
                color=discord.Color.blue()
            )
            embed.add_field(name="Coming Soon", value="Category-specific help is being developed", inline=False)
        
        await ctx.send(embed=embed)
        await log_command(ctx, "help", True)
    except Exception as e:
        await ctx.send(f"❌ Failed to show help: {str(e)}")
        await log_command(ctx, "help", False, e)

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")