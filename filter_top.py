import json
import base64

def save_top_100():
    try:
        with open("output.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # فیلتر کردن کانفیگ‌های سالم که پینگ بالای صفر دارند
        working = [node for node in data.get("nodes", []) if node.get("ping", 0) > 0]
        
        # مرتب‌سازی بر اساس کمترین پینگ
        working.sort(key=lambda x: x["ping"])
        
        # انتخاب ۱۰۰ کانفیگ برتر
        top_100 = [node["link"] for node in working[:100]]
        
        # ذخیره به صورت متن عادی و Base64 (مناسب کلاینت‌های V2rayNG / Streisand)
        raw_text = "\n".join(top_100)
        b64_text = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
        
        with open("sub.txt", "w", encoding="utf-8") as f:
            f.write(b64_text)
            
        print(f"Successfully saved {len(top_100)} best configs.")
    except Exception as e:
        print(f"Error processing results: {e}")

if __name__ == "__main__":
    save_top_100()
