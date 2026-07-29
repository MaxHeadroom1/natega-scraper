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

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://natega.elwatannews.com/'
        })

        # جلب الصفحة عبر GET مع المعطيات
        target_url = f"https://natega.elwatannews.com/?seating_no={seating_no}"
        response = session.get(target_url, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text(separator=' ', strip=True)

            # نعيد النص المجلوب مباشرة بدون فحص 404 لنرى ماذا يرى السيرفر
            return jsonify({
                "status": "success",
                "seating_no": seating_no,
                "page_snippet": page_text[:400]  # أول 400 حرف من الصفحة الناتج
            })
        else:
            return jsonify({"status": "error", "message": f"Status code: {response.status_code}"}), 502

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
