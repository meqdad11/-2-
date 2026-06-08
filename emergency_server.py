import os
from flask import Flask, request, render_template_string, jsonify
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xlaruzxqtbsqjqdbwbyb.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ خادم الطوارئ متصل بـ Supabase")
    except Exception as e:
        print(f"❌ فشل اتصال خادم الطوارئ: {e}")
else:
    print("⚠️ متغيرات البيئة SUPABASE_URL أو SUPABASE_SERVICE_KEY مفقودة")

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>شبكة أماني</title></head>
<body style="font-family:sans-serif;background:#1e1e2e;color:#cdd6f4;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
<div style="background:#313244;padding:40px;border-radius:16px;width:320px;">
<h2>🛡️ شبكة أماني</h2>
<p>هذه البيانات سرية ولا تُستخدم إلا في حالات الطوارئ.</p>
<form id="emergencyForm">
  <input type="hidden" id="userId" value="{{ user_id }}">
  <input type="hidden" id="token" value="{{ token }}">
  <label>الاسم الأول:</label><br>
  <input type="text" id="firstName" required style="width:100%;padding:8px;margin:5px 0;"><br>
  <label>رقم الهاتف:</label><br>
  <input type="tel" id="phoneNumber" required style="width:100%;padding:8px;margin:5px 0;"><br>
  <label>المدينة:</label><br>
  <input type="text" id="city" required style="width:100%;padding:8px;margin:5px 0;"><br>
  <button type="submit" style="background:#a6e3a1;border:none;padding:10px 20px;border-radius:8px;margin-top:10px;cursor:pointer;">حفظ</button>
</form>
<div id="message" style="margin-top:10px;"></div>
</div>
<script>
document.getElementById('emergencyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        user_id: document.getElementById('userId').value,
        token: document.getElementById('token').value,
        first_name: document.getElementById('firstName').value,
        phone_number: document.getElementById('phoneNumber').value,
        city: document.getElementById('city').value
    };
    const res = await fetch('/save', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    document.getElementById('message').textContent = data.message || data.error;
});
</script>
</body>
</html>
"""

@app.route('/emergency')
def emergency_form():
    user_id = request.args.get('user_id')
    token = request.args.get('token')
    return render_template_string(HTML_PAGE, user_id=user_id, token=token)

@app.route('/save', methods=['POST'])
def save_emergency():
    if not supabase:
        return jsonify({"error": "الخادم غير متصل بقاعدة البيانات"}), 500
    data = request.json
    try:
        supabase.table("emergency_contacts").upsert({
            "user_id": str(data['user_id']),
            "first_name": data['first_name'],
            "phone_number": data['phone_number'],
            "city": data['city'],
            "updated_at": "now()"
        }).execute()
        return jsonify({"message": "تم حفظ بياناتك بنجاح."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))