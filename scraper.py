
import os, json, re, random
from collections import Counter
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, messaging

BASE_URL = "https://www.lotto-8.com/Vietnam/listltoVM35.asp?indexpage={}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def crawl_lotto_535(pages=5):
    results = []
    for p in range(1, pages+1):
        try:
            r = requests.get(BASE_URL.format(p), headers=HEADERS, timeout=15)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            for tr in soup.find_all('tr'):
                text = tr.get_text(" ", strip=True)
                m = re.search(r'(\d{5}).*?(\d{1,2},\s*\d{1,2},\s*\d{1,2},\s*\d{1,2},\s*\d{1,2})\s+(\d{1,2})', text)
                if m:
                    ky = m.group(1)
                    nums = [int(x.strip()) for x in m.group(2).split(',')]
                    dac_biet = int(m.group(3))
                    if len(nums)==5 and 1 <= dac_biet <=12:
                        results.append({"ky": ky, "nums": nums, "db": dac_biet})
        except Exception as e:
            print(f"Loi trang {p}: {e}")
    return results

def predict_next(results):
    all_nums = [n for r in results for n in r['nums']]
    all_db = [r['db'] for r in results]
    freq = Counter(all_nums)
    freq_db = Counter(all_db)
    hot_5 = [n for n,_ in freq.most_common(10)] or list(range(1,11))
    last_seen = {i: 999 for i in range(1,36)}
    for idx, r in enumerate(results):
        for n in r['nums']:
            if last_seen[n]==999:
                last_seen[n]=idx
    cold_5 = sorted(last_seen, key=lambda x: last_seen[x])[:10]
    def gen_set(pool):
        s = sorted(random.sample(pool, 5))
        db = random.choice([n for n,_ in freq_db.most_common(6)])[0] if freq_db else random.randint(1,12)
        return s, db
    pred1 = gen_set(hot_5)
    pred2 = gen_set(cold_5)
    pred3 = (sorted(random.sample(range(1,36),5)), random.randint(1,12))
    return freq, freq_db, [pred1, pred2, pred3]

def send_fcm(message_text):
    fb_creds = json.loads(os.environ["FIREBASE_CREDENTIALS"])
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(fb_creds))
    token = os.environ["MY_APP_DEVICE_TOKEN"]
    msg = messaging.Message(
        notification=messaging.Notification(title="🎯 LOTTO 5/35 - Cap nhat", body=message_text),
        token=token,
        android=messaging.AndroidConfig(priority='high')
    )
    print(messaging.send(msg))

if __name__ == "__main__":
    data = crawl_lotto_535(pages=5)
    print(f"Cao duoc {len(data)} ky")
    if not data:
        exit(0)
    latest = data[0]
    freq, freq_db, preds = predict_next(data)
    text = f"Ky moi nhat #{latest['ky']}: {latest['nums']} DB:{latest['db']}\nDu doan:\n1) {preds[0][0]} + DB {preds[0][1]}\n2) {preds[1][0]} + DB {preds[1][1]}\n3) {preds[2][0]} + DB {preds[2][1]}"
    print(text)
    send_fcm(text)
