from app.reasons import reject
from app.values import instant
from app.service_day import SHANGHAI, resolve_cutoff, service_day_for
def evaluate(rows,context):
    good=[];bad=[];seen=set()
    cutoff,cutoff_text=resolve_cutoff(context.get("parameters",{}))
    for row in sorted(rows,key=lambda r:(r.get("card",""),r["at"],r.get("event_id",""))):
        if row.get("result")!="success":bad.append(reject(row,"FAILED_TAP","失败刷卡不构成行程"));continue
        key=(row["card"],row["at"])
        if key in seen:bad.append(reject(row,"SIMULTANEOUS_TAP","同卡同刻多行程"));continue
        seen.add(key)
        at=instant(row["at"])
        natural_day=at.astimezone(SHANGHAI).date().isoformat()
        day=service_day_for(at,cutoff)
        good.append({**row,"business_day":day,"natural_day":natural_day,"night_cutoff":cutoff_text,"journey":row["card"]+"-"+row["event_id"]})
    overnight=sum(1 for r in good if r["business_day"]!=r["natural_day"])
    return {"rows":good,"quarantine":bad,"metrics":{"journeys":len(good),"cards":len(set(r["card"] for r in good)),"overnight_reassigned":overnight,"night_cutoff":cutoff_text}}
