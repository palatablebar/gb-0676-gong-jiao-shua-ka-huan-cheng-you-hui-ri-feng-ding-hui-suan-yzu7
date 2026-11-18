from app.modules.m5_discounts.rules import evaluate
from app.errors import DomainError
from decimal import Decimal
import pytest
def ride(id,minute,route="01",base="2.50"):
    return {"event_id":str(id),"card":"0001","business_day":"2026-11-16","at":f"2026-11-16T{8+minute//60:02d}:{minute%60:02d}:00Z","route":route,"base_fare":base}
def test_real_day_cap(result): assert result["stages"][4]["metrics"]["expected_total"]=="48.00"
def test_exact_window_excluded():
    "TRAP-23 半开换乘窗"
    r=evaluate([ride(1,0),ride(2,60,"02")],{})["rows"];assert r[1]["transfer_discount"]=="0.00"
def test_within_window_discount(): assert evaluate([ride(1,0),ride(2,59,"02")],{})["rows"][1]["expected"]=="1.50"
def test_same_route_no_transfer(): assert evaluate([ride(1,0),ride(2,10)],{})["rows"][1]["expected"]=="2.50"
def test_zero_paid_not_anchor():
    r=evaluate([ride(1,0,base="1"),ride(2,30,"02",base="1"),ride(3,61,"03",base="1")],{})["rows"]
    assert r[1]["expected"]=="0.00" and r[2]["transfer_discount"]=="0.00"
def test_discount_before_cap_conservation():
    "TRAP-10 Decimal守恒"
    r=evaluate([ride(1,0),ride(2,10,"02"),ride(3,20,"03"),ride(4,90)],{})["rows"]
    assert sum(Decimal(x["expected"]) for x in r)==Decimal("6")
    assert all(Decimal(x["base_fare"])==Decimal(x["expected"])+Decimal(x["transfer_discount"])+Decimal(x["cap_discount"]) for x in r)
def test_negative_parameter_rejected():
    with pytest.raises(DomainError):evaluate([],{"parameters":{"daily_cap":"-1"}})
def test_input_order_invariant():
    rows=[ride(1,0),ride(2,10,"02")];assert evaluate(rows,{})["rows"]==evaluate(list(reversed(rows)),{})["rows"]
def night_ride(id,card,at,route,base="2.50",day="2026-11-16"):
    return {"event_id":str(id),"card":card,"business_day":day,"at":at,"route":route,"base_fare":base}
def test_overnight_chain_keeps_single_cap():
    "TRAP-30 跨零点四程同运营日：换乘与封顶连续累计，不重新起算"
    rows=[
        night_ride("N010","C100","2026-11-16T15:40:00Z","01"),
        night_ride("N011","C100","2026-11-16T16:20:00Z","02"),
        night_ride("N012","C100","2026-11-16T17:10:00Z","03"),
        night_ride("N013","C100","2026-11-16T18:30:00Z","01"),
    ]
    out=evaluate(rows,{})["rows"]
    assert len({(r["card"],r["business_day"]) for r in out})==1
    assert sum(Decimal(x["expected"]) for x in out)==Decimal("6.00")
    assert all(Decimal(x["base_fare"])==Decimal(x["expected"])+Decimal(x["transfer_discount"])+Decimal(x["cap_discount"]) for x in out)
def test_first_bus_does_not_inherit_overnight_quota():
    "截止点后的首班车属于新运营日，按新卡日重新累计，避免早高峰少扣"
    rows=[
        night_ride("N020","C200","2026-11-16T19:50:00Z","03",day="2026-11-16"),
        night_ride("N030","C200","2026-11-16T21:10:00Z","01",day="2026-11-17"),
    ]
    out={(r["event_id"]):r for r in evaluate(rows,{})["rows"]}
    assert out["N030"]["expected"]=="2.50" and out["N030"]["transfer_discount"]=="0.00"
    assert out["N030"]["day_paid"]=="2.50"
def test_unique_passenger_night_result(night_result):
    "每位乘客在每个运营日只有唯一一条换乘/封顶结果"
    rows=night_result["stages"][4]["rows"];seen=set()
    for r in rows:
        key=(r["card"],r["business_day"],r["event_id"])
        assert key not in seen;seen.add(key)
    assert night_result["stages"][4]["metrics"]["passenger_days"]==len({(r["card"],r["business_day"]) for r in rows})
