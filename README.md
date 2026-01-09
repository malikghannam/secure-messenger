# 🔐 Secure Messenger - Post-Quantum Encrypted Messaging

نظام مراسلة آمن مع تشفير ما بعد الكم (Post-Quantum Cryptography) ومصادقة ثنائية العامل (TOTP).

## 📋 نظرة عامة

Secure Messenger هو تطبيق مراسلة فورية يوفر:
- **تشفير ما بعد الكم (PQC)**: حماية ضد هجمات الحواسيب الكمومية المستقبلية
- **مصادقة ثنائية العامل (2FA/TOTP)**: طبقة أمان إضافية لتسجيل الدخول
- **مشاركة ملفات آمنة**: مع سياسات أمنية (عرض مرة واحدة، محدود الوقت)
- **تشفير من طرف لطرف (E2E)**: الرسائل مشفرة بين المرسل والمستلم فقط

## 🏗️ البنية المعمارية

```
secure_messenger/
├── messenger/                 # التطبيق الرئيسي
│   ├── crypto/               # طبقة التشفير (Kyber, Dilithium, X3DH)
│   ├── pq_backend/           # واجهة التشفير ما بعد الكم
│   ├── message/              # إدارة الجلسات والرسائل
│   ├── transport/            # طبقة الشبكة (WebSocket)
│   ├── auth/                 # المصادقة (TOTP, Email Verification)
│   ├── files/                # مشاركة الملفات الآمنة
│   └── ui/                   # واجهة المستخدم (Flask + HTML/JS)
├── relay_server/             # خادم الترحيل (Flask + SQLite)
└── tests/                    # اختبارات الوحدة
```

## 🔒 الميزات الأمنية

### 1. تشفير ما بعد الكم (Post-Quantum Cryptography)
- **Kyber-768**: لتبادل المفاتيح (Key Encapsulation)
- **Dilithium**: للتوقيعات الرقمية
- **X3DH + Double Ratchet**: بروتوكول Signal مع تحسينات PQ

### 2. المصادقة الثنائية (TOTP)
- توليد رموز OTP متوافقة مع RFC 6238
- دعم تطبيقات المصادقة (Google Authenticator, Authy)
- رموز احتياطية للطوارئ
- حماية من هجمات القوة الغاشمة

### 3. مشاركة الملفات الآمنة
- **عرض مرة واحدة (View Once)**: الملف يُحذف بعد المشاهدة
- **محدود الوقت (Time Limited)**: الملف يُحظر بعد انتهاء المؤقت
- دعم الصور والفيديو والملفات النصية

## 🚀 التثبيت والتشغيل

### المتطلبات
- Python 3.10+
- pip

### التثبيت

```bash
# استنساخ المشروع
git clone https://github.com/YOUR_USERNAME/secure-messenger.git
cd secure-messenger

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate     # Windows

# تثبيت المتطلبات
pip install -r requirements.txt
```

### التشغيل

```bash
# تشغيل خادم الترحيل (Terminal 1)
cd relay_server
python app.py

# تشغيل التطبيق الرئيسي (Terminal 2)
python main.py
```

ثم افتح المتصفح على: `http://127.0.0.1:5001`

## 📁 ملفات المتطلبات

- `requirements.txt` - متطلبات Python الرئيسية
- `relay_server/requirements.txt` - متطلبات خادم الترحيل

## 🧪 الاختبارات

```bash
# تشغيل اختبارات TOTP
pytest tests/test_totp_properties.py -v
```

## 📚 التوثيق

راجع مجلد `.kiro/specs/` للتوثيق التفصيلي:
- `totp-authentication/` - توثيق نظام المصادقة الثنائية
- `secure-file-sharing/` - توثيق مشاركة الملفات الآمنة

## 🛠️ التقنيات المستخدمة

| التقنية | الاستخدام |
|---------|----------|
| Python 3.10+ | اللغة الرئيسية |
| Flask | إطار الويب |
| SQLite | قاعدة البيانات |
| Socket.IO | الاتصال الفوري |
| liboqs-python | تشفير ما بعد الكم |
| cryptography | التشفير التقليدي |
| pyotp | توليد رموز TOTP |

## 👥 المساهمون

- [اسمك هنا]

## 📄 الرخصة

هذا المشروع للأغراض الأكاديمية.

---

**ملاحظة**: هذا المشروع تم تطويره كمشروع أكاديمي لدراسة تقنيات التشفير الحديثة.
