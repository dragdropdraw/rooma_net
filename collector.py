import urllib.request
import base64
import json
import re

# منابع فوق‌العاده قوی و آپدیت‌شده (استخراج‌شده از شبکه‌های تلگرامی و اسکنرهای فعال)
SOURCES = [
    # منبع تخصصی V2RayRoot (Vless جدا شده از چنل‌های تلگرام)
    "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/vless.txt",

     # پروژه معروف تجمیع خودکار سابسکریپشن VLESS و Reality
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2ray",
    
    # منبع بین‌المللی با آپدیت مداوم و حجم بالای کانفیگ‌های فعال
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/output/vless.txt",
    
    # مخازن کمکی معتبر
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/vless",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless"
]

def decode_base64(data):
    try:
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.b64decode(data).decode('utf-8', errors='ignore')
    except Exception:
        return data

def fetch_configs():
    raw_configs = set()
    pattern = r'^vless://[^\s<>"]+'
    
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8', errors='ignore')
                if "://" not in content:
                    content = decode_base64(content)
                
                for line in content.splitlines():
                    line = line.strip()
                    if re.match(pattern, line):
                        raw_configs.add(line)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            
    return list(raw_configs)

if __name__ == "__main__":
    configs = fetch_configs()
    print(f"Total VLESS configs fetched: {len(configs)}")
    with open("raw_configs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(configs))
