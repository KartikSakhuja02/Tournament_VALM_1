"""
Thread management utilities for registration processes
"""

import discord
import asyncio
import os
from typing import Optional


# Store threads waiting for HeadMod
_threads_waiting_for_headmod = {}


async def add_staff_to_thread(thread: discord.Thread, guild: discord.Guild):
    """
    Add staff members to a thread with smart online detection.
    
    Rules:
    - Administrators: Always added regardless of online status
    - HeadMods: Only added if online; if none online, waits for one to come online
    """
    
    # Add administrators (always, regardless of status)
    administrator_role_id = os.getenv("ADMINISTRATOR_ROLE_ID")
    if administrator_role_id:
        try:
            admin_role = guild.get_role(int(administrator_role_id))
            if admin_role:
                for member in admin_role.members:
                    try:
                        await thread.add_user(member)
                        await asyncio.sleep(0.5)
                        print(f"✓ Added admin {member.name} to thread {thread.name}")
                    except Exception as e:
                        print(f"✗ Failed to add admin {member.name}: {e}")
        except Exception as e:
            print(f"Error processing administrators: {e}")
    
    # Add head mods (only if online)
    headmod_role_id = os.getenv("HEADMOD_ROLE_ID")
    if headmod_role_id:
        try:
            headmod_role = guild.get_role(int(headmod_role_id))
            if headmod_role:
                online_headmods = [
                    member for member in headmod_role.members
                    if member.status != discord.Status.offline
                ]
                
                if online_headmods:
                    # Add all online headmods
                    for member in online_headmods:
                        try:
                            await thread.add_user(member)
                            await asyncio.sleep(0.5)
                            print(f"✓ Added online headmod {member.name} to thread {thread.name}")
                        except Exception as e:
                            print(f"✗ Failed to add headmod {member.name}: {e}")
                else:
                    # No headmods online - register thread for waiting
                    print(f"⏳ No HeadMods online. Thread {thread.name} will wait for one to come online.")
                    _threads_waiting_for_headmod[thread.id] = {
                        'thread': thread,
                        'guild': guild,
                        'role_id': int(headmod_role_id)
                    }
        except Exception as e:
            print(f"Error processing head mods: {e}")


async def on_presence_update(before: discord.Member, after: discord.Member):
    """
    Event handler for presence updates. Call this from bot's on_presence_update event.
    
    When a HeadMod comes online, adds them to any waiting threads.
    """
    headmod_role_id = os.getenv("HEADMOD_ROLE_ID")
    if not headmod_role_id:
        return
    
    # Check if member has HeadMod role and just came online
    headmod_role = after.guild.get_role(int(headmod_role_id))
    if not headmod_role or headmod_role not in after.roles:
        return
    
    # Check if they went from offline to online
    if before.status == discord.Status.offline and after.status != discord.Status.offline:
        print(f"✓ HeadMod {after.name} came online!")
        
        # Add them to all waiting threads
        threads_to_remove = []
        for thread_id, thread_info in _threads_waiting_for_headmod.items():
            thread = thread_info['thread']
            
            try:
                # Verify thread still exists
                try:
                    await thread.fetch_message(thread.id)  # Check if thread is accessible
                except:
                    # Thread no longer exists
                    threads_to_remove.append(thread_id)
                    continue
                
                # Add the online headmod to the thread
                await thread.add_user(after)
                print(f"✓ Added {after.name} to waiting thread: {thread.name}")
                
                # Remove from waiting list after successfully adding
                threads_to_remove.append(thread_id)
                
            except Exception as e:
                print(f"✗ Failed to add {after.name} to thread {thread.name}: {e}")
        
        # Clean up processed threads
        for thread_id in threads_to_remove:
            del _threads_waiting_for_headmod[thread_id]
        
        if threads_to_remove:
            print(f"✓ Processed {len(threads_to_remove)} waiting thread(s)")


def get_waiting_threads_count() -> int:
    """Get the number of threads currently waiting for a HeadMod"""
    return len(_threads_waiting_for_headmod)
