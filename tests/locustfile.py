"""
Load testing script for FastAPI application using Locust.

Run with: locust -f tests/locustfile.py --host=http://localhost:8000

Web UI: http://localhost:8089
"""

import argparse
import random
import subprocess
import sys

from locust import HttpUser, between, task


class APIUser(HttpUser):
    """Simulated API user for load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts."""
        # Register and login
        self.username = f"loadtest_user_{random.randint(1000, 9999)}"
        self.password = "testpassword123"

        # Register
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{self.username}@example.com",
                "username": self.username,
                "password": self.password,
            },
        )

        # Login and get token
        response = self.client.post(
            "/api/v1/auth/login", data={"username": self.username, "password": self.password}
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(3)
    def get_user_info(self):
        """Get current user information."""
        self.client.get("/api/v1/users/me", headers=self.headers)

    @task(5)
    def list_documents(self):
        """List user's documents."""
        self.client.get("/api/v1/documents/", headers=self.headers)

    @task(2)
    def create_document(self):
        """Create a new document."""
        self.client.post(
            "/api/v1/documents/",
            headers=self.headers,
            json={
                "title": f"Load Test Document {random.randint(1, 1000)}",
                "content": "This is a load test document",
                "description": "Generated during load testing",
            },
        )

    @task(1)
    def health_check(self):
        """Check health endpoint."""
        self.client.get("/health")


class RateLimitTest(HttpUser):
    """Test rate limiting specifically."""

    wait_time = between(0.1, 0.5)  # Very short wait time to trigger rate limits

    def on_start(self):
        """Setup user."""
        # Use a single user to test rate limiting
        response = self.client.post(
            "/api/v1/auth/login", data={"username": "testuser", "password": "testpassword"}
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task
    def rapid_requests(self):
        """Make rapid requests to trigger rate limiting."""
        response = self.client.get("/api/v1/users/me", headers=self.headers)
        if response.status_code == 429:
            # Rate limited - this is expected
            pass


# ============================================================================
# run_tests.py - Comprehensive test runner script
# ============================================================================

#!/usr/bin/env python3
"""
Comprehensive test runner for the FastAPI application.

Usage:
    python run_tests.py --all
    python run_tests.py --unit
    python run_tests.py --integration
    python run_tests.py --performance
    python run_tests.py --coverage
"""


class Colors:
    """Terminal colors."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(message):
    """Print colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"{Colors.OKBLUE}▶ {description}{Colors.ENDC}")
    print(f"  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"{Colors.OKGREEN}✓ {description} - PASSED{Colors.ENDC}\n")
        return True
    else:
        print(f"{Colors.FAIL}✗ {description} - FAILED{Colors.ENDC}\n")
        return False


def run_unit_tests():
    """Run unit tests."""
    print_header("Running Unit Tests")
    return run_command(
        ["pytest", "tests/test_utils.py", "-v", "-m", "unit"], "Unit Tests (Utilities)"
    )


def run_integration_tests():
    """Run integration tests."""
    print_header("Running Integration Tests")
    success = True

    tests = [
        ("tests/test_auth.py", "Authentication Tests"),
        ("tests/test_documents.py", "Document CRUD Tests"),
        ("tests/test_url_shortening.py", "URL Shortening Tests"),
    ]

    for test_file, description in tests:
        if not run_command(["pytest", test_file, "-v"], description):
            success = False

    return success


def run_validation_tests():
    """Run validation and edge case tests."""
    print_header("Running Validation Tests")
    return run_command(
        ["pytest", "tests/test_validation.py", "-v"], "Input Validation & Edge Cases"
    )


def run_middleware_tests():
    """Run middleware tests."""
    print_header("Running Middleware Tests")
    return run_command(["pytest", "tests/test_middleware.py", "-v"], "Middleware Tests")


def run_rate_limit_tests():
    """Run rate limiting tests."""
    print_header("Running Rate Limiting Tests")
    return run_command(["pytest", "tests/test_rate_limiting.py", "-v", "-s"], "Rate Limiting Tests")


def run_performance_tests():
    """Run performance tests."""
    print_header("Running Performance Tests")
    success = True

    tests = [
        (
            ["pytest", "tests/test_utils.py::TestSnowflakeID", "-v", "-s"],
            "Snowflake ID Performance (10,000 IDs)",
        ),
        (
            ["pytest", "tests/test_rate_limiting.py::TestRateLimiterPerformance", "-v", "-s"],
            "Rate Limiter Performance (1000 req/s)",
        ),
        (["pytest", "tests/test_performance.py", "-v", "-s"], "Database Performance Tests"),
    ]

    for cmd, description in tests:
        if not run_command(cmd, description):
            success = False

    return success


def run_coverage_tests():
    """Run all tests with coverage."""
    print_header("Running Tests with Coverage")

    cmd = [
        "pytest",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=70",
        "-v",
    ]

    success = run_command(cmd, "Full Test Suite with Coverage")

    if success:
        print(f"\n{Colors.OKGREEN}✓ Coverage report generated: htmlcov/index.html{Colors.ENDC}")

    return success


def run_all_tests():
    """Run all test suites."""
    print_header("Running Complete Test Suite")

    results = {
        "Unit Tests": run_unit_tests(),
        "Integration Tests": run_integration_tests(),
        "Validation Tests": run_validation_tests(),
        "Middleware Tests": run_middleware_tests(),
        "Rate Limiting Tests": run_rate_limit_tests(),
    }

    # Print summary
    print_header("Test Summary")

    all_passed = True
    for test_name, passed in results.items():
        status = (
            f"{Colors.OKGREEN}✓ PASSED{Colors.ENDC}"
            if passed
            else f"{Colors.FAIL}✗ FAILED{Colors.ENDC}"
        )
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print(f"{Colors.OKGREEN}{Colors.BOLD}All tests passed! 🎉{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}Some tests failed! ❌{Colors.ENDC}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tests for FastAPI application")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--validation", action="store_true", help="Run validation tests only")
    parser.add_argument("--middleware", action="store_true", help="Run middleware tests only")
    parser.add_argument("--rate-limit", action="store_true", help="Run rate limiting tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--coverage", action="store_true", help="Run all tests with coverage")

    args = parser.parse_args()

    # If no specific test type specified, run all
    if not any(
        [
            args.unit,
            args.integration,
            args.validation,
            args.middleware,
            args.rate_limit,
            args.performance,
            args.coverage,
            args.all,
        ]
    ):
        args.all = True

    success = True

    if args.unit:
        success = run_unit_tests() and success

    if args.integration:
        success = run_integration_tests() and success

    if args.validation:
        success = run_validation_tests() and success

    if args.middleware:
        success = run_middleware_tests() and success

    if args.rate_limit:
        success = run_rate_limit_tests() and success

    if args.performance:
        success = run_performance_tests() and success

    if args.coverage:
        success = run_coverage_tests() and success

    if args.all:
        success = run_all_tests() and success
        if success:
            # Also run coverage
            run_coverage_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


# ============================================================================
# test_checklist.py - Automated checklist validator
# ============================================================================

"""
Automated test checklist validator.

Runs all tests and checks against the requirements checklist.
"""


class TestChecker:
    """Check test coverage against requirements."""

    def __init__(self):
        self.results = {}

    def run_test(self, test_path: str) -> bool:
        """Run a specific test and return success status."""
        result = subprocess.run(
            ["pytest", test_path, "-v", "--tb=short"], capture_output=True, text=True
        )
        return result.returncode == 0

    def check_authentication(self) -> dict[str, bool]:
        """Check authentication tests."""
        tests = {
            "Register user": "tests/test_auth.py::TestAuthentication::test_register_user_success",
            "Login valid": "tests/test_auth.py::TestAuthentication::test_login_success",
            "Login invalid": "tests/test_auth.py::TestAuthentication::test_login_invalid_credentials",
            "Protected endpoint 401": "tests/test_auth.py::TestAuthentication::test_protected_endpoint_without_token",
            "Access other user docs 403": "tests/test_documents.py::TestDocuments::test_get_other_user_document",
        }

        return {name: self.run_test(path) for name, path in tests.items()}

    def check_rate_limiting(self) -> dict[str, bool]:
        """Check rate limiting tests."""
        tests = {
            "Rate limit enforcement": "tests/test_rate_limiting.py::TestRateLimiting::test_rate_limit_enforcement",
            "Rate limit headers": "tests/test_rate_limiting.py::TestRateLimiting::test_rate_limit_headers",
            "Rate limit reset": "tests/test_rate_limiting.py::TestRateLimiting::test_rate_limit_reset",
            "1000 req/s performance": "tests/test_rate_limiting.py::TestRateLimiterPerformance::test_high_throughput",
        }

        return {name: self.run_test(path) for name, path in tests.items()}

    def check_url_shortening(self) -> dict[str, bool]:
        """Check URL shortening tests."""
        tests = {
            "Base62 encoding": "tests/test_utils.py::TestBase62Encoder::test_encode_decode_roundtrip",
            "Create short URL": "tests/test_url_shortening.py::TestURLShortening::test_create_short_url",
            "Redirect": "tests/test_url_shortening.py::TestURLShortening::test_redirect_short_url",
            "Analytics": "tests/test_url_shortening.py::TestURLShortening::test_short_url_analytics",
            "Snowflake 10k IDs": "tests/test_utils.py::TestSnowflakeID::test_generate_unique_ids",
        }

        return {name: self.run_test(path) for name, path in tests.items()}

    def print_checklist(self):
        """Print formatted checklist."""
        print("\n" + "=" * 70)
        print("TEST COVERAGE CHECKLIST".center(70))
        print("=" * 70 + "\n")

        sections = [
            ("Authentication & Authorization", self.check_authentication()),
            ("Rate Limiting", self.check_rate_limiting()),
            ("URL Shortening", self.check_url_shortening()),
        ]

        total_tests = 0
        passed_tests = 0

        for section_name, tests in sections:
            print(f"\n{section_name}:")
            print("-" * 70)

            for test_name, passed in tests.items():
                status = "✓" if passed else "✗"
                color = Colors.OKGREEN if passed else Colors.FAIL
                print(f"  {color}[{status}]{Colors.ENDC} {test_name}")
                total_tests += 1
                if passed:
                    passed_tests += 1

        print("\n" + "=" * 70)
        coverage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Overall: {passed_tests}/{total_tests} tests passed ({coverage:.1f}%)")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    checker = TestChecker()
    checker.print_checklist()
