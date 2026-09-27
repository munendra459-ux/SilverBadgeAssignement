import io
import pandas as pd
ALIASES={"order date":"order_date","date":"order_date","revenue":"sales","product name":"product","customer name":"customer_id","review text":"review_text","review":"review_text","comment":"review_text"}
class CSVFormatError(ValueError):
    pass
def load_csv(source):
    try: df=pd.read_csv(io.BytesIO(source) if isinstance(source,bytes) else source)
    except FileNotFoundError: return pd.DataFrame()
    except pd.errors.EmptyDataError as error: raise CSVFormatError("The CSV file is empty. Add a header row and at least one data row.") from error
    except pd.errors.ParserError as error: raise CSVFormatError("The CSV format is invalid. Check that columns are separated consistently and quoted values are closed.") from error
    except UnicodeDecodeError as error: raise CSVFormatError("The CSV encoding is not supported. Save the file as UTF-8 and upload it again.") from error
    df.columns=[ALIASES.get(str(c).lower().strip().replace("_"," "),str(c).lower().strip().replace(" ","_")) for c in df.columns]
    if "order_date" in df: df["order_date"]=pd.to_datetime(df.order_date,errors="coerce")
    for c in ("sales","profit","quantity","rating"):
        if c in df: df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    if "review_text" in df: df["review_text"]=df.review_text.fillna("").astype(str)
    for c in ("product","region","category","customer_id"):
        if c not in df: df[c]="Unspecified"
    return df.dropna(subset=["order_date"]) if "order_date" in df else df


def quality_summary(df):
    """Return a small, display-ready profile of a loaded sales dataset."""
    rows = len(df)
    missing = int(df.isna().sum().sum())
    duplicate_orders = 0
    if "order_id" in df:
        duplicate_orders = int(df["order_id"].duplicated().sum())
    return {
        "Rows loaded": rows,
        "Columns": len(df.columns),
        "Missing values": missing,
        "Repeated order IDs": duplicate_orders,
        "Date range": (
            f"{df['order_date'].min():%d %b %Y} – {df['order_date'].max():%d %b %Y}"
            if rows and "order_date" in df else "Not available"
        ),
    }
