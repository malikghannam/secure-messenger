# File Encryption Benchmarks - Large File Performance Tests
# اختبارات أداء تشفير الملفات

"""
Benchmark file encryption and decryption performance for various file sizes.
قياس أداء تشفير وفك تشفير الملفات

Requirements: 4.1, 4.2, 4.3, 4.4
- Measure time for file sizes: 100KB, 1MB, 10MB, 50MB
- Measure both encryption and decryption times
- Calculate throughput in MB/s
- Measure memory usage during encryption of large files
"""

import os
import tracemalloc
from typing import Dict, Any, List, Tuple

from tests.benchmarks.base import Benchmarker, BenchmarkResult, PerformanceSuite
from messenger.files.encryption import (
    encrypt_file,
    decrypt_file,
    generate_file_key,
)


# File sizes to benchmark (in bytes)
FILE_SIZES = {
    "100KB": 100 * 1024,
    "1MB": 1 * 1024 * 1024,
    "10MB": 10 * 1024 * 1024,
    "50MB": 50 * 1024 * 1024,
}


class FileBenchmarks:
    """
    Benchmarks for file encryption operations.
    اختبارات أداء تشفير الملفات
    """
    
    def __init__(self, iterations: int = 50):
        """
        Initialize file benchmarks.
        
        Args:
            iterations: Number of iterations per benchmark (default: 50)
                       Lower for large files to save time
        """
        self.benchmarker = Benchmarker(iterations=iterations)
        self.key = generate_file_key()
    
    def _generate_file_content(self, size: int) -> bytes:
        """Generate random file content of specified size."""
        return os.urandom(size)
    
    def _get_iterations_for_size(self, size: int) -> int:
        """
        Get appropriate iteration count based on file size.
        Reduce iterations for larger files to keep benchmark time reasonable.
        """
        if size >= 50 * 1024 * 1024:  # 50MB+
            return 10
        elif size >= 10 * 1024 * 1024:  # 10MB+
            return 20
        elif size >= 1 * 1024 * 1024:  # 1MB+
            return 50
        else:
            return self.benchmarker.iterations
    
    def benchmark_file_encryption(self, file_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark file encryption for a specific file size.
        قياس أداء تشفير ملف بحجم محدد
        """
        content = self._generate_file_content(file_size)
        iterations = self._get_iterations_for_size(file_size)
        
        benchmarker = Benchmarker(iterations=iterations)
        return benchmarker.benchmark(
            func=encrypt_file,
            data_size=file_size,
            operation_name=f"File Encrypt ({size_name})",
            content=content,
            key=self.key
        )
    
    def benchmark_file_decryption(self, file_size: int, size_name: str) -> BenchmarkResult:
        """
        Benchmark file decryption for a specific file size.
        قياس أداء فك تشفير ملف بحجم محدد
        """
        content = self._generate_file_content(file_size)
        encrypted = encrypt_file(content, self.key)
        iterations = self._get_iterations_for_size(file_size)
        
        benchmarker = Benchmarker(iterations=iterations)
        return benchmarker.benchmark(
            func=decrypt_file,
            data_size=file_size,
            operation_name=f"File Decrypt ({size_name})",
            encrypted_content=encrypted,
            key=self.key
        )
    
    def benchmark_memory_usage(self, file_size: int, size_name: str) -> Dict[str, Any]:
        """
        Measure memory usage during file encryption.
        قياس استهلاك الذاكرة أثناء تشفير الملفات
        """
        content = self._generate_file_content(file_size)
        
        # Start memory tracking
        tracemalloc.start()
        
        # Perform encryption
        encrypted = encrypt_file(content, self.key)
        
        # Get memory stats
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            "operation": f"Memory Usage ({size_name})",
            "file_size_bytes": file_size,
            "file_size_display": self._format_size(file_size),
            "current_memory_bytes": current,
            "current_memory_display": self._format_size(current),
            "peak_memory_bytes": peak,
            "peak_memory_display": self._format_size(peak),
            "memory_overhead_ratio": peak / file_size if file_size > 0 else 0,
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human readable string."""
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes} B"
    
    def run_all_benchmarks(self) -> Tuple[PerformanceSuite, List[Dict[str, Any]]]:
        """
        Run all file encryption benchmarks.
        تشغيل جميع اختبارات تشفير الملفات
        
        Returns:
            Tuple of (PerformanceSuite, memory_results)
        """
        suite = PerformanceSuite(suite_name="File Encryption Operations")
        memory_results = []
        
        for size_name, file_size in FILE_SIZES.items():
            # Encryption benchmark
            suite.add_result(self.benchmark_file_encryption(file_size, size_name))
            
            # Decryption benchmark
            suite.add_result(self.benchmark_file_decryption(file_size, size_name))
            
            # Memory usage
            memory_results.append(self.benchmark_memory_usage(file_size, size_name))
        
        return suite, memory_results


def run_file_benchmarks(iterations: int = 50) -> Dict[str, Any]:
    """
    Run all file benchmarks and return results.
    تشغيل جميع اختبارات الملفات وإرجاع النتائج
    """
    benchmarks = FileBenchmarks(iterations=iterations)
    suite, memory_results = benchmarks.run_all_benchmarks()
    
    return {
        "performance": suite.to_dict(),
        "memory": memory_results,
    }


def print_benchmark_results(results: Dict[str, Any]) -> None:
    """Print benchmark results in formatted tables."""
    perf = results["performance"]
    memory = results["memory"]
    
    # Performance results
    print(f"\n{'='*90}")
    print(f"  {perf['suite_name']}")
    print(f"  Total Benchmarks: {perf['total_benchmarks']}")
    print(f"{'='*90}\n")
    
    header = f"{'Operation':<30} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Throughput':<15}"
    print(header)
    print("-" * len(header))
    
    for r in perf['results']:
        throughput = f"{r['throughput_mbps']:.2f} MB/s"
        print(f"{r['operation']:<30} {r['avg_ms']:<12.3f} {r['min_ms']:<12.3f} {r['max_ms']:<12.3f} {throughput:<15}")
    
    # Memory results
    print(f"\n{'='*90}")
    print("  Memory Usage During Encryption")
    print(f"{'='*90}\n")
    
    mem_header = f"{'File Size':<15} {'Peak Memory':<20} {'Overhead Ratio':<15}"
    print(mem_header)
    print("-" * len(mem_header))
    
    for m in memory:
        print(f"{m['file_size_display']:<15} {m['peak_memory_display']:<20} {m['memory_overhead_ratio']:.2f}x")
    
    print()


if __name__ == "__main__":
    print("Running File Encryption Benchmarks...")
    print("This may take a few minutes for large files.\n")
    
    results = run_file_benchmarks(iterations=50)
    print_benchmark_results(results)
