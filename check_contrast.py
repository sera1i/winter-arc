import os
import sys
import json
import urllib.request
import subprocess
from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'

def wait_for_server(url, timeout=10):
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status in (200, 302):
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def check_contrast():
    server_process = None
    if not wait_for_server(f"{BASE_URL}/", timeout=2):
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        wait_for_server(f"{BASE_URL}/", timeout=15)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.goto(f"{BASE_URL}/", wait_until="load")
            page.wait_for_timeout(3500) # wait for loader to hide

            contrast_issues = page.evaluate("""() => {
                function parseColor(c) {
                    const match = c.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
                    if (!match) return [0, 0, 0, 1];
                    return [
                        parseInt(match[1]),
                        parseInt(match[2]),
                        parseInt(match[3]),
                        match[4] !== undefined ? parseFloat(match[4]) : 1
                    ];
                }

                function luminance(r, g, b) {
                    const a = [r, g, b].map(v => {
                        v /= 255;
                        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                    });
                    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
                }

                function contrastRatio(lum1, lum2) {
                    const lighter = Math.max(lum1, lum2);
                    const darker = Math.min(lum1, lum2);
                    return (lighter + 0.05) / (darker + 0.05);
                }

                function blend(fg, bg) {
                    const alpha = fg[3];
                    const inv = 1 - alpha;
                    return [
                        Math.round(fg[0] * alpha + bg[0] * inv),
                        Math.round(fg[1] * alpha + bg[1] * inv),
                        Math.round(fg[2] * alpha + bg[2] * inv),
                        1
                    ];
                }

                function getEffectiveBg(el) {
                    const stack = [];
                    let cur = el;
                    while (cur && cur !== document.documentElement) {
                        const style = window.getComputedStyle(cur);
                        const bg = parseColor(style.backgroundColor);
                        if (bg[3] > 0) {
                            stack.unshift(bg);
                        }
                        cur = cur.parentElement;
                    }
                    // Determine base root color: default to [11, 13, 18] (ink) or [244, 241, 236] if bone
                    let result = [11, 13, 18, 1];
                    for (const layer of stack) {
                        result = blend(layer, result);
                    }
                    return result;
                }

                const issues = [];
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                let node;
                while (node = walker.nextNode()) {
                    if (node.id === 'wa-loader' || node.closest('#wa-loader')) continue;
                    // Only check leaf or text-containing elements
                    if (node.children.length === 0 && node.textContent.trim().length > 0) {
                        const style = window.getComputedStyle(node);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
                        
                        const rect = node.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;

                        const rawFg = parseColor(style.color);
                        const bg = getEffectiveBg(node);
                        const fg = blend(rawFg, bg);

                        const lumFg = luminance(fg[0], fg[1], fg[2]);
                        const lumBg = luminance(bg[0], bg[1], bg[2]);
                        const ratio = contrastRatio(lumFg, lumBg);

                        const fontSize = parseFloat(style.fontSize);
                        const isBold = parseInt(style.fontWeight) >= 700 || style.fontWeight === 'bold';
                        const isLarge = fontSize >= 24 || (fontSize >= 18.66 && isBold);
                        const req = isLarge ? 3.0 : 4.5;

                        if (ratio < req) {
                            issues.push({
                                tag: node.tagName,
                                text: node.textContent.trim().substring(0, 50),
                                selector: node.className,
                                fg: `rgb(${fg[0]}, ${fg[1]}, ${fg[2]})`,
                                bg: `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`,
                                ratio: Math.round(ratio * 100) / 100,
                                required: req,
                                fontSize: style.fontSize
                            });
                        }
                    }
                }
                return issues;
            }""")

            print(f"Detected {len(contrast_issues)} potential text contrast issues:")
            for issue in contrast_issues:
                clean_text = issue['text'].encode('ascii', errors='replace').decode('ascii')
                print(f"  - [{issue['tag']}] '{clean_text}' | Ratio: {issue['ratio']}:1 (req {issue['required']}:1) | FG: {issue['fg']} on BG: {issue['bg']} | Class: {issue['selector'][:40]}")

            browser.close()
    finally:
        if server_process:
            server_process.kill()

if __name__ == "__main__":
    check_contrast()
