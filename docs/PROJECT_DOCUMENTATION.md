# E-Commerce Item Segmentation System: Project Documentation

## 1. Project Summary

The E-Commerce Item Segmentation System is an AI-powered service designed to analyze and understand multilingual e-commerce product titles. It breaks down complex product names into meaningful keywords and assigns them to specific, predefined categories. 

### Key Features

The system's core strength lies in its AI-powered intelligence, which leverages Large Language Models (LLMs) for highly accurate, context-aware analysis of product titles across multiple languages, including Chinese, English, and Spanish. It deconstructs complex titles into meaningful keywords and classifies them into eight distinct semantic categories—such as Brand, Product, and Color—transforming unstructured text into valuable, structured data.

To ensure both performance and cost-effectiveness, the system is engineered with a smart, two-tier caching architecture that drastically reduces latency and minimizes expensive LLM API calls. Furthermore, it features a self-improving dictionary learning mechanism that automatically identifies and stores new patterns from high-confidence results. This allows the system to grow more intelligent and accurate over time, continuously enhancing its own capabilities with each transaction.

## 2. Core Functionality: The Segmentation Process

The primary function of the system is to take a raw product title (e.g., "Nike Air Max 90 black running shoes") and return a structured output. This is achieved through a sophisticated pipeline:

1. **Language Detection:** The system first automatically detects the language of the input title.
2. **AI-Powered Analysis:** The title is sent to an LLM, which performs both tokenization (breaking the title into keywords) and semantic tagging (assigning categories) in a single, efficient step.
3. **Dictionary Enrichment:** The AI's output is cross-referenced with an internal dictionary stored in a MySQL database. This step enhances the results by ensuring consistency and leveraging previously learned knowledge.
4. **Pattern Learning:** For results where the AI has a high degree of confidence, the system automatically learns the identified patterns and stores them in the database. This allows for faster and more accurate processing of similar titles in the future.
5. **Caching:** The final result is cached. If the same product title is processed again, the system can return the cached result instantly, bypassing the need for repeated AI analysis and reducing latency.

## 3. System Architecture

The system is built with a modern, scalable architecture designed for performance and reliability.

* **FastAPI Application:** The core of the system is a web service built with FastAPI, a high-performance Python framework. This service exposes the API endpoints that allow other applications to interact with the segmentation engine.
* **Database:** A MySQL database serves as the persistent storage layer. It is used for:
  * Caching processed results for long-term storage.
  * Storing the dictionary of learned patterns and keywords.
* **Two-Tier Cache:**
  1. **In-Memory Cache (LRU):** Provides ultra-fast access to the most recently processed items.
  2. **Database Cache:** A more persistent cache for less frequently accessed items.
* **Containerization:** The entire application, including the database, is containerized using Docker. This ensures a consistent and reproducible environment for both development and production, simplifying deployment and scaling.

## 4. Database Schema

The MySQL database is central to the system's learning and caching capabilities. The schema is designed to store learned knowledge, cache results, and manage semantic dictionaries.

### Core Tables

*   **`processing_cache`**: This table acts as the second layer of the cache (after the in-memory cache). It stores the full JSON response for processed keywords, using a hash of the keyword as the key. This significantly reduces API calls for repeated requests.
*   **`tag_mappings`**: This is the heart of the system's learning mechanism. It stores patterns and terms learned from high-confidence AI results. Each entry maps a normalized term to a specific `tag_type` (e.g., "brand_term"), along with a confidence score and occurrence count.

### Dictionary Tables

A set of tables serves as a dictionary for different semantic categories. These tables can be pre-seeded with known terms and are expanded by the system's learning process.

*   `brands`
*   `product_terms`
*   `color_terms`
*   `audience_terms`
*   `scenario_terms`
*   `selling_point_terms`
*   `attribute_terms`

## 4. Technology Stack

The project utilizes a selection of modern and robust technologies:

* **Backend:** Python, FastAPI
* **Database:** MySQL
* **AI / Machine Learning:**
  * DeepSeek (or other configurable LLMs)
  * spaCy (for NLP tasks and pattern matching)
  * Langdetect (for language detection)
* **Deployment:** Docker, Docker Compose
* **Testing:** Pytest

## 5. Project Structure Overview

The codebase is organized into a modular and logical structure:

```
app/
├── api/            # Defines the API endpoints (e.g., /tokenize, /health).
├── core/           # Handles application-level configuration and settings.
├── db/             # Manages all database interactions, including connections and queries.
├── models/         # Contains the data models (schemas) that define the structure of API requests and responses.
├── services/       # Houses the core business logic, including the AI processing, caching, and pattern learning services.
└── utils/          # Provides utility functions used across the application.
```

## 6. API Usage Highlights

The system exposes a simple yet powerful REST API for easy integration.

* **`/tokenize` Endpoint:** This is the main endpoint for processing a single product title. It accepts a keyword and returns the full structured analysis.
* **`/tokenize/batch` Endpoint:** For efficiency, this endpoint allows for processing multiple keywords in a single request.
* **`/health` Endpoint:** Provides a health check of the system, including the status of the database connection and AI service configuration.
* **`/stats` Endpoint:** Returns operational statistics, such as cache performance and the number of learned patterns.

## 7. API Usage Example

This section provides a practical example of how to use the core `/tokenize` endpoint.

### Endpoint: `POST /api/v1/tokenize`

This endpoint tokenizes and tags a single product title. It accepts a JSON body with the keyword and several optional parameters to control its behavior.

### Sample Request

Here is an example of a request to process a complex product title.

```json
{
  "keyword": "W-KING Bluetooth Speaker Loud, 120W Max Portable Speakers Bluetooth Wireless, IPX6 Waterproof Party Large Speaker Outdoor Boombox Subwoofer*2, 70W Triple Passive Radiator-42H Deep Bass, AUX, EQ",
  "language": "en",
  "use_cache": true,
  "learn_patterns": false,
  "use_spacy": true
}
```

### Sample Response

The API returns a detailed JSON object containing the original keyword, the detected language, the list of extracted tokens, and the semantic tags for each token.

```json
{
  "original_keyword": "W-KING Bluetooth Speaker Loud, 120W Max Portable Speakers Bluetooth Wireless, IPX6 Waterproof Party Large Speaker Outdoor Boombox Subwoofer*2, 70W Triple Passive Radiator-42H Deep Bass, AUX, EQ",
  "language": "en",
  "tokens": [
    "W-KING",
    "Bluetooth Speaker",
    "Loud",
    "120W Max",
    "Portable Speakers",
    "Bluetooth Wireless",
    "IPX6 Waterproof",
    "Party Large Speaker",
    "Outdoor Boombox",
    "Subwoofer*2",
    "70W Triple Passive Radiator",
    "42H Deep Bass",
    "AUX",
    "EQ"
  ],
  "tagged_tokens": [
    {
      "token": "W-KING",
      "tags": ["brand_term"],
      "confidence": 0.95
    },
    {
      "token": "Bluetooth Speaker",
      "tags": ["product_term"],
      "confidence": 0.9
    }
  ],
  "tag_summary": {
    "brand_term": ["W-KING"],
    "product_term": ["Bluetooth Speaker"]
  },
  "processing_time_ms": 250.0,
  "cache_hit": false,
  "pattern_matched": false
}
```
*(Note: The `tagged_tokens` and `tag_summary` in the example above are illustrative. The actual response for the given keyword would be more detailed.)*

## 8. API Reference

The E-Commerce Item Segmentation API provides a set of endpoints for processing product titles and monitoring the system's health.

---

### **Tokenization Endpoints**

These endpoints are the core of the service, providing access to the AI-powered tokenization and semantic tagging engine.

#### `POST /api/v1/tokenize`

Processes a single product title.

**Description:**
This endpoint takes a single keyword string, detects its language (if not provided), and returns a detailed breakdown of its components, including tokens, semantic tags, and confidence scores.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `keyword` | string | Yes | - | The product title or keyword string to be processed. |
| `language` | string | No | `null` | The two-letter language code (e.g., "en", "zh"). If omitted, the system will automatically detect the language. |
| `use_cache` | boolean | No | `true` | If `true`, the system will first check for a cached result before processing the keyword. |
| `learn_patterns` | boolean | No | `true` | If `true`, the system will learn new patterns from high-confidence results to improve future performance. |
| `use_spacy` | boolean | No | `false` | If `true`, the system may use a faster spaCy-based tokenization method if a matching pattern is found, potentially skipping the LLM call. |

**Example Request:**
```json
{
  "keyword": "Apple iPhone 15 Pro 256GB black",
  "language": "en"
}
```

---

#### `POST /api/v1/tokenize/batch`

Processes multiple product titles in a single request.

**Description:**
This endpoint is designed for efficiency, allowing you to process up to 100 keywords in a single API call. It processes the keywords concurrently to reduce overall processing time.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `keywords` | array[string] | Yes | - | A list of up to 100 product titles or keyword strings. |
| `language` | string | No | `null` | A single language code to apply to all keywords in the batch. If omitted, the language will be auto-detected for each keyword individually. |
| `use_cache` | boolean | No | `true` | Applies the caching logic to all keywords in the batch. |
| `learn_patterns` | boolean | No | `true` | Applies the pattern learning logic to all keywords in the batch. |
| `use_spacy` | boolean | No | `false` | Applies the spaCy-based tokenization logic to all keywords in the batch. |

**Example Request:**
```json
{
  "keywords": [
    "Apple iPhone 15 Pro",
    "Nike Air Max 90"
  ]
}
```

---

### **Monitoring Endpoints**

These endpoints provide visibility into the health and status of the API.

#### `GET /api/v1/health`

Provides a health check of the system.

**Description:**
This endpoint checks the status of the API, its connection to the database, and the configuration of the underlying AI service. It's a vital tool for monitoring the system's operational status.

**Input Parameters:** None.

---

#### `GET /api/v1/stats`

Retrieves operational statistics.

**Description:**
This endpoint returns statistics about the system's performance, including cache hit/miss ratios and counts of learned dictionary patterns.

**Input Parameters:** None.