"""Test script for all API endpoints."""

import requests
import time
import json

BASE_URL = "http://localhost:8000/api/v1"

def print_response(title, response):
    """Print formatted response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")
    print()

def test_sync_tokenization():
    """Test synchronous tokenization."""
    print("\n[TEST] POST /tokenize (Synchronous)")
    response = requests.post(
        f"{BASE_URL}/tokenize",
        json={
            "keyword": "Apple iPhone 15 Pro black",
            "language": "en"
        }
    )
    print_response("Sync Tokenization", response)
    return response.status_code == 200

def test_async_tokenization():
    """Test asynchronous tokenization."""
    print("\n[TEST] POST /tokenize/async (Submit Async Job)")

    # Submit async job
    response = requests.post(
        f"{BASE_URL}/tokenize/async",
        json={
            "keyword": "Nike Air Max 90 white running shoes",
            "language": "en"
        }
    )
    print_response("Submit Async Job", response)

    if response.status_code != 200:
        return False

    job_id = response.json()["job_id"]
    print(f"[OK] Job submitted with ID: {job_id}")

    # Poll for result
    print(f"\n[TEST] GET /tokenize/async/{job_id} (Poll for Result)")
    max_retries = 10
    for i in range(max_retries):
        time.sleep(1)
        result_response = requests.get(f"{BASE_URL}/tokenize/async/{job_id}")
        status = result_response.json()["status"]
        print(f"  Attempt {i+1}/{max_retries}: Status = {status}")

        if status == "completed":
            print_response("Async Job Result", result_response)
            return True
        elif status == "failed":
            print_response("Async Job Failed", result_response)
            return False

    print("[FAIL] Job did not complete in time")
    return False

def test_batch_async():
    """Test batch async processing."""
    print("\n[TEST] POST /tokenize/batch/async (Submit Batch Job)")

    # Submit batch job
    response = requests.post(
        f"{BASE_URL}/tokenize/batch/async",
        json={
            "keywords": [
                {"keyword": "Apple iPhone 15", "language": "en"},
                {"keyword": "Samsung Galaxy S24", "language": "en"},
                {"keyword": "Nike Air Jordan", "language": "en"}
            ],
            "use_llm": False  # Use fast dictionary workers
        }
    )
    print_response("Submit Batch Job", response)

    if response.status_code != 200:
        return False

    batch_id = response.json()["job_id"]
    print(f"[OK] Batch submitted with ID: {batch_id}")

    # Poll for batch results
    print(f"\n[TEST] GET /tokenize/batch/async/{batch_id} (Poll for Batch Results)")
    max_retries = 15
    for i in range(max_retries):
        time.sleep(2)
        result_response = requests.get(f"{BASE_URL}/tokenize/batch/async/{batch_id}")
        status = result_response.json()["status"]
        print(f"  Attempt {i+1}/{max_retries}: Status = {status}")

        if status == "completed":
            print_response("Batch Job Results", result_response)
            results = result_response.json()["result"]
            if results:
                print(f"[OK] Processed {len(results)} keywords")
            return True
        elif status == "failed":
            print_response("Batch Job Failed", result_response)
            return False

    print("[FAIL] Batch job did not complete in time")
    return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("API ENDPOINT TEST SUITE")
    print("="*60)

    results = {
        "Sync Tokenization": test_sync_tokenization(),
        "Async Tokenization": test_async_tokenization(),
        "Batch Async Processing": test_batch_async()
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("="*60 + "\n")

    return all_passed

if __name__ == "__main__":
    main()
