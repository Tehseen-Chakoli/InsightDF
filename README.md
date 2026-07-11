# InsightDF

InsightDF is a modular Streamlit app that lets a user upload a CSV or Excel dataset, ask analytical questions in natural language, and receive exact values computed directly from the uploaded data.

## What it does

- Accepts `.csv`, `.xlsx`, and `.xls` files
- Profiles the uploaded dataset so the language model understands the schema
- Converts natural-language questions into safe read-only SQL
- Executes the generated query against the uploaded dataset with DuckDB
- Returns scalar answers, tabular outputs, and comparison charts
- Uses LangChain with Groq by default so the model layer can be swapped later with minimal app changes

## Example questions

- `What is the average sales amount for each region?`
- `How many records have status completed?`
- `Show me a comparison plot of revenue by category.`

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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file and add your Groq API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
INSIGHTDF_LLM_PROVIDER=groq
INSIGHTDF_GROQ_MODEL=llama-3.1-8b-instant
```

## Run

```bash
streamlit run app.py
```

## Notes

- The app is dataset-agnostic, but best results come from clean column names and meaningful categorical values.
- SQL execution is guarded so only read-only analytical queries are allowed.
- The current provider abstraction defaults to Groq through LangChain, and new providers can be added in `src/insightdf/llm.py`.
