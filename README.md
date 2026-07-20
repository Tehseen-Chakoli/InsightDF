# InsightDF

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square)](https://groq.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-SQL-F9C74F?style=flat-square)](https://duckdb.org/)
[![Plotly](https://img.shields.io/badge/Plotly-Charts-3F4F75?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com/)

InsightDF is a modular Streamlit application for natural-language analytics on uploaded CSV and Excel datasets. It converts user questions into validated DuckDB SQL, executes them on the uploaded dataframe, and returns exact answers, result tables, and interactive charts.

## Technical Scope

- Single-table analytics over uploaded `.csv`, `.xlsx`, and `.xls` files
- Natural-language to SQL generation using Groq through LangChain
- Schema-aware prompting using sample rows, top values, and numeric summaries
- Read-only SQL validation before execution
- Query execution on in-memory DuckDB
- Automatic SQL repair when execution fails
- Plot recommendation and chart rendering with Plotly
- Short conversation memory for follow-up questions
- Caching for parsing, profiling, insights, and repeated analysis

## Architecture

```text
User Question
    ↓
Streamlit UI
    ↓
Dataset Upload + Caching
    ↓
Schema Profiling
    ↓
LLM Query Planning
    ↓
SQL Guard + SQL Repair
    ↓
DuckDB Execution
    ↓
Answer Formatting + Chart Recommendation
    ↓
Streamlit Output
```

## Current Features

### Data Understanding

- Dataset profiling with:
  - row and column counts
  - dtypes
  - sample values
  - top values
  - numeric summaries
  - sample rows
- Automatic dataset insights for missing values, numeric ranges, grouping columns, and duplicates

### Querying

- Natural-language question handling
- Exact scalar and tabular answers from uploaded data
- Short conversation memory for follow-up questions
- Generated SQL display
- SQL explanation display
- Automatic SQL correction loop on execution failure
- Read-only SQL validation against the uploaded `dataset` table

### Visualization

- Bar, line, and scatter charts
- Automatic chart recommendation from result shape
- Multi-view chart rendering for grouped outputs
- Plot normalization and repair before rendering

### Performance

- Cached file loading
- Cached dataset profiling
- Cached automatic insights
- Cached repeated analyses within the same dataset session

## Project Structure

```text
InsightDF/
├── app.py
├── requirements.txt
├── README.md
├── src/insightdf/
│   ├── analytics.py
│   ├── chart_recommender.py
│   ├── config.py
│   ├── data_loader.py
│   ├── errors.py
│   ├── insights.py
│   ├── llm.py
│   ├── plot_guard.py
│   ├── query_models.py
│   ├── question_guard.py
│   ├── schema.py
│   └── sql_guard.py
└── tests/
```

## Main Components

### `app.py`

- Streamlit entrypoint
- Handles upload, session state, query history, and rendering
- Shows answers, SQL, SQL explanation, tables, insights, and charts

### `data_loader.py`

- Loads CSV and Excel files into pandas
- Normalizes column names
- Caches parsed uploads

### `schema.py`

- Builds a compact dataset profile for prompting
- Extracts structural and statistical metadata from arbitrary datasets

### `llm.py`

- Sends structured prompts to Groq through LangChain
- Produces typed query plans
- Runs SQL repair prompting when execution errors occur

### `sql_guard.py`

- Enforces single-statement read-only SQL
- Blocks destructive commands
- Ensures queries target only the uploaded `dataset` table

### `analytics.py`

- Orchestrates planning, SQL validation, execution, repair, answer formatting, and chart generation

### `plot_guard.py`

- Repairs plot-breaking SQL patterns
- Normalizes result tables for charting
- Resolves x/y/series columns safely

### `chart_recommender.py`

- Recommends a clearer chart type from the result shape
- Helps separate trend-like, comparison, and numeric relationship outputs

### `insights.py`

- Generates lightweight automatic dataset insights

## Technical Learnings

### 1. Structured outputs are necessary

Natural-language analytics becomes much more reliable when the model is forced into a typed JSON schema and validated with Pydantic.

### 2. SQL generation is only one part of the system

The real reliability comes from combining:

- prompt design
- schema context
- SQL validation
- execution repair
- chart recommendation
- transparent UI output

### 3. Schema context improves generalization

Column names alone are not enough. Sample rows, top values, and numeric summaries give the model much better grounding on arbitrary datasets.

### 4. Visualization needs its own safety layer

A query can be logically valid and still produce a poor chart. Plot normalization and chart recommendation improved usability more than just adding more chart types.

### 5. Dataset-agnostic design requires removing hidden assumptions

Hardcoded domain-specific aliases and assumptions reduce generalization. The app becomes more reusable when it depends on the uploaded schema rather than fixed dataset rules.

### 6. Short memory is useful, long memory is risky

Conversation memory helps with follow-up questions, but it needs to stay intentionally limited to avoid contaminating self-contained questions with stale context.

### 7. Caching is important in Streamlit analytics apps

Caching parsing, profiling, insights, and repeated analysis noticeably improves responsiveness during iterative questioning.

## Tech Stack

- `streamlit`
- `pandas`
- `openpyxl`
- `duckdb`
- `plotly`
- `langchain`
- `langchain-groq`
- `pydantic`
- `python-dotenv`

## Current Limits

- Optimized for a single uploaded table
- No multi-table join planner yet
- Advanced chart families are still limited
- Accuracy still depends on dataset quality and model behavior
