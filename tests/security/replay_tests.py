# Replay Attack Resistance Tests
# اختبارات مقاومة هجمات إعادة التشغيل

"""
Security tests for replay attack resistance.
اختبارات أمان مقاومة هجمات إعادة التشغيل

Requirements: 8.1, 8.2, 8.3
- Verify that replayed messages are rejected
- Verify that message counters prevent replay
- Verify that old session keys cannot decrypt new messages
"""

import os
from typing import Dict, Any, Tuple

from cryptography.hazmat.primitives.asymmetric import x25519

from tests.security.base import SecurityTestResult, SecuritySuite, TestStatus
from messenger.crypto.ratchet import DoubleRatchet
from messenger.crypto.pqx3dh import (
    pqx3dh_initiate, 
    pqx3dh_respond,
    build_initiator_ratchet,
    build_responder_ratchet
)
from messenger.pq_backend.backend import OQSKyberBackend


class ReplayTests:
    """
    Tests for replay attack resistance.
    اختبارات مقاومة هجمات إعادة التشغيل
    """
    
    def __init__(self):
        """Initialize replay tests."""
        self.kyber_backend = OQSKyberBackend()
    
    def _create_session_pair(self) -> Tuple[DoubleRatchet, DoubleRatchet]:
        """Create a pair of Double Ratchet sessions."""
        # Generate identity bundles
        alice_ik = x25519.X25519PrivateKey.generate()
        bob_ik = x25519.X25519PrivateKey.generate()
        bob_spk = x25519.X25519PrivateKey.generate()
        bob_opk = x25519.X25519PrivateKey.generate()
        bob_kyber_pub, bob_kyber_priv = self.kyber_backend.generate_keypair()
        
        # Alice initiates PQ-X3DH
        alice_rk, alice_ek, kyber_ct, _ = pqx3dh_initiate(
            my_ik_priv=alice_ik,
            their_ik_pub=bob_ik.public_key(),
            their_spk_pub=bob_spk.public_key(),
            their_opk_pub=bob_opk.public_key(),
            their_kyber_pub=bob_kyber_pub,
        )
        
        # Bob responds
        bob_rk = pqx3dh_respond(
            my_ik_priv=bob_ik,
            my_spk_priv=bob_spk,
            my_opk_priv=bob_opk,
            my_kyber_priv=bob_kyber_priv,
            their_ik_pub=alice_ik.public_key(),
            ek_pub_bytes=alice_ek.public_key().public_bytes_raw(),
            kyber_ct=kyber_ct,
        )
        
        # Build ratchets
        alice_ratchet = build_initiator_ratchet(alice_rk, alice_ek, bob_spk.public_key())
        bob_ratchet = build_responder_ratchet(bob_rk, bob_spk, alice_ek.public_key().public_bytes_raw())
        
        return alice_ratchet, bob_ratchet
    
    def test_message_replay_rejection(self) -> SecurityTestResult:
        """
        Test that replayed messages are rejected.
        اختبار رفض الرسائل المعادة
        
        In Double Ratchet, each message uses a unique key derived from
        the chain key. Replaying a message should fail because the
        receiving ratchet has already advanced.
        """
        alice, bob = self._create_session_pair()
        
        # Alice sends a message
        message = b"Hello Bob!"
        encrypted = alice.encrypt(message)
        
        # Bob decrypts successfully
        decrypted = bob.decrypt(encrypted)
        assert decrypted == message
        
        # Try to replay the same message
        replay_rejected = False
        try:
            bob.decrypt(encrypted)
            # If we get here, replay was accepted (bad!)
        except Exception:
            replay_rejected = True
        
        details = {
            "original_message_decrypted": True,
            "replay_rejected": replay_rejected,
        }
        
        if replay_rejected:
            return SecurityTestResult(
                test_name="Message Replay Rejection",
                category="replay",
                status=TestStatus.PASSED,
                description="Replayed messages are correctly rejected",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Message Replay Rejection",
                category="replay",
                status=TestStatus.FAILED,
                description="Replayed messages were accepted (CRITICAL!)",
                details=details,
                recommendation="CRITICAL: Implement message replay protection"
            )
    
    def test_message_counter_protection(self) -> SecurityTestResult:
        """
        Test that message counters prevent replay.
        اختبار أن عدادات الرسائل تمنع الإعادة
        """
        alice, bob = self._create_session_pair()
        
        # Send multiple messages
        messages = [f"Message {i}".encode() for i in range(5)]
        encrypted_messages = [alice.encrypt(msg) for msg in messages]
        
        # Decrypt in order
        for i, enc in enumerate(encrypted_messages):
            decrypted = bob.decrypt(enc)
            assert decrypted == messages[i]
        
        # Try to decrypt old messages again (should fail)
        old_message_rejected = 0
        for enc in encrypted_messages:
            try:
                bob.decrypt(enc)
            except:
                old_message_rejected += 1
        
        details = {
            "messages_sent": len(messages),
            "old_messages_rejected": old_message_rejected,
            "all_old_rejected": old_message_rejected == len(messages),
        }
        
        if old_message_rejected == len(messages):
            return SecurityTestResult(
                test_name="Message Counter Protection",
                category="replay",
                status=TestStatus.PASSED,
                description="Message counters correctly prevent replay of old messages",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Message Counter Protection",
                category="replay",
                status=TestStatus.FAILED,
                description=f"Only {old_message_rejected}/{len(messages)} old messages were rejected",
                details=details,
                recommendation="Review message counter implementation"
            )
    
    def test_out_of_order_messages(self) -> SecurityTestResult:
        """
        Test handling of out-of-order messages.
        اختبار معالجة الرسائل غير المرتبة
        
        Double Ratchet should handle some out-of-order messages
        using skipped message keys.
        """
        alice, bob = self._create_session_pair()
        
        # Send multiple messages
        messages = [f"Message {i}".encode() for i in range(5)]
        encrypted_messages = [alice.encrypt(msg) for msg in messages]
        
        # Decrypt out of order (skip first two, then go back)
        # Decrypt message 2, 3, 4 first
        for i in [2, 3, 4]:
            decrypted = bob.decrypt(encrypted_messages[i])
            assert decrypted == messages[i]
        
        # Now try to decrypt skipped messages 0 and 1
        skipped_decrypted = 0
        for i in [0, 1]:
            try:
                decrypted = bob.decrypt(encrypted_messages[i])
                if decrypted == messages[i]:
                    skipped_decrypted += 1
            except:
                pass
        
        details = {
            "total_messages": len(messages),
            "skipped_messages": 2,
            "skipped_successfully_decrypted": skipped_decrypted,
        }
        
        # Double Ratchet should handle skipped messages
        if skipped_decrypted == 2:
            return SecurityTestResult(
                test_name="Out-of-Order Message Handling",
                category="replay",
                status=TestStatus.PASSED,
                description="Skipped messages can be decrypted (correct Double Ratchet behavior)",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Out-of-Order Message Handling",
                category="replay",
                status=TestStatus.WARNING,
                description=f"Only {skipped_decrypted}/2 skipped messages could be decrypted",
                details=details,
                recommendation="Review skipped message key storage"
            )
    
    def test_session_isolation(self) -> SecurityTestResult:
        """
        Test that different sessions are isolated.
        اختبار عزل الجلسات المختلفة
        """
        # Create two separate sessions
        alice1, bob1 = self._create_session_pair()
        alice2, bob2 = self._create_session_pair()
        
        # Encrypt with session 1
        message = b"Secret message"
        encrypted = alice1.encrypt(message)
        
        # Try to decrypt with session 2 (should fail)
        cross_session_rejected = False
        try:
            bob2.decrypt(encrypted)
        except:
            cross_session_rejected = True
        
        # Verify session 1 still works
        session1_works = False
        try:
            decrypted = bob1.decrypt(encrypted)
            session1_works = (decrypted == message)
        except:
            pass
        
        details = {
            "cross_session_rejected": cross_session_rejected,
            "original_session_works": session1_works,
        }
        
        if cross_session_rejected and session1_works:
            return SecurityTestResult(
                test_name="Session Isolation",
                category="replay",
                status=TestStatus.PASSED,
                description="Sessions are properly isolated - messages cannot be decrypted by other sessions",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Session Isolation",
                category="replay",
                status=TestStatus.FAILED,
                description="Session isolation failed",
                details=details,
                recommendation="CRITICAL: Sessions are not properly isolated"
            )
    
    def test_old_session_key_rejection(self) -> SecurityTestResult:
        """
        Test that old session keys cannot decrypt new messages.
        اختبار أن مفاتيح الجلسة القديمة لا تفك تشفير الرسائل الجديدة
        """
        alice, bob = self._create_session_pair()
        
        # Save Bob's initial state
        bob_initial_state = bob.to_dict()
        
        # Exchange several messages to advance the ratchet
        for i in range(10):
            msg = f"Message {i}".encode()
            enc = alice.encrypt(msg)
            bob.decrypt(enc)
            
            # Bob replies to trigger DH ratchet
            reply = bob.encrypt(f"Reply {i}".encode())
            alice.decrypt(reply)
        
        # Alice sends a new message
        new_message = b"New secret message"
        new_encrypted = alice.encrypt(new_message)
        
        # Try to decrypt with old Bob state
        old_bob = DoubleRatchet.from_dict(bob_initial_state)
        old_key_rejected = False
        try:
            old_bob.decrypt(new_encrypted)
        except:
            old_key_rejected = True
        
        # Current Bob should still work
        current_bob_works = False
        try:
            decrypted = bob.decrypt(new_encrypted)
            current_bob_works = (decrypted == new_message)
        except:
            pass
        
        details = {
            "ratchet_steps": 10,
            "old_key_rejected": old_key_rejected,
            "current_key_works": current_bob_works,
        }
        
        if old_key_rejected and current_bob_works:
            return SecurityTestResult(
                test_name="Old Session Key Rejection",
                category="replay",
                status=TestStatus.PASSED,
                description="Old session keys cannot decrypt new messages (Forward Secrecy)",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Old Session Key Rejection",
                category="replay",
                status=TestStatus.FAILED,
                description="Old session keys can still decrypt new messages",
                details=details,
                recommendation="CRITICAL: Forward secrecy may be compromised"
            )
    
    def run_all_tests(self) -> SecuritySuite:
        """
        Run all replay attack tests.
        تشغيل جميع اختبارات هجمات الإعادة
        """
        suite = SecuritySuite(suite_name="Replay Attack Resistance")
        
        suite.add_result(self.test_message_replay_rejection())
        suite.add_result(self.test_message_counter_protection())
        suite.add_result(self.test_out_of_order_messages())
        suite.add_result(self.test_session_isolation())
        suite.add_result(self.test_old_session_key_rejection())
        
        return suite


def run_replay_tests() -> Dict[str, Any]:
    """Run all replay tests and return results."""
    tests = ReplayTests()
    suite = tests.run_all_tests()
    return suite.to_dict()


def print_test_results(results: Dict[str, Any]) -> None:
    """Print test results in a formatted way."""
    print(f"\n{'='*70}")
    print(f"  {results['suite_name']}")
    print(f"  Summary: {results['summary']['passed']}/{results['summary']['total']} passed")
    print(f"{'='*70}\n")
    
    for r in results['results']:
        status_icon = "✅" if r['status'] == 'passed' else "⚠️" if r['status'] == 'warning' else "❌"
        print(f"{status_icon} {r['test_name']}")
        print(f"   {r['description']}")
        if r.get('details'):
            for key, value in r['details'].items():
                print(f"   {key}: {value}")
        print()


if __name__ == "__main__":
    print("Running Replay Attack Resistance Tests...")
    print("This may take a moment.\n")
    
    results = run_replay_tests()
    print_test_results(results)
