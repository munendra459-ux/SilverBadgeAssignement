# SmartB Assistant

Local Business Intelligence Assistant built with Streamlit, Pandas, and Plotly.

## What it does

- Upload and analyse sales CSV data
- Track sales, products, regions, customers, and profit
- Ask common business questions in plain English
- Surface automated recommendations
- Analyse optional customer review ratings
- Review data quality before analysis
- Upload inventory levels and download period-based business reports

## Run it

```bash
cd "SmartB Assistant"
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app includes built-in sample data, so it will run even before you download a dataset.

## Sales CSV format

Required columns are `order_date` (or `date`) and `sales` (or `revenue`). Optional supported columns: `product`, `category`, `region`, `customer_id`, `quantity`, and `profit`.

Use the Superstore dataset recommended in the project brief; map its `Order Date` and `Sales` fields directly.

## Customer feedback CSV format

Use `review_text` (or `review`/`comment`) and `rating` columns. The women's clothing reviews dataset works well for this feature.

## Inventory CSV format

Use `product_id`, `stock_quantity`, `reorder_level`, and `unit_cost`. Optional columns include `product_name` (or `product`) and `category`.

## Data privacy

The assistant answers locally by default. Enable **Allow external AI processing** only if you consent to sending your question and retrieved data excerpts to OpenAI.
