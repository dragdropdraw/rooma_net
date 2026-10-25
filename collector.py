import urllib.request
import base64
import re

# لیست منابع (لینک‌های سابسکریپشن عمومی گیت‌هاب یا کانال‌ها)
SOURCES = [
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    # منابع بیشتر را اینجا اضافه کنید
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
    pattern = r'(vmess|vless|trojan|ss|ssr|hy2|hysteria2|tuic)://[^\s<>"]+'
    
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8', errors='ignore')
                # اگر محتوا Base64 بود دیکود شود
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
