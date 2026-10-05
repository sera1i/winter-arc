import os
import re
import json
import sys
from bs4 import BeautifulSoup

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

templates_dir = 'templates/seo'
for fname in sorted(os.listdir(templates_dir)):
    if not fname.endswith('.html') or fname == 'base_public.html':
        continue
    fpath = os.path.join(templates_dir, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find JSON-LD
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL)
    json_faqs = []
    has_faq_schema = False
    json_breadcrumbs = []
    has_article_schema = False
    article_data = {}
    if m:
        try:
            raw_json = m.group(1)
            # Clean up template tags cleanly
            raw_json = re.sub(r'\{\{.*?\}\}/?', 'https://arcinwinter.up.railway.app/', raw_json)
            raw_json = re.sub(r'\{%.*?%\}', 'some_value', raw_json)
            data = json.loads(raw_json)
            graph = data.get('@graph', [data])
            for item in graph:
                itype = item.get('@type')
                if itype == 'FAQPage':
                    has_faq_schema = True
                    for q in item.get('mainEntity', []):
                        json_faqs.append((q.get('name', '').strip(), q.get('acceptedAnswer', {}).get('text', '').strip()))
                elif itype == 'BreadcrumbList':
                    for elem in item.get('itemListElement', []):
                        json_breadcrumbs.append(elem.get('name', '').strip())
                elif itype == 'Article':
                    has_article_schema = True
                    article_data = {
                        'headline': item.get('headline'),
                        'description': item.get('description'),
                        'mainEntityOfPage': item.get('mainEntityOfPage'),
                        'url': item.get('url'),
                        'author': item.get('author'),
                        'datePublished': item.get('datePublished'),
                    }
        except Exception as e:
            print(f'{fname}: JSON parse error: {e}')

    # Find visible FAQs
    soup = BeautifulSoup(content, 'html.parser')
    faq_section = None
    for sec in soup.find_all('section'):
        h2 = sec.find(['h2', 'h3'])
        if h2 and 'faq' in h2.text.lower():
            faq_section = sec
            break
    visible_faqs = []
    if faq_section:
        for h3 in faq_section.find_all('h3'):
            p = h3.find_next_sibling('p')
            visible_faqs.append((h3.text.strip(), p.text.strip() if p else ''))

    # Find visible breadcrumbs
    nav = soup.find('nav', attrs={'aria-label': 'Breadcrumb'})
    visible_breadcrumbs = []
    if nav:
        for tag in nav.find_all(['a', 'span']):
            t = tag.text.strip()
            if t and t != '/':
                visible_breadcrumbs.append(t)

    print(f'=== {fname} ===')
    print(f'  Breadcrumbs: JSON={json_breadcrumbs} | VIS={visible_breadcrumbs}')
    b_match = (json_breadcrumbs == visible_breadcrumbs)
    if not b_match:
        print(f'  [BREADCRUMB MISMATCH]')
    print(f'  Article Schema: {has_article_schema}')
    print(f'  Has FAQ Schema: {has_faq_schema} ({len(json_faqs)}) | Visible FAQs: {bool(faq_section)} ({len(visible_faqs)})')
    if has_faq_schema or visible_faqs:
        if len(json_faqs) != len(visible_faqs):
            print(f'    [WARNING] Count mismatch: schema={len(json_faqs)} vs visible={len(visible_faqs)}')
        for idx in range(max(len(json_faqs), len(visible_faqs))):
            jq = json_faqs[idx][0] if idx < len(json_faqs) else '<NONE>'
            vq = visible_faqs[idx][0] if idx < len(visible_faqs) else '<NONE>'
            ja = json_faqs[idx][1] if idx < len(json_faqs) else '<NONE>'
            va = visible_faqs[idx][1] if idx < len(visible_faqs) else '<NONE>'
            q_match = (jq.strip() == vq.strip())
            a_match = (ja.strip() == va.strip())
            if not q_match or not a_match:
                print(f'    [MISMATCH] Q{idx+1}:')
                print(f'      Schema Q: {jq}')
                print(f'      Visible Q: {vq}')
                print(f'      Schema A: {ja[:60]}...')
                print(f'      Visible A: {va[:60]}...')
