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
            
            # 1. استخراج اسم الطالب بمرونة (البحث عن كلمة 'الأسم:' أو 'الاسم:')
            student_name = "غير متوفر"
            full_text = soup.get_text()
            
            for elem in soup.find_all(['h1', 'h2', 'h3', 'div', 'span', 'p', 'strong']):
                txt = elem.text.strip()
                if "الأسم:" in txt or "الاسم:" in txt:
                    # تنظيف النص لاستخلاص الاسم فقط
                    student_name = txt.replace("الأسم:", "").replace("الاسم:", "").strip()
                    break

            # 2. استخراج بيانات إضافية (الشعبة وحالة الطالب)
            branch = "غير متوفر"
            status_student = "ناجح"
            for p in soup.find_all(['p', 'div', 'span', 'li']):
                t = p.text.strip()
                if "الشعبة:" in t:
                    branch = t.replace("الشعبة:", "").strip()
                if "حالة الطالب:" in t:
                    status_student = t.replace("حالة الطالب:", "").strip()

            # 3. استخراج المواد والدرجات من الجدول
            subjects = []
            total_marks = "غير متوفر"

            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = [td.text.strip() for td in row.find_all(['td', 'th'])]
                    if len(cols) >= 2:
                        # إذا كان صف المجموع
                        if "المجموع" in cols[0] or "المجموع الكلي" in cols[0]:
                            total_marks = cols[1]
                        else:
                            subjects.append({
                                "subject": cols[0],
                                "score": cols[1],
                                "percentage": cols[2] if len(cols) > 2 else ""
                            })

            # إذا لم يُعثر على جدول المجموع، نبحث عنه في العناصر العادية
            if total_marks == "غير متوفر":
                for tag in soup.find_all(['div', 'span', 'p', 'td', 'h4']):
                    txt = tag.text.strip()
                    if "المجموع الكلي" in txt or "المجموع:" in txt:
                        total_marks = txt
                        break

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "branch": branch,
                "student_status": status_student,
                "total": total_marks,
                "subjects": subjects
            })
        else:
            return jsonify({
                "status": "error", 
                "message": f"تعذر الاتصال بالموقع (رمز: {response.status_code})"
            }), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
