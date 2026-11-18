import hashlib,json
from app.errors import DomainError
from app.reasons import sources
def evaluate(rows,context):
    stages=[v for v in context.values() if isinstance(v,dict) and "metrics" in v]
    balances=[s["metrics"]["balanced"] for s in stages if "balanced" in s["metrics"]]
    if balances and not all(balances): raise DomainError("UNBALANCED","来源行未对平，不能归档")
    # 夜间归属核对完成前暂不发布日结：存在差异行说明逐笔扣费与申报尚未对平，
    # 复核员必须先行裁决；这里只置 ready=False，不产生任何已发布日结。
    unresolved=sum(r.get("status")=="差异" for r in rows)
    ids=[str(r.get("event_id",r.get("_line",""))) for r in rows]
    if len(ids)!=len(set(ids)): raise DomainError("ARCHIVE_DUPLICATE","归档业务键重复")
    encoded=json.dumps(rows,ensure_ascii=False,sort_keys=True,default=str).encode()
    ready=unresolved==0
    return {"rows":rows,"quarantine":[],"metrics":{"records":len(rows),"source_lines":len(set(x for row in rows for x in sources(row))),"sha256":hashlib.sha256(encoded).hexdigest(),"ready":ready,"differences":unresolved,"publish_blocked":not ready}}
