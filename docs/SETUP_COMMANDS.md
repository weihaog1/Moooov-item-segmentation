# Quick Command Guide

This guide provides the essential commands for setting up and running the E-Commerce Item Segmentation System.

## 1. Create Python Virtual Environment

First, create and activate a Python virtual environment to manage project dependencies.

### Windows

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate
```

### Linux/Mac

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate
```

## 2. Install Dependencies

Once the virtual environment is activated, install the required Python packages.

```bash
# Install all requirements
pip install -r requirements.txt
```

## 3. Set Up Database

Using Docker (Recommended)

This is the easiest way to get the database and the API running together.

```bash
# Start MySQL and API containers in detached mode
docker-compose up -d

# View the API logs to monitor startup
docker-compose logs -f api

# When you're done, stop the containers
docker-compose down
```

## 4. Initialize the Database

After starting the services, you need to initialize the database to create the necessary tables.

### If using Docker

Run the initialization script inside the running `api` container.

```bash
# Run the initialization script
docker-compose exec api python scripts/init_db.py
```

### If running locally

If you are managing the database and application manually (not with Docker), run the script directly.

```bash
python scripts/init_db.py
```

This will create all necessary tables, such as `processing_cache`, `tag_mappings`, `brands`, and `product_terms`.

## 5. Run the Application (if not using Docker)

If you are not using `docker-compose up`, you can run the application directly with Uvicorn.

```bash
# Run the development server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## 6. Quick API Test

Once the application is running, you can test its key endpoints to ensure everything is working correctly.

### A. Check Health Endpoint

This endpoint verifies that the API is running and can connect to the database and other required services.

**Command:**

```bash
curl http://localhost:8000/api/v1/health
```

**Expected Success Response:**
A successful response indicates that all systems are operational.

```json
{
  "status": "healthy",
  "database": true,
  "deepseek_api": true,
  "details": {
    "database": "Connected to MySQL at mysql:3306",
    "deepseek": "API key configured"
  }
}
```

---

### B. Explore with Interactive API Docs

For more detailed and interactive testing, use the auto-generated Swagger UI documentation. This interface allows you to test all endpoints directly from your browser.

**URL:** [http://localhost:8000/docs](http://localhost:8000/docs)

Here, you can:

- View all available API endpoints.
- See detailed information about request parameters and response models.
- Execute API calls and see live results.
