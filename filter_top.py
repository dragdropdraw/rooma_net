import json
import base64
import urllib.parse
import urllib.request
import subprocess
import socket
import time
import re
import os
import random
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone, timedelta

BRAND_NAME = "@Rooma_Net"
HEADER_MESSAGE = "📢 عضویت در کانال: @Rooma_Net"

# ۵ کشور مجاز: آمریکا، آلمان، استرالیا، ژاپن، بریتانیا
ALLOWED_COUNTRIES = {"US", "DE", "AU", "JP", "GB"}

socket.setdefaulttimeout(2.5)

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

def parse_link_to_xray_outbound(link):
    """تبدیل لینک کانفیگ به فرمت استاندارد هسته Xray برای تست واقعی"""
    try:
        if link.startswith("vmess://"):
            b64 = link[8:]
            padded = b64 + "=" * ((4 - len(b64) % 4) % 4)
            v = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            host = v.get("add", "")
            port = int(v.get("port", 443))
            net = v.get("net", "tcp")
            tls = v.get("tls", "")
            
            # فقط کانفیگ‌های دارای TLS یا WS که در ایران فیلتر نیستند
            if tls != "tls" and net not in ["ws", "grpc"]:
                return None, ""

            outbound = {
                "protocol": "vmess",
                "settings": {"vnext": [{"address": host, "port": port, "users": [{"id": v.get("id"), "alterId": 0, "security": "auto"}]}]},
                "streamSettings": {"network": net, "security": "tls" if tls == "tls" else "none"}
            }
            if tls == "tls":
                outbound["streamSettings"]["tlsSettings"] = {"serverName": v.get("sni") or v.get("host") or host, "allowInsecure": True}
            if net == "ws":
                outbound["streamSettings"]["wsSettings"] = {"path": v.get("path", "/"), "headers": {"Host": v.get("host") or host}}
            elif net == "grpc":
                outbound["streamSettings"]["grpcSettings"] = {"serviceName": v.get("path", "")}
            return outbound, host

        elif link.startswith("vless://") or link.startswith("trojan://"):
            proto = "vless" if link.startswith("vless://") else "trojan"
            parsed = urllib.parse.urlsplit(link)
            if not parsed.hostname or not parsed.port:
                return None, ""
            
            user = parsed.username
            host = parsed.hostname
            port = parsed.port
            params = dict(urllib.parse.parse_qsl(parsed.query))
            
            sec = params.get("security", "none")
            net = params.get("type", "tcp")
            
            # حذف کانفیگ‌های خام بدون امنیت که در ایران مسدودند
            if sec not in ["tls", "reality"] and net not in ["ws", "grpc"]:
                return None, ""

            if proto == "vless":
                settings = {"vnext": [{"address": host, "port": port, "users": [{"id": user, "encryption": "none", "flow": params.get("flow", "")}]}]}
            else:
                settings = {"servers": [{"address": host, "port": port, "password": user}]}

            stream = {"network": net, "security": sec}
            sni = params.get("sni") or params.get("host") or host
            
            if sec == "tls":
                stream["tlsSettings"] = {"serverName": sni, "allowInsecure": True}
            elif sec == "reality":
                stream["realitySettings"] = {
                    "serverName": sni,
                    "publicKey": params.get("pbk", ""),
                    "shortId": params.get("sid", ""),
                    "fingerprint": params.get("fp", "chrome")
                }

            if net == "ws":
                stream["wsSettings"] = {"path": params.get("path", "/"), "headers": {"Host": params.get("host", host)}}
            elif net == "grpc":
                stream["grpcSettings"] = {"serviceName": params.get("serviceName", "")}

            return {"protocol": proto, "settings": settings, "streamSettings": stream}, host
    except Exception:
        pass
    return None, ""

def test_real_xray_connection(item):
    idx, link = item
    outbound, host = parse_link_to_xray_outbound(link)
    if not outbound or not host or host in ["127.0.0.1", "localhost", "0.0.0.0"]:
        return None

    try:
        ip = socket.gethostbyname(host)
    except Exception:
        return None

    socks_port = 20000 + idx
    config = {
        "log": {"loglevel": "none"},
        "inbounds": [{"port": socks_port, "listen": "127.0.0.1", "protocol": "http"}],
        "outbounds": [outbound]
    }
    
    cfg_file = f"temp_{idx}.json"
    with open(cfg_file, "w") as f:
        json.dump(config, f)

    proc = None
    try:
        proc = subprocess.Popen(["./xray", "run", "-c", cfg_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.6) # زمان راه‌اندازی هسته
        
        proxy_handler = urllib.request.ProxyHandler({"http": f"http://127.0.0.1:{socks_port}", "https": f"http://127.0.0.1:{socks_port}"})
        opener = urllib.request.build_opener(proxy_handler)
        
        start = time.time()
        # ارسال درخواست واقعی به گوگل از داخل تانل V2Ray
        with opener.open("http://www.gstatic.com/generate_204", timeout=3.0) as resp:
            if resp.status in [200, 204]:
                ping = int((time.time() - start) * 1000)
                return {"link": link, "host": host, "ip": ip, "ping": ping}
    except Exception:
        pass
    finally:
        if proc:
            proc.kill()
        if os.path.exists(cfg_file):
            os.remove(cfg_file)
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
    except Exception:
        return

    random.shuffle(raw_links)
    # انتخاب ۳۵۰ کانفیگ برای تست واقعی با هسته Xray
    candidates = [(i, link) for i, link in enumerate(raw_links[:350])]
    print(f"Testing {len(candidates)} configs with real Xray core...")

    working = []
    executor = ThreadPoolExecutor(max_workers=35)
    futures = [executor.submit(test_real_xray_connection, item) for item in candidates]
    
    done, _ = wait(futures, timeout=75.0)
    for future in done:
        try:
            res = future.result()
            if res:
                working.append(res)
        except Exception:
            pass
    executor.shutdown(wait=False, cancel_futures=True)

    print(f"Real working Xray configs found: {len(working)}")

    country_filtered = filter_by_allowed_countries(working)
    print(f"Matching 5 countries (US, DE, AU, JP, GB): {len(country_filtered)}")

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

    print(f"Saved {len(top_nodes)} real-tested configs to sub.txt!")

if __name__ == "__main__":
    main()
