"""Small, auditable helpers shared as a standalone copy in each project."""
import argparse
import hashlib
import html
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SOURCES = {
 "retail": (352, "online%2Bretail", "Online Retail.xlsx", "Chen, D. (2015). Online Retail. https://doi.org/10.24432/C5BW33"),
 "bank": (222, "bank%2Bmarketing", "bank-full.csv", "Moro, S., Rita, P., & Cortez, P. (2014). Bank Marketing. https://doi.org/10.24432/C5K306"),
 "shoppers": (468, "online%2Bshoppers%2Bpurchasing%2Bintention%2Bdataset", "online_shoppers_intention.csv", "Sakar, C. & Kastro, Y. (2018). Online Shoppers Purchasing Intention. https://doi.org/10.24432/C5F88Q"),
 "bikes": (275, "bike%2Bsharing%2Bdataset", "day.csv", "Fanaee-T, H. (2013). Bike Sharing. https://doi.org/10.24432/C5W894"),
 "weekly": (396, "sales%2Btransactions%2Bdataset%2Bweekly", "Sales_Transactions_Dataset_Weekly.csv", "Tan, J. (2014). Sales Transactions Weekly. https://doi.org/10.24432/C5XS4Q"),
 "wholesale": (292, "wholesale%2Bcustomers", "Wholesale customers data.csv", "Cardoso, M. (2013). Wholesale customers. https://doi.org/10.24432/C5030X")
}
PROVENANCE = {}
def arguments():
    p = argparse.ArgumentParser(description="Reproduce the complete analysis.")
    p.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    p.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    return p.parse_args()

def member_bytes(blob, filename):
    with ZipFile(io.BytesIO(blob)) as archive:
        for name in archive.namelist():
            if Path(name).name == filename:
                return archive.read(name)
        for name in archive.namelist():
            if name.endswith(".zip"):
                try:
                    return member_bytes(archive.read(name), filename)
                except FileNotFoundError:
                    pass
    raise FileNotFoundError(filename)

def dataset(key, cache):
    ident, slug, filename, citation = SOURCES[key]
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{key}.zip"
    url = f"https://archive.ics.uci.edu/static/public/{ident}/{slug}.zip"
    if not path.exists():
        with urlopen(url, timeout=120) as response:
            blob = response.read()
        member_bytes(blob, filename)  # Validate archive before caching.
        path.write_bytes(blob)
    blob = path.read_bytes()
    PROVENANCE[key] = {"url": url, "sha256": hashlib.sha256(blob).hexdigest(),
                       "citation": citation, "license": "CC BY 4.0"}
    content = io.BytesIO(member_bytes(blob, filename))
    return pd.read_excel(content) if filename.endswith(".xlsx") else pd.read_csv(content, sep=";" if key == "bank" else ",")

def retail(cache, identified=False):
    raw = dataset("retail", cache)
    clean = raw.drop_duplicates().copy()
    clean["InvoiceNo"] = clean.InvoiceNo.astype(str)
    clean["InvoiceDate"] = pd.to_datetime(clean.InvoiceDate)
    clean = clean[clean.UnitPrice.gt(0) & clean.Quantity.ne(0)].copy()
    clean["amount"] = clean.Quantity * clean.UnitPrice
    purchases = clean[clean.Quantity.gt(0) & ~clean.InvoiceNo.str.upper().str.startswith("C")].copy()
    if identified:
        purchases = purchases.dropna(subset=["CustomerID"])
    audit = {"raw_rows": len(raw), "duplicate_rows_removed": len(raw)-len(raw.drop_duplicates()),
             "valid_nonzero_priced_rows": len(clean), "purchase_rows": len(purchases),
             "purchase_rows_missing_customer_id": int(clean[clean.Quantity.gt(0)].CustomerID.isna().sum())}
    return clean, purchases, audit

def theme():
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,
     "axes.spines.right":False,"axes.titleweight":"bold","axes.labelcolor":"#334155",
     "text.color":"#15263e","axes.prop_cycle":plt.cycler(color=["#087f8c","#192f4b","#d29237","#7998a2"]),
     "svg.fonttype":"none","figure.facecolor":"white","axes.facecolor":"white","savefig.facecolor":"white"})

def plain(value):
    if isinstance(value, dict): return {str(k): plain(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [plain(v) for v in value]
    if isinstance(value, np.ndarray): return plain(value.tolist())
    if isinstance(value, np.generic): return plain(value.item())
    if isinstance(value, float):
        if not np.isfinite(value): raise ValueError("Non-finite metric")
        return round(value, 6)
    return value

def finish(out, title, metrics, findings, limitations, fig):
    out.mkdir(parents=True, exist_ok=True)
    payload = plain({"project":title,"metrics":metrics,"provenance":PROVENANCE})
    (out/"results.json").write_text(json.dumps(payload, indent=2, allow_nan=False)+"\n")
    fig.tight_layout()
    svg_path=out/"analysis.svg"
    fig.savefig(svg_path, bbox_inches="tight", metadata={"Date":None})
    svg=svg_path.read_text(encoding="utf-8")
    root=svg.find("<svg "); root_end=svg.find(">",root)+1
    if root<0 or root_end==0: raise ValueError("SVG root element not found")
    accessibility=(f"\n <title>{html.escape(title)}</title>"
      f"\n <desc>{html.escape(' '.join(findings + limitations))}</desc>")
    svg_path.write_text(svg[:root_end]+accessibility+svg[root_end:],encoding="utf-8")
    plt.close(fig)
    report = f"# {title}: results\n\nGenerated by analysis.py.\n\n## Findings\n\n" + "\n".join("- "+x for x in findings)
    report += "\n\n## Decision boundaries\n\n" + "\n".join("- "+x for x in limitations)
    report += "\n\n## Metrics\n\n" + "\n".join(f"- **{k}**: {v}" for k,v in payload["metrics"].items() if not isinstance(v,(list,dict)))
    report += "\n\nFull metrics and source SHA-256 hashes: [results.json](results.json).\n"
    (out/"REPORT.md").write_text(report)
    print(json.dumps({"project":title,"status":"PASS","metrics":payload["metrics"]}))
