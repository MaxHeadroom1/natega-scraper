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
            return jsonify({"status": "error", "message": "Please provide seating_no"}), 400

        # استدعاء الرابط المباشر للنتيجة
        target_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(target_url, headers=headers, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # محاولة قراءة عناصر الجداول أولاً (حيث تُعرض النتائج عادة)
            tables = soup.find_all('table')
            tds = [td.text.strip() for td in soup.find_all('td') if td.text.strip()]
            
            # استخراج النصوص المهمة لمعرفتها
            all_text = soup.get_text(separator=' ', strip=True)

            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "extracted_tds": tds[:15],  # أول 15 عنصر داخل الجداول
                "sample_text": all_text[:500]  # أول 500 حرف من نص الصفحة
            })
        else:
            return jsonify({"status": "error", "message": f"Status code: {response.status_code}"}), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
