# Enterprise KnowledgeOps AI

Enterprise-grade KnowledgeOps API built with FastAPI and Snowflake Cortex for:
- PDF ingestion
- semantic retrieval over document chunks
- grounded answer generation
- query telemetry logging

## What This Project Does

This service accepts PDF documents, stores metadata in Snowflake, parses and chunks document text with Snowflake AI functions, and answers user questions by:
1. retrieving relevant chunks from a Snowflake Cortex Search Service
2. building a context-grounded prompt
3. generating a final answer with a Cortex model
4. logging query execution metrics into `QUERY_LOG`

## Architecture

Request flow for upload:
1. Client uploads a PDF to `POST /api/v1/documents/upload`
2. API validates and normalizes the filename
3. File is uploaded to Snowflake stage (`PUT`)
4. Metadata is inserted into `DOCUMENTS`
5. `AI_PARSE_DOCUMENT` + `SPLIT_TEXT_RECURSIVE_CHARACTER` create chunks in `DOCUMENT_CHUNKS`
6. Document status is updated to `PARSED`

Request flow for query:
1. Client sends question to `POST /api/v1/query`
2. API calls `SNOWFLAKE.CORTEX.SEARCH_PREVIEW` on the configured search service
3. Prompt is built from top-k chunks
4. API calls `AI_COMPLETE` (fallback: `SNOWFLAKE.CORTEX.COMPLETE`)
5. Query telemetry is inserted into `QUERY_LOG`

## Tech Stack

- Python 3.10+
- FastAPI
- Snowflake Connector for Python
- Snowflake Cortex (`AI_PARSE_DOCUMENT`, `SEARCH_PREVIEW`, `AI_COMPLETE`/`COMPLETE`)
- Pytest

## Project Structure

```text
app/
  api/v1/routes/           # API routes
  api/v1/schemas/          # Request/response models
  services/                # Business logic
  repositories/            # Snowflake queries and commands
  core/                    # Config, errors, logging, connection manager
  utils/                   # File and prompt helpers
sql/
  00_context_and_role.sql
  01_database_and_schema.sql
  02_stage.sql
  03_document_tables.sql
  04_ingest_procedure.sql
  05_cortex_search_service.sql
  06_query_log.sql
tests/
run.py
```

## Prerequisites

- Snowflake account with Cortex features enabled
- Role with permission to create roles/warehouse/database/schema/stage/tables/procedures/search service (for setup phase)
- Python environment with dependencies from `requirements.txt`

## Environment Variables

Create a `.env` file in project root:

```env
APP_NAME=Enterprise KnowledgeOps AI
APP_VERSION=1.0.0
API_PREFIX=/api/v1
LOG_LEVEL=INFO

SNOWFLAKE_ACCOUNT=<your_account>
SNOWFLAKE_USER=<your_user>
SNOWFLAKE_PASSWORD=<your_password>
SNOWFLAKE_ROLE=KNOWLEDGEOPS_APP_ROLE
SNOWFLAKE_WAREHOUSE=KNOWLEDGEOPS_WH
SNOWFLAKE_DATABASE=KNOWLEDGEOPS_AI
SNOWFLAKE_SCHEMA=DOCS
SNOWFLAKE_STAGE=DOCS_STAGE
SNOWFLAKE_SEARCH_SERVICE=DOCS_SEARCH_SERVICE
SNOWFLAKE_OCSP_FAIL_OPEN=true
SNOWFLAKE_DISABLE_OCSP_CHECKS=false
SNOWFLAKE_CONNECT_RETRIES=4
SNOWFLAKE_CONNECT_BACKOFF_SECONDS=2
SNOWFLAKE_LOGIN_TIMEOUT_SECONDS=30
SNOWFLAKE_NETWORK_TIMEOUT_SECONDS=120

CORTEX_MODEL=claude-3-5-sonnet
QUERY_RESULT_LIMIT=5
```

Minimum required variables for boot are:
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`

## Setup

### 1. Install dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Execute Snowflake SQL setup scripts

Run scripts in this order:
1. `sql/00_context_and_role.sql`
2. `sql/01_database_and_schema.sql`
3. `sql/02_stage.sql`
4. `sql/03_document_tables.sql`
5. `sql/04_ingest_procedure.sql`
6. `sql/05_cortex_search_service.sql`
7. `sql/06_query_log.sql`

## Run The API

Option 1:

```bash
python run.py
```

Option 2:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Swagger UI is available at:
- `http://localhost:8000/docs`

## API Reference

Base URL:
- `http://localhost:8000`

### 1) Health Check

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

### 2) Upload Document

`POST /api/v1/documents/upload`

Content type:
- `multipart/form-data`

Form fields:
- `file`: PDF file (required)

Validation:
- only `.pdf` extension
- MIME type must be `application/pdf` when provided
- empty files are rejected

Success response:

```json
{
  "success": true,
  "message": "Document uploaded and parsed successfully.",
  "data": {
    "doc_id": "8f39ad98-cad8-4abc-9ae5-98ad2b996f0f",
    "file_name": "employee_policy.pdf",
    "stage_path": "@KNOWLEDGEOPS_AI.DOCS.DOCS_STAGE/8f39ad98-cad8-4abc-9ae5-98ad2b996f0f_employee_policy.pdf",
    "status": "PARSED",
    "chunk_count": 42
  }
}
```

Example curl:

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@C:/path/to/document.pdf"
```

### 3) Query Documents

`POST /api/v1/query`

Request body:

```json
{
  "question": "What is the SLA for incident response?",
  "limit": 5
}
```

Field rules:
- `question`: required, min length 1
- `limit`: optional, default `5`, min `1`, max `20`

Success response:

```json
{
  "success": true,
  "message": "Answer generated successfully.",
  "data": {
    "question": "What is the SLA for incident response?",
    "answer": "The incident response SLA is 30 minutes for P1 incidents [1].",
    "model": "claude-3-5-sonnet",
    "chunks": [
      {
        "doc_id": "8f39ad98-cad8-4abc-9ae5-98ad2b996f0f",
        "page_number": 2,
        "chunk_text": "P1 incidents must be acknowledged within 30 minutes..."
      }
    ]
  }
}
```

Example curl:

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"Summarize the leave policy\",\"limit\":5}"
```

### Error Response Format

Handled route errors return:

```json
{
  "success": false,
  "message": "Error description"
}
```

Examples:
- invalid request input: HTTP `400`
- Snowflake/processing failures: HTTP `500`
- unexpected errors: HTTP `500` with message `Internal server error.`

## Snowflake Objects Created

- Role: `KNOWLEDGEOPS_APP_ROLE`
- Warehouse: `KNOWLEDGEOPS_WH`
- Database/Schema: `KNOWLEDGEOPS_AI.DOCS`
- Stage: `DOCS_STAGE`
- Tables:
  - `DOCUMENTS`
  - `DOCUMENT_CHUNKS`
  - `QUERY_LOG`
- Procedure: `SP_INGEST_DOCS_FROM_STAGE`
- Cortex Search Service: `DOCS_SEARCH_SERVICE`

`QUERY_LOG` captures:
- `QUERY_ID`, `USER_ID`, `QUERY_TEXT`, `TOP_K`
- `RESPONSE_TIME_MS`, `SEARCH_RESULTS_COUNT`
- `MODEL_USED`, `SUCCESS`, `ERROR_MESSAGE`, `CREATED_AT`

## Testing

Run tests:

```bash
python -m pytest -q
```
