import csv,io
from app.pipeline import execute,load_sample
from app import store
def test_full_sample_flow(client):
    r=client.post("/api/runs",json={"sample":"dirty.csv"});assert r.status_code==200
    p=r.get_json();assert len(p["stages"])==7
    assert p["stages"][5]["metrics"]["balanced"] is True
def test_idempotent_real_input(sample):
    a=execute(sample);b=execute(sample)
    assert a["run_id"]==b["run_id"] and len(store.history())==1
def test_stale_review_409(client):
    "TRAP-26 陈旧复核不得覆盖新版本"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json();u="/api/runs/"+p["run_id"]+"/review"
    assert client.post(u,json={"version":1,"decision":"已复核"}).status_code==200
    assert client.post(u,json={"version":1,"decision":"退回复核"}).status_code==409
def test_export_has_manifest_and_quarantine(client):
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    r=client.get("/api/runs/"+p["run_id"]+"/archive")
    rows=list(csv.reader(io.StringIO(r.data.decode("utf-8-sig"))))
    assert rows[0][1]=="input_sha256" and any(x[3]=="quarantine" for x in rows[1:])
def test_failed_import_is_atomic(client):
    assert client.post("/api/runs",json={"csv":"bad"}).status_code==422
    assert store.history()==[]
def test_module_entrances(client):
    from app.config import MODULES
    for slug,name in MODULES:
        assert client.get("/api/"+slug).status_code==200
        assert client.get("/"+slug).status_code==200
def test_missing_run_404(client): assert client.get("/api/runs/missing").status_code==404
def test_night_rerun_is_idempotent_and_keeps_attribution():
    "重跑同一天不新增也不改换已归属行程"
    from app.pipeline import execute,load_sample
    from app import store
    raw=load_sample("night.csv")
    a=execute(raw);b=execute(raw)
    assert a["run_id"]==b["run_id"] and len(store.history())==1
    assert a["stages"][3]["rows"]==b["stages"][3]["rows"]
def test_rule_switch_keeps_previous_batch():
    "切换规则失败后保留旧版；成功切换也不动旧批次"
    import pytest
    from app.pipeline import execute,load_sample
    from app import store
    from app.errors import DomainError
    raw=load_sample("night.csv")
    old=execute(raw)
    with pytest.raises(DomainError) as e:execute(raw,{"night_cutoff":"06:00"})
    assert e.value.code=="CUTOFF_OUTSIDE_GAP"
    assert store.get(old["run_id"])["stages"][3]["metrics"]["night_cutoff"]=="04:00"
    new=execute(raw,{"night_cutoff":"04:30"})
    assert new["run_id"]!=old["run_id"] and store.get(old["run_id"]) is not None
def test_settlement_blocked_until_reconciled(client):
    "核对完成前暂不发布日结"
    p=client.post("/api/runs",json={"sample":"night.csv"}).get_json()
    m=p["stages"][6]["metrics"]
    assert m["ready"] is True and m["publish_blocked"] is False
    dirty=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    assert dirty["stages"][6]["metrics"]["publish_blocked"] is True
