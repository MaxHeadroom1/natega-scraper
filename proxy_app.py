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
            return jsonify({"status": "error", "message": "يرجى إدخال رقم الجلوس"}), 400

        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
        }

        search_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
        response = session.get(search_url, headers=headers, timeout=15, allow_redirects=True)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # التحقق من أن النتيجة أعلنت أم أن الصفحة مجرد صفحة انتظار
            if "تسهيل الوصول إلى النتيجة" in page_text or "سجل بياناتك" in page_text and "المجموع الكلي" not in page_text:
                return jsonify({
                    "status": "pending",
                    "seating_no": seating_no,
                    "message": "النتيجة لم تظهر رسمياً بعد أو يتوجب تسجيل البيانات على الموقع أولاً."
                }), 200

            # 1. استخراج اسم الطالب
            student_name = "غير متوفر"
            name_tags = soup.find_all(['h1', 'h2', 'h3', 'div', 'td'], class_=lambda c: c and any(x in c.lower() for x in ['name', 'student']))
            for tag in name_tags:
                txt = tag.text.strip()
                if txt and "بيانات" not in txt and "نتيجة" not in txt:
                    student_name = txt
                    break

            # 2. استخراج المجموع
            total_marks = "غير متوفر"
            total_tags = soup.find_all(['div', 'span', 'td', 'p'], class_=lambda c: c and any(x in c.lower() for x in ['degree', 'total', 'score', 'result']))
            for tag in total_tags:
                txt = tag.text.strip()
                if txt and any(char.isdigit() for char in txt):
                    total_marks = txt
                    break

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "total": total_marks
            })
        else:
            return jsonify({
                "status": "error", 
                "message": f"تعذر الاتصال بالموقع المستهدف (رمز: {response.status_code})"
            }), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
