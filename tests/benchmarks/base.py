# Base Benchmark Classes
# الفئات الأساسية لقياس الأداء

"""
Base classes for performance benchmarking.
Requirements: 1.3, 1.4
"""

from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
import statistics
import time


@dataclass
class BenchmarkResult:
    """
    Result of a single benchmark operation.
    نتيجة قياس أداء عملية واحدة
    
    Attributes:
        operation_name: Name of the benchmarked operation
        data_size_bytes: Size of data used in the benchmark
        iterations: Number of iterations performed
        times_ms: List of execution times in milliseconds
    """
    operation_name: str
    data_size_bytes: int
    iterations: int
    times_ms: List[float] = field(default_factory=list)
    
    @property
    def avg_ms(self) -> float:
        """Calculate average execution time in milliseconds."""
        if not self.times_ms:
            return 0.0
        return statistics.mean(self.times_ms)
    
    @property
    def min_ms(self) -> float:
        """Get minimum execution time in milliseconds."""
        if not self.times_ms:
            return 0.0
        return min(self.times_ms)
    
    @property
    def max_ms(self) -> float:
        """Get maximum execution time in milliseconds."""
        if not self.times_ms:
            return 0.0
        return max(self.times_ms)
    
    @property
    def std_dev_ms(self) -> float:
        """Calculate standard deviation of execution times."""
        if len(self.times_ms) < 2:
            return 0.0
        return statistics.stdev(self.times_ms)
    
    @property
    def throughput_mbps(self) -> float:
        """
        Calculate throughput in MB/s.
        حساب الإنتاجية بـ MB/s
        
        Formula: (data_size_bytes / 1MB) / (avg_time_ms / 1000)
        """
        if self.avg_ms == 0 or self.data_size_bytes == 0:
            return 0.0
        # Convert bytes to MB and ms to seconds
        data_mb = self.data_size_bytes / (1024 * 1024)
        time_seconds = self.avg_ms / 1000
        return data_mb / time_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for reporting."""
        return {
            "operation": self.operation_name,
            "data_size_bytes": self.data_size_bytes,
            "data_size_display": self._format_size(self.data_size_bytes),
            "iterations": self.iterations,
            "avg_ms": round(self.avg_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "std_dev_ms": round(self.std_dev_ms, 3),
            "throughput_mbps": round(self.throughput_mbps, 2)
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human readable string."""
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes} B"


class Benchmarker:
    """
    Base class for running benchmarks.
    فئة أساسية لقياس الأداء
    """
    
    def __init__(self, iterations: int = 100):
        """
        Initialize benchmarker.
        
        Args:
            iterations: Number of iterations for each benchmark (default: 100)
        """
        self.iterations = iterations
    
    def benchmark(
        self, 
        func: Callable, 
        data_size: int,
        operation_name: Optional[str] = None,
        *args, 
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark a function.
        قياس أداء دالة معينة
        
        Args:
            func: Function to benchmark
            data_size: Size of data being processed
            operation_name: Optional name for the operation
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            BenchmarkResult with timing statistics
        """
        times = []
        name = operation_name or func.__name__
        
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds
        
        return BenchmarkResult(
            operation_name=name,
            data_size_bytes=data_size,
            iterations=self.iterations,
            times_ms=times
        )
    
    def benchmark_with_setup(
        self,
        setup_func: Callable,
        func: Callable,
        data_size: int,
        operation_name: Optional[str] = None
    ) -> BenchmarkResult:
        """
        Benchmark a function with setup before each iteration.
        
        Args:
            setup_func: Function that returns args for the main function
            func: Function to benchmark
            data_size: Size of data being processed
            operation_name: Optional name for the operation
            
        Returns:
            BenchmarkResult with timing statistics
        """
        times = []
        name = operation_name or func.__name__
        
        for _ in range(self.iterations):
            args = setup_func()
            start = time.perf_counter()
            func(*args) if isinstance(args, tuple) else func(args)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        return BenchmarkResult(
            operation_name=name,
            data_size_bytes=data_size,
            iterations=self.iterations,
            times_ms=times
        )


@dataclass
class PerformanceSuite:
    """
    Collection of benchmark results.
    مجموعة نتائج أداء
    """
    suite_name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result to the suite."""
        self.results.append(result)
    
    def get_summary_table(self) -> List[Dict[str, Any]]:
        """
        Get summary table of all results.
        الحصول على جدول ملخص
        """
        return [r.to_dict() for r in self.results]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert suite to dictionary for reporting."""
        return {
            "suite_name": self.suite_name,
            "total_benchmarks": len(self.results),
            "results": self.get_summary_table()
        }
