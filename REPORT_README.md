# 📄 تقرير مشروع التخرج - تطبيق مراسلة آمن

## Graduation Project Report - Secure Messaging Application

<div dir="rtl">

### معلومات المشروع

**العنوان:** تطبيق تبادل رسائل آمن باستخدام التشفير ما بعد الكم (Post-Quantum Cryptography) وبروتوكول PQX3DH الهجين

**الطالب:** محمد مالك غنام

**المشرف:** الدكتورة كريستين زينية

**الجامعة:** الجامعة السورية الخاصة - كلية الهندسة المعلوماتية

**التخصص:** هندسة أمن النظم والشبكات الحاسوبية

**العام الدراسي:** 2025 - 2026

---

### نبذة عن المشروع

يهدف هذا المشروع إلى تطوير نظام مراسلة آمن يجمع بين التشفير التقليدي والتشفير ما بعد الكم لحماية الاتصالات من التهديدات الكمومية المستقبلية، خاصة هجمات "اجمع الآن، فك لاحقاً" (Harvest Now, Decrypt Later - HNDL).

### الميزات الرئيسية

- ✅ **بروتوكول PQX3DH الهجين**: دمج X3DH التقليدي مع خوارزمية Kyber-512
- ✅ **Double Ratchet**: لضمان السرية الأمامية والخلفية
- ✅ **XChaCha20-Poly1305**: للتشفير المتماثل السريع والآمن
- ✅ **مصادقة ثنائية TOTP**: متوافقة مع RFC 6238
- ✅ **مشاركة ملفات آمنة**: مع سياسات أمنية متقدمة
- ✅ **اختبارات شاملة**: 19 اختبار أمني + 16 اختبار أداء

### محتويات التقرير

التقرير يتكون من **128 صفحة** ويشمل:

1. **الفصل الأول: الإطار النظري**
   - مفاهيم التشفير الأساسية
   - التشفير ما بعد الكم
   - خوارزمية Kyber
   - بروتوكولات X3DH و Double Ratchet
   - المصادقة الثنائية TOTP

2. **الفصل الثاني: الدراسات السابقة**
   - تحليل تطبيقات المراسلة الحالية
   - مراجعة الأبحاث في مجال التشفير ما بعد الكم
   - تحليل بروتوكول Signal
   - دراسات حول TOTP والمصادقة الثنائية

3. **الفصل الثالث: التصميم والتطوير**
   - البنية المعمارية للنظام
   - تصميم بروتوكول PQX3DH
   - آليات المصادقة والتشفير
   - نظام مشاركة الملفات الآمنة

4. **الفصل الرابع: التنفيذ والاختبارات**
   - تفاصيل التنفيذ العملي
   - الاختبارات الأمنية (19 اختبار)
   - اختبارات الأداء (16 اختبار)
   - تحليل النتائج

5. **الخاتمة**
   - ملخص الإنجازات
   - نقاط القوة والضعف
   - التوصيات والعمل المستقبلي

### النتائج الرئيسية

- ✅ **100% نجاح** في جميع الاختبارات الأمنية
- ✅ معدل إنتروبيا **7.98/8.0** (قريب من المثالي)
- ✅ معدل معالجة **3000 رسالة/ثانية**
- ✅ معدل تشفير ملفات **40 ميجابايت/ثانية**
- ✅ زمن مصافحة PQX3DH: **15-25 مللي ثانية**

### التقنيات المستخدمة

| التقنية | الاستخدام |
|---------|----------|
| Python 3.10+ | لغة البرمجة الرئيسية |
| Flask | إطار الويب |
| liboqs-python | مكتبة التشفير ما بعد الكم |
| cryptography | التشفير التقليدي |
| pyotp | توليد رموز TOTP |
| Socket.IO | الاتصال الفوري |
| SQLite | قاعدة البيانات |

### الملفات

- 📄 **[تقرير المشروع النهائي تخرج 2 النسخة النهائية.pdf](./تقرير%20المشروع%20النهائي%20تخرج%202%20النسخة%20النهائية.pdf)** - التقرير الكامل (128 صفحة)

### رابط الكود المصدري

الكود المصدري الكامل للمشروع متوفر على: [GitHub Repository Link]

---

### Project Information (English)

**Title:** Secure Messaging Application using Post-Quantum Cryptography and Hybrid PQX3DH Protocol

**Student:** Mohammad Malek Ghannam

**Supervisor:** Dr. Christine Zeineh

**University:** Syrian Private University - Faculty of Informatics Engineering

**Major:** Computer Systems and Networks Security Engineering

**Academic Year:** 2025 - 2026

### Abstract

This project aims to develop a secure messaging system that combines traditional cryptography with post-quantum cryptography to protect communications from future quantum threats, especially "Harvest Now, Decrypt Later" (HNDL) attacks.

The system implements a hybrid PQX3DH protocol combining traditional X3DH with Kyber-512, enhanced with Double Ratchet for forward and backward secrecy, XChaCha20-Poly1305 for symmetric encryption, TOTP two-factor authentication, and secure file sharing with advanced security policies.

### Key Results

- ✅ **100% success** in all security tests
- ✅ Entropy rate **7.98/8.0** (near perfect)
- ✅ Processing rate **3000 messages/second**
- ✅ File encryption rate **40 MB/second**
- ✅ PQX3DH handshake time: **15-25 milliseconds**

### Files

- 📄 **[Final Graduation Project Report.pdf](./تقرير%20المشروع%20النهائي%20تخرج%202%20النسخة%20النهائية.pdf)** - Complete report (128 pages, Arabic)

### Source Code

Full source code available at: [GitHub Repository Link]

</div>

---

## 📞 Contact | التواصل

For questions or collaboration:
- GitHub: [Your GitHub Profile]
- Email: [Your Email]

## 📜 License | الرخصة

This report is provided for academic and educational purposes.

---

**© 2026 Mohammad Malek Ghannam - Syrian Private University**
