#!/usr/bin/env python3
"""
Test runner script with coverage reporting.
"""
import os
import sys
import unittest
from typing import List, Optional

try:
    import coverage
except ImportError:
    print("Coverage package not found. Installing...")
    os.system(f"{sys.executable} -m pip install coverage")
    import coverage

def run_tests_with_coverage(test_pattern: Optional[str] = None) -> None:
    """Run tests with coverage reporting.
    
    Args:
        test_pattern: Optional pattern to filter test files
    """
    # Start coverage
    cov = coverage.Coverage(
        branch=True,
        source=['src'],
        omit=['*/__init__.py', '*/tests/*']
    )
    cov.start()
    
    try:
        # Discover and run tests
        loader = unittest.TestLoader()
        if test_pattern:
            pattern = f'test_{test_pattern}.py'
        else:
            pattern = 'test_*.py'
            
        suite = loader.discover('tests', pattern=pattern)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Stop coverage and generate report
        cov.stop()
        cov.save()
        
        print("\nCoverage Report:")
        print("=" * 60)
        cov.report()
        
        # Generate HTML report
        html_dir = 'coverage_html'
        cov.html_report(directory=html_dir)
        print(f"\nDetailed HTML coverage report: {html_dir}/index.html")
        
        # Return exit code
        return 0 if result.wasSuccessful() else 1
        
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\nError running tests: {e}")
        return 1

def main() -> int:
    """Main function."""
    # Parse command line arguments
    test_pattern = None
    if len(sys.argv) > 1:
        test_pattern = sys.argv[1]
        
    # Add src directory to Python path
    src_dir = os.path.join(os.path.dirname(__file__), 'src')
    sys.path.insert(0, src_dir)
    
    # Run tests
    return run_tests_with_coverage(test_pattern)

if __name__ == '__main__':
    sys.exit(main()) 