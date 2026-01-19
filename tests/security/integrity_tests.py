# Data Integrity Tests
# اختبارات سلامة البيانات

"""
Security tests for data integrity verification.
اختبارات أمان سلامة البيانات

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
- Verify detection of single-bit modifications in ciphertext
- Verify detection of modifications at different positions
- Verify detection of truncated ciphertexts
- Verify detection of extended ciphertexts
- Verify that AAD modifications are detected
"""

import os
from typing import Dict, Any, List

from tests.security.base import SecurityTestResult, SecuritySuite, TestStatus
from messenger.crypto.crypto_utils import (
    aead_encrypt_xchacha20poly1305,
    aead_decrypt_xchacha20poly1305,
)


class IntegrityTests:
    """
    Tests for data integrity verification.
    اختبارات سلامة البيانات
    """
    
    def __init__(self, iterations: int = 100):
        """
        Initialize integrity tests.
        
        Args:
            iterations: Number of test iterations
        """
        self.iterations = iterations
        self.key = os.urandom(32)
    
    def _flip_bit(self, data: bytes, position: int, bit: int = 0) -> bytes:
        """Flip a specific bit in the data."""
        data = bytearray(data)
        data[position] ^= (1 << bit)
        return bytes(data)
    
    def test_single_bit_modification(self) -> SecurityTestResult:
        """
        Test detection of single-bit modifications.
        اختبار كشف تعديل بت واحد
        """
        detected = 0
        not_detected = 0
        
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
            
            # Flip a random bit in the ciphertext (not in nonce)
            position = 24 + (os.urandom(1)[0] % (len(ciphertext) - 24))
            bit = os.urandom(1)[0] % 8
            modified = self._flip_bit(ciphertext, position, bit)
            
            try:
                aead_decrypt_xchacha20poly1305(modified, key=self.key)
                not_detected += 1
            except:
                detected += 1
        
        details = {
            "iterations": self.iterations,
            "modifications_detected": detected,
            "modifications_not_detected": not_detected,
            "detection_rate": f"{(detected/self.iterations)*100:.1f}%",
        }
        
        if not_detected == 0:
            return SecurityTestResult(
                test_name="Single-Bit Modification Detection",
                category="integrity",
                status=TestStatus.PASSED,
                description="All single-bit modifications were detected",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Single-Bit Modification Detection",
                category="integrity",
                status=TestStatus.FAILED,
                description=f"{not_detected} modifications were not detected",
                details=details,
                recommendation="CRITICAL: Authentication mechanism may be broken"
            )
    
    def test_modification_positions(self) -> SecurityTestResult:
        """
        Test detection of modifications at different positions.
        اختبار كشف التعديل في مواقع مختلفة
        """
        positions_tested = {
            "start": [],
            "middle": [],
            "end": [],
        }
        
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
            ct_len = len(ciphertext)
            
            # Test start (after nonce)
            modified_start = self._flip_bit(ciphertext, 24)
            try:
                aead_decrypt_xchacha20poly1305(modified_start, key=self.key)
                positions_tested["start"].append(False)
            except:
                positions_tested["start"].append(True)
            
            # Test middle
            mid_pos = 24 + (ct_len - 24) // 2
            modified_middle = self._flip_bit(ciphertext, mid_pos)
            try:
                aead_decrypt_xchacha20poly1305(modified_middle, key=self.key)
                positions_tested["middle"].append(False)
            except:
                positions_tested["middle"].append(True)
            
            # Test end (tag area)
            modified_end = self._flip_bit(ciphertext, ct_len - 1)
            try:
                aead_decrypt_xchacha20poly1305(modified_end, key=self.key)
                positions_tested["end"].append(False)
            except:
                positions_tested["end"].append(True)
        
        detection_rates = {
            pos: sum(results) / len(results) * 100
            for pos, results in positions_tested.items()
        }
        
        all_detected = all(rate == 100 for rate in detection_rates.values())
        
        details = {
            "iterations": self.iterations,
            "detection_rates": {k: f"{v:.1f}%" for k, v in detection_rates.items()},
        }
        
        if all_detected:
            return SecurityTestResult(
                test_name="Modification Position Detection",
                category="integrity",
                status=TestStatus.PASSED,
                description="Modifications detected at all positions (start, middle, end)",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Modification Position Detection",
                category="integrity",
                status=TestStatus.FAILED,
                description="Some modifications were not detected",
                details=details,
                recommendation="Review authentication implementation"
            )
    
    def test_truncation_detection(self) -> SecurityTestResult:
        """
        Test detection of truncated ciphertexts.
        اختبار كشف القطع
        """
        detected = 0
        not_detected = 0
        
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
            
            # Truncate by removing last 1-16 bytes
            truncate_amount = 1 + (os.urandom(1)[0] % 16)
            truncated = ciphertext[:-truncate_amount]
            
            try:
                aead_decrypt_xchacha20poly1305(truncated, key=self.key)
                not_detected += 1
            except:
                detected += 1
        
        details = {
            "iterations": self.iterations,
            "truncations_detected": detected,
            "truncations_not_detected": not_detected,
        }
        
        if not_detected == 0:
            return SecurityTestResult(
                test_name="Truncation Detection",
                category="integrity",
                status=TestStatus.PASSED,
                description="All truncated ciphertexts were rejected",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Truncation Detection",
                category="integrity",
                status=TestStatus.FAILED,
                description=f"{not_detected} truncated ciphertexts were accepted",
                details=details,
                recommendation="CRITICAL: Truncation attack possible"
            )
    
    def test_extension_detection(self) -> SecurityTestResult:
        """
        Test detection of extended ciphertexts.
        اختبار كشف التمديد
        """
        detected = 0
        not_detected = 0
        
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
            
            # Extend by adding random bytes
            extension = os.urandom(1 + (os.urandom(1)[0] % 16))
            extended = ciphertext + extension
            
            try:
                aead_decrypt_xchacha20poly1305(extended, key=self.key)
                not_detected += 1
            except:
                detected += 1
        
        details = {
            "iterations": self.iterations,
            "extensions_detected": detected,
            "extensions_not_detected": not_detected,
        }
        
        if not_detected == 0:
            return SecurityTestResult(
                test_name="Extension Detection",
                category="integrity",
                status=TestStatus.PASSED,
                description="All extended ciphertexts were rejected",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Extension Detection",
                category="integrity",
                status=TestStatus.FAILED,
                description=f"{not_detected} extended ciphertexts were accepted",
                details=details,
                recommendation="CRITICAL: Extension attack possible"
            )
    
    def test_aad_modification(self) -> SecurityTestResult:
        """
        Test detection of AAD (Additional Authenticated Data) modifications.
        اختبار كشف تعديل AAD
        """
        detected = 0
        not_detected = 0
        
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            aad = os.urandom(32)
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key, aad=aad)
            
            # Modify AAD
            modified_aad = self._flip_bit(aad, os.urandom(1)[0] % len(aad))
            
            try:
                aead_decrypt_xchacha20poly1305(ciphertext, key=self.key, aad=modified_aad)
                not_detected += 1
            except:
                detected += 1
        
        details = {
            "iterations": self.iterations,
            "aad_modifications_detected": detected,
            "aad_modifications_not_detected": not_detected,
        }
        
        if not_detected == 0:
            return SecurityTestResult(
                test_name="AAD Modification Detection",
                category="integrity",
                status=TestStatus.PASSED,
                description="All AAD modifications were detected",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="AAD Modification Detection",
                category="integrity",
                status=TestStatus.FAILED,
                description=f"{not_detected} AAD modifications were not detected",
                details=details,
                recommendation="CRITICAL: AAD authentication may be broken"
            )
    
    def test_wrong_key_rejection(self) -> SecurityTestResult:
        """
        Test that wrong keys are always rejected.
        اختبار رفض المفاتيح الخاطئة
        """
        detected = 0
        not_detected = 0
        
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
            
            # Try with wrong key
            wrong_key = os.urandom(32)
            
            try:
                aead_decrypt_xchacha20poly1305(ciphertext, key=wrong_key)
                not_detected += 1
            except:
                detected += 1
        
        details = {
            "iterations": self.iterations,
            "wrong_keys_rejected": detected,
            "wrong_keys_accepted": not_detected,
        }
        
        if not_detected == 0:
            return SecurityTestResult(
                test_name="Wrong Key Rejection",
                category="integrity",
                status=TestStatus.PASSED,
                description="All wrong keys were rejected",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Wrong Key Rejection",
                category="integrity",
                status=TestStatus.FAILED,
                description=f"{not_detected} wrong keys were accepted (CRITICAL!)",
                details=details,
                recommendation="CRITICAL: Key verification is broken"
            )
    
    def run_all_tests(self) -> SecuritySuite:
        """
        Run all integrity tests.
        تشغيل جميع اختبارات السلامة
        """
        suite = SecuritySuite(suite_name="Data Integrity")
        
        suite.add_result(self.test_single_bit_modification())
        suite.add_result(self.test_modification_positions())
        suite.add_result(self.test_truncation_detection())
        suite.add_result(self.test_extension_detection())
        suite.add_result(self.test_aad_modification())
        suite.add_result(self.test_wrong_key_rejection())
        
        return suite


def run_integrity_tests(iterations: int = 100) -> Dict[str, Any]:
    """Run all integrity tests and return results."""
    tests = IntegrityTests(iterations=iterations)
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
                if isinstance(value, dict):
                    print(f"   {key}:")
                    for k, v in value.items():
                        print(f"      {k}: {v}")
                else:
                    print(f"   {key}: {value}")
        print()


if __name__ == "__main__":
    print("Running Data Integrity Tests...")
    print("This may take a moment.\n")
    
    results = run_integrity_tests(iterations=100)
    print_test_results(results)
