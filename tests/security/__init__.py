# Security Tests Module
# اختبارات الأمان

"""
This module contains security tests for the secure messenger:
- timing_tests: Timing attack resistance
- entropy_tests: Key randomness and entropy
- integrity_tests: Data integrity verification
- replay_tests: Replay attack resistance
- forward_secrecy_tests: Forward secrecy verification
"""

from tests.security.base import (
    TestStatus,
    SecurityTestResult,
    SecurityTest,
    SecuritySuite
)

from tests.security.timing_tests import (
    TimingTests,
    run_timing_tests
)

from tests.security.entropy_tests import (
    EntropyTests,
    run_entropy_tests
)

from tests.security.integrity_tests import (
    IntegrityTests,
    run_integrity_tests
)

from tests.security.replay_tests import (
    ReplayTests,
    run_replay_tests
)

from tests.security.forward_secrecy_tests import (
    ForwardSecrecyTests,
    run_forward_secrecy_tests
)

__all__ = [
    'TestStatus',
    'SecurityTestResult',
    'SecurityTest',
    'SecuritySuite',
    'TimingTests',
    'run_timing_tests',
    'EntropyTests',
    'run_entropy_tests',
    'IntegrityTests',
    'run_integrity_tests',
    'ReplayTests',
    'run_replay_tests',
    'ForwardSecrecyTests',
    'run_forward_secrecy_tests'
]
