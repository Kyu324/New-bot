from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
import uuid
import uvicorn
from contextlib import asynccontextmanager
import asyncio
import subprocess
import signal
import sys

# Bot process variable
bot_process = None

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'discord_bot_db')

# MongoDB connection
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
servers_collection = db.servers
commands_collection = db.commands
logs_collection = db.logs

# Bot credentials
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN', 'MTE2MjA1MzM3OTMxMzM4MTUyOA.Gqbogw.-VgCiUDpRBRHYRj6LOON2HIRcDfXKu7CorjqYw')
DISCORD_APP_ID = os.environ.get('DISCORD_APP_ID', '1162053379313381528')

def start_discord_bot():
    """Start the Discord bot as a subprocess"""
    global bot_process
    try:
        bot_process = subprocess.Popen([
            sys.executable, "/app/backend/bot.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Discord bot started with PID: {bot_process.pid}")
    except Exception as e:
        print(f"Error starting Discord bot: {e}")

def stop_discord_bot():
    """Stop the Discord bot"""
    global bot_process
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
        print("Discord bot stopped")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Discord Bot Server...")
    start_discord_bot()
    yield
    # Shutdown
    print("Stopping Discord Bot Server...")
    stop_discord_bot()

app = FastAPI(
    title="Discord Bot Management API",
    description="API for managing Discord bot and server data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ServerConfig(BaseModel):
    server_id: str
    server_name: str
    prefix: str = "!"
    welcome_channel: Optional[str] = None
    log_channel: Optional[str] = None
    auto_role: Optional[str] = None
    settings: Dict[str, Any] = {}

class CommandLog(BaseModel):
    command_id: str
    server_id: str
    user_id: str
    command_name: str
    parameters: Dict[str, Any]
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

class BotStatus(BaseModel):
    status: str
    uptime: Optional[str] = None
    servers: int = 0
    commands_executed: int = 0

# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Discord Bot Management API", "status": "running"}

@app.get("/api/bot/status")
async def get_bot_status():
    """Get bot status information"""
    global bot_process
    
    bot_running = bot_process is not None and bot_process.poll() is None
    
    # Get server count from database
    server_count = servers_collection.count_documents({})
    
    # Get total commands executed
    total_commands = commands_collection.count_documents({})
    
    return BotStatus(
        status="running" if bot_running else "stopped",
        servers=server_count,
        commands_executed=total_commands
    )

@app.post("/api/bot/start")
async def start_bot():
    """Start the Discord bot"""
    global bot_process
    
    if bot_process and bot_process.poll() is None:
        return {"message": "Bot is already running"}
    
    start_discord_bot()
    return {"message": "Bot started successfully"}

@app.post("/api/bot/stop")
async def stop_bot():
    """Stop the Discord bot"""
    global bot_process
    
    if not bot_process or bot_process.poll() is not None:
        return {"message": "Bot is not running"}
    
    stop_discord_bot()
    return {"message": "Bot stopped successfully"}

@app.get("/api/servers")
async def get_servers():
    """Get all servers the bot is in"""
    servers = list(servers_collection.find({}, {"_id": 0}))
    return {"servers": servers}

@app.get("/api/servers/{server_id}")
async def get_server(server_id: str):
    """Get specific server configuration"""
    server = servers_collection.find_one({"server_id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@app.post("/api/servers")
async def create_server_config(config: ServerConfig):
    """Create or update server configuration"""
    config_dict = config.dict()
    config_dict["created_at"] = datetime.utcnow()
    config_dict["updated_at"] = datetime.utcnow()
    
    # Upsert server configuration
    servers_collection.update_one(
        {"server_id": config.server_id},
        {"$set": config_dict},
        upsert=True
    )
    
    return {"message": "Server configuration saved", "server_id": config.server_id}

@app.get("/api/commands")
async def get_commands():
    """Get all available commands"""
    commands = [
        # Moderation Commands
        {"name": "ban", "category": "moderation", "description": "Ban a user from the server"},
        {"name": "kick", "category": "moderation", "description": "Kick a user from the server"},
        {"name": "mute", "category": "moderation", "description": "Mute a user"},
        {"name": "unmute", "category": "moderation", "description": "Unmute a user"},
        {"name": "warn", "category": "moderation", "description": "Warn a user"},
        {"name": "timeout", "category": "moderation", "description": "Timeout a user"},
        {"name": "clear", "category": "moderation", "description": "Clear messages"},
        {"name": "slowmode", "category": "moderation", "description": "Set channel slowmode"},
        {"name": "lock", "category": "moderation", "description": "Lock a channel"},
        {"name": "unlock", "category": "moderation", "description": "Unlock a channel"},
        {"name": "purge", "category": "moderation", "description": "Purge messages by user"},
        {"name": "massban", "category": "moderation", "description": "Mass ban users"},
        {"name": "softban", "category": "moderation", "description": "Soft ban a user"},
        {"name": "tempban", "category": "moderation", "description": "Temporarily ban a user"},
        {"name": "unban", "category": "moderation", "description": "Unban a user"},
        {"name": "warnings", "category": "moderation", "description": "View user warnings"},
        {"name": "clearwarnings", "category": "moderation", "description": "Clear user warnings"},
        {"name": "lockdown", "category": "moderation", "description": "Server lockdown"},
        {"name": "unlockdown", "category": "moderation", "description": "Remove server lockdown"},
        {"name": "nuke", "category": "moderation", "description": "Recreate channel"},
        
        # Server Management Commands
        {"name": "serverinfo", "category": "server", "description": "Get server information"},
        {"name": "serverconfig", "category": "server", "description": "Configure server settings"},
        {"name": "prefix", "category": "server", "description": "Set bot prefix"},
        {"name": "welcome", "category": "server", "description": "Configure welcome messages"},
        {"name": "autorole", "category": "server", "description": "Set auto role for new members"},
        {"name": "backup", "category": "server", "description": "Backup server settings"},
        {"name": "restore", "category": "server", "description": "Restore server from backup"},
        {"name": "invitetracker", "category": "server", "description": "Track server invites"},
        {"name": "serverstats", "category": "server", "description": "Server statistics"},
        {"name": "membercount", "category": "server", "description": "Get member count"},
        {"name": "boostinfo", "category": "server", "description": "Server boost information"},
        {"name": "emojistats", "category": "server", "description": "Emoji usage statistics"},
        {"name": "channelstats", "category": "server", "description": "Channel statistics"},
        {"name": "activity", "category": "server", "description": "Server activity stats"},
        {"name": "growth", "category": "server", "description": "Server growth statistics"},
        
        # Role Management Commands
        {"name": "createrole", "category": "roles", "description": "Create a new role"},
        {"name": "deleterole", "category": "roles", "description": "Delete a role"},
        {"name": "editrole", "category": "roles", "description": "Edit role properties"},
        {"name": "assignrole", "category": "roles", "description": "Assign role to user"},
        {"name": "removerole", "category": "roles", "description": "Remove role from user"},
        {"name": "roleinfo", "category": "roles", "description": "Get role information"},
        {"name": "rolemembers", "category": "roles", "description": "List role members"},
        {"name": "rolecolor", "category": "roles", "description": "Change role color"},
        {"name": "rolepermissions", "category": "roles", "description": "Edit role permissions"},
        {"name": "massrole", "category": "roles", "description": "Mass assign/remove roles"},
        {"name": "autoroles", "category": "roles", "description": "Configure auto roles"},
        {"name": "reactionroles", "category": "roles", "description": "Set up reaction roles"},
        {"name": "rolehierarchy", "category": "roles", "description": "View role hierarchy"},
        {"name": "roleall", "category": "roles", "description": "Give role to all members"},
        {"name": "rolehumans", "category": "roles", "description": "Give role to all humans"},
        
        # Channel Management Commands
        {"name": "createchannel", "category": "channels", "description": "Create a new channel"},
        {"name": "deletechannel", "category": "channels", "description": "Delete a channel"},
        {"name": "editchannel", "category": "channels", "description": "Edit channel properties"},
        {"name": "channelinfo", "category": "channels", "description": "Get channel information"},
        {"name": "channelpermissions", "category": "channels", "description": "Edit channel permissions"},
        {"name": "clone", "category": "channels", "description": "Clone a channel"},
        {"name": "move", "category": "channels", "description": "Move channel position"},
        {"name": "topic", "category": "channels", "description": "Set channel topic"},
        {"name": "nsfw", "category": "channels", "description": "Toggle NSFW channel"},
        {"name": "announce", "category": "channels", "description": "Make announcement"},
        {"name": "categoryinfo", "category": "channels", "description": "Get category information"},
        {"name": "createcategory", "category": "channels", "description": "Create channel category"},
        {"name": "deletecategory", "category": "channels", "description": "Delete channel category"},
        {"name": "movecategory", "category": "channels", "description": "Move channel to category"},
        {"name": "listchannels", "category": "channels", "description": "List all channels"},
        
        # User Management Commands
        {"name": "userinfo", "category": "users", "description": "Get user information"},
        {"name": "nickname", "category": "users", "description": "Change user nickname"},
        {"name": "avatar", "category": "users", "description": "Get user avatar"},
        {"name": "userstats", "category": "users", "description": "Get user statistics"},
        {"name": "activity", "category": "users", "description": "Get user activity"},
        {"name": "permissions", "category": "users", "description": "Check user permissions"},
        {"name": "badges", "category": "users", "description": "View user badges"},
        {"name": "joindate", "category": "users", "description": "Get user join date"},
        {"name": "profile", "category": "users", "description": "View user profile"},
        {"name": "rank", "category": "users", "description": "View user rank"},
        
        # Auto-Moderation Commands
        {"name": "automod", "category": "automod", "description": "Configure auto moderation"},
        {"name": "antispam", "category": "automod", "description": "Configure anti-spam"},
        {"name": "antiraid", "category": "automod", "description": "Configure anti-raid"},
        {"name": "wordfilter", "category": "automod", "description": "Configure word filter"},
        {"name": "antiinvite", "category": "automod", "description": "Block invite links"},
        {"name": "antilink", "category": "automod", "description": "Block external links"},
        {"name": "anticaps", "category": "automod", "description": "Prevent excessive caps"},
        {"name": "antimention", "category": "automod", "description": "Prevent mass mentions"},
        {"name": "autodehoist", "category": "automod", "description": "Auto dehoist nicknames"},
        {"name": "verification", "category": "automod", "description": "Set verification level"},
        
        # Logging Commands
        {"name": "logs", "category": "logging", "description": "View server logs"},
        {"name": "modlogs", "category": "logging", "description": "View moderation logs"},
        {"name": "messagelogs", "category": "logging", "description": "View message logs"},
        {"name": "joinlogs", "category": "logging", "description": "View join/leave logs"},
        {"name": "voicelogs", "category": "logging", "description": "View voice logs"},
        {"name": "serverlogs", "category": "logging", "description": "View server change logs"},
        {"name": "auditlog", "category": "logging", "description": "View audit log"},
        {"name": "setlogchannel", "category": "logging", "description": "Set log channel"},
        {"name": "logconfig", "category": "logging", "description": "Configure logging"},
        {"name": "exportlogs", "category": "logging", "description": "Export logs to file"},
        
        # Utility Commands
        {"name": "poll", "category": "utility", "description": "Create a poll"},
        {"name": "embed", "category": "utility", "description": "Create custom embed"},
        {"name": "say", "category": "utility", "description": "Make bot say something"},
        {"name": "dm", "category": "utility", "description": "Send DM to user"},
        {"name": "remind", "category": "utility", "description": "Set reminder"},
        {"name": "timer", "category": "utility", "description": "Set timer"},
        {"name": "calc", "category": "utility", "description": "Calculator"},
        {"name": "weather", "category": "utility", "description": "Get weather info"},
        {"name": "translate", "category": "utility", "description": "Translate text"},
        {"name": "qr", "category": "utility", "description": "Generate QR code"},
        
        # Fun Commands
        {"name": "meme", "category": "fun", "description": "Get random meme"},
        {"name": "joke", "category": "fun", "description": "Get random joke"},
        {"name": "fact", "category": "fun", "description": "Get random fact"},
        {"name": "quote", "category": "fun", "description": "Get random quote"},
        {"name": "8ball", "category": "fun", "description": "Magic 8 ball"},
        {"name": "dice", "category": "fun", "description": "Roll dice"},
        {"name": "coinflip", "category": "fun", "description": "Flip coin"},
        {"name": "random", "category": "fun", "description": "Random number"},
        {"name": "trivia", "category": "fun", "description": "Trivia questions"},
        {"name": "riddle", "category": "fun", "description": "Get riddle"},
        
        # Economy Commands
        {"name": "balance", "category": "economy", "description": "Check balance"},
        {"name": "daily", "category": "economy", "description": "Daily reward"},
        {"name": "work", "category": "economy", "description": "Work for money"},
        {"name": "shop", "category": "economy", "description": "Server shop"},
        {"name": "buy", "category": "economy", "description": "Buy item"},
        {"name": "inventory", "category": "economy", "description": "View inventory"},
        {"name": "transfer", "category": "economy", "description": "Transfer money"},
        {"name": "leaderboard", "category": "economy", "description": "Economy leaderboard"},
        {"name": "gamble", "category": "economy", "description": "Gamble money"},
        {"name": "rob", "category": "economy", "description": "Rob another user"},
        
        # Advanced Commands
        {"name": "ticket", "category": "advanced", "description": "Ticket system"},
        {"name": "giveaway", "category": "advanced", "description": "Create giveaway"},
        {"name": "suggestion", "category": "advanced", "description": "Suggestion system"},
        {"name": "report", "category": "advanced", "description": "Report system"},
        {"name": "starboard", "category": "advanced", "description": "Configure starboard"},
        {"name": "levels", "category": "advanced", "description": "Leveling system"},
        {"name": "customcommand", "category": "advanced", "description": "Create custom command"},
        {"name": "tags", "category": "advanced", "description": "Tag system"},
        {"name": "afk", "category": "advanced", "description": "AFK system"},
        {"name": "music", "category": "advanced", "description": "Music commands"},
    ]
    
    return {"commands": commands, "total": len(commands)}

@app.get("/api/commands/{category}")
async def get_commands_by_category(category: str):
    """Get commands by category"""
    all_commands = await get_commands()
    commands = [cmd for cmd in all_commands["commands"] if cmd["category"] == category]
    return {"commands": commands, "category": category, "total": len(commands)}

@app.post("/api/commands/execute")
async def log_command_execution(command_log: CommandLog):
    """Log command execution"""
    log_dict = command_log.dict()
    log_dict["timestamp"] = datetime.utcnow()
    
    commands_collection.insert_one(log_dict)
    return {"message": "Command execution logged"}

@app.get("/api/logs")
async def get_logs():
    """Get command execution logs"""
    logs = list(commands_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(100))
    return {"logs": logs}

@app.get("/api/logs/{server_id}")
async def get_server_logs(server_id: str):
    """Get logs for specific server"""
    logs = list(commands_collection.find(
        {"server_id": server_id}, 
        {"_id": 0}
    ).sort("timestamp", -1).limit(100))
    return {"logs": logs, "server_id": server_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)