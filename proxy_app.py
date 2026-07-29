from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# رابط الخدمة التي تُرجع النتيجة من موقع الوطن
TARGET_URL = "https://natega.elwatannews.com/"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>استعلام النتيجة (سحب من موقع الوطن)</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; text-align: center; }
        .card { background: white; max-width: 550px; margin: 40px auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h2 { color: #047857; margin-bottom: 20px; }
        input[type="text"] { width: 80%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; text-align: center; }
        button { background-color: #059669; color: white; border: none; padding: 12px 25px; border-radius: 6px; font-size: 16px; cursor: pointer; transition: 0.3s; }
        button:hover { background-color: #047857; }
        .result-box { margin-top: 25px; border-top: 2px solid #e5e7eb; padding-top: 20px; text-align: right; }
        .result-item { font-size: 17px; margin: 8px 0; color: #333; }
        .error { color: #dc2626; font-weight: bold; margin-top: 15px; }
        .source-tag { font-size: 12px; color: #6b7280; margin-top: 15px; }
    </style>
</head>
<body>

<div class="card">
    <h2>استعلام عن النتيجة</h2>
    <form method="POST" action="/">
        <input type="text" name="seat_number" placeholder="أدخل رقم الجلوس" required value="{{ seat_number or '' }}">
        <br>
        <button type="submit">بحث مباشر</button>
    </form>

    {% if student_data %}
    <div class="result-box">
        {% for key, value in student_data.items() %}
            <div class="result-item"><strong>{{ key }}:</strong> {{ value }}</div>
        {% endfor %}
    </div>
    {% elif error %}
        <div class="error">{{ error }}</div>
    {% endif %}

    <div class="source-tag">يتم جلب البيانات برمجياً وبشكل لحظي</div>
</div>

</body>
</html>
"""

def fetch_from_elwatan(seat_number):
    """
    وظيفة إرسال طلب سري لموقع الوطن واستخلاص البيانات من الـ HTML
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://natega.elwatannews.com/'
    }
    
    # بيانات النموذج التي يطلبها موقع الوطن عند البحث
    payload = {
        'seating_no': seat_number
    }

    try:
        # إرسال طلب POST لموقع الوطن لرقم الجلوس
        response = requests.post(TARGET_URL, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # محاولة قراءة عناصر النتيجة من كود الـ HTML
            # ملاحظة: يتم ضبط الـ Selectors طبقاً لتقسيم الكود لديهم في الصفحة
            student_info = {}
            
            # مثال على سحب البيانات إذا كانت داخل جداول أو divs
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    student_info[key] = val

            # إذا لم يجد جدول، نبحث عن الحاويات العادية للنتيجة
            if not student_info:
                result_divs = soup.select('.result-details, .student-info, .result-box')
                for div in result_divs:
                    text = div.get_text(separator='\n', strip=True)
                    if text:
                        student_info['النتيجة'] = text

            if student_info:
                return student_info, None
            else:
                return None, "لم يتم العثور على نتيجة لرقم الجلوس هذا، أو أن السيستم مغلق حالياً."
        else:
            return None, f"تعذر الاتصال بالموقع المصدر (رمز الاستجابة: {response.status_code})"

    except Exception as e:
        return None, f"حدث خطأ أثناء جلب البيانات: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    student_data = None
    error = None
    seat_num = None

    if request.method == 'POST':
        seat_num = request.form.get('seat_number', '').strip()
        if seat_num:
            student_data, error = fetch_from_elwatan(seat_num)

    return render_template_string(HTML_TEMPLATE, student_data=student_data, error=error, seat_number=seat_num)

if __name__ == '__main__':
    app.run(debug=True, port=5000)