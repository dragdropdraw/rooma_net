import json
import base64
import urllib.parse
import urllib.request
import socket
import time
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

BRAND_NAME = "@Rooma_Net"
HEADER_MESSAGE = "📢 عضویت در کانال: @Rooma_Net"

# ۵ کشور مجاز: آمریکا، آلمان، استرالیا، ژاپن، بریتانیا
ALLOWED_COUNTRIES = {"DE", "PL", "NL", "IR", "GB"}

socket.setdefaulttimeout(2.0)

def get_iran_time():
    iran_tz = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(iran_tz).strftime("%Y/%m/%d - %H:%M")

def create_fake_config(remark_text):
    encoded = urllib.parse.quote(remark_text)
    return f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none&type=tcp#{encoded}"

def get_flagEmoji(country_code):
    if not country_code or len(country_code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def extract_host_port(link):
    try:
        # چون فقط vless داریم، استخراج هاست و پورت دقیق‌تر انجام می‌شود
        match = re.search(r"@([^:?/#\s]+):(\d+)", link)
        if match:
            return match.group(1).strip(), int(match.group(2))
    except Exception:
        pass
    return "", 0

def test_single_config(link):
    host, port = extract_host_port(link)
    if not host or not port or host in ["127.0.0.1", "localhost", "0.0.0.0"]:
        return None
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=1.5) as sock:
            ping = int((time.time() - start) * 1000)
            ip = sock.getpeername()[0]
            if 5 < ping < 1200:
                return {"link": link, "host": host, "ip": ip, "ping": ping}
    except Exception:
        pass
    return None

def filter_by_allowed_countries(nodes):
    ips_to_query = list({node["ip"] for node in nodes if node.get("ip")})
    ip_to_country = {}

    for i in range(0, len(ips_to_query), 100):
        batch = ips_to_query[i:i+100]
        try:
            req_data = json.dumps([{"query": ip, "fields": "countryCode,query"} for ip in batch]).encode("utf-8")
            req = urllib.request.Request(
                "http://ip-api.com/batch",
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                for item in json.loads(resp.read().decode("utf-8")):
                    ip_to_country[item.get("query")] = item.get("countryCode", "")
        except Exception:
            pass

    filtered = []
    for node in nodes:
        cc = ip_to_country.get(node["ip"], "")
        if cc in ALLOWED_COUNTRIES:
            flag = get_flagEmoji(cc)
            node["country_label"] = f"{flag} {cc}"
            filtered.append(node)
    return filtered

def rename_config(link, new_remark):
    try:
        # بازنویسی نام نمایشی برای لینک‌های vless
        base_link = link.split("#")[0]
        return f"{base_link}#{urllib.parse.quote(new_remark)}"
    except Exception:
        return link

def main():
    try:
        with open("raw_configs.txt", "r", encoding="utf-8") as f:
            raw_links = [line.strip() for line in f if line.strip()]
    except Exception:
        return

    # فیلتر بسیار مهم: فقط و فقط لینک‌هایی که با vless:// شروع می‌شوند
    vless_links = [link for link in raw_links if link.startswith("vless://")]
    print(f"Total VLESS configs found: {len(vless_links)}")

    random.shuffle(vless_links)
    links_to_test = vless_links[:2000] # تست روی حداکثر ۲۰۰۰ کانفیگ Vless
    print(f"Testing {len(links_to_test)} VLESS configs...")

    working = []
    with ThreadPoolExecutor(max_workers=80) as executor:
        futures = [executor.submit(test_single_config, link) for link in links_to_test]
        for future in as_completed(futures):
            res = future.result()
            if res:
                working.append(res)

    print(f"Responsive VLESS configs: {len(working)}")

    country_filtered = filter_by_allowed_countries(working)
    print(f"VLESS configs matching 5 countries (DE, PL, NL, IR, GB): {len(country_filtered)}")

    country_filtered.sort(key=lambda x: x["ping"])
    top_nodes = country_filtered[:100]

    final_configs = [
        create_fake_config(HEADER_MESSAGE),
        create_fake_config(f"🔄 آخرین بروزرسانی: {get_iran_time()}")
    ]

    for idx, node in enumerate(top_nodes, start=1):
        new_name = f"{node['country_label']} | ⚡ {node['ping']}ms | #{idx} | {BRAND_NAME}"
        final_configs.append(rename_config(node["link"], new_name))

    raw_text = "\n".join(final_configs)
    b64_text = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(b64_text)

    print(f"Successfully saved {len(top_nodes)} top VLESS configs to sub.txt!")

if __name__ == "__main__":
    main()
