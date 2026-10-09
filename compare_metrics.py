import json

b = json.load(open('baseline_metrics.json'))
o = json.load(open('optimized_metrics.json'))

for device in ['Desktop', 'Mobile']:
    for mode in ['cold', 'warm']:
        print(f"\n### {device} — {mode.upper()} Navigation\n")
        print("| Route | Server TTFB (Before -> After) | DCL (Before -> After) | Usable (Before -> After) | HTML Size | Requests |")
        print("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for route in b[device][mode]:
            bm = b[device][mode][route]
            om = o[device][mode][route]
            print(f"| {route} | {bm['server_response_time_ms']}ms -> **{om['server_response_time_ms']}ms** | {bm['dom_content_loaded_ms']}ms -> **{om['dom_content_loaded_ms']}ms** | {bm['time_to_visually_usable_ms']}ms -> **{om['time_to_visually_usable_ms']}ms** | {bm['html_response_size_bytes']}B -> {om['html_response_size_bytes']}B | {bm['network_requests_count']} -> {om['network_requests_count']} |")
