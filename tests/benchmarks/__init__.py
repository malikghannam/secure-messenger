# Performance Benchmarks Module
# اختبارات قياس الأداء

"""
This module contains performance benchmarks for the secure messenger:
- crypto_benchmarks: XChaCha20-Poly1305 encryption/decryption
- key_exchange_benchmarks: PQ-X3DH, Kyber512, X25519
- ratchet_benchmarks: Double Ratchet performance
- file_benchmarks: File encryption performance
"""

from tests.benchmarks.base import (
    BenchmarkResult,
    Benchmarker,
    PerformanceSuite
)

from tests.benchmarks.crypto_benchmarks import (
    CryptoBenchmarks,
    run_crypto_benchmarks,
    DATA_SIZES
)

from tests.benchmarks.key_exchange_benchmarks import (
    KeyExchangeBenchmarks,
    run_key_exchange_benchmarks
)

from tests.benchmarks.ratchet_benchmarks import (
    RatchetBenchmarks,
    run_ratchet_benchmarks,
    MESSAGE_SIZES
)

from tests.benchmarks.file_benchmarks import (
    FileBenchmarks,
    run_file_benchmarks,
    FILE_SIZES
)

__all__ = [
    'BenchmarkResult',
    'Benchmarker',
    'PerformanceSuite',
    'CryptoBenchmarks',
    'run_crypto_benchmarks',
    'DATA_SIZES',
    'KeyExchangeBenchmarks',
    'run_key_exchange_benchmarks',
    'RatchetBenchmarks',
    'run_ratchet_benchmarks',
    'MESSAGE_SIZES',
    'FileBenchmarks',
    'run_file_benchmarks',
    'FILE_SIZES'
]
