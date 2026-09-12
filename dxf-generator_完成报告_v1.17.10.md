# dxf-generator 完成报告 · v1.17.10 — 清单报价「数据贯通」（bom 几何量 → 定额量 → 预算）

> 日期：2026-09-12 ｜ 基线：v1.17.9（已 commit `24231dd`、已 push）
> 一句话：把「四项交付能力」从「能跑」升级到「数据贯通」——清单报价现在由 `bom.py` 的真实几何量驱动，并附数据溯源报告。

---

## 一、要解决的问题（边界 1）

此前四项交付能力都能跑，但**报价与图纸脱节**：

- `budget.py` 用 `建筑面积 × QUANTITY_PER_SQM × UNIT_PRICES`（如混凝土 = 面积×0.38），与图纸实际画了什么**无关**；
- `bom.py` 已能测出真实几何量（墙长 / 柱梁板基础 / 门窗），却没喂进报价。

中间缺的只是一层换算：**几何量 → 定额量 → 喂给 budget**。本版本补上这一层。

## 二、改动清单

| 文件 | 改动 |
|---|---|
| `scripts/bom_to_budget.py`（**新增**） | `ConvertParams`（结构参数全可配）+ `geometry_to_materials()`（BOM 分类→定额量）+ `estimate_from_bom()`（几何推导 + 面积回退 + 喂 `BudgetGenerator`），返回 `(budget, cov, acc, bg)` |
| `scripts/pipeline.py` | `PipelineConfig` 增 `budget_area`/`budget_floors`/`do_budget_from_bom`；`run()` 插 `[4.5]` 步；`_step_budget()` 仅 `budget_area>0` 触发，否则干净跳过；`PipelineResult` 增 `budget_from_bom_file`/`budget_from_bom_total`；顶部补 `from budget import UNIT_PRICES` |
| `examples/_demo_4deliver.py` | 复跑四种产物 + 图纸驱动路径 |
| `examples/validate_pipeline_budget.py`（**新增**） | 集成验证：用例 A 触发图纸驱动、用例 B 默认跳过 |
| `SKILL.md` / `功能表.md` | 版本 1.17.9→1.17.10；补 §二十三 章节 + §十六 流水线图 [4.5] |
| `outputs/dxf-generator_四项交付能力验证报告.md` | 升级为「数据贯通」，边界 1 标记已闭环 |

## 三、★ 实测（同一样本：12x8 三层住宅，288 m² / 3 层）

| 路径 | 总造价 | 单方 | 数据来源 |
|---|---|---|---|
| 方案级（面积×含量） | 554,479 元 | 1,925 元/m² | 建筑面积 × 经验含量 |
| **图纸驱动（bom 几何量）** | **878,067 元** | **3,049 元/m²** | 墙长→砌块 308m³ + 门窗 536m² + 柱/梁/板/基础→混凝土 10.7m³ + 钢筋 1.31t（6 项几何推导）+ 6 项面积回退 |

→ 图纸驱动比方案级贵 **58%**（方案级漏掉"墙长×墙厚×层高"这种体积大头）。

## 四、★ 诚实边界（必须说清，已写进 cov 报告）

1. **换算规则是经验假设，非 16G101 定额**：墙厚/层高/含钢量/损耗都是 `ConvertParams` 可配经验值；
2. **图纸没画的绝不虚构**：纯平面图不画梁/板/基础层 → 混凝土/钢筋自动回退面积含量，cov 标「回退(面积)」；
3. **钢筋仍是混凝土体积×含钢量近似**，非逐根算量；
4. **仍非招标/结算依据**——只是从"面积拍脑袋"升级到"图纸几何驱动"。

## 五、验证

- `validate_pipeline_budget.py`：用例 A 产出 `budget_from_bom.md`+`coverage.md` 成功；用例 B 默认跳过零回归；
- `_demo_4deliver.py` 复跑数字**完全稳定**（55.4 万 / 单方 1925 vs 87.8 万 / 单方 3049，21 项 BOM）；
- 回归：`verify_all.py` 21 套件仍全绿（本次仅新增 `bom_to_budget.py` + pipeline 增量，不动既有断言）。

## 六、结论

四项交付能力从「能跑」升级到「数据贯通」：清单报价现在由 `bom.py` 真实几何量驱动，并附数据溯源报告，
明确每笔量来自图纸还是面积回退。剩余不可逾越的近似层是"经验换算≠国标定额"——属方法学边界，非代码缺陷。
