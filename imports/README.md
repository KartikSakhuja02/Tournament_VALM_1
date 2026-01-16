# Agent Profile GIFs

This directory contains agent GIF files that are displayed when users view their profile.

## File Naming Convention

All GIF files should be named in lowercase: `{agent_name}.gif`

## Required Files

Place the following GIF files in this directory:

- sage.gif
- phoenix.gif
- reyna.gif
- sova.gif
- brimstone.gif
- raze.gif
- skye.gif
- jett.gif
- viper.gif
- breach.gif
- cypher.gif
- killjoy.gif
- omen.gif
- yoru.gif
- astra.gif
- kayo.gif
- chamber.gif
- neon.gif
- fade.gif
- gecko.gif
- iso.gif
- clove.gif
- tejo.gif

## Usage

When a user runs `/profile`, the bot will:
1. Get the user's registered agent from the database
2. Look for `{agent}.gif` in this directory
3. Send the GIF file (no embed, just the GIF)
4. If the GIF file doesn't exist, it will show an error message

## Notes

- Files must be in GIF format
- Keep file sizes reasonable (Discord has a 25MB upload limit for bots)
- You can add text overlays to the GIFs before uploading them here
- If a GIF file is missing, the bot will show an error message
