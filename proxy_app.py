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

        # إنشاء Session للحفاظ على الكوكيز وحالة الاتصال
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://natega.elwatannews.com/'
        })

        target_url = "https://natega.elwatannews.com/"

        # 1. فتح الصفحة الرئيسية عبر GET لجلب أية حقول مخفية وكوكيز
        get_response = session.get(target_url, timeout=10)
        
        payload = {'seating_no': seating_no}

        if get_response.status_code == 200:
            soup_get = BeautifulSoup(get_response.text, 'html.parser')
            # البحث عن أشكال الـ form وحقول الحماية المخفية إن وجدت
            form = soup_get.find('form')
            if form:
                action = form.get('action')
                if action and action != '/':
                    if action.startswith('http'):
                        target_url = action
                    else:
                        target_url = f"https://natega.elwatannews.com{action}"
                
                # إدراج جميع الحقول المخفية داخل الـ payload
                for hidden_input in form.find_all('input', type='hidden'):
                    name = hidden_input.get('name')
                    value = hidden_input.get('value', '')
                    if name:
                        payload[name] = value

        # 2. إرسال طلب البحث الآن
        response = session.post(target_url, data=payload, timeout=15)

        # إذا رفض الـ POST، نقوم بتجربة GET المباشرة بالـ Query Parameter كحل بديل
        if response.status_code == 405:
            response = session.get(f"https://natega.elwatannews.com/?seating_no={seating_no}", timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            if "رقم الجلوس غير صحيح" in page_text:
                return jsonify({
                    "status": "error",
                    "message": "رقم الجلوس غير صحيح أو غير متوفر حالياً"
                }), 404

            student_name = "غير متوفر"
            total_marks = "غير متوفر"

            # محاولة استخراج الاسم والمجموع
            for tag in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'td']):
                txt = tag.text.strip()
                if "اسم الطالب" in txt or "الاسم" in txt:
                    student_name = txt
                if "المجموع" in txt or "الدرجة" in txt:
                    total_marks = txt

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "total": total_marks,
                "raw_preview": page_text[:300]
            })
        else:
            return jsonify({"status": "error", "message": f"Status code: {response.status_code}"}), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
