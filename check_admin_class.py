with open('commands/admin.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_admin_class = False
admin_start = 0
class_indent = 0

for i, line in enumerate(lines, 1):
    # Check if we're starting the Admin class
    if line.strip().startswith('class Admin(commands.Cog):'):
        in_admin_class = True
        admin_start = i
        class_indent = len(line) - len(line.lstrip())
        print(f"Admin class starts at line {i}")
        print(f"Class indent level: {class_indent}")
        continue
    
    # If we're in the Admin class, check if we've exited it
    if in_admin_class:
        # Non-empty line that's not indented more than the class definition = we've exited
        if line.strip() and not line.startswith(' '):
            print(f"Admin class ends at line {i-1}")
            print(f"Next top-level code at line {i}: {line.strip()[:60]}")
            break
        # Check for another class definition at the same level
        elif line.strip().startswith('class ') and (len(line) - len(line.lstrip())) == class_indent:
            print(f"Admin class ends at line {i-1}")
            print(f"Next class starts at line {i}: {line.strip()[:60]}")
            break

print(f"\nTotal lines in file: {len(lines)}")
