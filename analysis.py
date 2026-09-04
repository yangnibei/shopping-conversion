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
    traffic["low"],traffic["high"]=zip(*[wilson(k,n) for k,n in zip(traffic["sum"],traffic["count"])])
    assert groups["count"].sum()==len(d) and groups["sum"].sum()==d.converted.sum()
    assert wilson(0,100)[0]>=-1e-12 and wilson(100,100)[1]<=1+1e-12
    metrics={"sessions":len(d),"purchasing_sessions":int(d.converted.sum()),"conversion_rate":d.converted.mean(),
      "visitor_segments":groups.reset_index().to_dict("records"),"largest_traffic_segments":traffic.reset_index().to_dict("records")}
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for ax,frame,title in [(axes[0],groups,"Visitor type conversion"),(axes[1],traffic,"Six largest anonymous traffic groups")]:
        frame=frame.sort_values("mean")
        y=np.arange(len(frame))
        ax.errorbar(frame["mean"]*100,y,xerr=np.array([frame["mean"]-frame.low,frame.high-frame["mean"]])*100,
          fmt="o",capsize=5,color="#087f8c",ecolor="#7998a2")
        labels=[f"{idx} · n={int(row['count']):,}" for idx,row in frame.iterrows()]
        ax.set(yticks=y,yticklabels=labels,title=title,xlabel="Conversion (%) · 95% Wilson interval",xlim=(0,max(frame.high)*115))
    finish(args.output_dir,"Shopping Conversion",metrics,
      [f"{int(d.converted.sum()):,} of {len(d):,} sessions end in purchase ({d.converted.mean():.1%}).",
       "Prioritise high-volume segments for qualitative investigation, and use interval width to recognise small-group uncertainty.",
       "Traffic categories are anonymised: do not relabel them as Google, email or paid search."],
      ["Observed associations are not channel effectiveness or causal effects.",
       "No sequential event log: this is segment conversion, not a checkout-stage funnel.",
       "PageValues is not used; multiple segment comparisons are exploratory and unadjusted."],fig)
if __name__=="__main__": main()
