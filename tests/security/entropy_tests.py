# Entropy and Randomness Tests
# اختبارات العشوائية والإنتروبيا

"""
Security tests for key randomness and entropy.
اختبارات أمان عشوائية المفاتيح

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
- Verify generated keys have high entropy
- Generate 10000 keys and verify uniqueness
- Verify uniform byte distribution (chi-square test)
- Verify no detectable patterns in key sequences
- Verify nonces are never repeated across 100000 encryptions
"""

import os
import math
from collections import Counter
from typing import List, Dict, Any, Set

from tests.security.base import SecurityTestResult, SecuritySuite, TestStatus
from messenger.crypto.crypto_utils import aead_encrypt_xchacha20poly1305
from messenger.files.encryption import generate_file_key


# Chi-square critical value for 255 degrees of freedom at 95% confidence
CHI_SQUARE_CRITICAL_95 = 293.25


class EntropyTests:
    """
    Tests for key randomness and entropy.
    اختبارات عشوائية المفاتيح
    """
    
    def __init__(self):
        """Initialize entropy tests."""
        pass
    
    def _calculate_entropy(self, data: bytes) -> float:
        """
        Calculate Shannon entropy of data.
        حساب إنتروبيا شانون للبيانات
        
        Returns:
            Entropy in bits per byte (max 8.0 for perfectly random)
        """
        if not data:
            return 0.0
        
        byte_counts = Counter(data)
        total = len(data)
        
        entropy = 0.0
        for count in byte_counts.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _chi_square_test(self, data: bytes) -> Dict[str, float]:
        """
        Perform chi-square test for uniform distribution.
        اختبار كاي تربيع للتوزيع المنتظم
        """
        byte_counts = Counter(data)
        total = len(data)
        expected = total / 256  # Expected count for each byte value
        
        chi_square = 0.0
        for i in range(256):
            observed = byte_counts.get(i, 0)
            chi_square += ((observed - expected) ** 2) / expected
        
        # Degrees of freedom = 256 - 1 = 255
        p_value_approx = 1.0 if chi_square < CHI_SQUARE_CRITICAL_95 else 0.0
        
        return {
            "chi_square": chi_square,
            "critical_value": CHI_SQUARE_CRITICAL_95,
            "passed": chi_square < CHI_SQUARE_CRITICAL_95,
        }
    
    def _detect_patterns(self, keys: List[bytes]) -> Dict[str, Any]:
        """
        Detect patterns in key sequences.
        كشف الأنماط في تسلسل المفاتيح
        """
        patterns_found = []
        
        # Check for sequential bytes
        for i, key in enumerate(keys[:100]):  # Check first 100 keys
            for j in range(len(key) - 2):
                if key[j] + 1 == key[j+1] == key[j+2] - 1:
                    patterns_found.append(f"Sequential pattern in key {i}")
                    break
        
        # Check for repeated keys
        key_set = set(keys)
        duplicates = len(keys) - len(key_set)
        
        # Check for common prefixes
        prefix_counts = Counter(k[:4] for k in keys)
        max_prefix_count = max(prefix_counts.values())
        
        return {
            "sequential_patterns": len(patterns_found),
            "duplicate_keys": duplicates,
            "max_common_prefix": max_prefix_count,
            "patterns_detected": len(patterns_found) > 0 or duplicates > 0,
        }
    
    def test_key_uniqueness(self, num_keys: int = 10000) -> SecurityTestResult:
        """
        Test that all generated keys are unique.
        اختبار تفرد المفاتيح المولدة
        """
        keys = [generate_file_key() for _ in range(num_keys)]
        unique_keys = set(keys)
        
        duplicates = num_keys - len(unique_keys)
        
        details = {
            "keys_generated": num_keys,
            "unique_keys": len(unique_keys),
            "duplicates": duplicates,
        }
        
        if duplicates == 0:
            return SecurityTestResult(
                test_name="Key Uniqueness",
                category="entropy",
                status=TestStatus.PASSED,
                description=f"All {num_keys} generated keys are unique",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Key Uniqueness",
                category="entropy",
                status=TestStatus.FAILED,
                description=f"Found {duplicates} duplicate keys out of {num_keys}",
                details=details,
                recommendation="Review random number generator"
            )
    
    def test_key_entropy(self, num_keys: int = 1000) -> SecurityTestResult:
        """
        Test that generated keys have high entropy.
        اختبار أن المفاتيح المولدة لديها إنتروبيا عالية
        """
        keys = [generate_file_key() for _ in range(num_keys)]
        
        # Concatenate all keys for entropy calculation
        all_bytes = b''.join(keys)
        entropy = self._calculate_entropy(all_bytes)
        
        # Individual key entropy
        individual_entropies = [self._calculate_entropy(k) for k in keys[:100]]
        avg_individual_entropy = sum(individual_entropies) / len(individual_entropies)
        
        details = {
            "combined_entropy": round(entropy, 4),
            "avg_individual_entropy": round(avg_individual_entropy, 4),
            "max_possible_entropy": 8.0,
            "keys_analyzed": num_keys,
        }
        
        # Entropy should be close to 8 bits per byte for random data
        if entropy >= 7.9:
            return SecurityTestResult(
                test_name="Key Entropy",
                category="entropy",
                status=TestStatus.PASSED,
                description=f"Key entropy ({entropy:.4f} bits/byte) is excellent",
                details=details
            )
        elif entropy >= 7.5:
            return SecurityTestResult(
                test_name="Key Entropy",
                category="entropy",
                status=TestStatus.WARNING,
                description=f"Key entropy ({entropy:.4f} bits/byte) is acceptable but not optimal",
                details=details,
                recommendation="Consider reviewing entropy source"
            )
        else:
            return SecurityTestResult(
                test_name="Key Entropy",
                category="entropy",
                status=TestStatus.FAILED,
                description=f"Key entropy ({entropy:.4f} bits/byte) is too low",
                details=details,
                recommendation="Entropy source may be compromised"
            )
    
    def test_byte_distribution(self, num_keys: int = 1000) -> SecurityTestResult:
        """
        Test uniform byte distribution using chi-square test.
        اختبار التوزيع المنتظم للبايتات
        """
        keys = [generate_file_key() for _ in range(num_keys)]
        all_bytes = b''.join(keys)
        
        chi_result = self._chi_square_test(all_bytes)
        
        details = {
            "chi_square_statistic": round(chi_result["chi_square"], 2),
            "critical_value_95": chi_result["critical_value"],
            "total_bytes": len(all_bytes),
            "keys_analyzed": num_keys,
        }
        
        if chi_result["passed"]:
            return SecurityTestResult(
                test_name="Byte Distribution (Chi-Square)",
                category="entropy",
                status=TestStatus.PASSED,
                description="Byte distribution is uniform (chi-square test passed)",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Byte Distribution (Chi-Square)",
                category="entropy",
                status=TestStatus.FAILED,
                description="Byte distribution is not uniform",
                details=details,
                recommendation="Random number generator may be biased"
            )
    
    def test_no_patterns(self, num_keys: int = 10000) -> SecurityTestResult:
        """
        Test that no detectable patterns exist in key sequences.
        اختبار عدم وجود أنماط قابلة للكشف
        """
        keys = [generate_file_key() for _ in range(num_keys)]
        pattern_result = self._detect_patterns(keys)
        
        details = {
            "keys_analyzed": num_keys,
            "sequential_patterns": pattern_result["sequential_patterns"],
            "duplicate_keys": pattern_result["duplicate_keys"],
            "max_common_prefix_count": pattern_result["max_common_prefix"],
        }
        
        if not pattern_result["patterns_detected"]:
            return SecurityTestResult(
                test_name="Pattern Detection",
                category="entropy",
                status=TestStatus.PASSED,
                description="No detectable patterns in key sequences",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Pattern Detection",
                category="entropy",
                status=TestStatus.FAILED,
                description="Patterns detected in key sequences",
                details=details,
                recommendation="Review random number generator for predictability"
            )
    
    def test_nonce_uniqueness(self, num_encryptions: int = 100000) -> SecurityTestResult:
        """
        Test that nonces are never repeated across many encryptions.
        اختبار عدم تكرار nonces عبر تشفيرات متعددة
        """
        key = os.urandom(32)
        plaintext = b"test message"
        
        nonces: Set[bytes] = set()
        duplicates = 0
        
        for _ in range(num_encryptions):
            ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=key)
            # Extract nonce (first 24 bytes for XChaCha20)
            nonce = ciphertext[:24]
            
            if nonce in nonces:
                duplicates += 1
            else:
                nonces.add(nonce)
        
        details = {
            "encryptions_performed": num_encryptions,
            "unique_nonces": len(nonces),
            "duplicate_nonces": duplicates,
        }
        
        if duplicates == 0:
            return SecurityTestResult(
                test_name="Nonce Uniqueness",
                category="entropy",
                status=TestStatus.PASSED,
                description=f"All {num_encryptions} nonces are unique",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Nonce Uniqueness",
                category="entropy",
                status=TestStatus.FAILED,
                description=f"Found {duplicates} duplicate nonces (CRITICAL!)",
                details=details,
                recommendation="CRITICAL: Nonce reuse detected - this breaks encryption security!"
            )
    
    def run_all_tests(self) -> SecuritySuite:
        """
        Run all entropy tests.
        تشغيل جميع اختبارات العشوائية
        """
        suite = SecuritySuite(suite_name="Entropy and Randomness")
        
        suite.add_result(self.test_key_uniqueness(10000))
        suite.add_result(self.test_key_entropy(1000))
        suite.add_result(self.test_byte_distribution(1000))
        suite.add_result(self.test_no_patterns(10000))
        suite.add_result(self.test_nonce_uniqueness(100000))
        
        return suite


def run_entropy_tests() -> Dict[str, Any]:
    """Run all entropy tests and return results."""
    tests = EntropyTests()
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
    print("Running Entropy and Randomness Tests...")
    print("This may take a minute (testing 100,000 nonces).\n")
    
    results = run_entropy_tests()
    print_test_results(results)
