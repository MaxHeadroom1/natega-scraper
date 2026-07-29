import os
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "success",
        "message": "API scraper is running successfully!"
    })

@app.route('/get_result', methods=['POST'])
def get_result():
    # استقبال رقم الجلوس من الطلب (JSON)
    data = request.get_json()
    seating_no = data.get('seating_no') if data else None

    if not seating_no:
        return jsonify({"error": "Please provide seating_no"}), 400

    # إعداد البيانات والمروسلات لإرسالها للموقع المستهدف
    target_url = "https://natega.elwatannews.com/"  # رابط الموقع المستهدف
    payload = {
        'seating_no': seating_no
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    try:
        # إرسال طلب POST للموقع الأصلي
        response = requests.post(target_url, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # استخلاص البيانات باستخدام BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # (قم بتعديل عناصر الاستخراج حسب هيكل الصفحة المستهدفة)
            student_name = soup.find('div', {'class': 'student-name'})
            total_marks = soup.find('div', {'class': 'total-degrees'})

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name.text.strip() if student_name else "غير متوفر",
                "total": total_marks.text.strip() if total_marks else "غير متوفر"
            })
        else:
            return jsonify({"error": f"Failed to fetch data, status code: {response.status_code}"}), 502

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# الجزء الأهم لضبط المنفذ على Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
