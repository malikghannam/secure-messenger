# Crypto Benchmarks - XChaCha20-Poly1305 Performance Tests
# اختبارات أداء التشفير المتماثل

"""
Benchmark XChaCha20-Poly1305 encryption and decryption performance.
قياس أداء تشفير وفك تشفير XChaCha20-Poly1305

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
- Measure encryption time for data sizes: 1KB, 10KB, 100KB, 1MB, 10MB
- Measure decryption time for the same data sizes
- Run each test at least 100 iterations
- Calculate average, min, max, and standard deviation
- Calculate throughput in MB/s
- Output results in structured format
"""

import os
from typing import List, Dict, Any

from tests.benchmarks.base import Benchmarker, BenchmarkResult, PerformanceSuite
from messenger.crypto.crypto_utils import (
    aead_encrypt_xchacha20poly1305,
    aead_decrypt_xchacha20poly1305
)


# Data sizes to benchmark (in bytes)
# أحجام البيانات للاختبار
DATA_SIZES = {
    "1KB": 1 * 1024,
    "10KB": 10 * 1024,
    "100KB": 100 * 1024,
    "1MB": 1 * 1024 * 1024,
    "10MB": 10 * 1024 * 1024,
}


class CryptoBenchmarks:
    """
    Benchmarks for XChaCha20-Poly1305 symmetric encryption.
    اختبارات أداء التشفير المتماثل XChaCha20-Poly1305
    """
    
    def __init__(self, iterations: int = 100):
        """
        Initialize crypto benchmarks.
        
        Args:
            iterations: Number of iterations per benchmark (default: 100)
        """
        self.benchmarker = Benchmarker(iterations=iterations)
        self.key = os.urandom(32)  # 256-bit key
    
    def _generate_test_data(self, size: int) -> bytes:
        """Generate random test data of specified size."""
        return os.urandom(size)
    
    def benchmark_encryption(self, data_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark encryption for a specific data size.
        قياس أداء التشفير لحجم بيانات محدد
        
        Args:
            data_size: Size of data in bytes
            size_name: Human-readable size name (e.g., "1KB")
            
        Returns:
            BenchmarkResult with encryption timing statistics
        """
        plaintext = self._generate_test_data(data_size)
        
        return self.benchmarker.benchmark(
            func=aead_encrypt_xchacha20poly1305,
            data_size=data_size,
            operation_name=f"XChaCha20-Poly1305 Encrypt ({size_name})",
            plaintext=plaintext,
            key=self.key
        )
    
    def benchmark_decryption(self, data_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark decryption for a specific data size.
        قياس أداء فك التشفير لحجم بيانات محدد
        
        Args:
            data_size: Size of original plaintext in bytes
            size_name: Human-readable size name (e.g., "1KB")
            
        Returns:
            BenchmarkResult with decryption timing statistics
        """
        # Pre-encrypt data for decryption benchmark
        plaintext = self._generate_test_data(data_size)
        ciphertext = aead_encrypt_xchacha20poly1305(plaintext, key=self.key)
        
        return self.benchmarker.benchmark(
            func=aead_decrypt_xchacha20poly1305,
            data_size=data_size,
            operation_name=f"XChaCha20-Poly1305 Decrypt ({size_name})",
            blob=ciphertext,
            key=self.key
        )
    
    def run_all_benchmarks(self) -> PerformanceSuite:
        """
        Run all encryption and decryption benchmarks.
        تشغيل جميع اختبارات التشفير وفك التشفير
        
        Returns:
            PerformanceSuite containing all benchmark results
        """
        suite = PerformanceSuite(suite_name="XChaCha20-Poly1305 Symmetric Encryption")
        
        for size_name, data_size in DATA_SIZES.items():
            # Benchmark encryption
            enc_result = self.benchmark_encryption(data_size, size_name)
            suite.add_result(enc_result)
            
            # Benchmark decryption
            dec_result = self.benchmark_decryption(data_size, size_name)
            suite.add_result(dec_result)
        
        return suite
    
    def run_encryption_benchmarks(self) -> List[BenchmarkResult]:
        """
        Run only encryption benchmarks.
        تشغيل اختبارات التشفير فقط
        
        Returns:
            List of BenchmarkResult for encryption operations
        """
        results = []
        for size_name, data_size in DATA_SIZES.items():
            result = self.benchmark_encryption(data_size, size_name)
            results.append(result)
        return results
    
    def run_decryption_benchmarks(self) -> List[BenchmarkResult]:
        """
        Run only decryption benchmarks.
        تشغيل اختبارات فك التشفير فقط
        
        Returns:
            List of BenchmarkResult for decryption operations
        """
        results = []
        for size_name, data_size in DATA_SIZES.items():
            result = self.benchmark_decryption(data_size, size_name)
            results.append(result)
        return results


def run_crypto_benchmarks(iterations: int = 100) -> Dict[str, Any]:
    """
    Run all crypto benchmarks and return results.
    تشغيل جميع اختبارات التشفير وإرجاع النتائج
    
    Args:
        iterations: Number of iterations per benchmark
        
    Returns:
        Dictionary with benchmark results in structured format
    """
    benchmarks = CryptoBenchmarks(iterations=iterations)
    suite = benchmarks.run_all_benchmarks()
    return suite.to_dict()


def print_benchmark_results(results: Dict[str, Any]) -> None:
    """
    Print benchmark results in a formatted table.
    طباعة نتائج الاختبارات في جدول منسق
    """
    print(f"\n{'='*80}")
    print(f"  {results['suite_name']}")
    print(f"  Total Benchmarks: {results['total_benchmarks']}")
    print(f"{'='*80}\n")
    
    # Print header
    header = f"{'Operation':<45} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Throughput':<15}"
    print(header)
    print("-" * len(header))
    
    # Print results
    for r in results['results']:
        print(f"{r['operation']:<45} {r['avg_ms']:<12.3f} {r['min_ms']:<12.3f} {r['max_ms']:<12.3f} {r['throughput_mbps']:<12.2f} MB/s")
    
    print()


if __name__ == "__main__":
    # Run benchmarks when executed directly
    print("Running XChaCha20-Poly1305 Benchmarks...")
    print("This may take a few minutes for larger data sizes.\n")
    
    results = run_crypto_benchmarks(iterations=100)
    print_benchmark_results(results)
