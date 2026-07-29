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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://natega.elwatannews.com',
            'Referer': 'https://natega.elwatannews.com/'
        }

        # 1. إرسال طلب POST المباشر لمسار نتيجة الوطن
        post_url = "https://natega.elwatannews.com/Result/1"
        payload = {'seating_no': seating_no}

        response = session.post(post_url, data=payload, headers=headers, timeout=15)

        # لو لم يستجب مسار POST، نأخذ رابط الاستعلام الاحتياطي
        if response.status_code != 200 or len(response.text) < 500:
            search_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
            response = session.get(search_url, headers=headers, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            student_name = "غير متوفر"
            branch = "غير متوفر"
            student_status = "ناجح"
            total_marks = "غير متوفر"
            subjects = []

            # استخراج اسم الطالب والشعبة والمجموع من الصفحة
            # البحث في النصوص والـ Tags المشهورة بصفحة الوطن
            for tag in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'td', 'th']):
                text = tag.get_text(strip=True)
                if ("اسم الطالب" in text or "الأسم" in text or "الاسم" in text) and student_name == "غير متوفر":
                    parts = text.split(":")
                    if len(parts) > 1:
                        student_name = parts[1].strip()
                elif "الشعبة" in text and branch == "غير متوفر":
                    parts = text.split(":")
                    if len(parts) > 1:
                        branch = parts[1].strip()
                elif ("المجموع الكلي" in text or "المجموع" in text) and total_marks == "غير متوفر":
                    parts = text.split(":")
                    if len(parts) > 1:
                        total_marks = parts[1].strip()

            # استخراج جدول الدرجات بالكامل
            for tr in soup.find_all('tr'):
                tds = tr.find_all(['td', 'th'])
                if len(tds) >= 2:
                    row_texts = [td.get_text(strip=True) for td in tds]
                    
                    sub_name = row_texts[0]
                    score_val = row_texts[1]
                    percentage_val = row_texts[2] if len(row_texts) > 2 else ""

                    # تجاهل صف عناوين الجدول
                    if any(h in sub_name for h in ["المادة", "الدرجة", "النسبة", "اسم"]):
                        continue

                    # لو السطر يمثل المجموع الكلي
                    if "المجموع" in sub_name:
                        total_marks = score_val
                        continue

                    # إضافة المادة للقائمة
                    if sub_name and score_val:
                        subjects.append({
                            "subject": sub_name,
                            "score": score_val,
                            "percentage": percentage_val
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
                "message": f"خطأ في الاتصال بالموقع: {response.status_code}"
            }), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
