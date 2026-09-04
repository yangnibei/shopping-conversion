from utils import arguments, dataset, theme, finish, plt, np
def wilson(k,n,z=1.96):
    p=k/n; den=1+z*z/n
    centre=(p+z*z/(2*n))/den; half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return centre-half,centre+half
def main():
    args=arguments(); theme(); d=dataset("shoppers",args.data_dir)
    d["converted"]=d.Revenue.astype(str).str.lower().eq("true").astype(int)
    groups=d.groupby("VisitorType").converted.agg(["sum","count","mean"]).sort_values("count",ascending=False)
    groups["low"],groups["high"]=zip(*[wilson(k,n) for k,n in zip(groups["sum"],groups["count"])])
    traffic=d.groupby("TrafficType").converted.agg(["sum","count","mean"]).sort_values("count",ascending=False).head(6)
    assert groups["count"].sum()==len(d) and groups["sum"].sum()==d.converted.sum()
    assert wilson(0,100)[0]>=-1e-12 and wilson(100,100)[1]<=1+1e-12
    metrics={"sessions":len(d),"purchasing_sessions":int(d.converted.sum()),"conversion_rate":d.converted.mean(),
      "visitor_segments":groups.reset_index().to_dict("records"),"largest_traffic_segments":traffic.reset_index().to_dict("records")}
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    axes[0].bar(groups.index,groups["mean"]*100,yerr=np.array([groups["mean"]-groups.low,groups.high-groups["mean"]])*100,capsize=5)
    axes[0].set(title="Visitor conversion · 95% Wilson intervals",ylabel="Conversion (%)")
    axes[0].tick_params(axis="x",rotation=15)
    axes[1].bar(traffic.index.astype(str),traffic["mean"]*100)
    axes[1].set(title="Six largest traffic groups",xlabel="Anonymous traffic category",ylabel="Conversion (%)")
    finish(args.output_dir,"Shopping Conversion",metrics,
      [f"{int(d.converted.sum()):,} of {len(d):,} sessions end in purchase ({d.converted.mean():.1%}).",
       "Prioritise high-volume segments for qualitative investigation, and use interval width to recognise small-group uncertainty.",
       "Traffic categories are anonymised: do not relabel them as Google, email or paid search."],
      ["Observed associations are not channel effectiveness or causal effects.",
       "No sequential event log: this is segment conversion, not a checkout-stage funnel.",
       "PageValues is not used; multiple segment comparisons are exploratory and unadjusted."],fig)
if __name__=="__main__": main()

