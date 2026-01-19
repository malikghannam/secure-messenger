# Key Exchange Benchmarks - PQ-X3DH, Kyber512, X25519 Performance Tests
# اختبارات أداء تبادل المفاتيح

"""
Benchmark key exchange operations including PQ-X3DH, Kyber512, and X25519.
قياس أداء عمليات تبادل المفاتيح

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
- Measure time for complete PQ-X3DH handshake
- Separately measure: key generation, initiation, response times
- Measure Kyber512: keypair generation, encapsulation, decapsulation
- Measure X25519: keypair generation, key exchange
- Run at least 50 iterations for each operation
"""

import os
from typing import Dict, Any, List

from cryptography.hazmat.primitives.asymmetric import x25519
import oqs

from tests.benchmarks.base import Benchmarker, BenchmarkResult, PerformanceSuite
from messenger.crypto.pqx3dh import pqx3dh_initiate, pqx3dh_respond
from messenger.pq_backend.backend import OQSKyberBackend


class KeyExchangeBenchmarks:
    """
    Benchmarks for key exchange operations.
    اختبارات أداء تبادل المفاتيح
    """
    
    def __init__(self, iterations: int = 50):
        """
        Initialize key exchange benchmarks.
        
        Args:
            iterations: Number of iterations per benchmark (default: 50)
        """
        self.benchmarker = Benchmarker(iterations=iterations)
        self.kyber_backend = OQSKyberBackend()
    
    # ==================
    # X25519 Benchmarks
    # ==================
    
    def benchmark_x25519_keypair(self) -> BenchmarkResult:
        """
        Benchmark X25519 keypair generation.
        قياس أداء توليد مفاتيح X25519
        """
        return self.benchmarker.benchmark(
            func=x25519.X25519PrivateKey.generate,
            data_size=32,  # X25519 key size
            operation_name="X25519 Keypair Generation"
        )
    
    def benchmark_x25519_exchange(self) -> BenchmarkResult:
        """
        Benchmark X25519 key exchange (DH).
        قياس أداء تبادل مفاتيح X25519
        """
        # Pre-generate keys for exchange benchmark
        alice_priv = x25519.X25519PrivateKey.generate()
        bob_priv = x25519.X25519PrivateKey.generate()
        bob_pub = bob_priv.public_key()
        
        return self.benchmarker.benchmark(
            func=alice_priv.exchange,
            data_size=32,  # Shared secret size
            operation_name="X25519 Key Exchange",
            peer_public_key=bob_pub
        )
    
    # ==================
    # Kyber512 Benchmarks
    # ==================
    
    def benchmark_kyber_keypair(self) -> BenchmarkResult:
        """
        Benchmark Kyber512 keypair generation.
        قياس أداء توليد مفاتيح Kyber512
        """
        return self.benchmarker.benchmark(
            func=self.kyber_backend.generate_keypair,
            data_size=800,  # Approximate Kyber512 public key size
            operation_name="Kyber512 Keypair Generation"
        )
    
    def benchmark_kyber_encapsulation(self) -> BenchmarkResult:
        """
        Benchmark Kyber512 encapsulation.
        قياس أداء تغليف Kyber512
        """
        # Pre-generate keypair for encapsulation benchmark
        pub_key, _ = self.kyber_backend.generate_keypair()
        
        return self.benchmarker.benchmark(
            func=self.kyber_backend.encapsulate,
            data_size=768,  # Kyber512 ciphertext size
            operation_name="Kyber512 Encapsulation",
            public_key=pub_key
        )
    
    def benchmark_kyber_decapsulation(self) -> BenchmarkResult:
        """
        Benchmark Kyber512 decapsulation.
        قياس أداء فك تغليف Kyber512
        """
        # Pre-generate keypair and ciphertext for decapsulation benchmark
        pub_key, priv_key = self.kyber_backend.generate_keypair()
        ciphertext, _ = self.kyber_backend.encapsulate(pub_key)
        
        return self.benchmarker.benchmark(
            func=self.kyber_backend.decapsulate,
            data_size=32,  # Shared secret size
            operation_name="Kyber512 Decapsulation",
            private_key=priv_key,
            ciphertext=ciphertext
        )
    
    # ==================
    # PQ-X3DH Benchmarks
    # ==================
    
    def _generate_identity_bundle(self):
        """Generate a complete identity bundle for PQ-X3DH."""
        ik_priv = x25519.X25519PrivateKey.generate()
        spk_priv = x25519.X25519PrivateKey.generate()
        opk_priv = x25519.X25519PrivateKey.generate()
        kyber_pub, kyber_priv = self.kyber_backend.generate_keypair()
        
        return {
            'ik_priv': ik_priv,
            'ik_pub': ik_priv.public_key(),
            'spk_priv': spk_priv,
            'spk_pub': spk_priv.public_key(),
            'opk_priv': opk_priv,
            'opk_pub': opk_priv.public_key(),
            'kyber_priv': kyber_priv,
            'kyber_pub': kyber_pub,
        }
    
    def benchmark_pqx3dh_key_generation(self) -> BenchmarkResult:
        """
        Benchmark PQ-X3DH key bundle generation.
        قياس أداء توليد حزمة مفاتيح PQ-X3DH
        """
        return self.benchmarker.benchmark(
            func=self._generate_identity_bundle,
            data_size=0,  # Key generation, no data size
            operation_name="PQ-X3DH Key Bundle Generation"
        )
    
    def benchmark_pqx3dh_initiation(self) -> BenchmarkResult:
        """
        Benchmark PQ-X3DH initiation (Alice's side).
        قياس أداء بدء PQ-X3DH (جانب أليس)
        """
        # Pre-generate keys
        alice = self._generate_identity_bundle()
        bob = self._generate_identity_bundle()
        
        def initiate():
            return pqx3dh_initiate(
                my_ik_priv=alice['ik_priv'],
                their_ik_pub=bob['ik_pub'],
                their_spk_pub=bob['spk_pub'],
                their_opk_pub=bob['opk_pub'],
                their_kyber_pub=bob['kyber_pub'],
            )
        
        return self.benchmarker.benchmark(
            func=initiate,
            data_size=32,  # Root key size
            operation_name="PQ-X3DH Initiation"
        )
    
    def benchmark_pqx3dh_response(self) -> BenchmarkResult:
        """
        Benchmark PQ-X3DH response (Bob's side).
        قياس أداء استجابة PQ-X3DH (جانب بوب)
        """
        # Pre-generate keys and initiation data
        alice = self._generate_identity_bundle()
        bob = self._generate_identity_bundle()
        
        # Alice initiates
        _, ek, kyber_ct, _ = pqx3dh_initiate(
            my_ik_priv=alice['ik_priv'],
            their_ik_pub=bob['ik_pub'],
            their_spk_pub=bob['spk_pub'],
            their_opk_pub=bob['opk_pub'],
            their_kyber_pub=bob['kyber_pub'],
        )
        ek_pub_bytes = ek.public_key().public_bytes_raw()
        
        def respond():
            return pqx3dh_respond(
                my_ik_priv=bob['ik_priv'],
                my_spk_priv=bob['spk_priv'],
                my_opk_priv=bob['opk_priv'],
                my_kyber_priv=bob['kyber_priv'],
                their_ik_pub=alice['ik_pub'],
                ek_pub_bytes=ek_pub_bytes,
                kyber_ct=kyber_ct,
            )
        
        return self.benchmarker.benchmark(
            func=respond,
            data_size=32,  # Root key size
            operation_name="PQ-X3DH Response"
        )
    
    def benchmark_pqx3dh_full_handshake(self) -> BenchmarkResult:
        """
        Benchmark complete PQ-X3DH handshake (both sides).
        قياس أداء مصافحة PQ-X3DH الكاملة
        """
        def full_handshake():
            # Generate keys for both parties
            alice = self._generate_identity_bundle()
            bob = self._generate_identity_bundle()
            
            # Alice initiates
            alice_rk, ek, kyber_ct, _ = pqx3dh_initiate(
                my_ik_priv=alice['ik_priv'],
                their_ik_pub=bob['ik_pub'],
                their_spk_pub=bob['spk_pub'],
                their_opk_pub=bob['opk_pub'],
                their_kyber_pub=bob['kyber_pub'],
            )
            
            # Bob responds
            bob_rk = pqx3dh_respond(
                my_ik_priv=bob['ik_priv'],
                my_spk_priv=bob['spk_priv'],
                my_opk_priv=bob['opk_priv'],
                my_kyber_priv=bob['kyber_priv'],
                their_ik_pub=alice['ik_pub'],
                ek_pub_bytes=ek.public_key().public_bytes_raw(),
                kyber_ct=kyber_ct,
            )
            
            return alice_rk, bob_rk
        
        return self.benchmarker.benchmark(
            func=full_handshake,
            data_size=64,  # Two root keys
            operation_name="PQ-X3DH Full Handshake"
        )
    
    # ==================
    # Run All Benchmarks
    # ==================
    
    def run_all_benchmarks(self) -> PerformanceSuite:
        """
        Run all key exchange benchmarks.
        تشغيل جميع اختبارات تبادل المفاتيح
        """
        suite = PerformanceSuite(suite_name="Key Exchange Operations")
        
        # X25519 benchmarks
        suite.add_result(self.benchmark_x25519_keypair())
        suite.add_result(self.benchmark_x25519_exchange())
        
        # Kyber512 benchmarks
        suite.add_result(self.benchmark_kyber_keypair())
        suite.add_result(self.benchmark_kyber_encapsulation())
        suite.add_result(self.benchmark_kyber_decapsulation())
        
        # PQ-X3DH benchmarks
        suite.add_result(self.benchmark_pqx3dh_key_generation())
        suite.add_result(self.benchmark_pqx3dh_initiation())
        suite.add_result(self.benchmark_pqx3dh_response())
        suite.add_result(self.benchmark_pqx3dh_full_handshake())
        
        return suite
    
    def run_x25519_benchmarks(self) -> List[BenchmarkResult]:
        """Run only X25519 benchmarks."""
        return [
            self.benchmark_x25519_keypair(),
            self.benchmark_x25519_exchange(),
        ]
    
    def run_kyber_benchmarks(self) -> List[BenchmarkResult]:
        """Run only Kyber512 benchmarks."""
        return [
            self.benchmark_kyber_keypair(),
            self.benchmark_kyber_encapsulation(),
            self.benchmark_kyber_decapsulation(),
        ]
    
    def run_pqx3dh_benchmarks(self) -> List[BenchmarkResult]:
        """Run only PQ-X3DH benchmarks."""
        return [
            self.benchmark_pqx3dh_key_generation(),
            self.benchmark_pqx3dh_initiation(),
            self.benchmark_pqx3dh_response(),
            self.benchmark_pqx3dh_full_handshake(),
        ]


def run_key_exchange_benchmarks(iterations: int = 50) -> Dict[str, Any]:
    """
    Run all key exchange benchmarks and return results.
    تشغيل جميع اختبارات تبادل المفاتيح وإرجاع النتائج
    """
    benchmarks = KeyExchangeBenchmarks(iterations=iterations)
    suite = benchmarks.run_all_benchmarks()
    return suite.to_dict()


def print_benchmark_results(results: Dict[str, Any]) -> None:
    """Print benchmark results in a formatted table."""
    print(f"\n{'='*80}")
    print(f"  {results['suite_name']}")
    print(f"  Total Benchmarks: {results['total_benchmarks']}")
    print(f"{'='*80}\n")
    
    header = f"{'Operation':<40} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Std Dev':<12}"
    print(header)
    print("-" * len(header))
    
    for r in results['results']:
        print(f"{r['operation']:<40} {r['avg_ms']:<12.3f} {r['min_ms']:<12.3f} {r['max_ms']:<12.3f} {r['std_dev_ms']:<12.3f}")
    
    print()


if __name__ == "__main__":
    print("Running Key Exchange Benchmarks...")
    print("This may take a minute.\n")
    
    results = run_key_exchange_benchmarks(iterations=50)
    print_benchmark_results(results)
