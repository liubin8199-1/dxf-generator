# dxf-generator 完成报告 · v1.17.3 — ③层节点大样交付 + 续页命名模板化

> 本轮收尾两件事：把 **③ 层四个标准节点大样**补齐并交付（桌面 `续页命名模板化.txt` 的 ② 重规格 + 既有规划），
> 以及把 **说明续页图幅命名**从硬编码中文后缀抽成可配置模板（桌面 spec 的 ①）。
> 全程未动 `dxfkit.py` 与既有模板，纯增量；回归中发现并修复 1 处旧测试断言残留（见第四节）。

## 一、交付物清单

### 1.1 ③ 层节点大样（标准图册 · `templates_atlas/`）

| 文件 | 作用 | 状态 |
|---|---|---|
| `scripts/templates_atlas/node_beam_column.py` | 框架梁柱节点大样（中柱/边柱/角柱/顶层端/顶层中柱，真画钢筋排布） | 新增（桌面 ② 重规格落地） |
| `scripts/templates_atlas/node_stair.py` | AT 型梯板支承节点（16G101-2） | 新增 |
| `scripts/templates_atlas/node_foundation.py` | 柱在独立基础/承台插筋（16G101-3） | 新增 |
| `scripts/templates_atlas/node_steel.py` | 桩基与承台锚固（16G101-3） | 新增 |
| `scripts/templates_atlas/__init__.py` | `NODES` 注册表（`beam_column`/`stair`/`foundation`/`pile` 四节点，各含 draw/Params/validate/doc） | 修改（补 NODES） |
| `examples/node_demo.py` | 生成 `out_nodes/nodes_综合大样.dxf`（四节点同图，216 实体） | 新增 |
| `examples/verify_nodes.py` | 四节点生成 + Φ/laE 落盘 + validate 正负样本 + NODES 完整 + 注册表驱动 **29/29** | 新增 |
| `examples/verify_node_beam_column.py` | 节点类型 / 参数变体 / 锚固长度 三组全过（9 断言） | 新增 |

### 1.2 续页命名模板化（①）

| 文件 | 作用 | 状态 |
|---|---|---|
| `scripts/gb_standards.py` | 新增 `NOTE_SHEET_NAME_TEMPLATE="{base}_notes_{n}"` + 模块函数 `get_note_sheet_name()` + 类方法 `BorderStandard.note_sheet_name()` | 修改 |
| `scripts/natural_language_engine.py` | `_draw_notes_pages` 改调 `BorderStandard.note_sheet_name(...)`，不再硬编码 `'GB_%s_说明%d'` | 修改 |
| `examples/verify_continuation.py` | 默认命名/中文回退/name 透传/自定义模板/类方法≡函数/NL 不再硬编码/NL 已改用 `note_sheet_name` **7/7** | 新增 |

### 1.3 文档同步

| 文件 | 改动 |
|---|---|
| `SKILL.md` | 版本 1.17.2 → 1.17.3；新增「③层节点大样收尾 + 续页命名模板化」章节（含 API 适配说明、NODES 注册表、总验证） |
| `功能表.md` | §20.6 修正为真实 `node_beam_column.node_beam_column`（中柱/边柱/角柱、column_width/column_depth）；新增 §20.7 续页命名模板化；§19.6 待办①/④ 标记 v1.17.3 已交付 |

## 二、梁柱节点重规格（桌面 ② 的关键决策）

桌面规格误用了 3 个**不存在的 builder API**，已按 dxfkit 真实 API 改写（保留桌面规格的全部附加值）：

| 桌面规格写的（不存在） | 实际 dxfkit API | 备注 |
|---|---|---|
| `add_hatch_pattern(points, pattern, scale, layer)` | `b.add_hatch(pts, pattern, scale, angle, layer)` | **第 4 参是 `angle` 不是 `layer`**，指定图层须 `layer=` 关键字 |
| `add_line(x1, y1, x2, y2)` | `b.line(x1, y1, x2, y2, layer=)` | 真实名 `line` |
| `add_dimension(x1, y1, x2, y2, offset, layer)` | `b.dim_h(y, x0, x1, label, off, layer)` / `b.dim_v(x, y0, y1, label, off, layer)` | H/V 分两个 |

重写后的 `BeamColumnNodeParams`：
- `node_type`：`middle`(中柱) / `edge`(边柱) / `corner`(角柱) / `top_end`(顶层端) / `top_middle`(顶层中柱)
- 截面：`column_width`/`column_depth`（柱宽/柱深）+ `beam_left_*`/`beam_right_*`/`beam_top_*`/`beam_bottom_*`（四向梁宽高）
- 快捷函数：`middle_node(b,cw,cd,bw,bh)` / `edge_node(...)` / `corner_node(...)`
- `NODE_TEMPLATES` 聚合 5 入口；`validate_beam_column` 抓柱纵筋非 4 倍数 / 抗震等级越界(0~4) / 节点类型未知

锚固实算经 `rebar_calc.anchorage_length`：`d22→890` / `d20→810` / `d25→1015`（±10mm，与设计值一致）。
直跑脚本的相对导入兜底：`try: from .rebar_calc ... except ImportError: from templates_atlas.rebar_calc ...`；`__main__` 的 `sys.path` 指向包根，`python node_beam_column.py` 可直跑（中柱 55 / 边柱 53 / 角柱 41 实体）。

## 三、续页命名模板化（①）

- 默认模板 `NOTE_SHEET_NAME_TEMPLATE = "{base}_notes_{n}"` → 续页名变为 **`GB_A3_notes_2`**（原 `GB_A3_说明2`）。
- 支持 `template=` 覆盖：`get_note_sheet_name(..., template="GB_{paper}_说明{n}")` 即回退旧中文命名；`name=` 透传仍可完全自定义。
- NL 引擎 `_draw_notes_pages` 已改用 `BorderStandard.note_sheet_name(base="GB_%s"%paper, paper=paper, n=idx+1, title=...)`。

## 四、回归与验证（**零 FAIL**，并修复 1 处旧测试残留）

完整复跑 **12 套件**：

```
verify_layout_notes   70/0   ← 原 69，+1 显式续页命名断言；修复下条回归
verify_v114           60/0
verify_pipeline_v115  57/0
verify_nl             46/0
verify_v115           37/0
verify_interfaces     21/0
verify_pipeline        4/0
verify_pingfa         53/0
verify_rebar_calc     26/0
verify_nodes          29/0
verify_continuation    7/0
verify_node_beam_column 9/0（节点类型/参数/laE 三组）
-----------------------------------
合计 419 项零 FAIL
```

⚠️ **发现的回归（已修）**：`verify_layout_notes` 原 69/0 复跑后变 **68/1**——
`[5]` 组的「按名字指定布局可用」断言硬编码了旧续页名 `GB_A3_说明2`，而续页命名模板化后
该布局名已改为 `GB_A3_notes_2`，故按名查找返回 `None` 判 FAIL。
这是**测试断言编码了被我故意改掉的行为**，非功能回归。修法：让该断言直接取生成结果里的
真实续页名（`gen["result"]["notes_layouts"]` 中非 `GB_A3` 的那项），并新增一条显式断言锁定
默认名 `GB_A3_notes_2`。修复后 **70/0**。

> 注意：`verify_continuation.py` 同时验证了「传 `template="GB_{paper}_说明{n}"` 可回退到 `GB_A3_说明2`」，
> 故旧中文命名作为**可选覆盖**仍被支持，只是不再是默认。

## 五、下一步（待主人拍板）

1. **② 识图评测集**（30~50 张真实图纸真值，放 `benchmarks/`）——作为改识别规则的前置，确定性最低，建议最后做。
2. ③ 层节点接 NL 路由（`画一个300×600框架梁柱节点`→`node_*.py`）+ 接 `pipeline` 注册表发现（当前 NODES 已就位，仅待接线）。
3. 版式信号识别（实体数/几何统计替代「关键词袋」路线，依赖评测集）。
