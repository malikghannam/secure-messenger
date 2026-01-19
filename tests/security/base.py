# Base Security Test Classes
# الفئات الأساسية لاختبارات الأمان

"""
Base classes for security testing.
Requirements: 5.1, 7.1, 8.1, 9.1
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class TestStatus(Enum):
    """Status of a security test."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class SecurityTestResult:
    """
    Result of a security test.
    نتيجة اختبار أمان
    
    Attributes:
        test_name: Name of the test
        category: Category (timing, entropy, integrity, replay, forward_secrecy)
        status: Test status (passed, failed, warning)
        description: Description of what was tested
        details: Optional detailed results
        recommendation: Optional recommendation if test failed/warning
    """
    test_name: str
    category: str
    status: TestStatus
    description: str
    details: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for reporting."""
        result = {
            "test_name": self.test_name,
            "category": self.category,
            "status": self.status.value,
            "description": self.description
        }
        if self.details:
            result["details"] = self.details
        if self.recommendation:
            result["recommendation"] = self.recommendation
        return result
    
    @property
    def is_passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.PASSED
    
    @property
    def is_failed(self) -> bool:
        """Check if test failed."""
        return self.status == TestStatus.FAILED


class SecurityTest(ABC):
    """
    Abstract base class for security tests.
    فئة أساسية لاختبارات الأمان
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the test."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Category of the test."""
        pass
    
    @abstractmethod
    def run(self) -> SecurityTestResult:
        """
        Run the security test.
        
        Returns:
            SecurityTestResult with test outcome
        """
        pass
    
    def _create_result(
        self,
        status: TestStatus,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        recommendation: Optional[str] = None
    ) -> SecurityTestResult:
        """Helper to create a test result."""
        return SecurityTestResult(
            test_name=self.name,
            category=self.category,
            status=status,
            description=description,
            details=details,
            recommendation=recommendation
        )


@dataclass
class SecuritySuite:
    """
    Collection of security test results.
    مجموعة نتائج أمان
    """
    suite_name: str
    results: List[SecurityTestResult] = field(default_factory=list)
    
    def add_result(self, result: SecurityTestResult) -> None:
        """Add a test result to the suite."""
        self.results.append(result)
    
    @property
    def passed_count(self) -> int:
        """Count of passed tests."""
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)
    
    @property
    def failed_count(self) -> int:
        """Count of failed tests."""
        return sum(1 for r in self.results if r.status == TestStatus.FAILED)
    
    @property
    def warning_count(self) -> int:
        """Count of warning tests."""
        return sum(1 for r in self.results if r.status == TestStatus.WARNING)
    
    @property
    def total_count(self) -> int:
        """Total number of tests."""
        return len(self.results)
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if not self.results:
            return 0.0
        return (self.passed_count / len(self.results)) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "total": self.total_count,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "warnings": self.warning_count,
            "pass_rate": round(self.pass_rate, 1)
        }
    
    def get_results_by_category(self) -> Dict[str, List[SecurityTestResult]]:
        """Group results by category."""
        by_category: Dict[str, List[SecurityTestResult]] = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)
        return by_category
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert suite to dictionary for reporting."""
        return {
            "suite_name": self.suite_name,
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results]
        }
