import discord
import logging
import asyncio
import os
from datetime import datetime
from discord import app_commands
from config import TARGET_CHANNEL_ID, TARGET_GUILD_ID
from utils import format_timestamp, get_user_from_cache, fetch_user_safe, prefetch_users, send_leaderboard_page
from data import (
    moderation_history, get_user_history, get_leaderboard, 
    add_moderation_action, save_moderation_history, calculate_server_stats
)

# Module-level function for fetching historical moderation actions
async def fetch_historical_moderation_actions(bot, guild, silent=False):
    """
    Fetch historical moderation actions from a server's audit logs
    
    Parameters:
    - bot: The Discord bot instance
    - guild: The guild to fetch actions from
    - silent: If True, only send messages for actual new actions, not status updates
    """
    try:
        # Get target channel
        target_channel = bot.get_channel(TARGET_CHANNEL_ID)
        if not target_channel:
            logging.error(f"Target channel {TARGET_CHANNEL_ID} not found")
            return
        
        # Initialize action count
        action_count = 0
        
        # Check if bot has permission to view audit logs
        bot_member = guild.get_member(bot.user.id)
        if not bot_member:
            if not silent:
                await target_channel.send(f"⚠️ Bot is not a member of **{guild.name}**")
            return
            
        permissions = bot_member.guild_permissions
        if not permissions.view_audit_log:
            if not silent:
                await target_channel.send(f"⚠️ Missing 'View Audit Log' permission in **{guild.name}**")
            return
            
        if not silent:
            await target_channel.send(f"✅ Bot has 'View Audit Log' permission in **{guild.name}**")
            return
            
        permissions = bot_member.guild_permissions
        if not permissions.view_audit_log:
            if not silent:
                await target_channel.send(f"⚠️ Missing 'View Audit Log' permission in **{guild.name}**")
            return
            
        if not silent:
            await target_channel.send(f"✅ Bot has 'View Audit Log' permission in **{guild.name}**")
        # Process each action type separately
        for action_type, action_name in [
            (discord.AuditLogAction.ban, "ban"),
            (discord.AuditLogAction.kick, "kick"),
            (discord.AuditLogAction.member_update, "timeout")  # For timeouts
        ]:
            try:
                if not silent:
                    await target_channel.send(f"Checking for {action_name}s in **{guild.name}**...")
                
                # Collect all valid entries first
                valid_entries = []
                
                # Get audit logs for this action type
                async for entry in guild.audit_logs(action=action_type, limit=50):
                    try:
                        # Debug info about the entry
                        entry_info = f"Entry ID: {entry.id}, Action: {entry.action}, User: {entry.user}, Target: {entry.target}"
                        logging.info(f"Processing entry in {guild.name}: {entry_info}")
                        
                        # For timeouts, check if it's actually a timeout
                        if action_type == discord.AuditLogAction.member_update:
                            # Skip if not a timeout
                            is_timeout = False
                            
                            # Check for timed_out_until attribute
                            if hasattr(entry, 'after') and hasattr(entry.after, 'timed_out_until'):
                                if entry.after.timed_out_until:
                                    is_timeout = True
                                    logging.info(f"Found timeout with timed_out_until: {entry.after.timed_out_until}")
                            
                            # Check for communication_disabled_until attribute
                            if hasattr(entry, 'after') and hasattr(entry.after, 'communication_disabled_until'):
                                if entry.after.communication_disabled_until:
                                    is_timeout = True
                                    logging.info(f"Found timeout with communication_disabled_until: {entry.after.communication_disabled_until}")
                            
                            if not is_timeout:
                                logging.info(f"Skipping non-timeout member update: {entry_info}")
                                continue
                        # Get target user
                        target_user = entry.target
                        if not target_user:
                            logging.warning(f"No target user for entry: {entry_info}")
                            continue
                        
                        # Add to valid entries
                        valid_entries.append(entry)
                        
                    except Exception as e:
                        error_msg = f"Error processing individual audit log entry in {guild.name}: {str(e)}"
                        logging.warning(error_msg)
                        if not silent:
                            await target_channel.send(f"⚠️ {error_msg}")
                        continue
                
                # Sort entries by timestamp (oldest first)
                valid_entries.sort(key=lambda e: e.created_at)
                
                # Process entries in order (oldest to newest)
                for entry in valid_entries:
                    try:
                        target_user = entry.target
                        reason = entry.reason or "No reason provided"
                        moderator = entry.user
                        timestamp = entry.created_at
                        
                        # Generate a unique action ID
                        action_id = f"{guild.id}:{action_name}:{target_user.id}:{entry.id}:{timestamp.isoformat()}"
                        
                        # Create and send an embed for this historical action
                        embed = discord.Embed(
                            title=f"{action_name.title()}",
                            description=f"{target_user.name} ({target_user.id}) was {action_name}ed in {guild.name}",
                            color=discord.Color.dark_red(),
                            timestamp=timestamp
                        )
                        # Add user avatar if available
                        if hasattr(target_user, 'avatar') and target_user.avatar:
                            embed.set_thumbnail(url=target_user.avatar.url)
                        
                        # Add user ID field
                        embed.add_field(
                            name="User ID",
                            value=f"`{target_user.id}`",
                            inline=True
                        )
                        
                        # Add reason if provided
                        if reason:
                            embed.add_field(
                                name="Reason",
                                value=reason,
                                inline=False
                            )
                        
                        # Add moderator if provided
                        if moderator:
                            embed.add_field(
                                name="Moderator",
                                value=f"{moderator.name} ({moderator.id})",
                                inline=True
                            )
                        
                        # Add timestamp field for clarity (with UTC specified)
                        embed.add_field(
                            name="When (UTC)",
                            value=format_timestamp(timestamp),
                            inline=True
                        )
                        
                        # Add footer with UTC mention
                        embed.set_footer(text="All timestamps are in UTC")
                        
                        # Add action to history
                        result = add_moderation_action(
                            user_id=target_user.id,
                            action_type=action_name,
                            guild_id=guild.id,
                            reason=reason,
                            moderator=moderator,
                            timestamp=timestamp.isoformat(),
                            action_id=action_id
                        )
                        
                        # Check if action was added or was a duplicate
                        if result.get("duplicate"):
                            logging.info(f"Skipping duplicate action: {action_id}")
                            continue
                        
                        # Send embed only if not in silent mode or if it's a new action
                        if not silent:
                            await target_channel.send(embed=embed)
                        else:
                            # In silent mode, only send the actual action data without status messages
                            await target_channel.send(embed=embed)
                        
                        # Increment action count
                        action_count += 1
                        
                        # Add a small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        error_msg = f"Error processing audit log entry in {guild.name}: {str(e)}"
                        logging.warning(error_msg)
                        if not silent:
                            await target_channel.send(f"⚠️ {error_msg}")
                        continue
            except Exception as e:
                error_msg = f"Error processing {action_name}s in {guild.name}: {str(e)}"
                logging.error(error_msg)
                if not silent:
                    await target_channel.send(f"⚠️ {error_msg}")
                continue
        
        # Send summary only if actions were found or not in silent mode
        if not silent and action_count > 0:
            await target_channel.send(f"✅ Imported {action_count} historical moderation actions from **{guild.name}**")
        
    except Exception as e:
        error_msg = f"Error fetching historical moderation actions for {guild.name}: {str(e)}"
        logging.error(error_msg)
        
        # Try to get more info about the error
        import traceback
        tb = traceback.format_exc()
        logging.error(f"Traceback: {tb}")
        
        # Try to send a message to the target channel only if not in silent mode
        if not silent:
            target_channel = bot.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                await target_channel.send(f"⚠️ {error_msg}")
def register_commands(bot):
    """Register all slash commands"""
    
    # Helper function to check if command is used in the target guild
    def check_guild_permission(interaction):
        """Check if the command is being used in the authorized guild"""
        if interaction.guild_id != TARGET_GUILD_ID:
            return False, "This command can only be used in the authorized server."
        return True, ""
    
    @bot.tree.command(name="ping", description="Check if the bot is responsive")
    async def ping_command(interaction: discord.Interaction):
        """Simple ping command to check if the bot is responsive"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
                
            latency = round(bot.latency * 1000)
            await interaction.response.send_message(f"Pong! Latency: {latency}ms")
        except Exception as e:
            logging.error(f"Error in ping command: {e}")
            await interaction.response.send_message(f"An error occurred: {e}")
    
    @bot.tree.command(name="import", description="Import historical moderation actions from a server")
    async def import_command(interaction: discord.Interaction, server_id: str = None):
        """Import historical moderation actions from a server's audit logs"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            # Get server
            if server_id:
                try:
                    guild = bot.get_guild(int(server_id))
                    if not guild:
                        await interaction.followup.send(f"Server with ID {server_id} not found.")
                        return
                except ValueError:
                    await interaction.followup.send(f"Invalid server ID: {server_id}")
                    return
            else:
                # Use the guild where the command was used
                guild = interaction.guild
            
            # Import historical actions with verbose output
            await interaction.followup.send(f"Importing historical moderation actions from **{guild.name}**...")
            await fetch_historical_moderation_actions(bot, guild, silent=False)
            
        except Exception as e:
            error_msg = f"Error in import command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    @bot.tree.command(name="history", description="View a user's moderation history")
    async def history_command(interaction: discord.Interaction, user: discord.User):
        """View a user's moderation history"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            
            # Get user history
            user_id = str(user.id)
            if user_id not in moderation_history:
                await interaction.followup.send(f"No moderation history found for {user.name}.")
                return
            
            # Get user data
            user_data = moderation_history[user_id]
            # Check if user has actions
            if "actions" not in user_data or not user_data["actions"]:
                embed = discord.Embed(
                    title=f"Moderation History for {user.name}",
                    description=f"User ID: {user.id}",
                    color=discord.Color.red()
                )
                
                # Add user avatar if available
                if user.avatar:
                    embed.set_thumbnail(url=user.avatar.url)
                
                embed.add_field(
                    name="Reputation Score",
                    value=str(user_data.get("reputation", 0)),
                    inline=False
                )
                
                embed.add_field(
                    name="Actions",
                    value="No actions recorded",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Sort actions by timestamp (newest first)
            actions = sorted(
                user_data["actions"], 
                key=lambda x: x.get("timestamp", "0"),
                reverse=True  # Newest first
            )
            
            # Send paginated history
            await send_history_page(bot, interaction, user, user_data, actions, page=0)
            
        except Exception as e:
            error_msg = f"Error in history command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")
    @bot.tree.command(name="check", description="Check a user's moderation history")
    async def check_command(interaction: discord.Interaction, user: discord.User):
        """Check a user's moderation history and provide a summary"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            
            # Get user history
            history = get_user_history(user.id)
            
            # Check if history is empty
            if not history.get("actions"):
                await interaction.followup.send(f"{user.name} has no moderation history.")
                return
            
            # Count actions by type
            action_counts = {}
            for action in history.get("actions", []):
                action_type = action.get("action", "unknown")
                if action_type not in action_counts:
                    action_counts[action_type] = 0
                action_counts[action_type] += 1
            
            # Count actions by guild
            guild_counts = {}
            for action in history.get("actions", []):
                guild_id = action.get("guild_id", "unknown")
                if guild_id not in guild_counts:
                    guild_counts[guild_id] = 0
                guild_counts[guild_id] += 1
            
            # Create embed
            embed = discord.Embed(
                title=f"Moderation Summary for {user.name}",
                description=f"User ID: {user.id}",
                color=discord.Color.orange()
            )
            # Add user avatar if available
            if user.avatar:
                embed.set_thumbnail(url=user.avatar.url)
            
            # Add reputation
            embed.add_field(
                name="Reputation Score",
                value=str(history.get("reputation", 0)),
                inline=True
            )
            
            # Add total actions
            embed.add_field(
                name="Total Actions",
                value=str(len(history.get("actions", []))),
                inline=True
            )
            
            # Add action counts by type
            if action_counts:
                action_summary = "\n".join([f"{action_type.title()}: {count}" for action_type, count in action_counts.items()])
                embed.add_field(
                    name="Action Types",
                    value=action_summary,
                    inline=False
                )
            
            # Add server counts
            if guild_counts:
                server_summary = ""
                for guild_id, count in guild_counts.items():
                    guild_name = "Unknown Server"
                    try:
                        guild = bot.get_guild(int(guild_id))
                        if guild:
                            guild_name = guild.name
                    except:
                        pass
                    server_summary += f"{guild_name}: {count}\n"
                
                embed.add_field(
                    name="Servers",
                    value=server_summary,
                    inline=False
                )
            
            # Send embed
            await interaction.followup.send(embed=embed)
        except Exception as e:
            error_msg = f"Error in check command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    @bot.tree.command(name="leaderboard", description="View users with the lowest reputation scores")
    async def leaderboard_command(interaction: discord.Interaction, limit: int = 10):
        """View users with the lowest reputation scores"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            
            # Cap the limit at 50 users
            capped_limit = min(50, limit)
            if capped_limit != limit:
                await interaction.followup.send(f"Limiting results to 50 users (you requested {limit}).", ephemeral=True)
            
            # Get leaderboard
            leaderboard = get_leaderboard(limit=capped_limit)
            
            # Check if leaderboard is empty
            if not leaderboard:
                await interaction.followup.send("No users with moderation history found.")
                return
            
            # Prefetch users
            user_ids = [user_id for user_id, _ in leaderboard]
            await prefetch_users(bot, user_ids)
            
            # Send paginated leaderboard
            await send_leaderboard_page(bot, interaction, leaderboard, page=0)
        except Exception as e:
            error_msg = f"Error in leaderboard command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    @bot.tree.command(name="stats", description="View moderation statistics for a server")
    async def stats_command(interaction: discord.Interaction, server_id: str = None):
        """View moderation statistics for a server"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            
            # Get server
            if server_id:
                try:
                    guild = bot.get_guild(int(server_id))
                    if not guild:
                        await interaction.followup.send(f"Server with ID {server_id} not found.")
                        return
                    guild_id = guild.id
                    guild_name = guild.name
                except ValueError:
                    await interaction.followup.send(f"Invalid server ID: {server_id}")
                    return
            else:
                # Use the guild where the command was used
                if not interaction.guild:
                    await interaction.followup.send("This command must be used in a server or with a server ID.")
                    return
                guild = interaction.guild
                guild_id = guild.id
                guild_name = guild.name
            
            # Calculate stats
            stats = calculate_server_stats(guild_id)
            # Create embed
            embed = discord.Embed(
                title=f"Moderation Statistics for {guild_name}",
                description=f"Server ID: {guild_id}",
                color=discord.Color.blue()
            )
            
            # Add server icon if available
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            # Add user count
            embed.add_field(
                name="Users with History",
                value=str(stats["total_users"]),
                inline=True
            )
            
            # Add average reputation
            embed.add_field(
                name="Average Reputation",
                value=f"{stats['avg_reputation']:.2f}",
                inline=True
            )
            
            # Add action counts
            if stats["action_counts"]:
                action_summary = "\n".join([f"{action_type.title()}: {count}" for action_type, count in stats["action_counts"].items()])
                embed.add_field(
                    name="Action Counts",
                    value=action_summary,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Action Counts",
                    value="No actions recorded",
                    inline=False
                )
            
            # Add most recent action
            if stats["recent_action"]:
                recent = stats["recent_action"]
                action_type = recent.get("action", "unknown")
                timestamp = recent.get("timestamp", "unknown")
                user_id = recent.get("user_id", "unknown")
                reason = recent.get("reason", "No reason provided")
                # Format timestamp
                formatted_time = timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = format_timestamp(dt)
                except:
                    pass
                
                # Try to get user
                user_name = f"User {user_id}"
                try:
                    user = await fetch_user_safe(bot, int(user_id))
                    if user:
                        user_name = f"{user.name} ({user_id})"
                except:
                    pass
                
                recent_text = f"**Type:** {action_type.title()}\n**User:** {user_name}\n**When:** {formatted_time}\n**Reason:** {reason}"
                
                embed.add_field(
                    name="Most Recent Action",
                    value=recent_text,
                    inline=False
                )
            
            # Send embed
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            error_msg = f"Error in stats command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")

    @bot.tree.command(name="rep", description="Check a user's reputation score by ID")
    async def rep_command(interaction: discord.Interaction, user_id: str):
        """Check a user's reputation score by ID"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            
            # Validate user ID
            if not user_id.isdigit():
                await interaction.followup.send("Invalid user ID. Please provide a valid Discord user ID.")
                return
            
            # Get user history
            history = get_user_history(user_id)
            
            # Try to fetch user info
            user = None
            try:
                user = await fetch_user_safe(bot, int(user_id))
            except:
                pass
            
            user_name = user.name if user else f"Unknown User ({user_id})"
            
            # Check if history is empty
            if not history:
                await interaction.followup.send(f"No moderation history found for {user_name}.")
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"Reputation for {user_name}",
                description=f"User ID: {user_id}",
                color=discord.Color.blue()
            )
            
            # Add user avatar if available
            if user and user.avatar:
                embed.set_thumbnail(url=user.avatar.url)
            
            # Add reputation
            embed.add_field(
                name="Reputation Score",
                value=str(history.get("reputation", 0)),
                inline=True
            )
            
            # Add action count
            action_count = len(history.get("actions", []))
            embed.add_field(
                name="Total Actions",
                value=str(action_count),
                inline=True
            )
            # Count actions by type
            if action_count > 0:
                action_counts = {}
                for action in history.get("actions", []):
                    action_type = action.get("action", "unknown")
                    if action_type not in action_counts:
                        action_counts[action_type] = 0
                    action_counts[action_type] += 1
                
                action_summary = "\n".join([f"{action_type.title()}: {count}" for action_type, count in action_counts.items()])
                embed.add_field(
                    name="Action Types",
                    value=action_summary,
                    inline=False
                )
            
            # Send embed
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            error_msg = f"Error in rep command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")
    
    @bot.tree.command(name="rep_guild", description="Check a guild's reputation statistics by ID")
    async def rep_guild_command(interaction: discord.Interaction, guild_id: str):
        """Check a guild's reputation statistics by ID"""
        try:
            # Check if command is used in the target guild
            allowed, message = check_guild_permission(interaction)
            if not allowed:
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            # Respond immediately to prevent timeout
            await interaction.response.defer(thinking=True)
            
            # Validate guild ID
            if not guild_id.isdigit():
                await interaction.followup.send("Invalid guild ID. Please provide a valid Discord server ID.")
                return
            # Try to get guild info
            guild = None
            guild_name = f"Unknown Server ({guild_id})"
            try:
                guild = bot.get_guild(int(guild_id))
                if guild:
                    guild_name = guild.name
            except:
                pass
            
            # Calculate stats for this guild
            stats = calculate_server_stats(guild_id)
            
            # Check if stats are empty
            if stats["total_users"] == 0:
                await interaction.followup.send(f"No moderation history found for {guild_name}.")
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"Reputation Statistics for {guild_name}",
                description=f"Server ID: {guild_id}",
                color=discord.Color.green()
            )
            
            # Add server icon if available
            if guild and guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            # Add user count
            embed.add_field(
                name="Users with History",
                value=str(stats["total_users"]),
                inline=True
            )
            
            # Add average reputation
            embed.add_field(
                name="Average Reputation",
                value=f"{stats['avg_reputation']:.2f}",
                inline=True
            )
            
            # Add total actions
            total_actions = sum(stats["action_counts"].values()) if stats["action_counts"] else 0
            embed.add_field(
                name="Total Actions",
                value=str(total_actions),
                inline=True
            )
            # Add action counts
            if stats["action_counts"]:
                action_summary = "\n".join([f"{action_type.title()}: {count}" for action_type, count in stats["action_counts"].items()])
                embed.add_field(
                    name="Action Types",
                    value=action_summary,
                    inline=False
                )
            
            # Send embed
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            error_msg = f"Error in rep_guild command: {str(e)}"
            logging.error(error_msg)
            await interaction.followup.send(f"An error occurred: {str(e)}")

    # Helper function for paginated history
    async def send_history_page(bot, interaction, user, user_data, actions, page=0):
        """Send a page of user history with pagination buttons"""
        # Calculate pagination
        items_per_page = 5  # Number of actions per page
        total_pages = max(1, (len(actions) + items_per_page - 1) // items_per_page)
        page = max(0, min(page, total_pages - 1))
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(actions))
        
        # Create embed for this page
        embed = discord.Embed(
            title=f"Moderation History for {user.name}",
            description=f"Reputation Score: {user_data.get('reputation', 0)}",
            color=discord.Color.red()
        )
        
        # Add user avatar if available
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        # Add actions for this page
        for i, action in enumerate(actions[start_idx:end_idx]):
            action_type = action.get("action", "unknown")
            guild_id = action.get("guild_id", "unknown")
            timestamp = action.get("timestamp", "unknown")
            reason = action.get("reason", "No reason provided")
            
            # Try to get guild name
            guild_name = "Unknown Server"
            try:
                guild = bot.get_guild(int(guild_id))
                if guild:
                    guild_name = guild.name
            except:
                pass
            
            # Format timestamp
            formatted_time = timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = format_timestamp(dt)
            except:
                pass
            
            # Format moderator info
            moderator_info = ""
            if "moderator" in action:
                mod = action["moderator"]
                if isinstance(mod, dict):
                    mod_name = mod.get("name", "Unknown")
                    moderator_info = f"Moderator: {mod_name}"
                else:
                    moderator_info = f"Moderator: {mod}"
            
            # Add action text
            action_text = f"**Type:** {action_type.title()}\n**Server:** {guild_name}\n**Date:** {formatted_time}\n**Reason:** {reason}\n{moderator_info}"
            
            embed.add_field(
                name=f"Action #{start_idx + i + 1}",
                value=action_text,
                inline=False
            )
        
        # Add footer with page info
        embed.set_footer(text=f"Page {page+1}/{total_pages} | Total Actions: {len(actions)}")
        # Create pagination buttons
        view = discord.ui.View(timeout=300)  # 5 minute timeout
        
        # Previous page button
        prev_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Previous",
            emoji="⬅️",
            disabled=(page == 0)
        )
        
        # Next page button
        next_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Next",
            emoji="➡️",
            disabled=(page == total_pages - 1)
        )
        
        # Set button callbacks
        async def prev_callback(interaction):
            await interaction.response.defer()
            await send_history_page(bot, interaction, user, user_data, actions, page=page-1)
        
        async def next_callback(interaction):
            await interaction.response.defer()
            await send_history_page(bot, interaction, user, user_data, actions, page=page+1)
        
        prev_button.callback = prev_callback
        next_button.callback = next_callback
        
        # Add buttons to view
        view.add_item(prev_button)
        view.add_item(next_button)
        
        # Send or edit message
        await interaction.followup.send(embed=embed, view=view)

    return bot  # Return the bot with commands registered
