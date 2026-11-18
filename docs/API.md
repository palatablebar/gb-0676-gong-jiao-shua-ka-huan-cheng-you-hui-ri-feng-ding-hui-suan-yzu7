# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV。

parameters支持night_cutoff（运营日截止点HH:MM，默认04:00）与line_schedule（线路末班/首班覆盖）。截止点不落在任一线路收班—首班空档时整批以422 CUTOFF_OUTSIDE_GAP拒绝且不写库，历史批次保持不变。重跑相同输入与参数复用同一run_id；规则版本或参数变化产生独立新批次，旧版保留。日结metrics.ready为false（仍有差异行）时publish_blocked=true，表示核对完成前暂不发布。
