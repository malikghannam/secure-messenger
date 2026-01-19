# Timing Attack Resistance Tests
# اختبارات مقاومة هجمات التوقيت

"""
Security tests for timing attack resistance.
اختبارات أمان مقاومة هجمات التوقيت

Requirements: 5.1, 5.2, 5.4, 5.5
- Verify decryption time is constant regardless of ciphertext content
- Compare decryption time for valid vs invalid ciphertexts
- Use statistical analysis to detect timing variations
- Flag timing variation exceeding 5% as potential vulnerability
"""

import os
import time
import statistics
from typing import List, Dict, Any, Tuple

from tests.security.base import SecurityTest, SecurityTestResult, SecuritySuite, TestStatus
from messenger.crypto.crypto_utils import (
    aead_encrypt_xchacha20poly1305,
    aead_decrypt_xchacha20poly1305,
)


# Timing variance threshold (5%)
TIMING_VARIANCE_THRESHOLD = 0.05


class TimingTests:
    """
    Tests for timing attack resistance.
    اختبارات مقاومة هجمات التوقيت
    """
    
    def __init__(self, iterations: int = 1000):
        """
        Initialize timing tests.
        
        Args:
            iterations: Number of iterations for timing measurements
        """
        self.iterations = iterations
        self.key = os.urandom(32)
    
    def _measure_decryption_times(self, ciphertexts: List[bytes]) -> List[float]:
        """
        Measure decryption times for a list of ciphertexts.
        قياس أوقات فك التشفير
        """
        times = []
        for ct in ciphertexts:
            try:
                start = time.perf_counter()
                aead_decrypt_xchacha20poly1305(ct, key=self.key)
                end = time.perf_counter()
                times.append((end - start) * 1000000)  # microseconds
            except:
                # For invalid ciphertexts, still measure time
                end = time.perf_counter()
                times.append((end - start) * 1000000)
        return times
    
    def _calculate_timing_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate timing statistics."""
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
        }
    
    def _calculate_variance_ratio(self, times1: List[float], times2: List[float]) -> float:
        """
        Calculate the variance ratio between two timing distributions.
        حساب نسبة التباين بين توزيعين
        """
        mean1 = statistics.mean(times1)
        mean2 = statistics.mean(times2)
        
        if mean1 == 0 or mean2 == 0:
            return 0
        
        # Calculate relative difference
        diff = abs(mean1 - mean2)
        avg = (mean1 + mean2) / 2
        return diff / avg
    
    def test_valid_vs_invalid_ciphertext_timing(self) -> SecurityTestResult:
        """
        Test that decryption time is similar for valid and invalid ciphertexts.
        اختبار أن وقت فك التشفير متشابه للنصوص الصالحة وغير الصالحة
        """
        # Generate valid ciphertexts
        valid_ciphertexts = []
        for _ in range(self.iterations):
            plaintext = os.urandom(100)
            ct = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
            valid_ciphertexts.append(ct)
        
        # Generate invalid ciphertexts (tampered)
        invalid_ciphertexts = []
        for ct in valid_ciphertexts:
            # Flip a bit in the middle of the ciphertext
            tampered = bytearray(ct)
            tampered[len(tampered) // 2] ^= 0x01
            invalid_ciphertexts.append(bytes(tampered))
        
        # Measure times
        valid_times = self._measure_decryption_times(valid_ciphertexts)
        invalid_times = self._measure_decryption_times(invalid_ciphertexts)
        
        # Calculate statistics
        valid_stats = self._calculate_timing_stats(valid_times)
        invalid_stats = self._calculate_timing_stats(invalid_times)
        variance_ratio = self._calculate_variance_ratio(valid_times, invalid_times)
        
        details = {
            "valid_ciphertext_stats": valid_stats,
            "invalid_ciphertext_stats": invalid_stats,
            "variance_ratio": round(variance_ratio, 4),
            "threshold": TIMING_VARIANCE_THRESHOLD,
            "iterations": self.iterations,
        }
        
        if variance_ratio <= TIMING_VARIANCE_THRESHOLD:
            return SecurityTestResult(
                test_name="Valid vs Invalid Ciphertext Timing",
                category="timing",
                status=TestStatus.PASSED,
                description=f"Timing variance ({variance_ratio:.2%}) is within acceptable threshold ({TIMING_VARIANCE_THRESHOLD:.0%})",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Valid vs Invalid Ciphertext Timing",
                category="timing",
                status=TestStatus.WARNING,
                description=f"Timing variance ({variance_ratio:.2%}) exceeds threshold ({TIMING_VARIANCE_THRESHOLD:.0%})",
                details=details,
                recommendation="Review decryption implementation for timing leaks"
            )
    
    def test_ciphertext_length_timing(self) -> SecurityTestResult:
        """
        Test that decryption time scales linearly with ciphertext length.
        اختبار أن وقت فك التشفير يتناسب خطياً مع طول النص المشفر
        """
        sizes = [100, 1000, 10000]
        timing_per_byte = []
        
        for size in sizes:
            ciphertexts = []
            for _ in range(100):
                plaintext = os.urandom(size)
                ct = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
                ciphertexts.append(ct)
            
            times = self._measure_decryption_times(ciphertexts)
            avg_time = statistics.mean(times)
            timing_per_byte.append(avg_time / size)
        
        # Check if timing per byte is consistent
        variance = statistics.stdev(timing_per_byte) / statistics.mean(timing_per_byte)
        
        details = {
            "sizes_tested": sizes,
            "timing_per_byte": [round(t, 6) for t in timing_per_byte],
            "variance": round(variance, 4),
        }
        
        if variance <= 0.5:  # Allow 50% variance for different sizes
            return SecurityTestResult(
                test_name="Ciphertext Length Timing",
                category="timing",
                status=TestStatus.PASSED,
                description="Decryption time scales linearly with ciphertext length",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Ciphertext Length Timing",
                category="timing",
                status=TestStatus.WARNING,
                description="Non-linear timing detected for different ciphertext lengths",
                details=details,
                recommendation="Investigate timing behavior for different input sizes"
            )
    
    def test_key_comparison_timing(self) -> SecurityTestResult:
        """
        Test that key comparison is constant-time.
        اختبار أن مقارنة المفاتيح ثابتة الوقت
        """
        plaintext = os.urandom(100)
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
        
        # Test with correct key
        correct_key_times = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            try:
                aead_decrypt_xchacha20poly1305(ciphertext, key=self.key)
            except:
                pass
            end = time.perf_counter()
            correct_key_times.append((end - start) * 1000000)
        
        # Test with wrong keys (different first bytes)
        wrong_key_times = []
        for _ in range(self.iterations):
            wrong_key = os.urandom(32)
            start = time.perf_counter()
            try:
                aead_decrypt_xchacha20poly1305(ciphertext, key=wrong_key)
            except:
                pass
            end = time.perf_counter()
            wrong_key_times.append((end - start) * 1000000)
        
        variance_ratio = self._calculate_variance_ratio(correct_key_times, wrong_key_times)
        
        details = {
            "correct_key_mean_us": round(statistics.mean(correct_key_times), 3),
            "wrong_key_mean_us": round(statistics.mean(wrong_key_times), 3),
            "variance_ratio": round(variance_ratio, 4),
        }
        
        if variance_ratio <= TIMING_VARIANCE_THRESHOLD:
            return SecurityTestResult(
                test_name="Key Comparison Timing",
                category="timing",
                status=TestStatus.PASSED,
                description="Key comparison appears to be constant-time",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Key Comparison Timing",
                category="timing",
                status=TestStatus.WARNING,
                description=f"Timing variance ({variance_ratio:.2%}) detected in key comparison",
                details=details,
                recommendation="Ensure constant-time key comparison"
            )
    
    def test_padding_oracle_resistance(self) -> SecurityTestResult:
        """
        Test resistance to padding oracle attacks.
        اختبار مقاومة هجمات Padding Oracle
        
        Note: XChaCha20-Poly1305 doesn't use padding, but we verify
        that authentication failures don't leak timing information.
        """
        plaintext = os.urandom(100)
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
        
        # Create ciphertexts with different types of corruption
        corruptions = {
            "tag_corruption": self._corrupt_tag(ciphertext),
            "nonce_corruption": self._corrupt_nonce(ciphertext),
            "data_corruption": self._corrupt_data(ciphertext),
        }
        
        timing_results = {}
        for corruption_type, corrupted_ct in corruptions.items():
            times = []
            for _ in range(500):
                start = time.perf_counter()
                try:
                    aead_decrypt_xchacha20poly1305(corrupted_ct, key=self.key)
                except:
                    pass
                end = time.perf_counter()
                times.append((end - start) * 1000000)
            timing_results[corruption_type] = statistics.mean(times)
        
        # Check if all corruption types have similar timing
        times_list = list(timing_results.values())
        max_variance = max(times_list) / min(times_list) - 1 if min(times_list) > 0 else 0
        
        details = {
            "timing_by_corruption_type": {k: round(v, 3) for k, v in timing_results.items()},
            "max_variance": round(max_variance, 4),
        }
        
        if max_variance <= TIMING_VARIANCE_THRESHOLD:
            return SecurityTestResult(
                test_name="Padding Oracle Resistance",
                category="timing",
                status=TestStatus.PASSED,
                description="No timing differences detected for different corruption types",
                details=details
            )
        else:
            return SecurityTestResult(
                test_name="Padding Oracle Resistance",
                category="timing",
                status=TestStatus.WARNING,
                description="Timing differences detected for different corruption types",
                details=details,
                recommendation="Review authentication failure handling"
            )
    
    def _corrupt_tag(self, ciphertext: bytes) -> bytes:
        """Corrupt the authentication tag (last 16 bytes)."""
        ct = bytearray(ciphertext)
        ct[-1] ^= 0x01
        return bytes(ct)
    
    def _corrupt_nonce(self, ciphertext: bytes) -> bytes:
        """Corrupt the nonce (first 24 bytes)."""
        ct = bytearray(ciphertext)
        ct[0] ^= 0x01
        return bytes(ct)
    
    def _corrupt_data(self, ciphertext: bytes) -> bytes:
        """Corrupt the encrypted data (middle)."""
        ct = bytearray(ciphertext)
        mid = len(ct) // 2
        ct[mid] ^= 0x01
        return bytes(ct)
    
    def run_all_tests(self) -> SecuritySuite:
        """
        Run all timing attack tests.
        تشغيل جميع اختبارات هجمات التوقيت
        """
        suite = SecuritySuite(suite_name="Timing Attack Resistance")
        
        suite.add_result(self.test_valid_vs_invalid_ciphertext_timing())
        suite.add_result(self.test_ciphertext_length_timing())
        suite.add_result(self.test_key_comparison_timing())
        suite.add_result(self.test_padding_oracle_resistance())
        
        return suite


def run_timing_tests(iterations: int = 1000) -> Dict[str, Any]:
    """Run all timing tests and return results."""
    tests = TimingTests(iterations=iterations)
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
    print("Running Timing Attack Resistance Tests...")
    print("This may take a minute.\n")
    
    results = run_timing_tests(iterations=1000)
    print_test_results(results)
