import pandas as pd
import pytest

from src.analytics import metrics
from src.data_loader import CSVFormatError, load_csv
from src.recommendations import actions
from src.sentiment import prepare, summary
from src.data_loader import quality_summary
from src.campaigns import calculate_campaign_metrics
from src.scheduler import _period_sales
from src.statistics import identify_seasonality
import src.database as database


def test_load_csv_normalizes_columns_and_types():
    data = b"Order Date,Revenue,Product Name\n2026-01-01,125.50,Shirt\n"

    result = load_csv(data)

    assert {"order_date", "sales", "product"}.issubset(result.columns)
    assert result.order_date.iloc[0] == pd.Timestamp("2026-01-01")
    assert result.sales.iloc[0] == 125.5


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"", "empty"),
        (b'a,b\n"broken,x\n', "invalid"),
    ],
)
def test_load_csv_reports_invalid_formats(data, message):
    with pytest.raises(CSVFormatError, match=message):
        load_csv(data)


def test_metrics_counts_unique_orders():
    sales = pd.DataFrame(
        {
            "order_id": ["A", "A", "B"],
            "sales": [10, 20, 30],
            "customer_id": ["C1", "C1", "C2"],
        }
    )

    result = metrics(sales)

    assert result["Orders"] == "2"
    assert result["Average order"] == "₹30"


def test_sentiment_prepare_and_summary():
    reviews = pd.DataFrame({"rating": [5, 3, 1], "review_text": ["great", "okay", "poor"]})

    result = prepare(reviews)

    assert result.sentiment.tolist() == ["Positive", "Neutral", "Negative"]
    assert summary(result) == {"Average rating": "3.0/5", "Positive": "1", "Negative": "1"}


def test_recommendations_include_decline_and_margin_actions():
    sales = pd.DataFrame(
        {
            "product": ["A", "A", "B", "B"],
            "sales": [100, 100, 50, 50],
            "profit": [10, 10, -5, -5],
        }
    )
    findings = ["Latest-month revenue changed -10.0% from the prior month."]

    result = actions(sales, findings)

    assert result[0] == "Promote and keep the top-revenue product in stock."
    assert any("Investigate" in item for item in result)
    assert any("supplier costs" in item for item in result)


def test_quality_summary_counts_repeated_order_ids():
    sales = pd.DataFrame({
        "order_id": ["A", "A", "B"],
        "order_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02"]),
        "sales": [10, 20, 30],
    })

    result = quality_summary(sales)

    assert result["Rows loaded"] == 3
    assert result["Repeated order IDs"] == 1
    assert result["Date range"] == "01 Jan 2026 – 02 Jan 2026"


def test_campaign_sales_metrics_use_unique_orders_for_average_order_value():
    sales = pd.DataFrame({
        "order_id": ["A", "A", "B"],
        "customer_id": ["C1", "C1", "C2"],
        "sales": [10, 20, 30],
    })

    result = calculate_campaign_metrics(sales)

    assert result["orders"] == 2
    assert result["avg_order_value"] == 30


def test_period_sales_uses_the_latest_date_in_the_dataset():
    sales = pd.DataFrame({
        "order_date": pd.to_datetime(["2020-01-01", "2020-01-07", "2020-01-08"]),
        "sales": [10, 20, 30],
    })

    result = _period_sales(sales, 7)

    assert result.sales.tolist() == [20, 30]


def test_seasonality_uses_monthly_revenue_not_order_line_average():
    sales = pd.DataFrame({
        "order_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-02-01", "2024-03-01"]),
        "sales": [100, 100, 150, 50],
    })

    result = identify_seasonality(sales)

    assert result["peak_month"] == "Jan"
    assert result["peak_sales"] == 200


def test_sales_persistence_keeps_multiple_lines_for_one_order(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "smartb.db")
    sales = pd.DataFrame({
        "order_id": ["A", "A"],
        "order_date": ["2026-01-01", "2026-01-01"],
        "product_id": ["P1", "P2"],
        "sales": [10, 20],
        "quantity": [1, 1],
    })

    assert database.insert_sales(sales) == 2
    with database.sqlite3.connect(database.DB_PATH) as connection:
        persisted = pd.read_sql_query("SELECT * FROM sales_transactions", connection)

    assert len(persisted) == 2
    assert persisted.order_id.tolist() == ["A", "A"]
