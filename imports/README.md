# Agent Video Files

This directory contains agent video files that are displayed when users view their profile.

## File Naming Convention

All video files should be named in lowercase: `{agent_name}.mp4`

## Required Files

Place the following video files in this directory:

- sage.mp4
- phoenix.mp4
- reyna.mp4
- sova.mp4
- brimstone.mp4
- raze.mp4
- skye.mp4
- jett.mp4
- viper.mp4
- breach.mp4
- cypher.mp4
- killjoy.mp4
- omen.mp4
- yoru.mp4
- astra.mp4
- kayo.mp4
- chamber.mp4
- neon.mp4
- fade.mp4
- gecko.mp4
- iso.mp4
- clove.mp4
- tejo.mp4

## Usage

When a user runs `/profile`, the bot will:
1. Get the user's registered agent from the database
2. Look for `{agent}.mp4` in this directory
3. Send the video file along with the profile embed
4. If the video file doesn't exist, it will just send the profile embed without the video

## Notes

- Videos should be in MP4 format
- Keep file sizes reasonable (Discord has upload limits)
- If a video file is missing, the bot will show a warning but still display the profile
