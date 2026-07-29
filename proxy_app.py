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

        # محاولة جلب النتيجة عبر GET أو POST حسب بناء موقع الوطن
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }

        # تجربة GET مع الـ seating_no كـ Query Parameter أو المسار المباشر
        target_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
        
        response = requests.get(target_url, headers=headers, timeout=15)
        
        # إذا أعاد 405 أو فشل، نجرب POST على الرابط المباشر
        if response.status_code == 405:
            target_url_post = "https://natega.elwatannews.com/result"
            response = requests.post(target_url_post, data={'seating_no': seating_no}, headers=headers, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # البحث عن بيانات الطالب داخل عناصر الصفحة
            student_name_elem = soup.find('div', {'class': 'student-name'}) or soup.find('h3') or soup.find('div', {'class': 'name'})
            total_marks_elem = soup.find('div', {'class': 'total-degrees'}) or soup.find('span', {'class': 'degree'}) or soup.find('div', {'class': 'total'})

            student_name = student_name_elem.text.strip() if student_name_elem else "غير متوفر"
            total_marks = total_marks_elem.text.strip() if total_marks_elem else "غير متوفر"

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "total": total_marks
            })
        else:
            return jsonify({"status": "error", "message": f"الموقع المستهدف أعاد استجابة برقم {response.status_code}"}), 502

    except requests.exceptions.Timeout:
        return jsonify({"status": "error", "message": "استغرق الموقع المستهدف وقتاً طويلاً في الرد"}), 540
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
