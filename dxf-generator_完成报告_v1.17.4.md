# dxf-generator 完成报告 · v1.17.4 — 节点路由 + 钢结构扩展 + 识图评测集 + 统一验证入口

> 本轮把桌面 `路由接线.txt` 的 **A / B / C / D 四条路线全部落地**：
> **A** ③ 层节点接入自然语言路由 · **B** 识图评测集脚手架 · **C** 统一验证入口 · **D** 钢结构节点扩展。
> 全程只新增模块 + 在 `natural_language_engine.py` 内接线；**未动 `dxfkit.py`、未动既有模板、未破坏既有 NODES 注册表**。

---

## 一、交付物清单

| # | 文件 | 作用 | 状态 |
|---|---|---|---|
| A | `scripts/natural_language_engine.py` | 4 处接入 ③ 层 4 类节点（关键词/默认尺寸/dispatch/discipline_map）+ `_parse_node_text` + 4 handler | 修改 |
| A | `examples/verify_node_routing.py` | 节点 NL 路由验证 **23/23** | 新增 |
| B | `benchmarks/ground_truth.json` | 识图真值表（`file/type/family/oov/source`） | 新增 |
| B | `benchmarks/eval.py` | 识图评测（严格/宽松/拒识/**认错** 四口径） | 新增 |
| B | `benchmarks/import_samples.py` | 把外部 DXF 导入 `raw/`（`raw/` 不入库） | 新增 |
| B | `benchmarks/README.md` | 口径 + 基线 + 根因 + 边界 | 新增 |
| C | `examples/verify_all.py` | 统一验证入口（18 套件一键跑 + 汇总 + `--list/--json/子集`） | 新增 |
| D | `scripts/templates_atlas/node_steel_v2.py` | 钢结构三节点（钢柱脚/钢梁柱栓焊混接/钢梁拼接）+ `STEEL_NODES` | 新增 |
| D | `scripts/templates_atlas/__init__.py` | 导出 `STEEL_NODES`（独立于 `NODES`，不动既有 4 项） | 修改 |
| D | `examples/verify_steel_nodes.py` | 钢结构节点验证 **24/24** | 新增 |
| D | `scripts/natural_language_engine.py` | 钢结构 3 类图别接入 NL 路由 | 修改 |
| — | `SKILL.md` / `功能表.md` | → v1.17.4（描述 23→26 类；新增 §20.8/§20.9/§20.10；待办 2/6/7 标记已交付） | 修改 |

---

## 二、A · ③ 层节点接入自然语言路由（23/23）

把 v1.17.3 交付的 4 个标准节点从"只能手写 Python"扩成"**一句中文直出图**"。

**4 处接入（全在 `natural_language_engine.py`）**：`NLPParser.DRAWING_TYPE_PATTERNS`（**类属性**）·
`DEFAULT_DIMS_MM` · `NaturalLanguageGenerator._dispatch`（**实例字典**）· `discipline_map`。

**尺寸解析 `_parse_node_text`**：中文柱/梁截面有两种语序（`600x600柱300x600梁` / `柱800×800 梁400×800`），
且尺寸对可能被相邻名词夹住。采用「**零间隔相邻 + 尺寸在名词前优先**」——
**不能用「名词最近中心距」**（第一例里 `柱` 距 `300x600` 更近，会把柱判成 300x600）。

### 本轮真实报错（自己代码 + 桌面规格各踩坑）

| # | 坑 | 现象 | 修复 |
|---|---|---|---|
| 1 | **函数名不是 `node_xxx`** | `from templates_atlas.node_stair import node_stair` → **ImportError** | 真实名 `stair_node`/`foundation_node`/`pile_node`；**`node_beam_column.py` 例外** |
| 2 | **无 `node_pile.py`** | 桩基 import 指向不存在的模块 | 桩基在 **`node_steel.py`**（`pile_node` + `PileNodeParams`）|
| 3 | dispatch 表位置 | 桌面规格用模块级 `NL_DISPATCH`（**不存在**）| 实为 `self._dispatch` 实例字典 |
| 4 | 关键词表位置 | 桌面规格用模块级 `DRAWING_TYPE_PATTERNS` | 实为 `NLPParser` **类属性** |
| 5 | 尺寸串字 | 「600x600柱300x600梁」柱被判 300x600 | 零间隔相邻 + 前置优先 |

### 桌面规格三处高风险接口的核查结论

| 规格提出 | 核查结果 | 处理 |
|---|---|---|
| `NL_DISPATCH` 模块级字典 | 不存在 → 实为 `self._dispatch` | 直接进 `natural_language_engine.py` |
| `SPECIALTY_TEMPLATES` + `pipeline_patch.py` | `SPECIALTY_TEMPLATES` 不在生成路径上（pipeline 走 `generate_from_text`） | **未采用**（死代码）；节点进 NL 引擎即自动覆盖 pipeline |
| `nl_router_patch.py` 独立补丁 | 会形成双份关键词表（易漂移） | **未采用**；直接进 NL 引擎，复用 `templates_atlas` 单一真相源 |

---

## 三、D · 钢结构连接节点（24/24）

补 `node_steel.py`（只有混凝土桩基承台）的缺口：

| 节点 | 函数 / 参数 | 依据 | 画什么 | 实体 |
|---|---|---|---|---|
| 钢柱脚 | `steel_column_base(SteelColumnBaseParams)` | GB 50017-2017 / 16G519 | 底板 + 二次浇筑层 + 工字形柱身 + 加劲肋(刚接) + 锚栓(铰接4/刚接8) + 锚固段 | 27 |
| 钢梁柱节点 | `steel_beam_column(SteelBeamColumnParams)` | GB 50017-2017 / 16G519 | 工字形柱 + 工字形梁 + 端板 + 翼缘焊缝(全/部分熔透) + 腹板高强螺栓双列 | 29 |
| 钢梁拼接 | `steel_beam_splice(SteelBeamSpliceParams)` | GB 50017-2017 / 16G519 | 两段工字形梁 + 翼缘/腹板拼接板 + 高强螺栓 | 31 |

- **注册表 `STEEL_NODES` 独立于 `NODES`**：`verify_nodes.py` 断言 `len(NODES)==4`，并入会破坏既有验证。
- **NL 路由新增 3 类图别**：`node_steel_base` / `node_steel_beam_column` / `node_steel_splice`。
  ⚠️ **顺序敏感**：「钢**梁柱节点**」含子串「梁柱节点」，若混凝土节点规则在前会被 `node_beam_column` 抢走
  —— 实测踩过，已把钢结构规则**前置**（关键词表内顺序 = 匹配优先级）。
- 反例校验各抓 ≥3 条（底板<柱 / 锚栓<4 / 非法牌号 / 拼接板厚<腹板厚 / 螺栓数不足 …）。

---

## 四、B · 识图评测集（`benchmarks/`）

**为什么需要**：改识图规则前必须有评测集。7 张样本调阈值必然过拟合。

**四口径**：严格正确 / 宽松正确 / 正确拒识（**OOV 真值下拒识 = 合格**）/ **认错**。

> ⚠️ **度量纪律（本项目最该记住的一条）**：旧口径「识别成功 100%」是**假指标** ——
> 它只统计"有没有输出"，不统计"输出对不对"。本项目实测**可同时成立**
> 「识别成功 100%」与「严格正确 0%」。改规则必须给 before/after **认错率**。

### 实测基线（复现 v1.17.1，7 张真实图纸）

| 口径 | 结果 |
|---|---|
| 严格正确 | **0 / 7 = 0%** |
| 宽松正确 | **1 / 7 = 14.3%** |
| 正确拒识 | 0 / 7 |
| **★ 认错** | **6 / 7 = 85.7%** ← 最该压到 0 的指标 |

典型错法：`材料表 → 火灾报警图`、`各层平面 → 火灾报警图`、`暖通图 → 节点大样图`。

### 根因（v1.17.1 已用数据确认）

1. **规则只认自家图层命名**：`TYPE_BY_LAYERS` 匹配 `G_WALL`/`G_DOOR` 这套（本技能自己的输出约定），
   真实图纸用 `A建墙`/`IRC灯具` → 图层信号**零命中**。
2. **模板图例污染**：同一家设计院模板的 **189 行图例文字出现在全部 7 个文件**里，
   且**图名"首层平面图"本身就是模板行**（7/7 都有）→ 批量去模板会把正确答案一起删掉（结构性矛盾）。
3. **图层是"文档级"而非"图纸级"**：6 张图各带 120~469 图层且共享同一套 → 判不出平面/剖面。

### 可判别信号在版式/几何

`01 材料表` 模型空间仅 **262~996** 实体（主体在 Layout1），`03 1F` 有 **29,361** 实体
→ **实体数量级本身就是强信号**。需要 `LWPOLYLINE`/`HATCH` 几何统计（`read()` 已有 `geometry`）。

### 工程处理

`benchmarks/raw/` 已加入 `.gitignore`（7 张预处理 DXF 合计 **136MB**，不适合入库）；
`ground_truth.json` 的 `source` 提供回落绝对路径 → 现在即可跑；
`import_samples.py` 一键把外部 DXF 导入 `raw/` 使评测集脱离外部路径。

---

## 五、C · 统一验证入口（`examples/verify_all.py`）

```bash
python examples/verify_all.py            # 全部 18 套件
python examples/verify_all.py nl nodes   # 子集过滤
python examples/verify_all.py --list     # 列出
python examples/verify_all.py --json     # 机器可读（CI）
```

**判定顺序**（顺序即语义）：① 显式计数 → ② 明确失败语 → ③ **明确通过语优先于标记计数** → ④ 兜底数 ✅/❌。

> ⚠️ 第 ③ 条是踩坑后加的：最初只用「数 ❌」兜底，`verify_fonts` 因列出 **6 个本机未安装的字体候选**
> 打了 6 个 ❌，被误判为「6 项失败」——而脚本自身输出其实是「✅ 验证通过」。
> 教训：**探测类 ❌ ≠ 失败**。另外自动发现新增 `verify_*.py`（排除自身防递归），rc 也参与判定。

---

## 六、总验证

```
18 套件全绿 · 469 项可计数断言 · 0 失败（约 1 分 32 秒）
  layout_notes 70 · v114 60 · pipeline_v115 57 · nl 46 · v115 37 · interfaces 21 · pipeline 4
  pingfa 53 · rebar_calc 26 · nodes 29 · continuation 7 · node_beam_column 12
  node_routing 23 · steel_nodes 24
  + 字体配置 / 全量扩展 / 高级模板+审图 / 说明全套（无计数，按判定语通过）
```

一条命令复跑：`python examples/verify_all.py`

---

## 七、下一步（本报告之后的真正待办）

| 路线 | 内容 | 备注 |
|---|---|---|
| B-扩样本 | 识图评测集扩到 **30~50 张** | **前置条件**：不扩就改规则 = 过拟合 |
| B-改规则 | 版式/几何信号替换"关键词袋" | 依赖扩样本；改完必须给 before/after **认错率** |
| — | 节点图框自动挂载 / 节点置信度 / 3D 门窗开洞 | 能力层遗留，优先级低 |

---

*报告生成：2026-09-11 · dxf-generator v1.17.4（A/B/C/D 四路线）*
