import os
import re
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

        # 1. طلب POST المباشر
        post_url = "https://natega.elwatannews.com/Result/1"
        payload = {'seating_no': seating_no}

        response = session.post(post_url, data=payload, headers=headers, timeout=15)

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

            # 1. تنظيف ودقة استخراج الاسم والشعبة من الـ Elements المباشرة
            for el in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'td', 'th', 'b', 'strong']):
                txt = el.get_text(strip=True)
                
                # استخراج الاسم
                if ("اسم الطالب" in txt or "الأسم" in txt or "الاسم" in txt) and student_name == "غير متوفر":
                    # تنظيف النص
                    clean_txt = re.sub(r'^(اسم الطالب|الأسم|الاسم)\s*:\s*', '', txt)
                    # قطع النص لو اشتبك مع كلمة حالة أو شعبة
                    clean_txt = re.split(r'(حالة|الشعبة|رقم|المجموع)', clean_txt)[0].strip()
                    if clean_txt and len(clean_txt) > 3:
                        student_name = clean_txt

                # استخراج الشعبة
                if "الشعبة" in txt and branch == "غير متوفر":
                    clean_branch = re.sub(r'^الشعبة\s*:\s*', '', txt)
                    clean_branch = re.split(r'(حالة|الاسم|الأسم|رقم|المجموع)', clean_branch)[0].strip()
                    if clean_branch and len(clean_branch) > 2:
                        branch = clean_branch

            # إذا لم يجد الشعبة صراحة، يتم الاستدلال عليها من المواد
            if branch == "غير متوفر":
                page_full_text = soup.get_text()
                if "الرياضيات البحتة" in page_full_text or "مجموع الرياضيات" in page_full_text:
                    branch = "علمي رياضة"
                elif "الأحياء" in page_full_text and "غير مقرر" not in page_full_text:
                    branch = "علمي علوم"
                elif "التاريخ" in page_full_text and "غير مقرر" not in page_full_text:
                    branch = "أدبي"

            # 2. استخراج جدول المواد والدرجات
            for tr in soup.find_all('tr'):
                tds = tr.find_all(['td', 'th'])
                if len(tds) >= 2:
                    row_texts = [td.get_text(strip=True) for td in tds]
                    
                    sub_name = row_texts[0]
                    score_val = row_texts[1]
                    percentage_val = row_texts[2] if len(row_texts) > 2 else ""

                    # تجاهل صف عناوين الجدول
                    if any(h in sub_name for h in ["المادة", "الدرجة", "النسبة", "رقم الجلوس"]):
                        continue

                    # استخراج المجموع الكلي
                    if "المجموع" in sub_name or "المجموع الكلي" in sub_name:
                        total_marks = score_val
                        continue

                    # إضافة المادة للقائمة
                    if sub_name and score_val and not any(s['subject'] == sub_name for s in subjects):
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
