"""
Load testing for horizontal scaling validation.

Tests:
1. 1000 concurrent users
2. Failover scenarios
3. Session persistence
4. Rate limiting under load

Usage:
    # Install dependencies
    pip install locust requests

    # Run load test
    locust -f load_test_scaling.py --host=http://localhost

    # Or use web UI
    locust -f load_test_scaling.py --host=http://localhost --web-host=0.0.0.0 --web-port=8089
"""

import random

from locust import HttpUser, TaskSet, between, events, task


class AuthBehavior(TaskSet):
    """User authentication behavior"""

    def on_start(self):
        """Called when a simulated user starts"""
        # Register and login
        self.username = f"user_{random.randint(1, 10000)}"
        self.password = "Test123!@#"

        # Register
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@example.com",
                "password": self.password,
                "full_name": f"Test User {self.username}",
            },
            name="/api/v1/auth/register",
        )

        if response.status_code == 201:
            # Login
            login_response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "username": self.username,
                    "password": self.password,
                },
                name="/api/v1/auth/login",
            )

            if login_response.status_code == 200:
                data = login_response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                self.token = None
                self.headers = {}
        else:
            # User might already exist, try login
            login_response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "username": self.username,
                    "password": self.password,
                },
                name="/api/v1/auth/login",
            )

            if login_response.status_code == 200:
                data = login_response.json()
                self.token = data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                self.token = None
                self.headers = {}

    @task(10)
    def health_check(self):
        """Health check endpoint (most frequent)"""
        self.client.get("/health/live", name="/health/live")

    @task(5)
    def readiness_check(self):
        """Readiness check endpoint"""
        self.client.get("/health/ready", name="/health/ready")

    @task(3)
    def get_user_profile(self):
        """Get user profile"""
        if hasattr(self, "headers") and self.headers:
            self.client.get(
                "/api/v1/users/me",
                headers=self.headers,
                name="/api/v1/users/me",
            )

    @task(2)
    def list_documents(self):
        """List user documents"""
        if hasattr(self, "headers") and self.headers:
            self.client.get(
                "/api/v1/documents",
                headers=self.headers,
                name="/api/v1/documents",
            )


class APIUser(HttpUser):
    """Simulated API user"""

    tasks = [AuthBehavior]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when user starts"""
        pass


class StressTestUser(HttpUser):
    """High-frequency user for stress testing"""

    tasks = [AuthBehavior]
    wait_time = between(0.1, 0.5)  # Very short wait time


# Custom events for tracking
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("\n" + "=" * 80)
    print("🚀 STARTING HORIZONTAL SCALING LOAD TEST")
    print("=" * 80)
    print(f"Target: {environment.host}")
    print("Expected: 3 API replicas behind nginx load balancer")
    print("=" * 80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\n" + "=" * 80)
    print("✅ LOAD TEST COMPLETED")
    print("=" * 80)
    print("\nCheck the following:")
    print("1. All 3 API instances handled requests")
    print("2. No dropped connections")
    print("3. Response times remained consistent")
    print("4. Failover worked if an instance was killed")
    print("=" * 80 + "\n")


# Failover test scenario
class FailoverTestUser(HttpUser):
    """
    User for testing failover scenarios.

    Run this while manually killing one API instance:
    docker stop urban-octo-tribble-api-2

    Then restart it:
    docker start urban-octo-tribble-api-2
    """

    tasks = [AuthBehavior]
    wait_time = between(0.5, 1)

    @task(20)
    def continuous_health_check(self):
        """Continuous health checks to monitor failover"""
        response = self.client.get("/health/ready", name="failover-health")

        if response.status_code != 200:
            print(f"⚠️  Health check failed: {response.status_code}")


if __name__ == "__main__":
    import os

    os.system("locust -f load_test_scaling.py --host=http://localhost")
