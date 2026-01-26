"""
Migration script to upload existing team logos to permanent Discord storage
and update database URLs.

Run this once after setting up LOGO_STORAGE_CHANNEL_ID in .env
"""

import discord
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables FIRST before importing db
load_dotenv()

from database.db import db

async def migrate_logos():
    """Upload all existing logos from team_logos/ folder to Discord storage"""
    
    # Initialize bot
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"✓ Logged in as {client.user}")
        
        try:
            # Get storage channel
            logo_storage_channel_id = os.getenv('LOGO_STORAGE_CHANNEL_ID')
            if not logo_storage_channel_id:
                logo_storage_channel_id = os.getenv('BOT_LOGS_CHANNEL_ID')
            
            if not logo_storage_channel_id:
                print("❌ No LOGO_STORAGE_CHANNEL_ID or BOT_LOGS_CHANNEL_ID found in .env")
                await client.close()
                return
            
            storage_channel = client.get_channel(int(logo_storage_channel_id))
            if not storage_channel:
                print(f"❌ Channel {logo_storage_channel_id} not found")
                await client.close()
                return
            
            print(f"✓ Using storage channel: #{storage_channel.name}")
            
            # Connect to database
            await db.connect()
            print("✓ Connected to database")
            
            # Get all teams
            teams = await db.get_all_teams()
            print(f"✓ Found {len(teams)} teams")
            
            # Check team_logos folder
            if not os.path.exists('team_logos'):
                print("❌ team_logos/ folder not found")
                await client.close()
                return
            
            migrated_count = 0
            skipped_count = 0
            
            for team in teams:
                team_name = team['team_name']
                team_id = team['id']
                current_logo_url = team.get('logo_url')
                
                # Check if logo file exists
                filename = f"team_logos/{team_name.replace(' ', '_')}.png"
                
                if os.path.exists(filename):
                    print(f"\n📁 Found logo for: {team_name}")
                    
                    try:
                        # Upload to storage channel
                        logo_file = discord.File(filename, filename=f"{team_name.replace(' ', '_')}.png")
                        storage_message = await storage_channel.send(
                            f"Logo for team: **{team_name}** (Team ID: {team_id})",
                            file=logo_file
                        )
                        
                        # Get permanent URL
                        if storage_message.attachments:
                            new_logo_url = storage_message.attachments[0].url
                            
                            # Update database
                            await db.pool.execute(
                                "UPDATE teams SET logo_url = $1 WHERE id = $2",
                                new_logo_url, team_id
                            )
                            
                            print(f"  ✅ Migrated: {team_name}")
                            print(f"     Old URL: {current_logo_url[:50] if current_logo_url else 'None'}...")
                            print(f"     New URL: {new_logo_url[:50]}...")
                            migrated_count += 1
                        else:
                            print(f"  ❌ Failed to upload: {team_name}")
                    
                    except Exception as e:
                        print(f"  ❌ Error migrating {team_name}: {e}")
                else:
                    if current_logo_url:
                        print(f"⚠️  No local file for: {team_name} (has URL in DB)")
                    skipped_count += 1
            
            print(f"\n{'='*50}")
            print(f"✓ Migration complete!")
            print(f"  Migrated: {migrated_count}")
            print(f"  Skipped: {skipped_count}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()
            await client.close()
    
    # Run bot
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ DISCORD_BOT_TOKEN not found in .env")
        return
    
    await client.start(token)

if __name__ == "__main__":
    asyncio.run(migrate_logos())
