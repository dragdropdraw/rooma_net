import urllib.request
import base64
import json
import re

# منابع معتبر که کانفیگ‌های پاک و ضد فیلتر (Reality و Cloudflare) منتشر می‌کنند
SOURCES = [
    "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/Vless",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/mix",
    "https://raw.githubusercontent.com/matinghanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt"
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
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read().decode('utf-8', errors='ignore')
                if "://" not in content:
                    content = decode_base64(content)
                
                for line in content.splitlines():
                    line = line.strip()
                    # فقط استخراج لینک‌های vless
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
