import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

FINAL_TOTAL = 320


def normalize_text(value):
    """تنظيف المسافات الزائدة مع الحفاظ على النص العربي."""
    return re.sub(r"\s+", " ", value or "").strip()


def format_number(value):
    """إظهار 50 بدل 50.0 مع الحفاظ على الكسور عند وجودها."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def extract_labeled_value(soup, labels, stop_labels):
    """
    استخراج قيمة عنوان مثل:
    الأسم: يوسف محمد فاروق إبراهيم
    مع إيقاف الالتقاط عند بداية العنوان التالي مثل: حالة الطالب.
    """
    labels = sorted(labels, key=len, reverse=True)
    stop_labels = sorted(stop_labels, key=len, reverse=True)

    label_pattern = "|".join(re.escape(label) for label in labels)
    stop_pattern = "|".join(re.escape(label) for label in stop_labels)

    pattern = re.compile(
        rf"(?:{label_pattern})\s*[:：]\s*(.+?)"
        rf"(?=\s*(?:{stop_pattern})\s*[:：]|$)"
    )

    candidates = []

    for element in soup.find_all(
        ["h1", "h2", "h3", "h4", "div", "p", "span", "td", "b", "strong"]
    ):
        text = normalize_text(element.get_text(" ", strip=True))

        if text and any(label in text for label in labels):
            candidates.append(text)

    # حل احتياطي إذا كانت البيانات داخل عنصر كبير في الصفحة
    candidates.append(normalize_text(soup.get_text(" ", strip=True)))

    # نبدأ بأقصر عنصر لأنه غالبًا الأقرب للبيانات المطلوبة
    for text in sorted(set(candidates), key=len):
        match = pattern.search(text)

        if match:
            value = normalize_text(match.group(1)).strip(" :-：")

            if value and len(value) <= 150:
                return value

    return None


def extract_score(score_text):
    """
    استخراج درجة الطالب من صيغة مثل:
    50 / 80
    ويعيد 50 وليس 80.
    """
    if not score_text or "غير مقرر" in score_text:
        return None

    score_text = score_text.translate(
        str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
    )

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
        score_text
    )

    if not match:
        return None

    return float(match.group(1))


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "success",
        "message": "API scraper is running successfully!"
    })


@app.route("/get_result", methods=["POST"])
def get_result():
    try:
        data = request.get_json(silent=True) or {}
        seating_no = normalize_text(str(data.get("seating_no", "")))

        if not seating_no:
            return jsonify({
                "status": "error",
                "message": "يرجى إدخال رقم الجلوس"
            }), 400

        session = requests.Session()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://natega.elwatannews.com",
            "Referer": "https://natega.elwatannews.com/"
        }

        post_url = "https://natega.elwatannews.com/Result/1"
        payload = {"seating_no": seating_no}

        response = session.post(
            post_url,
            data=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200 or len(response.text) < 500:
            search_url = (
                "https://natega.elwatannews.com/"
                f"?seating_no={seating_no}"
            )

            response = session.get(
                search_url,
                headers=headers,
                timeout=15
            )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": (
                    "خطأ في الاتصال بالموقع: "
                    f"{response.status_code}"
                )
            }), 502

        soup = BeautifulSoup(response.text, "html.parser")

        # استخراج الاسم مع التوقف قبل "حالة الطالب" وباقي البيانات
        student_name = extract_labeled_value(
            soup,
            labels=["اسم الطالب", "الاسم", "الأسم"],
            stop_labels=[
                "حالة الطالب",
                "الحالة",
                "نوعية التعليم",
                "نوع التعليم",
                "الشعبة",
                "رقم الجلوس",
                "المجموع"
            ]
        ) or "غير متوفر"

        # استخراج حالة الطالب بدل تثبيتها دائمًا على ناجح
        student_status = extract_labeled_value(
            soup,
            labels=["حالة الطالب", "الحالة"],
            stop_labels=[
                "نوعية التعليم",
                "نوع التعليم",
                "الشعبة",
                "رقم الجلوس",
                "المجموع"
            ]
        ) or "غير متوفر"

        branch = extract_labeled_value(
            soup,
            labels=["الشعبة"],
            stop_labels=[
                "رقم الجلوس",
                "المجموع",
                "اللغة العربية",
                "المادة"
            ]
        ) or "غير متوفر"

        subjects = []
        calculated_total = 0.0
        has_calculated_marks = False
        website_total = "غير متوفر"

        overall_total_labels = {
            "المجموع",
            "المجموع الكلي",
            "إجمالي المجموع",
            "الاجمالي",
            "الإجمالي"
        }

        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])

            if len(cells) < 2:
                continue

            row_texts = [
                normalize_text(cell.get_text(" ", strip=True))
                for cell in cells
            ]

            sub_name = row_texts[0]
            score_val = row_texts[1]
            percentage_val = (
                row_texts[2] if len(row_texts) > 2 else ""
            )

            if not sub_name or not score_val:
                continue

            # تجاهل عنوان الجدول فقط
            if sub_name in {
                "المادة",
                "اسم المادة",
                "الدرجة",
                "النسبة",
                "النسبة المئوية",
                "رقم الجلوس"
            }:
                continue

            # لا نعتبر "مجموع الرياضيات البحتة" مجموعًا كليًا
            if sub_name in overall_total_labels:
                website_total = score_val
                continue

            if any(subject["subject"] == sub_name for subject in subjects):
                continue

            subjects.append({
                "subject": sub_name,
                "score": score_val,
                "percentage": percentage_val
            })

            actual_score = extract_score(score_val)

            if actual_score is not None:
                calculated_total += actual_score
                has_calculated_marks = True

        # نعتمد مجموع المواد الفعلية ونجعله من 320
        if has_calculated_marks:
            total_marks = (
                f"{format_number(calculated_total)} / {FINAL_TOTAL}"
            )
        else:
            total_marks = website_total

        # تحديد الشعبة تلقائيًا فقط إذا لم يذكرها الموقع
        if branch in {"غير متوفر", "غير محدد"}:
            subjects_text = " ".join(
                subject["subject"] for subject in subjects
            )

            if any(
                subject["subject"] == "مجموع الرياضيات البحتة"
                and "غير مقرر" not in subject["score"]
                for subject in subjects
            ):
                branch = "علمي رياضة"

            elif any(
                subject["subject"] == "الأحياء"
                and "غير مقرر" not in subject["score"]
                for subject in subjects
            ):
                branch = "علمي علوم"

            elif any(
                subject["subject"] in {"التاريخ", "الجغرافيا"}
                and "غير مقرر" not in subject["score"]
                for subject in subjects
            ):
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

    except requests.Timeout:
        return jsonify({
            "status": "error",
            "message": "انتهت مهلة الاتصال بموقع النتيجة"
        }), 504

    except requests.RequestException as error:
        return jsonify({
            "status": "error",
            "message": f"خطأ في الاتصال: {str(error)}"
        }), 502

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
