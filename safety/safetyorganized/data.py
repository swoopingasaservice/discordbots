import json
import logging
import os
from datetime import datetime
from config import HISTORY_FILE

# Global variables
moderation_history = {}

def load_moderation_history():
    """Load moderation history from file"""
    global moderation_history
    
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                loaded_data = json.load(f)
                
            # Verify the data is a dictionary
            if not isinstance(loaded_data, dict):
                logging.error(f"Loaded data is not a dictionary: {type(loaded_data)}")
                return moderation_history
                
            # Clear and update the global variable
            moderation_history.clear()
            moderation_history.update(loaded_data)
            
            logging.info(f"Loaded moderation history with {len(moderation_history)} users")
        else:
            logging.warning(f"No history file found at {HISTORY_FILE}, starting with empty history")
            moderation_history = {}
    except Exception as e:
        logging.error(f"Error loading moderation history: {e}")
        import traceback
        logging.error(traceback.format_exc())
        moderation_history = {}
    
    # Return the loaded data to ensure it's accessible
    return moderation_history

def save_moderation_history():
    """Save moderation history to file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(HISTORY_FILE)), exist_ok=True)
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(moderation_history, f, indent=2)
        logging.info(f"Saved moderation history with {len(moderation_history)} users")
    except Exception as e:
        logging.error(f"Error saving moderation history: {e}")
        import traceback
        logging.error(traceback.format_exc())

def get_user_history(user_id):
    """Get a user's moderation history"""
    global moderation_history
    
    # Convert to string to ensure consistent format
    user_id = str(user_id)
    
    # Try different formats of the user ID
    if user_id not in moderation_history:
        # Try without quotes
        if user_id.strip('"\'') not in moderation_history:
            # Create new entry if not found
            moderation_history[user_id] = {
                "reputation": 0,
                "actions": []
            }
            logging.info(f"Created new history entry for user {user_id}")
        else:
            # Use the version without quotes
            user_id = user_id.strip('"\'')
            logging.info(f"Found history for user {user_id} after stripping quotes")
    
    return moderation_history[user_id]

def add_moderation_action(user_id, action_type, guild_id, reason=None, moderator=None, timestamp=None, action_id=None):
    """Add a moderation action to a user's history"""
    global moderation_history
    
    user_id = str(user_id)
    guild_id = str(guild_id)
    
    # Get user history
    user_history = get_user_history(user_id)
    
    # Check if this action already exists (to avoid duplicates)
    if action_id and "actions" in user_history:
        for action in user_history["actions"]:
            if action.get("action_id") == action_id:
                return {"duplicate": True}
    
    # Create action object
    action = {
        "action": action_type,
        "guild_id": guild_id,
        "timestamp": timestamp or datetime.utcnow().isoformat(),
        "reason": reason or "No reason provided"
    }
    
    # Add moderator if provided
    if moderator:
        if hasattr(moderator, 'id') and hasattr(moderator, 'name'):
            action["moderator"] = {
                "id": str(moderator.id),
                "name": moderator.name
            }
        else:
            action["moderator"] = str(moderator)
    
    # Add action ID if provided
    if action_id:
        action["action_id"] = action_id
    
    # Add action to history
    if "actions" not in user_history:
        user_history["actions"] = []
    user_history["actions"].append(action)
    
    # Update reputation
    if action_type == "ban":
        user_history["reputation"] -= 5
    elif action_type == "kick":
        user_history["reputation"] -= 3
    elif action_type == "timeout":
        user_history["reputation"] -= 1
    
    # Save history
    save_moderation_history()
    
    return {"success": True}

def get_leaderboard(limit=100):
    """Get users with the lowest reputation scores"""
    global moderation_history
    
    # Filter users with actions
    users_with_actions = {
        user_id: data for user_id, data in moderation_history.items()
        if "actions" in data and data["actions"]
    }
    
    # Sort by reputation (lowest first)
    sorted_users = sorted(
        users_with_actions.items(),
        key=lambda x: x[1].get("reputation", 0)
    )
    
    # Return limited number of users
    return sorted_users[:limit]

def calculate_server_stats(guild_id):
    """Calculate reputation statistics for a server"""
    guild_id = str(guild_id)
    
    # Initialize stats
    stats = {
        "action_counts": {},
        "total_users": 0,
        "total_reputation": 0,
        "avg_reputation": 0,
        "recent_action": None
    }
    
    # Track users in this guild
    users_in_guild = set()
    
    # Track most recent action
    most_recent_time = None
    
    # Process all users
    for user_id, user_data in moderation_history.items():
        if "actions" not in user_data or not isinstance(user_data["actions"], list):
            continue
        
        user_in_guild = False
        
        # Sort actions by timestamp (oldest first)
        actions = sorted(user_data["actions"], key=lambda x: x.get("timestamp", "0"))
        
        # Process actions for this user
        for action in actions:
            if action.get("guild_id") == guild_id:
                user_in_guild = True
                
                # Count action type
                action_type = action.get("action", "unknown")
                if action_type not in stats["action_counts"]:
                    stats["action_counts"][action_type] = 0
                stats["action_counts"][action_type] += 1
                
                # Check if this is the most recent action
                if "timestamp" in action:
                    try:
                        action_time = datetime.fromisoformat(action["timestamp"].replace('Z', '+00:00'))
                        if most_recent_time is None or action_time > most_recent_time:
                            most_recent_time = action_time
                            stats["recent_action"] = {
                                "action": action_type,
                                "timestamp": action["timestamp"],
                                "user_id": user_id,
                                "reason": action.get("reason", "No reason provided")
                            }
                    except:
                        pass
        
        # Add user to count if they have actions in this guild
        if user_in_guild:
            users_in_guild.add(user_id)
            stats["total_reputation"] += user_data.get("reputation", 0)
    
    # Calculate final stats
    stats["total_users"] = len(users_in_guild)
    if stats["total_users"] > 0:
        stats["avg_reputation"] = stats["total_reputation"] / stats["total_users"]
    
    return stats
