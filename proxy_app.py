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
            
            student_name = "غير متوفر"
            branch = "غير متوفر"
            status_student = "ناجح"
            total_marks = "غير متوفر"
            subjects = []

            # 1. استخراج النصوص والمسميات الأساسية
            for tag in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'strong']):
                txt = tag.text.strip()
                if ("الأسم:" in txt or "الاسم:" in txt) and student_name == "غير متوفر":
                    # يستخرج الجزء بعد الكلمة
                    student_name = txt.split(":")[-1].strip()
                elif "الشعبة:" in txt and branch == "غير متوفر":
                    branch = txt.split(":")[-1].strip()
                elif "حالة الطالب:" in txt:
                    status_student = txt.split(":")[-1].strip()

            # 2. قراءة درجات المواد من السطور أو الجداول
            # البحث عن جميع الصفوف <tr> أو مجموعات البيانات <div> التي تحتوي على درجات
            rows = soup.find_all(['tr', 'div'], class_=lambda c: c and any(x in str(c).lower() for x in ['row', 'subject', 'item', 'result']))
            
            # إذا لم توجد كلاسات محددة، نمر على كل الصفوف <tr> في الصفحة
            if not rows:
                rows = soup.find_all('tr')

            for row in rows:
                cols = [c.text.strip() for c in row.find_all(['td', 'th', 'div', 'span']) if c.text.strip()]
                # نقوم بتصفية العناصر لضمان وجود مادة ودرجة
                if len(cols) >= 2:
                    first_col = cols[0]
                    # تخطي رؤوس الجداول أو العناوين
                    if any(header_word in first_col for header_word in ["المادة", "الدرجة", "النسبة", "اسم"]):
                        continue
                    
                    if "المجموع" in first_col or "المجموع الكلي" in first_col:
                        total_marks = cols[1]
                    else:
                        # إضافة المادة للكتلة
                        subject_name = cols[0]
                        score = cols[1]
                        percentage = cols[2] if len(cols) > 2 else ""
                        
                        # منع تكرار نفس المادة في القائمة
                        if not any(s['subject'] == subject_name for s in subjects):
                            subjects.append({
                                "subject": subject_name,
                                "score": score,
                                "percentage": percentage
                            })

            # 3. محاولة احتياطية لجلب المجموع في حال لم يظهر في السطور
            if total_marks == "غير متوفر":
                for tag in soup.find_all(['div', 'p', 'span', 'td', 'h4']):
                    txt = tag.text.strip()
                    if "المجموع" in txt and len(txt) < 40:
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
                "message": f"تعذر الاتصال بالموقع المستهدف (رمز: {response.status_code})"
            }), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
