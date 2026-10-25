import json
import base64
import urllib.parse
import urllib.request
import socket
import re
from datetime import datetime, timezone, timedelta

# نام برند، سایت یا آیدی کانال خود را اینجا بنویسید
BRAND_NAME = "@Rooma_Net"
# پیام دلخواه برای ردیف اول (مثلاً آدرس کانال یا سایت)
HEADER_MESSAGE = "📢 عضویت در کانال: @Rooma_Net"

def get_iran_time():
    # محاسبه زمان دقیق ایران (UTC + 3:30)
    iran_tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(iran_tz)
    return now.strftime("%Y/%m/%d - %H:%M")

def create_fake_config(remark_text):
    # ساخت یک کانفیگ نمایشی در بالای لیست که فقط متن دلخواه را نشان می‌دهد
    encoded_remark = urllib.parse.quote(remark_text)
    return f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none&type=tcp#{encoded_remark}"

def get_flagEmoji(country_code):
    if not country_code or len(country_code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def extract_host(link):
    try:
        if link.startswith("vmess://"):
            b64 = link[8:]
            padded = b64 + "=" * ((4 - len(b64) % 4) % 4)
            data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            return data.get("add", "")
        else:
            match = re.search(r"@([^:?/#]+)", link)
            if match:
                return match.group(1)
    except Exception:
        pass
    return ""

def resolve_ips_and_countries(links):
    host_to_ip = {}
    ips_to_query = set()
    link_to_host = {}

    for link in links:
        host = extract_host(link)
        link_to_host[link] = host
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
                results = json.loads(resp.read().decode("utf-8"))
                for item in results:
                    ip_to_country[item.get("query")] = item.get("countryCode", "")
        except Exception as e:
            print(f"GeoIP Lookup Error: {e}")

    link_to_flag = {}
    for link, host in link_to_host.items():
        ip = host_to_ip.get(host)
        cc = ip_to_country.get(ip, "")
        flag = get_flagEmoji(cc)
        country_label = f"{flag} {cc}" if cc else "🌐 UNK"
        link_to_flag[link] = country_label

    return link_to_flag

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
            encoded_remark = urllib.parse.quote(new_remark)
            return f"{base_link}#{encoded_remark}"
    except Exception:
        return link

def save_top_100():
    try:
        with open("output.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        working = [node for node in data.get("nodes", []) if node.get("ping", 0) > 0]
        working.sort(key=lambda x: x["ping"])
        
        top_nodes = working[:100]
        raw_links = [node["link"] for node in top_nodes]
        
        flags_map = resolve_ips_and_countries(raw_links)
        
        final_configs = []
        
        # ۱. اضافه کردن کانفیگ‌های نمایشی (اطلاعات و ساعت بروزرسانی) در بالای لیست
        update_time = get_iran_time()
        final_configs.append(create_fake_config(HEADER_MESSAGE))
        final_configs.append(create_fake_config(f"🔄 آخرین بروزرسانی: {update_time}"))
        
        # ۲. اضافه کردن ۱۰۰ کانفیگ اصلی تست‌شده
        for idx, node in enumerate(top_nodes, start=1):
            link = node["link"]
            ping = node["ping"]
            country_info = flags_map.get(link, "🌐")
            
            new_name = f"{country_info} | ⚡ {ping}ms | #{idx} | {BRAND_NAME}"
            renamed_link = rename_config(link, new_name)
            final_configs.append(renamed_link)
        
        # ذخیره خروجی نهایی به صورت Base64
        raw_text = "\n".join(final_configs)
        b64_text = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
        
        with open("sub.txt", "w", encoding="utf-8") as f:
            f.write(b64_text)
            
        print(f"Successfully processed {len(top_nodes)} configs with header info.")
    except Exception as e:
        print(f"Error processing results: {e}")

if __name__ == "__main__":
    save_top_100()
