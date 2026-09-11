# dxf-generator 完成报告 · v1.17.2 — 标准图册 templates_atlas 包

> 主人拍板先推「① 16G101 平法节点库」。本轮按桌面 `标准图册.txt` 的 `templates_atlas/` 包结构落地：
> 地基 `rebar_calc.py`（钢筋计算）+ 上层 `pingfa.py`（平法标注生成器），并把架构与分工边界拍板固化。

## 一、交付物清单

| 文件 | 作用 | 状态 |
|---|---|---|
| `scripts/templates_atlas/__init__.py` | 包入口（再导出 rebar_calc / pingfa） | 新增 |
| `scripts/templates_atlas/rebar_calc.py` | 钢筋计算（锚固/搭接/弯钩/保护层/箍筋），按 GB 50010-2010 / 16G101-1 | 新增（按桌面 spec 落地） |
| `scripts/templates_atlas/pingfa.py` | 平法标注生成器（柱KZ/梁KL/板LB/墙Q/梯AT/基DJ 六类 + 16G101 自洽校验） | 新增（权威实现） |
| `scripts/templates_pingfa.py` | 改为 `templates_atlas.pingfa` 的**薄再导出层**（单一真相源） | 重构 |
| `examples/rebar_calc.py` 自测 | 跑通（见下） | 实测 |
| `examples/verify_rebar_calc.py` | 钢筋数值核对 **26/26** | 新增 |
| `examples/verify_pingfa.py` | 平法节点核对 **53/53**（不变） | 保留 |
| `examples/pingfa_demo.py` | 生成 `out_pingfa/` 两张综合 DXF | 保留 |

## 二、锚固长度核对（主人重点要求）✅ 代码正确

**公式**（GB 50010-2010 第 8.3 节）：`lab = α·(fy/ft)·d`，α=0.14（带肋）/0.16（光圆）。

| 核查项 | 结论 |
|---|---|
| 基本锚固 HRB400 C30 d20 | `lab=705`（35.2d），与 16G101-1 表 8.3.1（35d）一致 ✓ |
| 抗震锚固 laE（一级 1.15） | d20→`810` ✓；二级同 810；三级 `740`(1.05×705)；四级 `705`(1.00×705) ✓ |
| 搭接 ll（25%→1.2） | d20→`845`(1.2×705)；50%→1.4；100%→1.6 ✓；下限 300mm 生效 ✓ |
| 弯钩 | 90°=12d；135°箍筋钩=max(10d,75)+1.9d；180°=3d+6.25d ✓ |
| 保护层（16G101-1 表 8.2.1） | 一类板15/梁20 … 三b 板40/梁50 行对行一致 ✓ |
| 箍筋下料 300×600 保护层25 d8 | 周长1600 + 两钩190 = 下料 1790 ✓ |
| d>25 带肋 ζa=1.10 修正 | d28→la=1085（含×1.10），正确 ✓ |

**⚠️ 桌面 `标准图册.txt` 的「预期输出」表有手算笔误（非代码错误）**：
- `d=28/32` **漏算 d>25 的 ×1.10 修正**（txt 写 1030/1180，代码实测 1085/1240，代码正确）。
- 多处 ±5mm 差异（d8/10/12/25 的 la/laE/ll/llE）：因**代码保留未取整中间值**（更准），txt 用手算取整值。
- 自测块 d=16/20 完全一致；d=25 laE 实测 1015（未取整中间值）vs txt 1010。

> 说明：16G101-1 表给的是「35d」这类**取整倍数**，设计值用公式得 705（差 ≤5mm），二者均合规，代码取公式精确值。

**已知简化（非 bug，供知悉）**：`ζa` 仅实现 d>25×1.10；未实现 16G101-1 8.3.2 其余修正（并筋×0.8、环氧涂层×1.25、施工扰动区×1.1、>C60 修正等）。常用情形已覆盖，需要时再补可选修正。

## 三、架构与分工（已拍板 · 回答主人 Q1-Q3）

**三层架构**（不是「节点大样 vs 配筋图」二分）：
- ① `templates_struct.py` = 通用构件配筋（单构件钢筋一根根画）
- ② `templates_atlas/pingfa.py` = 平法注写（只标符号，不画钢筋）
- ③ `templates_atlas/node_*.py`（规划）= 标准连接节点大样（梁柱节点/楼梯/基础插筋/桩基）

**Q2 复用**：③ 层直接复用 `bar()/bar_label()/hook()/bar_mark()` 作基元，缺啥补啥，不预建。
**Q3 挂载**：③ 层 = builder-agnostic 独立函数 `func(b, params, x, y)`；不绑 NL 路由、不绑 GBDxfBuilder（国标图框是输出承载层、正交）；注册表供 pipeline/NL 后续发现。

## 四、回归与验证

- `verify_pingfa.py`：**53/53** 全 PASS（六类生成 + 国标符号落盘 + 校验器正负样本）。
- `verify_rebar_calc.py`：**26/26** 全 PASS（锚固/搭接/弯钩/保护层/箍筋逐条合国标）。
- 历史 294 套件（layout_notes 69 / v114 60 / pipeline_v115 57 / nl 46 / v115 37 / interfaces 21 / pipeline 4）：**全绿，零回归**。
- `templates_pingfa.py` 重构为再导出层后，examples 引用与 SKILL.md/功能表.md 公开 API 名全部不变。

## 五、下一步（待主人拍板）

1. **③ 层节点大样**：`node_beam_column.py`（梁柱节点钢筋排布）/ `node_stair.py` / `node_foundation.py` / `node_steel.py`。
2. **续页图幅命名模板化**（`{base}_notes_{n}`，0.5h quick win）。
3. **② 识图评测集**（30~50 张真值，作为改识别规则前置——仍是确定性最低的，建议最后做）。
