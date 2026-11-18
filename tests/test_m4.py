from app.modules.m4_journeys.rules import evaluate
from app.service_day import service_day_for, parse_hhmm, resolve_cutoff
from app.errors import DomainError
import pytest
def tap(id="1",at="2026-11-16T16:30:00Z",state="success"):return {"event_id":id,"card":"0001","at":at,"result":state}
def test_real_failed_not_journey(result): assert any(r["reason"]=="FAILED_TAP" for r in result["stages"][3]["quarantine"])
def test_real_business_day(result): assert result["stages"][3]["rows"][0]["business_day"]=="2026-11-16"
def test_local_midnight():
    "00:30（本地）在 04:00 截止点前，归入前一运营日而非当日自然日"
    row=evaluate([tap()],{})["rows"][0]
    assert row["business_day"]=="2026-11-16" and row["natural_day"]=="2026-11-17"
def test_same_card_same_time_conflict(): assert evaluate([tap("1"),tap("2")],{})["quarantine"][0]["reason"]=="SIMULTANEOUS_TAP"
def test_failed_cannot_anchor(): assert evaluate([tap(state="failed")],{})["rows"]==[]
def test_real_journeys_count(result): assert result["stages"][3]["metrics"]["journeys"]==32
def test_empty_journey(): assert evaluate([],{})["metrics"]["cards"]==0
def test_after_midnight_belongs_to_previous_service_day():
    "TRAP-30 跨零点换乘不得拆到两个自然日"
    rows=evaluate([tap("1","2026-11-16T16:30:00Z"),tap("2","2026-11-16T17:30:00Z")],{})["rows"]
    assert {r["business_day"] for r in rows}=={"2026-11-16"}
    assert rows[1]["natural_day"]=="2026-11-17" and rows[1]["business_day"]=="2026-11-16"
def test_after_cutoff_starts_new_service_day():
    "首班车在截止点之后，必须开启新运营日，不能沿用上夜额度"
    at="2026-11-16T21:00:00Z"
    assert service_day_for(at,parse_hhmm("04:00"))=="2026-11-17"
def test_cutoff_boundary_half_open():
    "恰好落在截止点上归入新运营日（半开区间）"
    assert service_day_for("2026-11-16T20:00:00Z",parse_hhmm("04:00"))=="2026-11-17"
    assert service_day_for("2026-11-16T19:59:00Z",parse_hhmm("04:00"))=="2026-11-16"
def test_cutoff_must_stand_in_every_line_gap():
    "逐线末班/首班不同，统一截止点必须落在每条线路的收班空档内"
    with pytest.raises(DomainError) as e:
        resolve_cutoff({"night_cutoff":"06:00"})
    assert e.value.code=="CUTOFF_OUTSIDE_GAP"
def test_bad_cutoff_format():
    with pytest.raises(DomainError):parse_hhmm("25:00")
def test_night_sample_chain_kept_one_day(night_result):
    rows=night_result["stages"][3]["rows"]
    chain=[r for r in rows if r["card"]=="C100"]
    assert len({r["business_day"] for r in chain})==1
    assert any(r["natural_day"]!=r["business_day"] for r in chain)
def test_first_bus_after_cutoff_is_new_day(night_result):
    rows={r["event_id"]:r for r in night_result["stages"][3]["rows"]}
    assert rows["N020"]["business_day"]=="2026-11-16"
    assert rows["N030"]["business_day"]=="2026-11-17"
