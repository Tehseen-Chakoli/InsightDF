# InsightDF

InsightDF is a modular Streamlit app that lets a user upload a CSV or Excel dataset, ask analytical questions in natural language, and receive exact values computed directly from the uploaded data.

## What it does

- Accepts `.csv`, `.xlsx`, and `.xls` files
- Profiles the uploaded dataset so the language model understands the schema
- Converts natural-language questions into safe read-only SQL
- Executes the generated query against the uploaded dataset with DuckDB
- Returns scalar answers, tabular outputs, and comparison charts

## Example questions

- `How many passengers boarded from C and survived?`
- `What is the average fare for female passengers in first class?`
- `Show me the comparison plot between survived males and females who boarded from C and belong to upper middle class.`

## Project structure

```text
InsightDF/
├── app.py
├── requirements.txt
├── README.md
└── src/
    └── insightdf/
        ├── analytics.py
        ├── config.py
        ├── data_loader.py
        ├── llm.py
        ├── query_models.py
        ├── schema.py
        └── sql_guard.py
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Run

```bash
streamlit run app.py
```

## Notes

- The app is dataset-agnostic, but best results come from clean column names and meaningful categorical values.
- SQL execution is guarded so only read-only analytical queries are allowed.
- If the uploaded file does not already have a useful semantic column like `survived`, the app can still answer questions as long as the intent can be mapped from the dataset schema.
