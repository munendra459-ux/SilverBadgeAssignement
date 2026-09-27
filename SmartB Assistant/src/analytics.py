def metrics(df):
    revenue=df.sales.sum(); n=df.order_id.nunique() if "order_id" in df else len(df); profit=df.profit.sum() if "profit" in df else 0
    return {"Revenue":f"₹{revenue:,.0f}","Orders":f"{n:,}","Average order":f"₹{revenue/max(n,1):,.0f}","Profit":f"₹{profit:,.0f}","Customers":f"{df.customer_id.nunique():,}"}
def monthly(df): return df.set_index("order_date").resample("MS").sales.sum().reset_index()
