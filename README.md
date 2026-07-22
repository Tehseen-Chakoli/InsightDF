# InsightDF

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-In--Memory%20SQL-F7C948?style=for-the-badge)](https://duckdb.org/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Orchestration-1C7C54?style=for-the-badge)](https://www.langchain.com/)
[![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=for-the-badge)](https://groq.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-Structured%20Models-E92063?style=for-the-badge)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Tests-21%20Passing-2EA44F?style=for-the-badge)](#testing)

InsightDF is a Streamlit-based analytical tool for asking natural-language questions over uploaded tabular datasets. It accepts CSV and Excel files, profiles the schema, generates guarded DuckDB SQL, executes the query on the uploaded dataframe, and returns exact answers, tables, and interactive charts.

The project is designed around one idea: analytics tools should stay flexible across very different datasets without becoming careless. That is why the app combines schema-aware prompting, SQL validation, repair loops, chart normalization, and short-lived query memory instead of relying on plain text-to-SQL alone.

## Highlights

![Single Table](https://img.shields.io/badge/Scope-Single%20Uploaded%20Dataset-0A66C2?style=flat-square)
![Safe SQL](https://img.shields.io/badge/Safety-Read--Only%20SQL%20Guard-C0392B?style=flat-square)
![Schema Aware](https://img.shields.io/badge/Prompting-Schema%20Aware-16A085?style=flat-square)
![Auto Repair](https://img.shields.io/badge/Execution-Auto%20SQL%20Repair-F39C12?style=flat-square)
![Charting](https://img.shields.io/badge/Charts-Bar%20%7C%20Line%20%7C%20Scatter-7D3C98?style=flat-square)
![Caching](https://img.shields.io/badge/Performance-Streamlit%20Caching-34495E?style=flat-square)

- Upload `.csv`, `.xlsx`, and `.xls` files directly in the UI.
- Build a compact dataset profile with column stats, sample values, top values, numeric summaries, and sample rows.
- Convert natural-language analytical questions into structured query plans.
- Validate generated SQL so only safe read-only queries against the uploaded `dataset` table are executed.
- Retry failed queries through a targeted SQL repair loop.
- Recommend clearer chart types from the returned result shape.
- Preserve a short query history for follow-up analysis without letting long context pollute new questions.

## What The App Does

```text
User Uploads Dataset
        |
        v
Column Normalization + Cached Load
        |
        v
Schema Profile + Deterministic Insights
        |
        v
LLM Query Plan (typed JSON)
        |
        v
SQL Guard + Plot Repair + Execution Repair
        |
        v
DuckDB Execution on in-memory table: dataset
        |
        v
Answer Formatting + Chart Recommendation + Streamlit Rendering
```

## Core Capabilities

### 1. Dataset-Agnostic Analysis

InsightDF is built for multiple datasets, not one hardcoded business case. The app does not assume fixed columns, domain-specific aliases, or a predefined schema. It works from the uploaded file each time and reconstructs context from the profile.

### 2. Safe Query Execution

Generated SQL is validated before execution. The guard blocks destructive statements, strips misleading comments and literals during checks, and requires a real `FROM` or `JOIN` reference to the uploaded `dataset` table.

### 3. Reliable Analytical Flow

The app does more than generate SQL:

- it profiles the dataset first
- it plans the query through structured output
- it validates the SQL
- it retries failed SQL with a repair prompt
- it formats the result for direct use
- it normalizes chart inputs before plotting

### 4. Practical Visualization

Chart generation is result-driven. If a chart question produces usable grouped output, InsightDF recommends a chart type and can produce both a primary view and a faceted breakdown when the result includes extra categorical dimensions.

## Project Structure

```text
InsightDF/
├── app.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── data/
├── src/
│   ├── __init__.py
│   └── insightdf/
│       ├── __init__.py
│       ├── analytics.py
│       ├── chart_recommender.py
│       ├── config.py
│       ├── data_loader.py
│       ├── errors.py
│       ├── insights.py
│       ├── llm.py
│       ├── plot_guard.py
│       ├── query_models.py
│       ├── question_guard.py
│       ├── schema.py
│       └── sql_guard.py
└── tests/
    ├── conftest.py
    ├── test_analytics_sql_repair.py
    ├── test_chart_recommender.py
    ├── test_insights.py
    ├── test_llm_parsing.py
    ├── test_question_guard.py
    └── test_sql_guard.py
```

## Key Modules

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit UI, upload flow, session state, result rendering |
| `data_loader.py` | Cached file parsing and stable column-name normalization |
| `schema.py` | Dataset profiling for prompt context |
| `insights.py` | Deterministic summary insights from the uploaded data |
| `llm.py` | Query-plan generation and SQL repair prompting |
| `sql_guard.py` | Read-only SQL validation and table-reference enforcement |
| `analytics.py` | End-to-end orchestration from question to answer/chart |
| `plot_guard.py` | Chart-safe normalization of SQL results |
| `chart_recommender.py` | Result-shape based chart selection |
| `question_guard.py` | Dataset/question validation before analysis |

## Important Implementation Snippets

### Stable Column Normalization

This keeps uploaded datasets usable even when files contain duplicate headers, blank headers, or spreadsheet-generated column name issues.

```python
def _normalize_column_names(columns) -> list[str]:
    """Create stable, non-empty, unique column names across arbitrary uploads."""
    normalized_columns: list[str] = []
    counts: dict[str, int] = {}

    for index, raw_column in enumerate(columns, start=1):
        cleaned_name = str(raw_column).strip()
        if not cleaned_name or cleaned_name.lower() == "nan":
            cleaned_name = f"column_{index}"

        counts[cleaned_name] = counts.get(cleaned_name, 0) + 1
        if counts[cleaned_name] > 1:
            cleaned_name = f"{cleaned_name}__{counts[cleaned_name]}"

        normalized_columns.append(cleaned_name)

    return normalized_columns
```

### Read-Only SQL Guard

This is one of the most important safety pieces in the project. It is deliberately strict because the app is designed to run LLM-generated SQL on arbitrary user uploads.

```python
def validate_read_only_sql(sql: str) -> str:
    """Allow only single-statement read-only SQL."""
    normalized_sql = sql.strip()

    if normalized_sql.endswith(";"):
        normalized_sql = normalized_sql[:-1].rstrip()

    if not normalized_sql:
        raise ValueError("The generated SQL is empty.")

    sql_without_comments = _strip_sql_comments(normalized_sql)
    sql_for_validation = _strip_sql_string_literals(sql_without_comments)
    upper_sql = sql_for_validation.upper()

    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        raise ValueError("Only SELECT queries are allowed.")

    if ";" in sql_for_validation:
        raise ValueError("The generated SQL contains multiple statements.")

    if not _references_dataset_table(sql_for_validation):
        raise ValueError("The generated SQL must query the uploaded dataset table.")

    return normalized_sql
```

### Analysis Orchestration

The main analytical path is intentionally thin and readable: guard the question, generate a plan, execute safely, then build the final answer and optional visual output.

```python
def run_analysis(
    dataframe: pd.DataFrame,
    profile: DatasetProfile,
    user_question: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> AnalysisOutput:
    """Plan the analysis, execute it against DuckDB, and format the response."""
    prepared_question = prepare_question_for_analysis(
        profile=profile,
        dataframe=dataframe,
        user_question=user_question,
    )

    query_plan = generate_query_plan(
        profile=profile,
        user_question=prepared_question.resolved_question,
        conversation_history=conversation_history,
    )

    connection = duckdb.connect(database=":memory:")
    connection.register("dataset", dataframe)
```

## Current Tech Stack

- `streamlit`
- `pandas`
- `duckdb`
- `plotly`
- `langchain`
- `langchain-groq`
- `pydantic`
- `openpyxl`
- `python-dotenv`

## Local Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_api_key_here
INSIGHTDF_LLM_PROVIDER=groq
INSIGHTDF_GROQ_MODEL=llama-3.1-8b-instant
```

### 4. Run the app

```bash
streamlit run app.py
```

## Testing

The codebase includes focused tests around guardrails, parsing, chart recommendation, insights, and SQL repair behavior.

```bash
pytest -q tests
```

Current local status:

- `21` tests passing
- SQL guard behavior covered
- chart recommendation behavior covered
- LLM response parsing covered
- question validation covered

## Design Notes

### Why DuckDB?

DuckDB makes the analytical path simple and fast for single uploaded datasets. Registering the dataframe as `dataset` gives the app deterministic SQL execution without standing up a separate database service.

### Why Structured Query Plans?

The LLM does not return freeform prose for the main analysis step. It returns a typed plan that includes:

- analysis type
- SQL
- reasoning
- answer behavior
- chart metadata

That keeps the orchestration layer much easier to validate and debug.

### Why Short Conversation Memory?

InsightDF keeps only a short recent analysis history so follow-up questions like "compare that with the previous result" stay useful without making every new question dependent on long chat context.

## Current Constraints

- Optimized for one uploaded table at a time
- No multi-table join planner yet
- Visualization families are intentionally focused rather than broad
- Answer quality still depends on the uploaded data quality and LLM behavior
- The app is strongest for analysis questions grounded in actual dataset columns and values

## Roadmap Ideas

- Multi-table support with controlled join planning
- Better date/time understanding for uploaded business reports
- More chart families for distributions and correlations
- Stronger ambiguity handling when multiple columns partially match a user question
- Exportable analysis sessions and shareable results

## Summary

InsightDF is not just a text-to-SQL demo. It is a guarded analytical workflow for real uploaded datasets, with schema-aware prompting, SQL safety, repair loops, deterministic execution, and chart-aware result rendering. The codebase is intentionally modular so each reliability layer can evolve independently as the tool grows.
