"""
اختبارات شاملة لنظام التشفير في التطبيق
Comprehensive Encryption System Tests

يتضمن:
1. اختبارات XChaCha20-Poly1305 (التشفير المتماثل)
2. اختبارات PQ-X3DH (تبادل المفاتيح الكمي)
3. اختبارات Double Ratchet (تشفير الرسائل)
4. اختبارات تشفير الملفات
"""

import os
import pytest
from hypothesis import given, strategies as st, settings

# استيراد وحدات التشفير
from messenger.crypto.crypto_utils import (
    aead_encrypt_xchacha20poly1305,
    aead_decrypt_xchacha20poly1305,
)
from messenger.crypto.ratchet import DoubleRatchet, b64e, b64d
from messenger.crypto.pqx3dh import (
    pqx3dh_initiate,
    pqx3dh_respond,
    build_initiator_ratchet,
    build_responder_ratchet,
)
from messenger.files.encryption import (
    generate_file_key,
    encrypt_file,
    decrypt_file,
    encrypt_file_with_new_key,
    KEY_SIZE,
)

from cryptography.hazmat.primitives.asymmetric import x25519
import oqs


# ============================================
# 1. اختبارات XChaCha20-Poly1305
# ============================================

class TestXChaCha20Poly1305:
    """اختبارات التشفير المتماثل XChaCha20-Poly1305"""
    
    def test_encrypt_decrypt_roundtrip_basic(self):
        """اختبار أساسي: تشفير ثم فك تشفير يعيد النص الأصلي"""
        key = os.urandom(32)
        plaintext = "Hello, World! مرحبا بالعالم".encode('utf-8')
        
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
        decrypted = aead_decrypt_xchacha20poly1305(ciphertext, key=key)
        
        assert decrypted == plaintext
        print(f"✓ النص الأصلي: {plaintext}")
        print(f"✓ النص المشفر (أول 50 بايت): {ciphertext[:50].hex()}...")
        print(f"✓ النص بعد فك التشفير: {decrypted}")
    
    @given(st.binary(min_size=1, max_size=10000))
    @settings(max_examples=50)
    def test_encrypt_decrypt_roundtrip_property(self, plaintext):
        """Property: لأي نص، التشفير ثم فك التشفير يعيد النص الأصلي"""
        key = os.urandom(32)
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
        decrypted = aead_decrypt_xchacha20poly1305(ciphertext, key=key)
        assert decrypted == plaintext
    
    def test_ciphertext_different_from_plaintext(self):
        """التحقق من أن النص المشفر مختلف عن النص الأصلي"""
        key = os.urandom(32)
        plaintext = b"Secret message"
        
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
        
        # النص المشفر يجب أن يكون مختلف
        assert ciphertext != plaintext
        # النص المشفر أطول (يحتوي على nonce + tag)
        assert len(ciphertext) > len(plaintext)
        print(f"✓ طول النص الأصلي: {len(plaintext)} بايت")
        print(f"✓ طول النص المشفر: {len(ciphertext)} بايت")
    
    def test_different_keys_produce_different_ciphertext(self):
        """مفاتيح مختلفة تنتج نصوص مشفرة مختلفة"""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Same message"
        
        ct1 = aead_encrypt_xchacha20poly1305(plaintext, key=key1)
        ct2 = aead_encrypt_xchacha20poly1305(plaintext, key=key2)
        
        # حتى مع نفس النص، المفاتيح المختلفة تنتج نتائج مختلفة
        assert ct1 != ct2
        print("✓ مفاتيح مختلفة تنتج نصوص مشفرة مختلفة")
    
    def test_wrong_key_fails_decryption(self):
        """المفتاح الخاطئ يفشل في فك التشفير"""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Secret"
        
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key1)
        
        with pytest.raises(Exception):
            aead_decrypt_xchacha20poly1305(ciphertext, key=key2)
        print("✓ المفتاح الخاطئ يرفض فك التشفير")
    
    def test_tampered_ciphertext_fails(self):
        """النص المشفر المعدّل يفشل في فك التشفير"""
        key = os.urandom(32)
        plaintext = b"Important data"
        
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
        
        # تعديل بايت واحد في النص المشفر
        tampered = bytearray(ciphertext)
        tampered[30] ^= 0xFF  # قلب البتات
        tampered = bytes(tampered)
        
        with pytest.raises(Exception):
            aead_decrypt_xchacha20poly1305(tampered, key=key)
        print("✓ النص المعدّل يُرفض (حماية من التلاعب)")
    
    def test_aad_authentication(self):
        """اختبار البيانات الإضافية المصادق عليها (AAD)"""
        key = os.urandom(32)
        plaintext = b"Message"
        aad = b"metadata:user123"
        
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key, aad=aad)
        
        # فك التشفير مع نفس AAD ينجح
        decrypted = aead_decrypt_xchacha20poly1305(ciphertext, key=key, aad=aad)
        assert decrypted == plaintext
        
        # فك التشفير مع AAD مختلف يفشل
        with pytest.raises(Exception):
            aead_decrypt_xchacha20poly1305(ciphertext, key=key, aad=b"wrong_aad")
        print("✓ AAD يوفر حماية إضافية للبيانات الوصفية")
    
    def test_invalid_key_size_rejected(self):
        """المفاتيح بأحجام خاطئة تُرفض"""
        plaintext = b"Test"
        
        with pytest.raises(ValueError):
            aead_encrypt_xchacha20poly1305(plaintext, key=b"short")
        
        with pytest.raises(ValueError):
            aead_encrypt_xchacha20poly1305(plaintext, key=os.urandom(64))
        print("✓ أحجام المفاتيح الخاطئة تُرفض")


# ============================================
# 2. اختبارات تشفير الملفات
# ============================================

class TestFileEncryption:
    """اختبارات تشفير الملفات"""
    
    def test_file_key_generation(self):
        """توليد مفتاح ملف بالحجم الصحيح"""
        key = generate_file_key()
        assert len(key) == KEY_SIZE
        assert len(key) == 32
        print(f"✓ مفتاح الملف: {key.hex()[:32]}...")
    
    def test_file_keys_are_unique(self):
        """كل مفتاح ملف فريد"""
        keys = [generate_file_key() for _ in range(100)]
        unique_keys = set(keys)
        assert len(unique_keys) == 100
        print("✓ 100 مفتاح فريد تم توليدهم")
    
    def test_file_encrypt_decrypt_roundtrip(self):
        """تشفير وفك تشفير ملف"""
        content = "File content with Arabic: محتوى الملف".encode('utf-8')
        key = generate_file_key()
        
        encrypted = encrypt_file(content, key)
        decrypted = decrypt_file(encrypted, key)
        
        assert decrypted == content
        print(f"✓ محتوى الملف الأصلي: {len(content)} بايت")
        print(f"✓ محتوى الملف المشفر: {len(encrypted)} بايت")
    
    @given(st.binary(min_size=1, max_size=50000))
    @settings(max_examples=30)
    def test_file_roundtrip_property(self, content):
        """Property: لأي محتوى ملف، التشفير ثم فك التشفير يعيد المحتوى الأصلي"""
        key = generate_file_key()
        encrypted = encrypt_file(content, key)
        decrypted = decrypt_file(encrypted, key)
        assert decrypted == content
    
    def test_encrypt_with_new_key(self):
        """تشفير ملف مع توليد مفتاح جديد"""
        content = b"New file content"
        
        encrypted, key = encrypt_file_with_new_key(content)
        
        assert len(key) == KEY_SIZE
        decrypted = decrypt_file(encrypted, key)
        assert decrypted == content
        print("✓ تشفير مع مفتاح جديد يعمل بشكل صحيح")
    
    def test_file_wrong_key_fails(self):
        """المفتاح الخاطئ يفشل في فك تشفير الملف"""
        content = b"Secret file"
        key1 = generate_file_key()
        key2 = generate_file_key()
        
        encrypted = encrypt_file(content, key1)
        
        with pytest.raises(ValueError):
            decrypt_file(encrypted, key2)
        print("✓ المفتاح الخاطئ يُرفض")


# ============================================
# 3. اختبارات PQ-X3DH (تبادل المفاتيح الكمي)
# ============================================

class TestPQX3DH:
    """اختبارات بروتوكول PQ-X3DH لتبادل المفاتيح"""
    
    def _generate_keypair(self):
        """توليد زوج مفاتيح X25519"""
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key()
        return priv, pub
    
    def _generate_kyber_keypair(self):
        """توليد زوج مفاتيح Kyber512"""
        with oqs.KeyEncapsulation("Kyber512") as kem:
            pub = kem.generate_keypair()
            priv = kem.export_secret_key()
        return priv, pub
    
    def test_pqx3dh_key_agreement(self):
        """اختبار اتفاق المفاتيح بين طرفين"""
        # مفاتيح Alice (المرسل)
        alice_ik_priv, alice_ik_pub = self._generate_keypair()
        
        # مفاتيح Bob (المستقبل)
        bob_ik_priv, bob_ik_pub = self._generate_keypair()
        bob_spk_priv, bob_spk_pub = self._generate_keypair()
        bob_opk_priv, bob_opk_pub = self._generate_keypair()
        bob_kyber_priv, bob_kyber_pub = self._generate_kyber_keypair()
        
        # Alice تبدأ الجلسة
        alice_rk, alice_ek, kyber_ct, opk_used = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_pub,
            their_spk_pub=bob_spk_pub,
            their_opk_pub=bob_opk_pub,
            their_kyber_pub=bob_kyber_pub,
        )
        
        # Bob يستجيب
        bob_rk = pqx3dh_respond(
            my_ik_priv=bob_ik_priv,
            my_spk_priv=bob_spk_priv,
            my_opk_priv=bob_opk_priv,
            my_kyber_priv=bob_kyber_priv,
            their_ik_pub=alice_ik_pub,
            ek_pub_bytes=alice_ek.public_key().public_bytes_raw(),
            kyber_ct=kyber_ct,
        )
        
        # يجب أن يتفق الطرفان على نفس المفتاح الجذري
        assert alice_rk == bob_rk
        assert len(alice_rk) == 32
        print(f"✓ Alice root key: {alice_rk.hex()[:32]}...")
        print(f"✓ Bob root key: {bob_rk.hex()[:32]}...")
        print("✓ الطرفان اتفقا على نفس المفتاح!")
    
    def test_pqx3dh_without_opk(self):
        """اختبار PQ-X3DH بدون مفتاح OPK"""
        alice_ik_priv, alice_ik_pub = self._generate_keypair()
        bob_ik_priv, bob_ik_pub = self._generate_keypair()
        bob_spk_priv, bob_spk_pub = self._generate_keypair()
        bob_kyber_priv, bob_kyber_pub = self._generate_kyber_keypair()
        
        alice_rk, alice_ek, kyber_ct, opk_used = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_pub,
            their_spk_pub=bob_spk_pub,
            their_opk_pub=None,  # بدون OPK
            their_kyber_pub=bob_kyber_pub,
        )
        
        bob_rk = pqx3dh_respond(
            my_ik_priv=bob_ik_priv,
            my_spk_priv=bob_spk_priv,
            my_opk_priv=None,  # بدون OPK
            my_kyber_priv=bob_kyber_priv,
            their_ik_pub=alice_ik_pub,
            ek_pub_bytes=alice_ek.public_key().public_bytes_raw(),
            kyber_ct=kyber_ct,
        )
        
        assert alice_rk == bob_rk
        assert opk_used is None
        print("✓ PQ-X3DH يعمل بدون OPK")
    
    def test_different_sessions_different_keys(self):
        """جلسات مختلفة تنتج مفاتيح مختلفة"""
        alice_ik_priv, alice_ik_pub = self._generate_keypair()
        bob_ik_priv, bob_ik_pub = self._generate_keypair()
        bob_spk_priv, bob_spk_pub = self._generate_keypair()
        bob_kyber_priv, bob_kyber_pub = self._generate_kyber_keypair()
        
        # جلسة 1
        rk1, _, _, _ = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_pub,
            their_spk_pub=bob_spk_pub,
            their_opk_pub=None,
            their_kyber_pub=bob_kyber_pub,
        )
        
        # جلسة 2 (مفاتيح Kyber جديدة)
        bob_kyber_priv2, bob_kyber_pub2 = self._generate_kyber_keypair()
        rk2, _, _, _ = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_pub,
            their_spk_pub=bob_spk_pub,
            their_opk_pub=None,
            their_kyber_pub=bob_kyber_pub2,
        )
        
        assert rk1 != rk2
        print("✓ جلسات مختلفة تنتج مفاتيح مختلفة")


# ============================================
# 4. اختبارات Double Ratchet
# ============================================

class TestDoubleRatchet:
    """اختبارات بروتوكول Double Ratchet للرسائل"""
    
    def _setup_ratchets(self):
        """إعداد ratchets لطرفين"""
        # توليد المفاتيح
        alice_ik_priv = x25519.X25519PrivateKey.generate()
        alice_ik_pub = alice_ik_priv.public_key()
        
        bob_ik_priv = x25519.X25519PrivateKey.generate()
        bob_ik_pub = bob_ik_priv.public_key()
        bob_spk_priv = x25519.X25519PrivateKey.generate()
        bob_spk_pub = bob_spk_priv.public_key()
        
        with oqs.KeyEncapsulation("Kyber512") as kem:
            bob_kyber_pub = kem.generate_keypair()
            bob_kyber_priv = kem.export_secret_key()
        
        # PQ-X3DH
        alice_rk, alice_ek, kyber_ct, _ = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_pub,
            their_spk_pub=bob_spk_pub,
            their_opk_pub=None,
            their_kyber_pub=bob_kyber_pub,
        )
        
        bob_rk = pqx3dh_respond(
            my_ik_priv=bob_ik_priv,
            my_spk_priv=bob_spk_priv,
            my_opk_priv=None,
            my_kyber_priv=bob_kyber_priv,
            their_ik_pub=alice_ik_pub,
            ek_pub_bytes=alice_ek.public_key().public_bytes_raw(),
            kyber_ct=kyber_ct,
        )
        
        # بناء Ratchets
        alice_ratchet = build_initiator_ratchet(alice_rk, alice_ek, bob_spk_pub)
        bob_ratchet = build_responder_ratchet(bob_rk, bob_spk_priv, 
                                              alice_ek.public_key().public_bytes_raw())
        
        return alice_ratchet, bob_ratchet
    
    def test_single_message_exchange(self):
        """تبادل رسالة واحدة"""
        alice, bob = self._setup_ratchets()
        
        message = "Hello Bob! مرحبا بوب".encode('utf-8')
        encrypted = alice.encrypt(message)
        decrypted = bob.decrypt(encrypted)
        
        assert decrypted == message
        print(f"✓ الرسالة الأصلية: {message}")
        print(f"✓ الرسالة المشفرة: {encrypted['ciphertext'][:50]}...")
        print(f"✓ الرسالة بعد فك التشفير: {decrypted}")
    
    def test_bidirectional_messages(self):
        """تبادل رسائل في الاتجاهين"""
        alice, bob = self._setup_ratchets()
        
        # Alice -> Bob
        msg1 = b"Hi Bob!"
        enc1 = alice.encrypt(msg1)
        dec1 = bob.decrypt(enc1)
        assert dec1 == msg1
        
        # Bob -> Alice
        msg2 = b"Hi Alice!"
        enc2 = bob.encrypt(msg2)
        dec2 = alice.decrypt(enc2)
        assert dec2 == msg2
        
        # Alice -> Bob مرة أخرى
        msg3 = b"How are you?"
        enc3 = alice.encrypt(msg3)
        dec3 = bob.decrypt(enc3)
        assert dec3 == msg3
        
        print("✓ تبادل رسائل ثنائي الاتجاه يعمل")
    
    def test_multiple_messages_same_direction(self):
        """رسائل متعددة في نفس الاتجاه"""
        alice, bob = self._setup_ratchets()
        
        messages = [f"Message {i}".encode() for i in range(10)]
        
        for msg in messages:
            encrypted = alice.encrypt(msg)
            decrypted = bob.decrypt(encrypted)
            assert decrypted == msg
        
        print(f"✓ {len(messages)} رسائل تم تبادلها بنجاح")
    
    def test_out_of_order_messages(self):
        """رسائل خارج الترتيب"""
        alice, bob = self._setup_ratchets()
        
        # Alice ترسل 3 رسائل
        enc1 = alice.encrypt(b"Message 1")
        enc2 = alice.encrypt(b"Message 2")
        enc3 = alice.encrypt(b"Message 3")
        
        # Bob يستقبل بترتيب مختلف
        dec3 = bob.decrypt(enc3)
        dec1 = bob.decrypt(enc1)
        dec2 = bob.decrypt(enc2)
        
        assert dec1 == b"Message 1"
        assert dec2 == b"Message 2"
        assert dec3 == b"Message 3"
        print("✓ الرسائل خارج الترتيب تُعالج بشكل صحيح")
    
    def test_ratchet_serialization(self):
        """حفظ واستعادة حالة Ratchet"""
        alice, bob = self._setup_ratchets()
        
        # تبادل بعض الرسائل
        enc1 = alice.encrypt(b"Before save")
        bob.decrypt(enc1)
        
        # حفظ الحالة
        alice_state = alice.to_dict()
        bob_state = bob.to_dict()
        
        # استعادة الحالة
        alice_restored = DoubleRatchet.from_dict(alice_state)
        bob_restored = DoubleRatchet.from_dict(bob_state)
        
        # متابعة التبادل
        enc2 = alice_restored.encrypt(b"After restore")
        dec2 = bob_restored.decrypt(enc2)
        
        assert dec2 == b"After restore"
        print("✓ حفظ واستعادة حالة Ratchet يعمل")
    
    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=20)
    def test_message_roundtrip_property(self, message):
        """Property: لأي رسالة، التشفير ثم فك التشفير يعيد الرسالة الأصلية"""
        alice, bob = self._setup_ratchets()
        encrypted = alice.encrypt(message)
        decrypted = bob.decrypt(encrypted)
        assert decrypted == message


# ============================================
# 5. اختبارات الأمان
# ============================================

class TestSecurityProperties:
    """اختبارات خصائص الأمان"""
    
    def test_forward_secrecy(self):
        """اختبار السرية الأمامية (Forward Secrecy)"""
        # إذا تم اختراق مفتاح جلسة، الرسائل السابقة تبقى آمنة
        alice_ik_priv = x25519.X25519PrivateKey.generate()
        bob_ik_priv = x25519.X25519PrivateKey.generate()
        bob_spk_priv = x25519.X25519PrivateKey.generate()
        
        with oqs.KeyEncapsulation("Kyber512") as kem:
            bob_kyber_pub = kem.generate_keypair()
            bob_kyber_priv = kem.export_secret_key()
        
        # جلسة 1
        rk1, ek1, ct1, _ = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_priv.public_key(),
            their_spk_pub=bob_spk_priv.public_key(),
            their_opk_pub=None,
            their_kyber_pub=bob_kyber_pub,
        )
        
        # جلسة 2 (مفاتيح ephemeral جديدة)
        rk2, ek2, ct2, _ = pqx3dh_initiate(
            my_ik_priv=alice_ik_priv,
            their_ik_pub=bob_ik_priv.public_key(),
            their_spk_pub=bob_spk_priv.public_key(),
            their_opk_pub=None,
            their_kyber_pub=bob_kyber_pub,
        )
        
        # المفاتيح الجذرية مختلفة
        assert rk1 != rk2
        # المفاتيح المؤقتة مختلفة
        assert ek1.public_key().public_bytes_raw() != ek2.public_key().public_bytes_raw()
        print("✓ السرية الأمامية: كل جلسة لها مفاتيح فريدة")
    
    def test_key_randomness(self):
        """اختبار عشوائية المفاتيح"""
        keys = [os.urandom(32) for _ in range(1000)]
        
        # التحقق من التفرد
        unique_keys = set(keys)
        assert len(unique_keys) == 1000
        
        # التحقق من التوزيع (كل بايت يجب أن يظهر)
        all_bytes = b''.join(keys)
        byte_counts = [all_bytes.count(bytes([i])) for i in range(256)]
        
        # كل قيمة بايت يجب أن تظهر على الأقل مرة واحدة
        assert all(count > 0 for count in byte_counts)
        print("✓ المفاتيح عشوائية وموزعة بشكل جيد")
    
    def test_ciphertext_indistinguishability(self):
        """اختبار عدم تمييز النصوص المشفرة"""
        key = os.urandom(32)
        
        # نفس النص يُشفر بشكل مختلف كل مرة (بسبب nonce عشوائي)
        plaintext = b"Same message"
        ciphertexts = [aead_encrypt_xchacha20poly1305(plaintext, key=key) for _ in range(100)]
        
        unique_cts = set(ciphertexts)
        assert len(unique_cts) == 100
        print("✓ نفس النص يُشفر بشكل مختلف كل مرة")


# ============================================
# تشغيل الاختبارات
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
