# dxf-generator 完成报告 · v1.17.11（增强2 接单价库 + 增强3 识图兜底）

**日期**：2026-09-12
**来源**：桌面 `接单价库.txt`（用户草稿）→ 落地 + 跑通
**范围**：两项增强均来自用户草稿；草稿含接口错配，已按 dxf-generator 真实代码修正后落地。

---

## 一、增强2：接单价库（可配市场价 / 地区定额）

### 1.1 新增文件
- `scripts/price_library.py` — 单价库数据模型（`PriceItem` / `PriceLibrary`）、JSON/CSV 导入导出、`QuotaLoader`（Excel/文本定额加载）、`create_default_library()`（**实时从 `budget.UNIT_PRICES` 迁移**，单一事实源）、`to_budget_prices()` / `apply_to_budget()`。
- `scripts/price_library_nanning.py` — `create_nanning_library()`（南宁 2026-09 市场价：4 主材 + 13 人工 + 3 机械）。
- `examples/demo_price_lib.py` — A/B/C/D 四路对比验证。

### 1.2 关键修正（草稿→落地，避免静默空操作）
| 草稿（错） | 落地（对） |
|---|---|
| `to_budget_prices()` 返回 `{code: {dict}}` | 返回 `{name: (unit, price)}` 元组（与 `budget.UNIT_PRICES` 完全对齐） |
| `create_default_library()` 硬编码 28 项 | 从 `budget.UNIT_PRICES` 实时迁移 12 项，name 对齐 |
| 自测导出 `/tmp/` | `tempfile.gettempdir()`（Windows 兼容） |

> 用 code 做 key 会整体 miss `UNIT_PRICES`（name-keyed）→ 静默空操作（总价不变）。这是草稿最隐蔽的 bug，已根除。

### 1.3 覆盖入口（两条等价路径）
- (A) 显式：`ov = lib.to_budget_prices()` → `QuantityCalculator(..., unit_prices=ov)` 或 `estimate_from_bom(..., unit_prices=ov)`
- (B) 全局：`lib.apply_to_budget(budget_module)`（`UNIT_PRICES.update(...)`）

### 1.4 ★ 实测：覆盖确实生效
| 路径 | 总造价 | 单方 | 变化 |
|---|---|---|---|
| A 方案·默认 | 554,479 | 1,925 | — |
| B 方案·南宁 | 531,046 | 1,844 | **−4.2%** |
| C 图纸·默认 | 878,067 | 3,049 | — |
| D 图纸·南宁 | 874,337 | 3,036 | **−0.4%** |

差值偏小因仅覆盖 4 主材，符合诚实预期。

### 1.5 诚实边界
南宁材料 = 2026-09 市场参考价（非广西 2026 版官方定额）；人工 = 南宁造价信息 2026-01 区间中值。正式造价须用官方定额组价表。

---

## 二、增强3：识图兜底（图别不确定→回退通用模板 + 警告）

### 2.1 新增文件
- `scripts/reader_fallback.py` — `ConfidenceLevel` / `FallbackResult` / `ReaderFallback`（判定）/ `get_notes_with_fallback()`。
- `examples/demo_reader_fallback.py` — 单元 + 集成验证。

### 2.2 关键修正（草稿→落地）
| 草稿（错） | 真实代码 | 落地修正 |
|---|---|---|
| `DrawingUnderstanding` 类 | 不存在；真实 `drawing_reader.DrawingInfo` | 读 `DrawingInfo` 字段 |
| `.confidence` / `.margin` | `.type_confidence` / `.type_margin` / `.abstained` | `_extract()` 按真实字段名抽取，兼容旧名 |
| `patch_pipeline_fallback` 改 `Pipeline._step_notes` / `self.result._understanding_obj` | 这俩不存在 → monkeypatch 必崩 | `_step_notes` 内直接调 `ReaderFallback.evaluate_from_info(self.result.understanding)` |

### 2.3 判定逻辑（沿用 v1.17.9 实证：margin 才有判别力）
- `margin ≥ 0.2 且 confidence ≥ 0.7` → 高（直接用）
- `margin ≥ 0.1` → 中（建议人工确认）
- 否则 / 弃权（`abstained` 或图别="未识别"）→ 低 / 未知（必须人工确认）

### 2.4 主链接入点（pipeline.py 三处）
1. `PipelineResult` 新增 `notes_warning` 字段；
2. `_step_reader` 落盘 `understanding` 新增 `type_margin` / `abstained`；
3. `_step_notes`：`source=="识图匹配"` 且 `needs_review` 时，回退 `notes_key=floor_plan`、`source=识图兜底`、写 `notes_warning`，并在 `construction_notes.md` 顶部 `> ⚠ ...` 警示。`reader_strict` 配置可切严格阈值（默认关闭）。

### 2.5 ★ 实测：主链生效
- 场景A（火灾报警图 conf=0.5/margin=0.0）→ `floor_plan` + `识图兜底` + 警告入文件；
- 场景B（高置信）→ 保留原模板、无警告。

---

## 三、验证汇总
| 项 | 结果 |
|---|---|
| `price_library.py` / `price_library_nanning.py` 自测 | 12 / 20 项，格式对齐 ✅ |
| `reader_fallback.py` 自测 | 5 用例全过 ✅ |
| `examples/demo_price_lib.py`（四路对比） | 覆盖生效 ✅ |
| `examples/demo_reader_fallback.py`（单元+集成） | 全过 ✅ |
| 回归 `examples/validate_pipeline_budget.py` | 用例A 219,319 元、用例B 干净跳过 ✅ |
| 单独复跑 `examples/verify_pipeline_v115.py` | 修复后 **57/57**（原 56/57） ✅ |
| **全量 `examples/verify_all.py`** | **21 套件 · 575 断言 · 0 失败** ✅ |

---

## 三之二、★ 顺带修掉 v1.17.10 遗留的步骤槽位回归

首次真实复跑 `verify_all.py` 即暴露 `verify_pipeline_v115.py` 断言失败（56/57）。
**根因不是本次 v1.17.11 的改动，而是 v1.17.10 插入 `[4.5]` 步骤时的疏漏**
（且 v1.17.10 完成报告里"verify_all 全绿"的说法当时并未真正复跑验证——已在功能表 §23.6 就地更正留痕）。

| 症状 | 根因 | 修复 |
|---|---|---|
| 断言 `len(r.steps) == 8` 失败（实际 9） | `_safe(4.5, ...)` 未登记进 `plan` | `plan` 增 `(4.5, "报价", cfg.do_budget_from_bom)`；断言 8→9 |
| 第 9 槽位显示「**步骤4**」，与 [4] 说明撞名 | `_plan_name` 回退 `"步骤%d" % 4.5` → **`%d` 把 4.5 截断成 4** | 回退改 `%s`；`_run_step` 打印与报告渲染改 `%g`（现正确显示 `[4.5/8] 报价`） |
| `_is_enabled(4.5)` 恒 True，绕过 `do_budget_from_bom` | 查不到 plan 条目即返回 True | 登记后由 plan 的 `enabled` 决定 |

**⚠️ 通用教训（`%d` 陷阱）**：允许小数编号的槽位/枚举用 `%d` 格式化会**静默截断**（4.5→4），
既造成显示撞名，也掩盖了"该条目实际未登记"这一事实。**能取小数的编号一律用 `%s`/`%g`。**
另一条：**"改动很小"不等于"没有回归"——回归结论只能以真实跑过的输出为准。**

## 四、升级结论
- 报价：写死经验常数 → 可配市场价/地区定额（增强2）
- 施工说明：盲信识图图别 → 不确定即回退通用模板 + 写警告（增强3）
- 两增强均 opt-in、零回归。

## 五、未做 / 待确认
- 草稿的 `patch_pipeline_fallback` 已废弃（引用不存在的方法）；改为直接接入 `_step_notes`。如坚持要"可插拔补丁"形态，需另设计，但当前直接接入更稳。
- 人工/机械单价（南宁库 13+3 项）尚未接入预算（本版 `budget.py` 用平摊 `LABOR_PER_SQM`），仅作库完整性保留。
