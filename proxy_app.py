import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "success",
        "message": "API scraper is running successfully!"
    })

@app.route('/get_result', methods=['POST'])
def get_result():
    try:
        data = request.get_json(silent=True) or {}
        seating_no = data.get('seating_no')

        if not seating_no:
            return jsonify({"status": "error", "message": "Please provide seating_no"}), 400

        # رابط جلب النتيجة من الوطن
        target_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

        response = requests.get(target_url, headers=headers, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. البحث عن اسم الطالب بمحددات دقيقة (مع استبعاد نصوص القوائم مثل 'تواصل معنا')
            student_name = "غير متوفر"
            name_candidates = soup.find_all(['h1', 'h2', 'h3', 'div', 'span'], class_=lambda c: c and any(x in c.lower() for x in ['name', 'student', 'st-name']))
            for elem in name_candidates:
                txt = elem.text.strip()
                if txt and "تواصل" not in txt and "اتصل" not in txt and len(txt) > 3:
                    student_name = txt
                    break
            
            # إذا لم يجد بالكلاسات، يجرب البحث عن أول عنوان يحتوي نص معقول
            if student_name == "غير متوفر":
                for tag in ['h2', 'h3', 'h4']:
                    found = soup.find(tag)
                    if found and "تواصل" not in found.text:
                        student_name = found.text.strip()
                        break

            # 2. البحث عن المجموع الكلي
            total_marks = "غير متوفر"
            degree_candidates = soup.find_all(['div', 'span', 'td', 'p'], class_=lambda c: c and any(x in c.lower() for x in ['degree', 'total', 'mark', 'score', 'result']))
            for elem in degree_candidates:
                txt = elem.text.strip()
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
            return jsonify({"status": "error", "message": f"Status code: {response.status_code}"}), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
