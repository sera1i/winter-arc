import os

base_dir = 'templates/accounts'
os.makedirs(base_dir, exist_ok=True)

templates = {
    'password_reset.html': '''{% extends 'base/base.html' %}
{% load widget_tweaks %}
{% block title %}Reset Password{% endblock %}
{% block content %}
<div class="max-w-md mx-auto mt-10 bg-white p-8 border border-gray-200 rounded-lg shadow-sm">
    <h2 class="text-2xl font-bold mb-4">Reset Password</h2>
    <form method="post">{% csrf_token %}
        {% for field in form %}
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
                {{ field|add_class:"w-full px-3 py-2 border rounded-md" }}
            </div>
        {% endfor %}
        <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded">Send Reset Email</button>
    </form>
</div>
{% endblock %}''',

    'password_reset_done.html': '''{% extends 'base/base.html' %}
{% block title %}Reset Email Sent{% endblock %}
{% block content %}
<div class="max-w-md mx-auto mt-10 bg-white p-8 border rounded-lg shadow-sm text-center">
    <h2 class="text-2xl font-bold mb-4">Check your email</h2>
    <p>We've emailed you instructions for setting your password.</p>
</div>
{% endblock %}''',

    'password_reset_confirm.html': '''{% extends 'base/base.html' %}
{% load widget_tweaks %}
{% block title %}Set New Password{% endblock %}
{% block content %}
<div class="max-w-md mx-auto mt-10 bg-white p-8 border rounded-lg shadow-sm">
    <h2 class="text-2xl font-bold mb-4">Set New Password</h2>
    <form method="post">{% csrf_token %}
        {% for field in form %}
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
                {{ field|add_class:"w-full px-3 py-2 border rounded-md" }}
            </div>
        {% endfor %}
        <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded">Save Password</button>
    </form>
</div>
{% endblock %}''',

    'password_reset_complete.html': '''{% extends 'base/base.html' %}
{% block title %}Password Reset Complete{% endblock %}
{% block content %}
<div class="max-w-md mx-auto mt-10 bg-white p-8 border rounded-lg shadow-sm text-center">
    <h2 class="text-2xl font-bold mb-4">Password Reset Complete</h2>
    <p class="mb-4">Your password has been set.</p>
    <a href="{% url 'login' %}" class="text-blue-600">Log in now</a>
</div>
{% endblock %}'''
}

for name, content in templates.items():
    with open(os.path.join(base_dir, name), 'w') as f:
        f.write(content)

print("Templates generated.")
