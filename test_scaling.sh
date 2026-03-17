#!/bin/bash

# Phase 3.6 - Horizontal Scaling Validation Script
# Tests all requirements for the phase

set -e

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RESET='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

echo -e "${COLOR_BLUE}╔════════════════════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_BLUE}║  Phase 3.6: Horizontal Scaling - Validation Tests        ║${COLOR_RESET}"
echo -e "${COLOR_BLUE}╚════════════════════════════════════════════════════════════╝${COLOR_RESET}"
echo ""

# Helper functions
pass() {
    echo -e "${COLOR_GREEN}✓ PASS:${COLOR_RESET} $1"
    ((PASS_COUNT++))
}

fail() {
    echo -e "${COLOR_RED}✗ FAIL:${COLOR_RESET} $1"
    ((FAIL_COUNT++))
}

info() {
    echo -e "${COLOR_BLUE}ℹ INFO:${COLOR_RESET} $1"
}

warn() {
    echo -e "${COLOR_YELLOW}⚠ WARN:${COLOR_RESET} $1"
}

# Test 1: Check if all 3 API instances are running
echo -e "\n${COLOR_BLUE}[Test 1] Checking API Replicas...${COLOR_RESET}"
if docker ps | grep -q "urban-octo-tribble-api-1" && \
   docker ps | grep -q "urban-octo-tribble-api-2" && \
   docker ps | grep -q "urban-octo-tribble-api-3"; then
    pass "All 3 API instances are running"
else
    fail "Not all API instances are running"
fi

# Test 2: Check nginx is running
echo -e "\n${COLOR_BLUE}[Test 2] Checking Nginx Load Balancer...${COLOR_RESET}"
if docker ps | grep -q "urban-octo-tribble-nginx"; then
    pass "Nginx load balancer is running"
else
    fail "Nginx is not running"
fi

# Test 3: Check health endpoints through nginx
echo -e "\n${COLOR_BLUE}[Test 3] Testing Health Endpoints...${COLOR_RESET}"
if curl -s -f http://localhost/health/live > /dev/null; then
    pass "Liveness check responds through load balancer"
else
    fail "Liveness check failed"
fi

# Summary
echo ""
echo -e "${COLOR_BLUE}╔════════════════════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_BLUE}║  Test Results Summary                                      ║${COLOR_RESET}"
echo -e "${COLOR_BLUE}╚════════════════════════════════════════════════════════════╝${COLOR_RESET}"
echo ""
echo -e "${COLOR_GREEN}Passed: $PASS_COUNT${COLOR_RESET}"
echo -e "${COLOR_RED}Failed: $FAIL_COUNT${COLOR_RESET}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${COLOR_GREEN}🎉 All tests passed!${COLOR_RESET}"
    exit 0
else
    echo -e "${COLOR_RED}❌ Some tests failed.${COLOR_RESET}"
    exit 1
fi
