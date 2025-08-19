#!/usr/bin/env python3
"""
Test script to verify Market Analyst profile functionality
"""

import subprocess
import sys
import json


def run_janito_command(cmd):
    """Run janito command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def test_market_flag():
    """Test --market flag functionality"""
    print("Testing --market flag...")

    # Test basic market analysis
    cmd = (
        "janito --market --read 'List 2 NASDAQ stocks with bearish technical patterns'"
    )
    returncode, stdout, stderr = run_janito_command(cmd)

    if returncode == 0:
        print("✅ --market flag works correctly")

        # Check if response contains technical analysis elements
        technical_indicators = ["RSI", "MACD", "support", "resistance", "pattern"]
        found_indicators = [
            indicator
            for indicator in technical_indicators
            if indicator.lower() in stdout.lower()
        ]

        if found_indicators:
            print(f"✅ Technical analysis detected: {', '.join(found_indicators)}")
        else:
            print("⚠️ No technical indicators found in response")

        return True
    else:
        print(f"❌ --market flag failed: {stderr}")
        return False


def test_profile_explicit():
    """Test explicit profile specification"""
    print("\nTesting explicit Market Analyst profile...")

    cmd = 'janito --profile "Market Analyst" --read "Analyze TSLA stock"'
    returncode, stdout, stderr = run_janito_command(cmd)

    if returncode == 0:
        print("✅ Explicit profile works correctly")
        return True
    else:
        print(f"❌ Explicit profile failed: {stderr}")
        return False


def test_no_canned_response():
    """Test that we don't get canned "no real-time data" response"""
    print("\nTesting for canned response avoidance...")

    cmd = "janito --market --read 'What stocks should I consider selling?'"
    returncode, stdout, stderr = run_janito_command(cmd)

    if returncode == 0:
        canned_phrases = [
            "I don't have access to real-time market data",
            "I can't provide real-time trading recommendations",
            "I don't have access to current stock prices",
        ]

        found_canned = [
            phrase for phrase in canned_phrases if phrase.lower() in stdout.lower()
        ]

        if found_canned:
            print(f"❌ Found canned response: {found_canned[0]}")
            return False
        else:
            print("✅ No canned responses detected")
            return True
    else:
        print(f"❌ Command failed: {stderr}")
        return False


def main():
    """Run all tests"""
    print("🧪 Testing Market Analyst Profile Functionality")
    print("=" * 50)

    tests = [test_market_flag, test_profile_explicit, test_no_canned_response]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Market Analyst profile is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
