# InsightDF

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM-Groq-F55036?style=for-the-badge)](https://groq.com/)
[![DuckDB](https://img.shields.io/badge/SQL-DuckDB-F9C74F?style=for-the-badge)](https://duckdb.org/)
[![Plotly](https://img.shields.io/badge/Charts-Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)

InsightDF is a modular Streamlit application for natural-language analytics on uploaded datasets. Users can upload a CSV or Excel file, ask analytical questions in plain English, and get exact answers, SQL-backed tables, and readable visualizations generated directly from the uploaded data.

## Highlights

- Upload `.csv`, `.xlsx`, or `.xls` files
- Ask analytical questions in natural language
- Generate safe read-only DuckDB SQL
- Return exact scalar answers and result tables
- Build chart-ready visualizations with automatic chart recommendation
- Repair failed SQL automatically when execution errors occur
- Keep short conversation memory for follow-up questions
- Cache uploaded data, profiles, and repeated analyses for better performance
- Show automatic dataset insights after upload
- Keep generated SQL and SQL reasoning visible for transparency

## How It Works

1. The user uploads a dataset in CSV or Excel format.
2. InsightDF loads the file into pandas and profiles the schema.
3. The dataset profile is sent to a Groq model through LangChain.
4. The model returns a structured query plan with SQL and chart metadata.
5. SQL is sanitized and validated so only read-only queries can run.
6. Queries execute against the uploaded dataframe through DuckDB.
7. If execution fails, InsightDF attempts an automatic SQL repair loop.
8. Results are shown as:
   - direct answers
   - result tables
   - recommended charts
   - generated SQL
   - SQL explanation

## Current Feature Set

### Data Understanding

- Dataset profiling with:
  - row and column counts
  - column dtypes
  - sample values
  - top values
  - numeric summaries
  - sample rows
- Automatic dataset insights such as missing values, useful grouping columns, numeric ranges, and duplicate-row checks

### Querying

- Natural-language question handling
- Exact numerical outputs from uploaded data
- Short conversation memory for follow-up questions
- SQL explanation mode
- Automatic SQL correction when execution fails
- Safe single-table read-only SQL validation

### Visualization

- Bar, line, and scatter charts
- Automatic chart recommendation based on result shape
- Multi-view chart rendering for richer grouped outputs
- Better labels, titles, and color handling for readability

### Performance

- Cached file loading
- Cached dataset profiling
- Cached dataset insights
- Cached repeated question results within the same dataset session

## Project Structure

```text
InsightDF/
├── app.py
├── README.md
├── requirements.txt
├── data/
├── src/
│   └── insightdf/
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
    ├── test_analytics_sql_repair.py
    ├── test_chart_recommender.py
    ├── test_insights.py
    ├── test_llm_parsing.py
    ├── test_question_guard.py
    └── test_sql_guard.py
```

## Tech Stack

- `Streamlit` for the application UI
- `pandas` for dataframe handling
- `DuckDB` for analytical SQL execution
- `Plotly` for interactive visualizations
- `LangChain` for model orchestration
- `Groq` for fast LLM inference
- `Pydantic` for structured plan validation
- `python-dotenv` for local environment configuration

## Installation

```bash
cd /home/rounak-mishra/Anuj/Projects/InsightDF
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Create a local `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
INSIGHTDF_LLM_PROVIDER=groq
INSIGHTDF_GROQ_MODEL=llama-3.1-8b-instant
```

## Run The App

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal, usually:

```text
http://localhost:8501
```

## Example Questions

- `What is the average sales amount for each region?`
- `How many records have status completed?`
- `Show me a comparison plot of revenue by category.`
- `Compare east and west region sales over time.`
- `What changed from the previous query if we only include 2024?`

## Why InsightDF Is Useful

- It reduces the need to write SQL manually for everyday analysis
- It keeps answers grounded in the uploaded dataset
- It gives transparency by exposing the generated SQL and reasoning
- It supports both quick answers and exploratory analysis
- It is designed in a modular way so future features can be added more easily

## Current Limitations

- The current execution flow is optimized for a single uploaded table
- Multi-table joins are not yet supported
- Advanced chart families such as heatmaps, histograms, box plots, and pie charts are not yet implemented
- Accuracy still depends on dataset quality, column naming clarity, and model output quality

## Roadmap

- Multi-table joins support
- Advanced chart families
- Metadata-aware RAG for external documentation
- Stronger follow-up reasoning
- More dataset-specific chart templates when useful

## Testing

After activating the virtual environment and installing dependencies:

```bash
pytest -v
```

## License

This project currently does not define a separate license file.
