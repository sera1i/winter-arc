import os
import re
import urllib.request

FONTS = {
    'Cormorant_Garamond': 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap',
    'Onest': 'https://fonts.googleapis.com/css2?family=Onest:wght@100..900&display=swap'
}

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'

FONT_DIR = os.path.join('static', 'fonts')
CSS_FILE = os.path.join('static', 'css', 'fonts.css')

os.makedirs(FONT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CSS_FILE), exist_ok=True)

css_content = ""

for name, url in FONTS.items():
    print(f"Fetching CSS for {name}...")
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as response:
        css = response.read().decode('utf-8')
    
    # Find all url(...) in the CSS
    urls = re.findall(r'url\((.*?)\)', css)
    for font_url in urls:
        font_url = font_url.strip("'\"")
        filename = font_url.split('/')[-1]
        local_path = os.path.join(FONT_DIR, filename)
        
        if not os.path.exists(local_path):
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(font_url, local_path)
        
        # Replace remote URL with local URL in CSS
        css = css.replace(font_url, f'../fonts/{filename}')
    
    css_content += f"/* {name} */\n{css}\n\n"

with open(CSS_FILE, 'w', encoding='utf-8') as f:
    f.write(css_content)

print("Fonts downloaded and fonts.css generated.")
