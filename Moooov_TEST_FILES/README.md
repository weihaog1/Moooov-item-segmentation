# Comprehensive Keyword Testing Script

This directory contains a powerful Python script (`test_all.py`) for batch testing and analyzing the performance of the E-Commerce Item Segmentation API.

## What it Does

The `test_all.py` script is designed to:
1.  **Load a large dataset** of keywords from a CSV file (`keywords.csv`).
2.  **Test each keyword** against the `/api/v1/tokenize` endpoint in concurrent batches for efficiency.
3.  **Analyze the results** to generate detailed statistics on performance, success rates, and AI model behavior.
4.  **Generate comprehensive reports**, including a detailed JSON output and a summary of any failed requests.

## How to Use

You can run the script from your terminal. It offers several command-line options to customize the test run.

### Basic Usage

```bash
python Moooov_TEST_FILES/test_all.py
```

### Common Options

*   `--limit N`: Test only the first `N` keywords from the CSV.
    ```bash
    python Moooov_TEST_FILES/test_all.py --limit 100
    ```
*   `--batch-size N`: Set the number of concurrent API calls per batch (default is 10).
    ```bash
    python Moooov_TEST_FILES/test_all.py --batch-size 5
    ```
*   `--no-cache`: Force the API to re-process keywords instead of using cached results.
    ```bash
    python Moooov_TEST_FILES/test_all.py --no-cache
    ```
*   `--output <filename>`: Specify a different name for the JSON results file.
    ```bash
    python Moooov_TEST_FILES/test_all.py --output my_results.json
    ```

## Input File

The script expects a CSV file named `keywords.csv` in the same directory. The CSV should have at least a `search_term` column. An optional `language` column can be included to specify the language for each term.

**Example `keywords.csv`:**
```csv
search_term,language
"Apple iPhone 15 Pro 256GB black",en
"zapatillas de correr para hombre",es
"华为 Mate 60 Pro",zh
```

## Output Files

After running, the script generates two files:

1.  **`test_results.json`**: A detailed JSON file containing a summary of the test run, performance statistics (like average processing time and cache hit rate), and the full request/response data for every keyword.
2.  **`failed_keywords.csv`**: A simple CSV file listing all the keywords that resulted in an error, along with the HTTP status code and error message, for easy debugging.
