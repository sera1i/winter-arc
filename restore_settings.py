with open('winter_arc/settings.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip().startswith('# ') and line.replace('# ', '').strip() in [f"'{app}'," for app in ['core', 'accounts', 'arcs', 'goals', 'tasks', 'habits', 'journal', 'study', 'workouts', 'analytics', 'gamification', 'notifications', 'api']]:
        new_lines.append(line.replace('# ', '', 1))
    elif line.strip().startswith('# AUTH_USER_MODEL'):
        new_lines.append(line.replace('# ', '', 1))
    else:
        new_lines.append(line)

with open('winter_arc/settings.py', 'w') as f:
    f.writelines(new_lines)
