def actions(df, findings):
    out=["Promote and keep the top-revenue product in stock."]
    if any("changed -" in x for x in findings): out.append("Investigate price, discount, inventory, and campaign changes behind the sales decline.")
    if "profit" in df: out.append("Review supplier costs and discounts for low-margin products.")
    return out
