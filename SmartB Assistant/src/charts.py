import plotly.express as px
from src.analytics import monthly
def charts(df):
    p=df.groupby("product",as_index=False).sales.sum().nlargest(10,"sales").sort_values("sales"); r=df.groupby("region",as_index=False).sales.sum()
    return [px.line(monthly(df),x="order_date",y="sales",markers=True,title="Sales trend"),px.bar(p,x="sales",y="product",orientation="h",title="Top products"),px.bar(r,x="region",y="sales",color="region",title="Regional sales")]
