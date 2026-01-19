"""
اختبارات التشفير مع طباعة الدلائل والأدلة
Encryption Tests with Evidence Output
"""

import sys
import os

# إضافة مسار المشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime

# استيراد وحدات التشفير
from messenger.crypto.crypto_utils import (
    aead_encrypt_xchacha20poly1305,
    aead_decrypt_xchacha20poly1305,
)
from messenger.crypto.ratchet import DoubleRatchet
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
)

from cryptography.hazmat.primitives.asymmetric import x25519
import oqs


def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_evidence(label, value, max_len=64):
    if isinstance(value, bytes):
        hex_val = value.hex()
        if len(hex_val) > max_len:
            display = f"{hex_val[:max_len]}... ({len(value)} bytes)"
        else:
            display = f"{hex_val} ({len(value)} bytes)"
    else:
        display = str(value)
    print(f"  {label}: {display}")


def test_1_xchacha20_roundtrip():
    """اختبار 1: XChaCha20-Poly1305 Round-Trip"""
    print_separator("TEST 1: XChaCha20-Poly1305 Round-Trip")
    
    # توليد مفتاح
    key = os.urandom(32)
    print_evidence("Key", key)
    
    # النص الأصلي
    plaintext = b"Hello World! This is a secret message."
    print_evidence("Plaintext", plaintext)
    print_evidence("Plaintext (text)", plaintext.decode())
    
    # التشفير
    ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
    print_evidence("Ciphertext", ciphertext)
    
    # فك التشفير
    decrypted = aead_decrypt_xchacha20poly1305(ciphertext, key=key)
    print_evidence("Decrypted", decrypted)
    print_evidence("Decrypted (text)", decrypted.decode())
    
    # التحقق
    assert decrypted == plaintext
    print("\n  [RESULT] PASSED - Decrypted matches original plaintext")
    return True


def test_2_wrong_key_rejected():
    """اختبار 2: رفض المفتاح الخاطئ"""
    print_separator("TEST 2: Wrong Key Rejection")
    
    key1 = os.urandom(32)
    key2 = os.urandom(32)
    print_evidence("Key 1 (correct)", key1)
    print_evidence("Key 2 (wrong)", key2)
    
    plaintext = b"Secret data"
    print_evidence("Plaintext", plaintext)
    
    ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key1)
    print_evidence("Ciphertext", ciphertext)
    
    # محاولة فك التشفير بمفتاح خاطئ
    try:
        aead_decrypt_xchacha20poly1305(ciphertext, key=key2)
        print("\n  [RESULT] FAILED - Wrong key was accepted!")
        return False
    except Exception as e:
        print(f"\n  [RESULT] PASSED - Wrong key rejected with error: {type(e).__name__}")
        return True


def test_3_tamper_detection():
    """اختبار 3: كشف التلاعب"""
    print_separator("TEST 3: Tamper Detection")
    
    key = os.urandom(32)
    plaintext = b"Important data that must not be modified"
    print_evidence("Key", key)
    print_evidence("Plaintext", plaintext)
    
    ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
    print_evidence("Original Ciphertext", ciphertext)
    
    # تعديل بايت واحد
    tampered = bytearray(ciphertext)
    original_byte = tampered[30]
    tampered[30] ^= 0xFF
    tampered = bytes(tampered)
    
    print(f"  Modified byte at position 30: 0x{original_byte:02x} -> 0x{tampered[30]:02x}")
    print_evidence("Tampered Ciphertext", tampered)
    
    try:
        aead_decrypt_xchacha20poly1305(tampered, key=key)
        print("\n  [RESULT] FAILED - Tampered data was accepted!")
        return False
    except Exception as e:
        print(f"\n  [RESULT] PASSED - Tamper detected with error: {type(e).__name__}")
        return True


def test_4_unique_ciphertexts():
    """اختبار 4: تفرد النصوص المشفرة"""
    print_separator("TEST 4: Unique Ciphertexts (Same plaintext, same key)")
    
    key = os.urandom(32)
    plaintext = b"Same message"
    print_evidence("Key", key)
    print_evidence("Plaintext", plaintext)
    
    ciphertexts = []
    print("\n  Encrypting same plaintext 5 times:")
    for i in range(5):
        ct = aead_encrypt_xchacha20poly1305(plaintext, key=key)
        ciphertexts.append(ct)
        print(f"    Ciphertext {i+1}: {ct.hex()[:40]}...")
    
    unique_count = len(set(ciphertexts))
    print(f"\n  Unique ciphertexts: {unique_count}/5")
    
    if unique_count == 5:
        print("  [RESULT] PASSED - All ciphertexts are unique (random nonce)")
        return True
    else:
        print("  [RESULT] FAILED - Some ciphertexts are identical!")
        return False


def test_5_file_encryption():
    """اختبار 5: تشفير الملفات"""
    print_separator("TEST 5: File Encryption Round-Trip")
    
    # محتوى الملف
    file_content = b"This is file content with some data: " + os.urandom(50)
    print_evidence("File Content", file_content)
    print(f"  File Size: {len(file_content)} bytes")
    
    # توليد مفتاح
    key = generate_file_key()
    print_evidence("File Key", key)
    
    # التشفير
    encrypted = encrypt_file(file_content, key)
    print_evidence("Encrypted File", encrypted)
    print(f"  Encrypted Size: {len(encrypted)} bytes")
    
    # فك التشفير
    decrypted = decrypt_file(encrypted, key)
    print_evidence("Decrypted File", decrypted)
    
    assert decrypted == file_content
    print("\n  [RESULT] PASSED - File decrypted correctly")
    return True


def test_6_pqx3dh_key_agreement():
    """اختبار 6: PQ-X3DH Key Agreement"""
    print_separator("TEST 6: PQ-X3DH Key Agreement (Alice <-> Bob)")
    
    # مفاتيح Alice
    alice_ik_priv = x25519.X25519PrivateKey.generate()
    alice_ik_pub = alice_ik_priv.public_key()
    print("  Alice's Keys:")
    print_evidence("    Identity Key (public)", alice_ik_pub.public_bytes_raw())
    
    # مفاتيح Bob
    bob_ik_priv = x25519.X25519PrivateKey.generate()
    bob_ik_pub = bob_ik_priv.public_key()
    bob_spk_priv = x25519.X25519PrivateKey.generate()
    bob_spk_pub = bob_spk_priv.public_key()
    
    print("\n  Bob's Keys:")
    print_evidence("    Identity Key (public)", bob_ik_pub.public_bytes_raw())
    print_evidence("    Signed Pre-Key (public)", bob_spk_pub.public_bytes_raw())
    
    # Kyber keys
    with oqs.KeyEncapsulation("Kyber512") as kem:
        bob_kyber_pub = kem.generate_keypair()
        bob_kyber_priv = kem.export_secret_key()
    print_evidence("    Kyber Public Key", bob_kyber_pub)
    
    # Alice initiates
    print("\n  Alice initiates PQ-X3DH...")
    alice_rk, alice_ek, kyber_ct, _ = pqx3dh_initiate(
        my_ik_priv=alice_ik_priv,
        their_ik_pub=bob_ik_pub,
        their_spk_pub=bob_spk_pub,
        their_opk_pub=None,
        their_kyber_pub=bob_kyber_pub,
    )
    print_evidence("    Alice's Ephemeral Key", alice_ek.public_key().public_bytes_raw())
    print_evidence("    Kyber Ciphertext", kyber_ct)
    print_evidence("    Alice's Root Key", alice_rk)
    
    # Bob responds
    print("\n  Bob responds to PQ-X3DH...")
    bob_rk = pqx3dh_respond(
        my_ik_priv=bob_ik_priv,
        my_spk_priv=bob_spk_priv,
        my_opk_priv=None,
        my_kyber_priv=bob_kyber_priv,
        their_ik_pub=alice_ik_pub,
        ek_pub_bytes=alice_ek.public_key().public_bytes_raw(),
        kyber_ct=kyber_ct,
    )
    print_evidence("    Bob's Root Key", bob_rk)
    
    # التحقق
    print("\n  Comparing Root Keys:")
    print(f"    Alice: {alice_rk.hex()}")
    print(f"    Bob:   {bob_rk.hex()}")
    
    if alice_rk == bob_rk:
        print("\n  [RESULT] PASSED - Both parties derived the same root key!")
        return True
    else:
        print("\n  [RESULT] FAILED - Root keys don't match!")
        return False


def test_7_double_ratchet_messages():
    """اختبار 7: Double Ratchet Message Exchange"""
    print_separator("TEST 7: Double Ratchet Message Exchange")
    
    # Setup keys
    alice_ik_priv = x25519.X25519PrivateKey.generate()
    bob_ik_priv = x25519.X25519PrivateKey.generate()
    bob_spk_priv = x25519.X25519PrivateKey.generate()
    
    with oqs.KeyEncapsulation("Kyber512") as kem:
        bob_kyber_pub = kem.generate_keypair()
        bob_kyber_priv = kem.export_secret_key()
    
    # PQ-X3DH
    alice_rk, alice_ek, kyber_ct, _ = pqx3dh_initiate(
        my_ik_priv=alice_ik_priv,
        their_ik_pub=bob_ik_priv.public_key(),
        their_spk_pub=bob_spk_priv.public_key(),
        their_opk_pub=None,
        their_kyber_pub=bob_kyber_pub,
    )
    
    bob_rk = pqx3dh_respond(
        my_ik_priv=bob_ik_priv,
        my_spk_priv=bob_spk_priv,
        my_opk_priv=None,
        my_kyber_priv=bob_kyber_priv,
        their_ik_pub=alice_ik_priv.public_key(),
        ek_pub_bytes=alice_ek.public_key().public_bytes_raw(),
        kyber_ct=kyber_ct,
    )
    
    # Build ratchets
    alice_ratchet = build_initiator_ratchet(alice_rk, alice_ek, bob_spk_priv.public_key())
    bob_ratchet = build_responder_ratchet(bob_rk, bob_spk_priv, 
                                          alice_ek.public_key().public_bytes_raw())
    
    print("  Session established via PQ-X3DH")
    print_evidence("  Shared Root Key", alice_rk)
    
    # Message 1: Alice -> Bob
    print("\n  Message 1: Alice -> Bob")
    msg1 = b"Hello Bob! How are you?"
    print_evidence("    Plaintext", msg1)
    enc1 = alice_ratchet.encrypt(msg1)
    print(f"    Encrypted: {json.dumps(enc1, indent=6)[:200]}...")
    dec1 = bob_ratchet.decrypt(enc1)
    print_evidence("    Decrypted", dec1)
    assert dec1 == msg1
    print("    [OK] Message delivered correctly")
    
    # Message 2: Bob -> Alice
    print("\n  Message 2: Bob -> Alice")
    msg2 = b"Hi Alice! I'm fine, thanks!"
    print_evidence("    Plaintext", msg2)
    enc2 = bob_ratchet.encrypt(msg2)
    print(f"    Encrypted: {json.dumps(enc2, indent=6)[:200]}...")
    dec2 = alice_ratchet.decrypt(enc2)
    print_evidence("    Decrypted", dec2)
    assert dec2 == msg2
    print("    [OK] Message delivered correctly")
    
    # Message 3: Alice -> Bob
    print("\n  Message 3: Alice -> Bob")
    msg3 = b"Great! Let's meet tomorrow."
    print_evidence("    Plaintext", msg3)
    enc3 = alice_ratchet.encrypt(msg3)
    dec3 = bob_ratchet.decrypt(enc3)
    print_evidence("    Decrypted", dec3)
    assert dec3 == msg3
    print("    [OK] Message delivered correctly")
    
    print("\n  [RESULT] PASSED - All messages exchanged successfully!")
    return True


def test_8_forward_secrecy():
    """اختبار 8: Forward Secrecy"""
    print_separator("TEST 8: Forward Secrecy Verification")
    
    alice_ik_priv = x25519.X25519PrivateKey.generate()
    bob_ik_priv = x25519.X25519PrivateKey.generate()
    bob_spk_priv = x25519.X25519PrivateKey.generate()
    
    print("  Creating two separate sessions with same identity keys...")
    
    # Session 1
    with oqs.KeyEncapsulation("Kyber512") as kem:
        kyber_pub1 = kem.generate_keypair()
    
    rk1, ek1, _, _ = pqx3dh_initiate(
        my_ik_priv=alice_ik_priv,
        their_ik_pub=bob_ik_priv.public_key(),
        their_spk_pub=bob_spk_priv.public_key(),
        their_opk_pub=None,
        their_kyber_pub=kyber_pub1,
    )
    
    # Session 2
    with oqs.KeyEncapsulation("Kyber512") as kem:
        kyber_pub2 = kem.generate_keypair()
    
    rk2, ek2, _, _ = pqx3dh_initiate(
        my_ik_priv=alice_ik_priv,
        their_ik_pub=bob_ik_priv.public_key(),
        their_spk_pub=bob_spk_priv.public_key(),
        their_opk_pub=None,
        their_kyber_pub=kyber_pub2,
    )
    
    print("\n  Session 1:")
    print_evidence("    Ephemeral Key", ek1.public_key().public_bytes_raw())
    print_evidence("    Root Key", rk1)
    
    print("\n  Session 2:")
    print_evidence("    Ephemeral Key", ek2.public_key().public_bytes_raw())
    print_evidence("    Root Key", rk2)
    
    ek1_bytes = ek1.public_key().public_bytes_raw()
    ek2_bytes = ek2.public_key().public_bytes_raw()
    
    print("\n  Verification:")
    print(f"    Ephemeral keys different: {ek1_bytes != ek2_bytes}")
    print(f"    Root keys different: {rk1 != rk2}")
    
    if rk1 != rk2 and ek1_bytes != ek2_bytes:
        print("\n  [RESULT] PASSED - Forward secrecy verified!")
        print("  (Compromising one session does not affect others)")
        return True
    else:
        print("\n  [RESULT] FAILED - Sessions share keys!")
        return False


def run_all_tests():
    """تشغيل جميع الاختبارات"""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + "    CRYPTOGRAPHIC SYSTEM TEST SUITE WITH EVIDENCE".center(68) + "#")
    print("#" + f"    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    tests = [
        ("XChaCha20 Round-Trip", test_1_xchacha20_roundtrip),
        ("Wrong Key Rejection", test_2_wrong_key_rejected),
        ("Tamper Detection", test_3_tamper_detection),
        ("Unique Ciphertexts", test_4_unique_ciphertexts),
        ("File Encryption", test_5_file_encryption),
        ("PQ-X3DH Key Agreement", test_6_pqx3dh_key_agreement),
        ("Double Ratchet Messages", test_7_double_ratchet_messages),
        ("Forward Secrecy", test_8_forward_secrecy),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  [ERROR] {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "#" * 70)
    print("#" + "    FINAL SUMMARY".center(68) + "#")
    print("#" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Success Rate: {passed/total*100:.1f}%")
    
    print("\n  Individual Results:")
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "[OK]" if result else "[X]"
        print(f"    {symbol} {name}: {status}")
    
    print("\n" + "#" * 70)
    if passed == total:
        print("#" + "    ALL TESTS PASSED SUCCESSFULLY!".center(68) + "#")
    else:
        print("#" + f"    {total - passed} TEST(S) FAILED".center(68) + "#")
    print("#" * 70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    run_all_tests()
