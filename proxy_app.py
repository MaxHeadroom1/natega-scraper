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

        # نرسل طلب البحث المباشر
        search_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
        response = session.get(search_url, headers=headers, timeout=15, allow_redirects=True)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. استخراج اسم الطالب والشعبة وحالة النتيجة
            student_name = "غير متوفر"
            branch = "غير متوفر"
            student_status = "ناجح"
            total_marks = "غير متوفر"

            # فحص كامل عناصر النص في الصفحة
            full_text = soup.get_text()

            # استخراج الاسم ببحث مباشر عن الأسم/الاسم
            for el in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'b', 'strong']):
                txt = el.text.strip()
                if ("الأسم:" in txt or "الاسم:" in txt) and len(txt) < 100:
                    student_name = txt.replace("الأسم:", "").replace("الاسم:", "").strip()
                    break

            # استخراج الشعبة
            for el in soup.find_all(['div', 'p', 'span', 'td']):
                txt = el.text.strip()
                if "الشعبة:" in txt and len(txt) < 60:
                    branch = txt.replace("الشعبة:", "").strip()
                    break

            # 2. استخراج جدول المواد بالكامل (شامل المواد المقررة وغير المقررة)
            subjects = []
            
            # البحث عن جميع الجداول في الصفحة
            tables = soup.find_all('table')
            
            # إذا لم يجد جدول <table> صريح، يبحث عن صفوف التنسيق Standard
            rows = []
            if tables:
                for t in tables:
                    rows.extend(t.find_all('tr'))
            else:
                rows = soup.find_all(['tr', 'div'], class_=lambda c: c and any(k in str(c).lower() for k in ['row', 'item', 'subject', 'table']))

            for row in rows:
                cols = [c.text.strip() for c in row.find_all(['td', 'th', 'div', 'span']) if c.text.strip()]
                
                # تصفية الصفوف المزدوجة والتأكد من وجود اسم مادة ودرجة
                if len(cols) >= 2:
                    sub_name = cols[0]
                    score_val = cols[1]
                    percentage_val = cols[2] if len(cols) > 2 else ""

                    # تجاهل العناوين الرئيسية
                    if any(header in sub_name for header in ["المادة", "الدرجة", "النسبة", "رقم الجلوس"]):
                        continue

                    # إذا كان الصف للمجموع الكلي
                    if "المجموع" in sub_name or "المجموع الكلي" in sub_name:
                        total_marks = score_val
                    else:
                        # التأكد من عدم تكرار إضافة المادة
                        if not any(s['subject'] == sub_name for s in subjects):
                            subjects.append({
                                "subject": sub_name,
                                "score": score_val,
                                "percentage": percentage_val,
                                "is_optional": "غير مقرر" in score_val
                            })

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "name": student_name,
                "branch": branch,
                "student_status": student_status,
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
