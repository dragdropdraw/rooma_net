import urllib.request
import base64
import re

# منابع گلچین شده مخصوص اینترنت ایران (تست شده روی اپراتورهای ایران و کلودفلر)
SOURCES = [
    # مخازن تخصصی Reality و Vless ضد فیلتر
    "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/Reality",
    "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/Vless",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/trojan.txt",
    
    # مخازن ایرانی که از کانال‌های تلگرامی تست‌شده در ایران جمع‌آوری می‌کنند
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/normal/mix",
    "https://raw.githubusercontent.com/matinghanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/reality",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt"
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
    pattern = r'^(vless|vmess|trojan)://[^\s<>"]+'
    
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
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
    print(f"Total unique configs fetched: {len(configs)}")
    with open("raw_configs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(configs))
