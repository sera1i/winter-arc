with open('winter_arc/settings.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() in [f"'{app}'," for app in ['core', 'accounts', 'arcs', 'goals', 'tasks', 'habits', 'journal', 'study', 'workouts', 'analytics', 'gamification', 'notifications', 'api']]:
        new_lines.append('# ' + line)
    elif line.strip().startswith("AUTH_USER_MODEL"):
        new_lines.append('# ' + line)
    else:
        new_lines.append(line)

with open('winter_arc/settings.py', 'w') as f:
    f.writelines(new_lines)
