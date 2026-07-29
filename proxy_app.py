import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "success", "message": "API scraper is running successfully!"})

@app.route('/get_result', methods=['POST'])
def get_result():
    try:
        data = request.get_json(silent=True) or {}
        seating_no = data.get('seating_no')

        if not seating_no:
            return jsonify({"status": "error", "message": "Please provide seating_no"}), 400

        session = requests.Session()
        
        # headers شاملة لإيهام السيرفر بأن الطلب من متصفح عادي
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }

        # 1. فتح الصفحة الرئيسية أولاً لمعرفة الرابط الذي يتم التوجيه إليه
        base_url = "https://natega.elwatannews.com/"
        main_resp = session.get(base_url, headers=headers, timeout=10, allow_redirects=True)

        # الرابط النهائي بعد التحويلات (Redirects)
        final_url = main_resp.url

        # 2. إرسال طلب البحث عبر GET أولاً
        search_url = f"{final_url.rstrip('/')}/?seating_no={seating_no}"
        response = session.get(search_url, headers=headers, timeout=15, allow_redirects=True)

        # 3. إذا لم ينجح GET، نجرب POST على الرابط الفعلي
        if response.status_code != 200:
            payload = {'seating_no': seating_no}
            response = session.post(final_url, data=payload, headers=headers, timeout=15, allow_redirects=True)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text(separator=' ', strip=True)

            student_name = "غير متوفر"
            total_marks = "غير متوفر"

            # محاولة قراءة البيانات
            for tag in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'td']):
                txt = tag.text.strip()
                if "اسم" in txt and len(txt) < 50:
                    student_name = txt
                if "المجموع" in txt or "درجة" in txt:
                    total_marks = txt

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "total": total_marks,
                "fetched_url": response.url
            })
        else:
            return jsonify({
                "status": "error", 
                "message": f"Target server returned HTTP {response.status_code}",
                "attempted_url": response.url
            }), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
