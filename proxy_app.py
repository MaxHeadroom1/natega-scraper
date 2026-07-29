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

            # 1. استخراج الاسم الحقيقي وتنظيفه من نصوص الـ SEO
            for el in soup.find_all(['h1', 'h2', 'h3', 'div', 'p', 'span', 'td', 'b', 'strong']):
                txt = el.get_text(strip=True)
                if ("الأسم:" in txt or "الاسم:" in txt or "اسم الطالب:" in txt) and len(txt) < 150:
                    # قص كل ما قبل النقطتين :
                    clean = re.sub(r'^.*?(الأسم|الاسم|اسم الطالب)\s*:\s*', '', txt)
                    # قص أي نصوص إعلانية تابعة للموقع
                    clean = re.sub(r'جريدة الوطن|نتيجة الثانوية|حرصاً|عام 2026|تقديم|حصل', '', clean).strip()
                    # أخذ كلمات الاسم فقط
                    words = [w for w in clean.split() if re.match(r'^[\u0600-\u06FF]+$', w)]
                    if len(words) >= 2:
                        student_name = " ".join(words[:5])
                        break

            # 2. استخراج الشعبة
            for el in soup.find_all(['div', 'p', 'span', 'td']):
                txt = el.get_text(strip=True)
                if "الشعبة:" in txt and len(txt) < 80:
                    clean_b = txt.split("الشعبة:")[-1].strip()
                    words_b = [w for w in clean_b.split() if re.match(r'^[\u0600-\u06FF]+$', w)]
                    if words_b:
                        branch = " ".join(words_b[:2])
                        break

            # 3. استخراج جدول المواد والدرجات
            calculated_total = 0.0
            has_calculated_marks = False

            for tr in soup.find_all('tr'):
                tds = tr.find_all(['td', 'th'])
                if len(tds) >= 2:
                    row_texts = [td.get_text(strip=True) for td in tds]
                    
                    sub_name = row_texts[0]
                    score_val = row_texts[1]
                    percentage_val = row_texts[2] if len(row_texts) > 2 else ""

                    if any(h in sub_name for h in ["المادة", "الدرجة", "النسبة", "رقم الجلوس"]):
                        continue

                    # فحص المجموع الكلي إذا كان مذكوراً في الجدول
                    if "المجموع" in sub_name:
                        total_marks = score_val
                        continue

                    if sub_name and score_val and not any(s['subject'] == sub_name for s in subjects):
                        subjects.append({
                            "subject": sub_name,
                            "score": score_val,
                            "percentage": percentage_val
                        })

                        # جمع الدرجات الفعلية للمواد المقررة لتأكيد المجموع
                        if "غير مقرر" not in score_val and "/" in score_val:
                            try:
                                actual_score = float(score_val.split("/")[1].strip())
                                calculated_total += actual_score
                                has_calculated_marks = True
                            except ValueError:
                                pass

            # 4. إذا لم يجد المجموع صراحة، يبحث عنه في بقية الصفحة أو يستخدم المجموع المحسوب
            if total_marks == "غير متوفر":
                for el in soup.find_all(['div', 'p', 'span', 'h3', 'h4']):
                    txt = el.get_text(strip=True)
                    if "المجموع الكلي" in txt or "المجموع:" in txt:
                        match = re.search(r'(\d+(?:\.\d+)?)', txt)
                        if match:
                            total_marks = match.group(1)
                            break

            if total_marks == "غير متوفر" and has_calculated_marks:
                total_marks = f"{calculated_total} / 410"

            # تحديد الشعبة تلقائياً إذا لم تظهر
            if branch == "غير متوفر":
                subjects_str = " ".join([s['subject'] for s in subjects])
                if "الرياضيات البحتة" in subjects_str:
                    branch = "علمي رياضة"
                elif "الأحياء" in subjects_str and not any(s['subject'] == 'الأحياء' and 'غير مقرر' in s['score'] for s in subjects):
                    branch = "علمي علوم"
                elif "التاريخ" in subjects_str and not any(s['subject'] == 'التاريخ' and 'غير مقرر' in s['score'] for s in subjects):
                    branch = "أدبي"

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
