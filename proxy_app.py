import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)  # للسماح بطلبات الـ HTML

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

        target_url = "https://natega.elwatannews.com/"
        payload = {'seating_no': seating_no}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # زيادات الـ timeout لتجنب Network Error عند بطء موقع الوطن
        response = requests.post(target_url, data=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # محاولة استخراج الاسم والمجموع بأكثر من طريقة
            student_name_elem = soup.find('div', {'class': 'student-name'}) or soup.find('h3')
            total_marks_elem = soup.find('div', {'class': 'total-degrees'}) or soup.find('span', {'class': 'degree'})

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
