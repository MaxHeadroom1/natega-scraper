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

        target_url = "https://natega.elwatannews.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://natega.elwatannews.com/'
        }
        
        payload = {
            'seating_no': seating_no,
            'seating_no_btn': 'بحث'
        }

        # إرسال طلب POST ببيانات النموذج
        response = requests.post(target_url, data=payload, headers=headers, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # التحقق مما إذا كان رقم الجلوس خاطئاً أو غير موجود
            if "رقم الجلوس غير صحيح" in page_text:
                return jsonify({
                    "status": "error",
                    "message": "رقم الجلوس غير صحيح أو غير متوفر حالياً"
                }), 404

            # استخراج اسم الطالب والمجموع في حال توفرهم
            student_name = "غير متوفر"
            total_marks = "غير متوفر"

            # البحث عن عناصر النتيجة في عناصر الـ HTML
            name_elem = soup.find(class_=lambda c: c and 'name' in c.lower()) or soup.find('h3')
            if name_elem and "بيانات" not in name_elem.text:
                student_name = name_elem.text.strip()

            degree_elem = soup.find(class_=lambda c: c and any(x in c.lower() for x in ['degree', 'total', 'mark']))
            if degree_elem:
                total_marks = degree_elem.text.strip()

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "total": total_marks
            })
        else:
            return jsonify({"status": "error", "message": f"Status code: {response.status_code}"}), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
