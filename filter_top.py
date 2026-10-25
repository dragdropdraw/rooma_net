import json
import base64
import urllib.parse
import urllib.request
import socket
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

# نام برند، سایت یا آیدی کانال خود را اینجا بنویسید
BRAND_NAME = "@Rooma_Net"
HEADER_MESSAGE = "📢 عضویت در کانال: @Rooma_Net"

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
        if link.startswith("vmess://"):
            b64 = link[8:]
            padded = b64 + "=" * ((4 - len(b64) % 4) % 4)
            data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            return data.get("add", ""), int(data.get("port", 443))
        else:
            match = re.search(r"@([^:?/#]+):(\d+)", link)
            if match:
                return match.group(1), int(match.group(2))
    except Exception:
        pass
    return "", 0

def test_single_config(link):
    host, port = extract_host_port(link)
    if not host or not port or host == "127.0.0.1":
        return None
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=2.5):
            ping = int((time.time() - start) * 1000)
            if 5 < ping < 2000:
                return {"link": link, "host": host, "ping": ping}
    except Exception:
        pass
    return None

def resolve_countries(nodes):
    host_to_ip = {}
    ips_to_query = set()

    for node in nodes:
        host = node["host"]
        if host and host not in host_to_ip:
            try:
                ip = socket.gethostbyname(host)
                host_to_ip[host] = ip
                ips_to_query.add(ip)
            except Exception:
                host_to_ip[host] = None

    ip_to_country = {}
    ip_list = list(ips_to_query)
    for i in range(0, len(ip_list), 100):
        batch = ip_list[i:i+100]
        try:
            req_data = json.dumps([{"query": ip, "fields": "countryCode,query"} for ip in batch]).encode("utf-8")
            req = urllib.request.Request(
                "http://ip-api.com/batch",
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                for item in json.loads(resp.read().decode("utf-8")):
                    ip_to_country[item.get("query")] = item.get("countryCode", "")
        except Exception:
            pass

    host_to_flag = {}
    for host, ip in host_to_ip.items():
        cc = ip_to_country.get(ip, "")
        flag = get_flagEmoji(cc)
        host_to_flag[host] = f"{flag} {cc}" if cc else "🌐 UNK"

    return host_to_flag

def rename_config(link, new_remark):
    try:
        if link.startswith("vmess://"):
            b64 = link[8:]
            padded = b64 + "=" * ((4 - len(b64) % 4) % 4)
            data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            data["ps"] = new_remark
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            return f"vmess://{new_b64}"
        else:
            base_link = link.split("#")[0]
            return f"{base_link}#{urllib.parse.quote(new_remark)}"
    except Exception:
        return link

def main():
    try:
        with open("raw_configs.txt", "r", encoding="utf-8") as f:
            raw_links = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading raw_configs.txt: {e}")
        return

    # تست حداکثر ۶۰۰ کانفیگ به صورت همزمان با سرعت بالا
    links_to_test = raw_links[:600]
    print(f"Testing {len(links_to_test)} configs...")

    working = []
    with ThreadPoolExecutor(max_workers=60) as executor:
        futures = [executor.submit(test_single_config, link) for link in links_to_test]
        for future in as_completed(futures):
            res = future.result()
            if res:
                working.append(res)

    print(f"Working configs found: {len(working)}")
    working.sort(key=lambda x: x["ping"])
    top_nodes = working[:100]

    host_flags = resolve_countries(top_nodes)

    final_configs = [
        create_fake_config(HEADER_MESSAGE),
        create_fake_config(f"🔄 آخرین بروزرسانی: {get_iran_time()}")
    ]

    for idx, node in enumerate(top_nodes, start=1):
        country_info = host_flags.get(node["host"], "🌐 UNK")
        new_name = f"{country_info} | ⚡ {node['ping']}ms | #{idx} | {BRAND_NAME}"
        final_configs.append(rename_config(node["link"], new_name))

    raw_text = "\n".join(final_configs)
    b64_text = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(b64_text)

    print(f"Successfully saved {len(top_nodes)} top configs to sub.txt!")

if __name__ == "__main__":
    main()
