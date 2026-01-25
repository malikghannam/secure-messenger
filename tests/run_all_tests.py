#!/usr/bin/env python3
# Run All Performance and Security Tests
# تشغيل جميع اختبارات الأداء والأمان

"""
Main script to run all benchmarks and security tests.
السكريبت الرئيسي لتشغيل جميع اختبارات الأداء والأمان

Requirements: 10.1
"""

import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_benchmarks(verbose: bool = True) -> dict:
    """Run all performance benchmarks."""
    from tests.benchmarks import (
        run_crypto_benchmarks,
        run_key_exchange_benchmarks,
        run_ratchet_benchmarks,
        run_file_benchmarks
    )
    
    results = {}
    
    if verbose:
        print_header("اختبارات الأداء / Performance Benchmarks")
    
    # Crypto benchmarks
    if verbose:
        print("Running XChaCha20-Poly1305 benchmarks...")
    results['crypto'] = run_crypto_benchmarks()
    if verbose:
        _print_benchmark_summary(results['crypto'])
    
    # Key exchange benchmarks
    if verbose:
        print("\nRunning Key Exchange benchmarks...")
    results['key_exchange'] = run_key_exchange_benchmarks()
    if verbose:
        _print_benchmark_summary(results['key_exchange'])
    
    # Ratchet benchmarks
    if verbose:
        print("\nRunning Double Ratchet benchmarks...")
    results['ratchet'] = run_ratchet_benchmarks()
    if verbose:
        _print_benchmark_summary(results['ratchet'])
    
    # File benchmarks
    if verbose:
        print("\nRunning File Encryption benchmarks...")
    results['file'] = run_file_benchmarks()
    if verbose:
        _print_benchmark_summary(results['file'])
    
    return results


def _print_benchmark_summary(results: dict) -> None:
    """Print benchmark summary."""
    suite_name = results.get('suite_name', 'Benchmarks')
    total = len(results.get('results', []))
    print(f"  {suite_name}: {total} benchmarks completed")


def run_security_tests(verbose: bool = True) -> dict:
    """Run all security tests."""
    from tests.security import (
        run_timing_tests,
        run_entropy_tests,
        run_integrity_tests,
        run_replay_tests,
        run_forward_secrecy_tests
    )
    
    results = {}
    
    if verbose:
        print_header("اختبارات الأمان / Security Tests")
    
    # Timing tests
    if verbose:
        print("Running Timing Attack tests...")
    results['timing'] = run_timing_tests()
    if verbose:
        _print_security_summary(results['timing'])
    
    # Entropy tests
    if verbose:
        print("\nRunning Entropy tests...")
    results['entropy'] = run_entropy_tests()
    if verbose:
        _print_security_summary(results['entropy'])
    
    # Integrity tests
    if verbose:
        print("\nRunning Integrity tests...")
    results['integrity'] = run_integrity_tests()
    if verbose:
        _print_security_summary(results['integrity'])
    
    # Replay tests
    if verbose:
        print("\nRunning Replay Attack tests...")
    results['replay'] = run_replay_tests()
    if verbose:
        _print_security_summary(results['replay'])
    
    # Forward secrecy tests
    if verbose:
        print("\nRunning Forward Secrecy tests...")
    results['forward_secrecy'] = run_forward_secrecy_tests()
    if verbose:
        _print_security_summary(results['forward_secrecy'])
    
    return results


def _print_security_summary(results: dict) -> None:
    """Print security test summary."""
    suite_name = results.get('suite_name', 'Security Tests')
    summary = results.get('summary', {})
    passed = summary.get('passed', 0)
    total = summary.get('total', 0)
    warnings = summary.get('warnings', 0)
    failed = summary.get('failed', 0)
    
    status = "✅" if failed == 0 else "❌"
    warning_str = f" ({warnings} warnings)" if warnings > 0 else ""
    print(f"  {status} {suite_name}: {passed}/{total} passed{warning_str}")


def generate_report(benchmark_results: dict, security_results: dict, output_dir: str) -> None:
    """Generate test reports."""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate simple Markdown report
    md_path = os.path.join(output_dir, "TEST_RESULTS.md")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Test Results\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        # Benchmark results
        if benchmark_results:
            f.write("## Performance Benchmarks\n\n")
            for name, results in benchmark_results.items():
                f.write(f"### {results.get('suite_name', name)}\n\n")
                for result in results.get('results', []):
                    f.write(f"- {result.get('name', 'Test')}: {result.get('value', 'N/A')}\n")
                f.write("\n")
        
        # Security results
        if security_results:
            f.write("## Security Tests\n\n")
            for name, results in security_results.items():
                summary = results.get('summary', {})
                f.write(f"### {results.get('suite_name', name)}\n\n")
                f.write(f"- Passed: {summary.get('passed', 0)}/{summary.get('total', 0)}\n")
                f.write(f"- Warnings: {summary.get('warnings', 0)}\n")
                f.write(f"- Failed: {summary.get('failed', 0)}\n\n")
    
    print(f"Report saved to: {md_path}")


def print_final_summary(benchmark_results: dict, security_results: dict) -> None:
    """Print final summary of all tests."""
    print_header("الملخص النهائي / Final Summary")
    
    # Benchmark summary
    total_benchmarks = sum(
        len(r.get('results', [])) for r in benchmark_results.values()
    )
    print(f"اختبارات الأداء / Performance Benchmarks: {total_benchmarks} completed")
    
    # Security summary
    total_security = 0
    passed_security = 0
    warnings_security = 0
    failed_security = 0
    
    for results in security_results.values():
        summary = results.get('summary', {})
        total_security += summary.get('total', 0)
        passed_security += summary.get('passed', 0)
        warnings_security += summary.get('warnings', 0)
        failed_security += summary.get('failed', 0)
    
    print(f"اختبارات الأمان / Security Tests: {passed_security}/{total_security} passed")
    if warnings_security > 0:
        print(f"  ⚠️  تحذيرات / Warnings: {warnings_security}")
    if failed_security > 0:
        print(f"  ❌ فشل / Failed: {failed_security}")
    
    # Overall status
    print()
    if failed_security == 0:
        print("✅ جميع الاختبارات الحرجة ناجحة / All critical tests passed!")
    else:
        print("❌ بعض الاختبارات فشلت / Some tests failed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run all performance and security tests'
    )
    parser.add_argument(
        '--benchmarks-only',
        action='store_true',
        help='Run only performance benchmarks'
    )
    parser.add_argument(
        '--security-only',
        action='store_true',
        help='Run only security tests'
    )
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip report generation'
    )
    parser.add_argument(
        '--output-dir',
        default='tests/reports',
        help='Output directory for reports (default: tests/reports)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )
    
    args = parser.parse_args()
    verbose = not args.quiet
    
    if verbose:
        print_header("تشغيل اختبارات الأداء والأمان")
        print(f"Started at: {datetime.now().isoformat()}")
    
    benchmark_results = {}
    security_results = {}
    
    # Run benchmarks
    if not args.security_only:
        benchmark_results = run_benchmarks(verbose)
    
    # Run security tests
    if not args.benchmarks_only:
        security_results = run_security_tests(verbose)
    
    # Generate report
    if not args.no_report and (benchmark_results or security_results):
        if verbose:
            print_header("توليد التقرير / Generating Report")
        generate_report(benchmark_results, security_results, args.output_dir)
        if verbose:
            print(f"Reports saved to: {args.output_dir}/")
    
    # Print final summary
    if verbose and benchmark_results and security_results:
        print_final_summary(benchmark_results, security_results)
    
    if verbose:
        print(f"\nCompleted at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
