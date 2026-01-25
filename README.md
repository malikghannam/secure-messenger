# 🔐 Secure Messenger - Post-Quantum Encrypted Messaging

<div dir="rtl">

## تطبيق مراسلة آمن مع تشفير ما بعد الكم

نظام مراسلة فوري متقدم يجمع بين التشفير التقليدي والتشفير ما بعد الكم لحماية الاتصالات من التهديدات الكمومية المستقبلية.

</div>

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Post-Quantum](https://img.shields.io/badge/Security-Post--Quantum-red.svg)](https://csrc.nist.gov/projects/post-quantum-cryptography)

## 📋 Overview | نظرة عامة

**Secure Messenger** is an end-to-end encrypted messaging application that combines traditional cryptography with post-quantum algorithms to protect against future quantum computer attacks.

<div dir="rtl">

**Secure Messenger** هو تطبيق مراسلة مشفر من طرف لطرف يجمع بين التشفير التقليدي وخوارزميات ما بعد الكم للحماية من هجمات الحواسيب الكمومية المستقبلية.

</div>

### ✨ Key Features | الميزات الرئيسية

- 🔐 **Post-Quantum Cryptography**: Hybrid protocol combining X3DH with Kyber-512
- 🔑 **End-to-End Encryption**: Messages encrypted using XChaCha20-Poly1305
- 🔄 **Double Ratchet**: Forward secrecy and post-compromise security
- 🛡️ **Two-Factor Authentication (TOTP)**: RFC 6238 compliant
- 📁 **Secure File Sharing**: View-once and time-limited policies
- 🕵️ **Server Blindness**: Relay server cannot read message content
- ✅ **Comprehensive Testing**: 19 security tests + 16 performance benchmarks

<div dir="rtl">

- 🔐 **تشفير ما بعد الكم**: بروتوكول هجين يجمع X3DH مع Kyber-512
- 🔑 **تشفير من طرف لطرف**: رسائل مشفرة باستخدام XChaCha20-Poly1305
- 🔄 **Double Ratchet**: سرية أمامية وحماية بعد الاختراق
- 🛡️ **مصادقة ثنائية (TOTP)**: متوافق مع RFC 6238
- 📁 **مشاركة ملفات آمنة**: سياسات عرض مرة واحدة ومحدودة الوقت
- 🕵️ **خادم أعمى**: السيرفر لا يستطيع قراءة محتوى الرسائل
- ✅ **اختبارات شاملة**: 19 اختبار أمني + 16 اختبار أداء

</div>

## 🏗️ Architecture | البنية المعمارية

```
secure_messenger/
├── messenger/                 # Main application | التطبيق الرئيسي
│   ├── crypto/               # Cryptography layer (PQX3DH, Double Ratchet)
│   │   ├── pqx3dh.py        # Hybrid X3DH + Kyber protocol
│   │   ├── ratchet.py       # Double Ratchet implementation
│   │   └── crypto_utils.py  # XChaCha20-Poly1305 encryption
│   ├── auth/                 # Authentication (TOTP, QR codes)
│   ├── files/                # Secure file sharing with policies
│   ├── transport/            # Network layer (WebSocket)
│   ├── message/              # Session and message management
│   └── ui/                   # User interface (Flask + HTML/JS)
├── relay_server/             # Blind relay server (Flask + SQLite)
│   ├── app.py               # Main server application
│   ├── totp_routes.py       # TOTP authentication routes
│   └── file_routes.py       # File transfer routes
└── tests/                    # Comprehensive test suite
    ├── security/            # Security tests (entropy, timing, replay)
    └── benchmarks/          # Performance benchmarks
```

## 🔒 الميزات الأمنية

### 1. تشفير ما بعد الكم (Post-Quantum Cryptography)
- **Kyber-768**: لتبادل المفاتيح (Key Encapsulation)
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

- `requirements.txt` - متطلبات بايثون الرئيسية
- `relay_server/requirements.txt` - متطلبات السيرفر 


<<<<<<< HEAD

=======
```bash
# تشغيل اختبارات TOTP
pytest tests/test_totp_properties.py -v
```

#
>>>>>>> ea5b05d9b9eaebe2e5ba2c0bb8b7a7f5e36af613
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

- [محمد مالك غنام]
=======
>>>>>>> ea5b05d9b9eaebe2e5ba2c0bb8b7a7f5e36af613
