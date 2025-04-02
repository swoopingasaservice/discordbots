import discord
import logging
import asyncio
from datetime import datetime
from cache import user_cache

def format_timestamp(dt):
    """Format a datetime object as a string"""
    if not dt:
        return "Unknown"
    
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logging.error(f"Error formatting timestamp: {e}")
        return str(dt)

async def prefetch_users(bot, user_ids, batch_size=50):
    """Prefetch user information in batches to reduce API calls"""
    global user_cache
    
    # Filter out users that are already in the cache
    user_ids_to_fetch = [str(user_id) for user_id in user_ids if str(user_id) not in user_cache]
    
    # Fetch users in batches
    for i in range(0, len(user_ids_to_fetch), batch_size):
        batch = user_ids_to_fetch[i:i+batch_size]
        tasks = []
        
        for user_id in batch:
            # Convert to string and check if it's a valid digit string
            user_id_str = str(user_id)
            if user_id_str.isdigit():
                tasks.append(fetch_user_safe(bot, int(user_id_str)))
        
        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

async def fetch_user_safe(bot, user_id):
    """Fetch a user safely and add to cache"""
    global user_cache
    
    try:
        user = await bot.fetch_user(user_id)
        user_cache[str(user_id)] = user
        return user
    except Exception as e:
        logging.warning(f"Error fetching user {user_id}: {e}")
        return None

def get_user_from_cache(user_id):
    """Get a user from the cache or return None"""
    global user_cache
    
    user_id = str(user_id)
    return user_cache.get(user_id)

async def send_leaderboard_page(bot, interaction, leaderboard, page=0):
    """Send a page of the leaderboard with pagination buttons"""
    # Show loading indicator
    if interaction.response.is_done():
        loading_message = await interaction.edit_original_response(content="Loading leaderboard page...", embed=None, view=None)
    
    # Calculate pagination
    items_per_page = 20  # Discord allows up to 25 fields per embed, but we'll use 20 for better display
    total_pages = max(1, (len(leaderboard) + items_per_page - 1) // items_per_page)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(leaderboard))
    
    # Create embed
    embed = discord.Embed(
        title="Moderation Leaderboard",
        description=f"Users with the lowest reputation scores (Page {page+1}/{total_pages})",
        color=discord.Color.gold()
    )
    
    # Add fields for each user on this page
    for i, (user_id, data) in enumerate(leaderboard[start_idx:end_idx], start=start_idx+1):
        try:
            # Try to get user from cache first
            user = get_user_from_cache(user_id)
            user_name = user.name if user else f"Unknown User ({user_id})"
            
            # Get reputation
            reputation = data.get("reputation", 0)
            
            # Get action count
            action_count = len(data.get("actions", []))
            
            # Get most recent action timestamp (if any)
            most_recent_time = None
            if data.get("actions"):
                try:
                    # Sort actions by timestamp (oldest first)
                    sorted_actions = sorted(
                        data.get("actions", []),
                        key=lambda x: datetime.fromisoformat(x.get("timestamp", "1970-01-01T00:00:00").replace('Z', '+00:00'))
                    )
                    
                    # Get the most recent action (last in the sorted list)
                    if sorted_actions:
                        recent = sorted_actions[-1]
                        timestamp = recent.get("timestamp", "Unknown")
                        if isinstance(timestamp, str):
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            most_recent_time = f"Last action (UTC): {format_timestamp(dt)}"
                except Exception as e:
                    logging.error(f"Error formatting timestamp for user {user_id}: {e}")
                    most_recent_time = "Last action: Error parsing timestamp"
            
            # Add field with user ID and timestamp if available
            value_text = f"User ID: `{user_id}`\nReputation: {reputation}\nActions: {action_count}"
            if most_recent_time:
                value_text += f"\n{most_recent_time}"
                
            embed.add_field(
                name=f"#{i}: {user_name}",
                value=value_text,
                inline=True
            )
        except Exception as e:
            logging.error(f"Error formatting leaderboard entry: {e}")
            embed.add_field(
                name=f"#{i}: Unknown User",
                value=f"User ID: `{user_id}`\nReputation: {data.get('reputation', 0)}\nActions: {len(data.get('actions', []))}\nError: {e}",
                inline=True
            )
    
    # Add pagination info with UTC mention
    embed.set_footer(text=f"Page {page+1}/{total_pages} | Total Users: {len(leaderboard)} | All timestamps are in UTC")
    
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
        await send_leaderboard_page(bot, interaction, leaderboard, page=page-1)
    
    async def next_callback(interaction):
        await interaction.response.defer()
        await send_leaderboard_page(bot, interaction, leaderboard, page=page+1)
    
    prev_button.callback = prev_callback
    next_button.callback = next_callback
    
    # Add buttons to view
    view.add_item(prev_button)
    view.add_item(next_button)
    
    # Send or edit message
    if interaction.response.is_done():
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    else:
        await interaction.followup.send(embed=embed, view=view)
