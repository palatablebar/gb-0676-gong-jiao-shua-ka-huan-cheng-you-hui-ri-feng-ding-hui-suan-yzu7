"""夜间运营日裁决。

背景：夜间公交跨过零点后，若按自然日切分，同一张卡的连续换乘会被拆到两个
日子，后一程在新的一天重新累计封顶（多扣）；而清晨首班车若继续沿用上一自然
日的额度，早高峰又会少扣。因此业务日（service day）必须由统一的运营日截止点
裁决，而不是简单地按 00:00 切分，也不是逐线各算各的。

裁决原则（详见 docs/DATA-DICTIONARY.md「夜间运营日」）：

1. 全市统一运营日截止点 ``night_cutoff``（本地时钟 HH:MM，默认 04:00）。
   截止点前（含 00:00 之后的凌晨段）归入前一运营日；截止点及之后归入当日。
   区间语义与全项目一致为 [start, end)。
2. 逐线末班/首班时刻只用于**校验**统一截止点是否落在所有线路的收班—首班
   空档内，不参与逐线归属：跨线路换乘链必须落在同一个运营日，逐线归属会把
   同一换乘链拆散，无法形成每位乘客唯一的夜间换乘与封顶结果。
3. 每条线路记录 last_bus（末班发车）与 first_bus（首班发车）。合法截止点必须
   严格晚于每条线路的末班、严格早于每条线路的首班（半开区间）。
"""
from datetime import datetime, time, timedelta, timezone

from app.errors import DomainError
from app.values import instant

SHANGHAI = timezone(timedelta(hours=8))
DEFAULT_CUTOFF = "04:00"

# 登记线路的末班/首班本地时刻。收班时间各不相同，但运营日截止点必须对全部
# 线路同时成立，故只取一条统一边界。
LINE_SCHEDULE = {
    "01": {"last_bus": "23:30", "first_bus": "05:00"},
    "02": {"last_bus": "22:45", "first_bus": "05:20"},
    "03": {"last_bus": "23:55", "first_bus": "04:40"},
}


def parse_hhmm(value, code="BAD_CUTOFF"):
    text = str(value).strip()
    try:
        hour_text, minute_text = text.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
        parsed = time(hour=hour, minute=minute)
    except (ValueError, TypeError):
        raise DomainError(code, "时刻需为 HH:MM 格式")
    if parsed < time(0, 0) or parsed > time(23, 59):
        raise DomainError(code, "截止点超出当日范围")
    return parsed


def resolve_cutoff(parameters):
    """读取并校验运营日截止点参数。"""
    params = parameters or {}
    cutoff_text = params.get("night_cutoff", DEFAULT_CUTOFF)
    cutoff = parse_hhmm(cutoff_text)
    schedules = params.get("line_schedule", LINE_SCHEDULE)
    if not isinstance(schedules, dict) or not schedules:
        raise DomainError("BAD_SCHEDULE", "线路时刻登记不能为空")
    # 收班—首班空档跨过零点：把末班放在前一自然日、首班放在当日，截止点
    # 映射到当日凌晨后再比较。截止点按定义是凌晨时刻（早于最早首班）。
    base = datetime(2000, 1, 2, tzinfo=SHANGHAI)
    for route, window in schedules.items():
        try:
            last_bus = parse_hhmm(window["last_bus"], "BAD_LAST_BUS")
            first_bus = parse_hhmm(window["first_bus"], "BAD_FIRST_BUS")
        except (KeyError, TypeError):
            raise DomainError("BAD_SCHEDULE", f"线路 {route} 缺少末班或首班时刻")
        last_dt = datetime.combine(base.date() - timedelta(days=1), last_bus, tzinfo=SHANGHAI)
        first_dt = datetime.combine(base.date(), first_bus, tzinfo=SHANGHAI)
        cutoff_dt = datetime.combine(base.date(), cutoff, tzinfo=SHANGHAI)
        # 截止点必须落在 (末班, 首班) 的收班空档内；恰好等于边界时两侧行程会
        # 出现归属歧义，沿用全项目半开区间惯例予以排除。
        if not last_dt < cutoff_dt < first_dt:
            raise DomainError(
                "CUTOFF_OUTSIDE_GAP",
                f"截止点 {cutoff_text} 不在线路 {route} 的收班—首班空档内",
            )
    return cutoff, cutoff_text


def service_day_for(at, cutoff):
    """按统一截止点把一个带时区时刻裁决到运营日（Asia/Shanghai 日期字符串）。"""
    local = instant(at).astimezone(SHANGHAI)
    if local.timetz().replace(tzinfo=None) < cutoff:
        local = local - timedelta(days=1)
    return local.date().isoformat()
