from app.modules.m7_settlement.rules import evaluate
from app.errors import DomainError
import pytest
def test_real_sample_archive_ready(result):
    "脏批申报与复算存在差异，核对完成前不发布"
    assert result["stages"][6]["metrics"]["ready"] is False
def test_real_sample_archive_source_count(result): assert result["stages"][6]["metrics"]["source_lines"]==result["stages"][5]["metrics"]["accepted_inputs"]
def test_real_sample_seal_stable(result):
    rows=result["stages"][5]["rows"];assert evaluate(rows,{})["metrics"]["sha256"]==evaluate(rows,{})["metrics"]["sha256"]
def test_unbalanced_blocked():
    with pytest.raises(DomainError) as e:evaluate([],{"reconcile":{"metrics":{"balanced":False}}})
    assert e.value.code=="UNBALANCED"
def test_duplicate_archive_key():
    with pytest.raises(DomainError):evaluate([{"event_id":"1"},{"event_id":"1"}],{})
def test_real_sample_manifest_has_hash(result): assert len(result["manifest"]["input_sha256"])==64
def test_real_sample_export_rows_match(result): assert result["stages"][6]["rows"]==result["stages"][5]["rows"]
def test_differences_block_publication(result):
    "核对完成前暂不发布日结：脏批存在差异行时 ready=False"
    m=result["stages"][6]["metrics"]
    assert m["differences"]>0 and m["ready"] is False and m["publish_blocked"] is True
def test_balanced_run_publishable():
    "无差异行的批次 ready=True，允许发布日结"
    rows=[{"event_id":"1","_sources":[1],"status":"通过"},{"event_id":"2","_sources":[2],"status":"通过"}]
    m=evaluate(rows,{})["metrics"]
    assert m["ready"] is True and m["publish_blocked"] is False
def test_night_sample_publishable(night_result):
    m=night_result["stages"][6]["metrics"]
    assert m["ready"] is True and m["records"]==8
