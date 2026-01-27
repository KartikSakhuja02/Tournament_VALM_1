import asyncio
from main import bot
from dotenv import load_dotenv

load_dotenv()

async def check():
    # Load all extensions
    await bot.load_extension('commands.ping')
    await bot.load_extension('commands.registration')
    await bot.load_extension('commands.team_registration')
    await bot.load_extension('commands.manager_registration')
    await bot.load_extension('commands.coach_registration')
    await bot.load_extension('commands.team_management')
    await bot.load_extension('commands.admin')
    await bot.load_extension('commands.profile')
    await bot.load_extension('commands.team_profile')
    await bot.load_extension('commands.announce')
    
    # Get all commands
    cmds = [cmd.name for cmd in bot.tree.get_commands()]
    print(f'\n✓ Total commands registered: {len(cmds)}\n')
    for cmd in sorted(cmds):
        print(f'  - {cmd}')
    print()

asyncio.run(check())
