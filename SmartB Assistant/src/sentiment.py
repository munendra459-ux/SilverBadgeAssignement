import plotly.express as px
def prepare(df):
    if df.empty or "rating" not in df: return df
    df=df.copy(); df["sentiment"]=df.rating.map(lambda x:"Positive" if x>=4 else "Negative" if x<=2 else "Neutral"); return df
def summary(df): return {"Average rating":f"{df.rating.mean():.1f}/5","Positive":f"{(df.sentiment=='Positive').sum():,}","Negative":f"{(df.sentiment=='Negative').sum():,}"}
def chart(df): return px.bar(df.sentiment.value_counts().rename_axis("sentiment").reset_index(name="reviews"),x="sentiment",y="reviews",color="sentiment",title="Customer sentiment")
