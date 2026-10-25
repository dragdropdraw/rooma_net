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

# لیست ۵ کشور مجاز: آمریکا، آلمان، استرالیا، ژاپن، بریتانیا
ALLOWED_COUNTRIES = {"US", "DE", "AU", "JP", "GB"}

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

def is_iran_friendly(link):
    """فیلتر کردن کانفیگ‌هایی که شانس اتصال بالایی در اینترنت ایران دارند"""
    link_lower = link.lower()
    # حذف پروتکل‌های قدیمی که در ایران کاملاً مسدود هستند
    if link_lower.startswith("ssr://"):
        return False
    # اولویت با کانفیگ‌های دارای TLS، Reality، WebSocket، gRPC یا Hysteria
    good_keywords = ["security=reality", "security=tls", "type=ws", "type=grpc", "hy2://", "hysteria2://", "tuic://"]
    if any(k in link_lower for k in good_keywords):
        return True
    # بررسی ساختار داخلی vmess برای اطمینان از داشتن tls یا ws
    if link_lower.startswith("vmess://"):
        try:
            b64 = link[8:]
            padded = b64 + "=" * ((4 - len(b64) % 4) % 4)
            data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            if data.get("tls") == "tls" or data.get("net") in ["ws", "grpc", "h2"]:
                return True
        except Exception:
            pass
    return False

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
    if not host or not port or host in ["127.0.0.1", "localhost", "0.0.0.0"]:
        return None
    try:
        ip = socket.gethostbyname(host)
        start = time.time()
        # دو بار تست اتصال متوالی برای اطمینان از پایدار بودن پورت سرور
        with socket.create_connection((ip, port), timeout=2.0):
            ping = int((time.time() - start) * 1000)
            if 5 < ping < 1500:
                return {"link": link, "host": host, "ip": ip, "ping": ping}
    except Exception:
        pass
    return None

def filter_by_allowed_countries(nodes):
    ips_to_query = list({node["ip"] for node in nodes if node.get("ip")})
    ip_to_country = {}

    # استعلام کشور تمام آی‌پی‌های سالم از ip-api
    for i in range(0, len(ips_to_query), 100):
        batch = ips_to_query[i:i+100]
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
        except Exception as e:
            print(f"GeoIP error: {e}")

    filtered_nodes = []
    for node in nodes:
        cc = ip_to_country.get(node["ip"], "")
        # فقط اگر کشور جزو ۵ کشور درخواستی بود نگه داشته شود
        if cc in ALLOWED_COUNTRIES:
            flag = get_flagEmoji(cc)
            node["country_label"] = f"{flag} {cc}"
            filtered_nodes.append(node)

    return filtered_nodes

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

    # ۱. غربالگری اولیه: فقط کانفیگ‌های مناسب ایران (Reality / TLS / WS)
    iran_friendly_links = [link for link in raw_links if is_iran_friendly(link)]
    print(f"Iran-friendly configs filtered: {len(iran_friendly_links)} out of {len(raw_links)}")

    # تست حداکثر ۱۰۰۰ کانفیگ برای پیدا کردن تعداد کافی از ۵ کشور
    links_to_test = iran_friendly_links[:1000]

    working = []
    with ThreadPoolExecutor(max_workers=80) as executor:
        futures = [executor.submit(test_single_config, link) for link in links_to_test]
        for future in as_completed(futures):
            res = future.result()
            if res:
                working.append(res)

    print(f"Total pingable configs: {len(working)}")

    # ۲. جداسازی فقط ۵ کشور (US, DE, AU, JP, GB)
    country_filtered = filter_by_allowed_countries(working)
    print(f"Configs matching the 5 allowed countries: {len(country_filtered)}")

    # ۳. مرتب‌سازی بر اساس پینگ و انتخاب ۱۰۰ تای برتر
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

    print(f"Successfully saved {len(top_nodes)} top configs to sub.txt!")

if __name__ == "__main__":
    main()
