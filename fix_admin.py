#!/usr/bin/env python3
"""
Fix admin.py by moving misplaced admin commands into the Admin class.
"""

with open('commands/admin.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where Admin class ends (line 1490)
admin_class_end = 1489  # 0-indexed, so line 1490 is index 1489

# Find where the misplaced commands start (line 2763) 
misplaced_start = 2762  # 0-indexed

# Find where setup function starts
setup_start = None
for i, line in enumerate(lines):
    if line.strip().startswith('async def setup(bot'):
        setup_start = i
        break

if not setup_start:
    print("ERROR: Could not find setup function!")
    exit(1)

print(f"Admin class ends at line {admin_class_end + 1}")
print(f"Misplaced commands start at line {misplaced_start + 1}")
print(f"Setup function starts at line {setup_start + 1}")
print(f"Moving {setup_start - misplaced_start} lines")

# Extract the misplaced commands
misplaced_commands = lines[misplaced_start:setup_start]

# Remove empty lines at the end of misplaced commands
while misplaced_commands and misplaced_commands[-1].strip() == '':
    misplaced_commands.pop()

# Build the new file
new_lines = []

# Add everything up to the end of admin_transfer_captain method (line 1490)
new_lines.extend(lines[:admin_class_end + 1])

# Add the misplaced commands (they become part of Admin class)
new_lines.extend(misplaced_commands)

# Add everything from AdminTransferCaptainTeamView to the start of misplaced commands
new_lines.extend(lines[admin_class_end + 1:misplaced_start])

# Add the setup function and everything after
new_lines.extend(lines[setup_start:])

# Write the fixed file
with open('commands/admin.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Fixed admin.py successfully!")
print(f"Old file: {len(lines)} lines")
print(f"New file: {len(new_lines)} lines")
