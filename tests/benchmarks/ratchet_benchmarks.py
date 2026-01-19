# Double Ratchet Benchmarks - Message Encryption Performance Tests
# اختبارات أداء خوارزمية Double Ratchet

"""
Benchmark Double Ratchet message encryption and decryption performance.
قياس أداء تشفير وفك تشفير الرسائل بخوارزمية Double Ratchet

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
- Measure time for first message encryption after session setup
- Measure time for subsequent messages (same direction)
- Measure time for messages with DH ratchet step (direction change)
- Test with message sizes: 100 bytes, 1KB, 10KB
- Calculate messages per second throughput
"""

import os
from typing import Dict, Any, List, Tuple

from cryptography.hazmat.primitives.asymmetric import x25519

from tests.benchmarks.base import Benchmarker, BenchmarkResult, PerformanceSuite
from messenger.crypto.ratchet import DoubleRatchet
from messenger.crypto.pqx3dh import pqx3dh_initiate, pqx3dh_respond, build_initiator_ratchet, build_responder_ratchet
from messenger.pq_backend.backend import OQSKyberBackend


# Message sizes to benchmark
MESSAGE_SIZES = {
    "100B": 100,
    "1KB": 1024,
    "10KB": 10 * 1024,
}


class RatchetBenchmarks:
    """
    Benchmarks for Double Ratchet message encryption.
    اختبارات أداء تشفير الرسائل بـ Double Ratchet
    """
    
    def __init__(self, iterations: int = 100):
        """
        Initialize ratchet benchmarks.
        
        Args:
            iterations: Number of iterations per benchmark (default: 100)
        """
        self.benchmarker = Benchmarker(iterations=iterations)
        self.kyber_backend = OQSKyberBackend()
    
    def _create_session_pair(self) -> Tuple[DoubleRatchet, DoubleRatchet]:
        """
        Create a pair of Double Ratchet sessions using PQ-X3DH.
        إنشاء زوج من جلسات Double Ratchet باستخدام PQ-X3DH
        """
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
    
    def _generate_message(self, size: int) -> bytes:
        """Generate random message of specified size."""
        return os.urandom(size)
    
    # ==================
    # First Message Benchmarks
    # ==================
    
    def benchmark_first_message_encrypt(self, msg_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark first message encryption after session setup.
        قياس أداء تشفير الرسالة الأولى بعد إعداد الجلسة
        """
        message = self._generate_message(msg_size)
        
        def encrypt_first():
            alice, bob = self._create_session_pair()
            return alice.encrypt(message)
        
        return self.benchmarker.benchmark(
            func=encrypt_first,
            data_size=msg_size,
            operation_name=f"First Message Encrypt ({size_name})"
        )
    
    def benchmark_first_message_decrypt(self, msg_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark first message decryption.
        قياس أداء فك تشفير الرسالة الأولى
        """
        message = self._generate_message(msg_size)
        
        # Pre-create session and encrypt message
        alice, bob = self._create_session_pair()
        encrypted = alice.encrypt(message)
        
        def decrypt_first():
            # Create fresh bob ratchet for each iteration
            _, fresh_bob = self._create_session_pair()
            # Use the same encrypted message structure
            return fresh_bob.decrypt(encrypted)
        
        # For decryption, we need to measure with pre-encrypted data
        # but fresh ratchet state each time
        times = []
        import time
        for _ in range(self.benchmarker.iterations):
            alice, bob = self._create_session_pair()
            enc = alice.encrypt(message)
            start = time.perf_counter()
            bob.decrypt(enc)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        return BenchmarkResult(
            operation_name=f"First Message Decrypt ({size_name})",
            data_size_bytes=msg_size,
            iterations=self.benchmarker.iterations,
            times_ms=times
        )
    
    # ==================
    # Subsequent Message Benchmarks (Same Direction)
    # ==================
    
    def benchmark_subsequent_message_encrypt(self, msg_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark subsequent message encryption (same direction, no DH ratchet).
        قياس أداء تشفير الرسائل المتتالية (نفس الاتجاه)
        """
        message = self._generate_message(msg_size)
        alice, bob = self._create_session_pair()
        
        # Send first message to initialize
        alice.encrypt(message)
        
        return self.benchmarker.benchmark(
            func=alice.encrypt,
            data_size=msg_size,
            operation_name=f"Subsequent Message Encrypt ({size_name})",
            plaintext=message
        )
    
    def benchmark_subsequent_message_decrypt(self, msg_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark subsequent message decryption (same direction).
        قياس أداء فك تشفير الرسائل المتتالية
        """
        message = self._generate_message(msg_size)
        alice, bob = self._create_session_pair()
        
        # Send and receive first message
        enc1 = alice.encrypt(message)
        bob.decrypt(enc1)
        
        # Pre-encrypt messages for decryption benchmark
        encrypted_messages = [alice.encrypt(message) for _ in range(self.benchmarker.iterations)]
        
        times = []
        import time
        for enc in encrypted_messages:
            start = time.perf_counter()
            bob.decrypt(enc)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        return BenchmarkResult(
            operation_name=f"Subsequent Message Decrypt ({size_name})",
            data_size_bytes=msg_size,
            iterations=self.benchmarker.iterations,
            times_ms=times
        )
    
    # ==================
    # DH Ratchet Step Benchmarks (Direction Change)
    # ==================
    
    def benchmark_dh_ratchet_encrypt(self, msg_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark message encryption with DH ratchet step (direction change).
        قياس أداء التشفير مع خطوة DH ratchet (تغيير الاتجاه)
        """
        message = self._generate_message(msg_size)
        
        times = []
        import time
        for _ in range(self.benchmarker.iterations):
            alice, bob = self._create_session_pair()
            
            # Alice sends first
            enc1 = alice.encrypt(message)
            bob.decrypt(enc1)
            
            # Bob replies (triggers DH ratchet)
            start = time.perf_counter()
            bob.encrypt(message)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        return BenchmarkResult(
            operation_name=f"DH Ratchet Encrypt ({size_name})",
            data_size_bytes=msg_size,
            iterations=self.benchmarker.iterations,
            times_ms=times
        )
    
    def benchmark_dh_ratchet_decrypt(self, msg_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark message decryption with DH ratchet step.
        قياس أداء فك التشفير مع خطوة DH ratchet
        """
        message = self._generate_message(msg_size)
        
        times = []
        import time
        for _ in range(self.benchmarker.iterations):
            alice, bob = self._create_session_pair()
            
            # Alice sends first
            enc1 = alice.encrypt(message)
            bob.decrypt(enc1)
            
            # Bob replies
            enc2 = bob.encrypt(message)
            
            # Alice decrypts (triggers DH ratchet on her side)
            start = time.perf_counter()
            alice.decrypt(enc2)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        return BenchmarkResult(
            operation_name=f"DH Ratchet Decrypt ({size_name})",
            data_size_bytes=msg_size,
            iterations=self.benchmarker.iterations,
            times_ms=times
        )
    
    # ==================
    # Throughput Benchmark
    # ==================
    
    def benchmark_message_throughput(self) -> BenchmarkResult:
        """
        Benchmark messages per second throughput.
        قياس عدد الرسائل في الثانية
        """
        message = self._generate_message(100)  # Small message for throughput test
        alice, bob = self._create_session_pair()
        
        # Warm up
        enc = alice.encrypt(message)
        bob.decrypt(enc)
        
        import time
        start = time.perf_counter()
        for _ in range(1000):
            enc = alice.encrypt(message)
        end = time.perf_counter()
        
        total_time_ms = (end - start) * 1000
        msgs_per_sec = 1000 / (total_time_ms / 1000)
        
        return BenchmarkResult(
            operation_name="Message Throughput (1000 msgs)",
            data_size_bytes=100 * 1000,
            iterations=1,
            times_ms=[total_time_ms]
        )
    
    # ==================
    # Run All Benchmarks
    # ==================
    
    def run_all_benchmarks(self) -> PerformanceSuite:
        """
        Run all Double Ratchet benchmarks.
        تشغيل جميع اختبارات Double Ratchet
        """
        suite = PerformanceSuite(suite_name="Double Ratchet Message Encryption")
        
        for size_name, msg_size in MESSAGE_SIZES.items():
            # First message benchmarks
            suite.add_result(self.benchmark_first_message_encrypt(msg_size, size_name))
            suite.add_result(self.benchmark_first_message_decrypt(msg_size, size_name))
            
            # Subsequent message benchmarks
            suite.add_result(self.benchmark_subsequent_message_encrypt(msg_size, size_name))
            suite.add_result(self.benchmark_subsequent_message_decrypt(msg_size, size_name))
            
            # DH ratchet step benchmarks
            suite.add_result(self.benchmark_dh_ratchet_encrypt(msg_size, size_name))
            suite.add_result(self.benchmark_dh_ratchet_decrypt(msg_size, size_name))
        
        # Throughput benchmark
        suite.add_result(self.benchmark_message_throughput())
        
        return suite


def run_ratchet_benchmarks(iterations: int = 100) -> Dict[str, Any]:
    """
    Run all Double Ratchet benchmarks and return results.
    تشغيل جميع اختبارات Double Ratchet وإرجاع النتائج
    """
    benchmarks = RatchetBenchmarks(iterations=iterations)
    suite = benchmarks.run_all_benchmarks()
    return suite.to_dict()


def print_benchmark_results(results: Dict[str, Any]) -> None:
    """Print benchmark results in a formatted table."""
    print(f"\n{'='*90}")
    print(f"  {results['suite_name']}")
    print(f"  Total Benchmarks: {results['total_benchmarks']}")
    print(f"{'='*90}\n")
    
    header = f"{'Operation':<45} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Throughput':<15}"
    print(header)
    print("-" * len(header))
    
    for r in results['results']:
        throughput = f"{r['throughput_mbps']:.2f} MB/s" if r['throughput_mbps'] > 0 else "N/A"
        print(f"{r['operation']:<45} {r['avg_ms']:<12.3f} {r['min_ms']:<12.3f} {r['max_ms']:<12.3f} {throughput:<15}")
    
    print()


if __name__ == "__main__":
    print("Running Double Ratchet Benchmarks...")
    print("This may take a few minutes.\n")
    
    results = run_ratchet_benchmarks(iterations=50)
    print_benchmark_results(results)
