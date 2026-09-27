def insights(df):
    out=[]; m=df.set_index("order_date").resample("MS").sales.sum()
    if len(m)>1 and m.iloc[-2]: out.append(f"Latest-month revenue changed {(m.iloc[-1]/m.iloc[-2]-1):+.1%} from the prior month.")
    p=df.groupby("product").sales.sum().sort_values()
    if len(p): out.append(f"Top product: {p.index[-1]} (₹{p.iloc[-1]:,.0f}); lowest: {p.index[0]} (₹{p.iloc[0]:,.0f}).")
    if "profit" in df:
        x=df.groupby("product").agg(sales=("sales","sum"),profit=("profit","sum")); x["margin"]=x.profit/x.sales.where(x.sales!=0,1); out.append(f"Lowest margin: {x.margin.idxmin()} ({x.margin.min():.1%}).")
    return out
