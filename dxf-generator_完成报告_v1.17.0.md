# dxf-generator Skill 完成报告 v1.17.0

| 项 | 内容 |
|---|---|
| 技能名 | `dxf-generator` 图纸工坊 |
| 版本 | **v1.17.0**（v1.16.0 → v1.17.0） |
| 技术栈 | 纯 Python / 离线 / ezdxf 1.4.4 |
| 报告日期 | 2026-09-11 |
| 主题 | **施工说明移入图纸空间说明栏（待办①）+ 视口 bug 修复 + 成品图幅渲染** |
| 状态 | ✅ 验证 **294 项全绿**（新增 69 项）；✅ 流水线端到端跑通；⚠️ 修掉一个从 v1.14 静默至今的视口 bug |

---

## 一、任务来源

v1.16.0 报告里列了四条待办，主人点名 **①**：

> ① 说明栏移入图纸空间 Layout（`target=layout`，消除模型空间 34500mm 高的文字柱）

**为什么这条排第一**：v1.16.0 修完"文字落点"后，说明书虽然不再糊成一团，但被按 1:100
放大画在**模型空间**里 → 模型空间被撑成 **34500mm 高**的一根文字柱。后果有两个：

1. 不符合国标"模型 1:1、说明进图纸空间"的做法；
2. **模型空间渲染出来的图形缩成角落一小块**（画布被文字柱撑开，图形只占 5%）。

---

## 二、核心改动：说明搬进图纸空间说明栏

### 2.1 说明栏位置不是拍脑袋，是从图框几何推出来的

`add_gb_sheet` 的视口宽 = 内框宽 − 标题栏宽(180) − 5，且视口**左对齐**内框
→ 内框右侧天然空出一条竖带；标题栏（180×56）只占这条竖带的**底部一角**
→ **说明栏 = 竖带 ∩ 标题栏之上**。

新增 `BorderStandard.paper_notes_rect(paper_size)` 输出 (x, y, 宽, 高)，单位**图纸毫米**：

| 图幅 | 内框 | 视口 | **说明栏** |
|---|---|---|---|
| A3 | 25..410 × 10..287 | 200×272 | **(230, 71, 180, 216)** |
| A4 | 25..287 × 10..200 | 77×185 | (107, 71, 180, 129) |
| A2 | 25..584 × 10..410 | 374×395 | (404, 71, 180, 339) |
| A1 | 25..831 × 10..584 | 621×569 | (651, 71, 180, 513) |

> **关键结论：不需要压缩视口**。A3 内框右侧本来就有 180×216mm 的空白，
> 说明栏直接可用 —— 这比"缩小视口腾地方"干净得多。

### 2.2 顺序必须倒过来

老代码是「先写说明 → 后建图框」，说明只能落在模型空间；
现在改成 **「先建图框 → 再往它的说明栏写」**。

```python
# natural_language_engine.generate()
[1] sheet_layout = builder.add_gb_sheet(paper_size, td, view_center=vc, scale=sc)
[2] builder.add_construction_notes_by_discipline(..., target=sheet_layout)
    builder.add_code_references(..., target=sheet_layout)
```

### 2.3 落点策略（三种情况都覆盖）

| 场景 | 说明落点 | 行为 |
|---|---|---|
| `add_sheet=True`（默认） | **图纸空间说明栏** | 自动分页，模型空间保持干净 |
| `notes_in_layout=False` | 模型空间右侧空白区 | 有图框但强制说明留模型（旧行为） |
| `add_sheet=False` | 模型空间右侧空白区 | 无图框，只能回退（旧行为） |

**实测效果**：

| 指标 | v1.16.0 | **v1.17.0** |
|---|---|---|
| 模型空间 bbox 高度 | 34500+ mm | **17550 mm**（只剩图纸本体） |
| 模型空间文字数 | 100+ 条（含说明） | **23 条**（只剩图纸标注） |
| 说明位置 | 模型空间巨型文字柱 | **GB_A3 说明栏**（+ 续页） |
| 模型空间渲染 PNG | 377 KB（图形缩成小块） | **48 KB（图形占满画面）** |

---

## 三、⚠️ 顺带挖出的视口 bug（从 v1.14 静默至今）

做成品图幅渲染时发现：**图纸空间渲染出来只有图框，视口里的图形一片空白**。
一路查下去，根因是 `add_gb_sheet` 从 v1.14 起就写错了一个参数。

### 3.1 根因

```python
Layout.add_viewport(center, size, view_center_point, view_height)
#                                                    ^^^^^^^^^^^
#                                     这是「视口内可见的模型高度（模型单位）」，不是比例！
```

老代码把 `scale=1/100` **直接**当第 4 参传进去 → `view_height = 0.01mm`
→ 视口只看到模型里 **0.01mm 高的一刀切片**。

**铁证**（读回文件实测）：

```
get_modelspace_limits() = (5999.996, 3999.995) .. (6000.004, 4000.005)   # 退化成一个点！
get_scale()             = 27200        # 应为 0.01（= 1:100）
```

**为什么一直没暴露**：`_to_raster` 以前**只渲染 msp**（模型空间），
从不渲染图纸空间；在 AutoCAD 里打开也只会看到视口是空白——很容易被当成"没设置视口"而忽略。

### 3.2 修复与新增 API

`view_height = 视口高(纸mm) / scale`。

| 新 API | 作用 |
|---|---|
| `BorderStandard.viewport_size(paper)` | 视口 (宽, 高)；与 `add_gb_sheet` **同源**，避免两处各算一遍 |
| `BorderStandard.fit_scale(w, h, paper)` | 按模型包围盒挑**标准比例**（1/2/5/10/20/25/50/100/150/…），取能装下的最大比例 |
| `BorderStandard.scale_label(scale)` | `0.01 → "1:100"` |
| `add_gb_sheet(..., view_center=None)` | 传 None **自动取模型包围盒中心**（图框自动居中图形） |
| `add_gb_sheet(..., with_viewport=False)` | 只画图框不画视口（给"说明续页"用） |

**NL 出图现在自动定比例 + 自动居中**：`12x8米三层住宅` 实测模型 16621×17550mm
→ 自动挑 **1:100**（能装下的最大标准比例），标题栏比例同步写 `1:100`。

---

## 四、自动分页：宁可分页，也不把字缩到读不出

### 4.1 走过的弯路（诚实记录）

第一版实现用 `auto_fit` 把整套说明**硬压进一页**。结果：字高被压到 **1.8mm**
（撞上下限），页面确实不溢出了 —— 但**印出来根本读不出**。这是**假达标**。

### 4.2 改成工程上的正解

| 机制 | 做法 |
|---|---|
| **可读优先** | 说明正文 **2.5mm** / 行距 3.8mm；执行规范基数 5.0（最小一级 2.5mm） |
| **自动分页** | 一页装不下 → 自动新建 `GB_A3_说明2` 图幅（同图框/标题栏、**无视口**） |
| **标题不落单** | 切页时若本页末尾是「三、引用规范」这类标题，挪到下一页开头 |
| **`auto_fit` 保留** | 给定 `max_height` 时迭代压缩行距/字高，但下限 **2.5mm**；压不下去就交给调用方分页 |

**实测（A3 · 建筑专业）**：第 1 页 **37 行说明 + 9 行规范**，第 2 页 **47 行说明**，
全部字高 **≥2.5mm**。

### 4.3 实现方式：把「排版」和「落笔」拆开

为了让分页可行，把施工说明的绘制重构为两步：

```python
items, end_y = builder._notes_line_items(notes, width, ls, th, tht, ...)
#   items = [(dx, dy, text, height, layer, style)]  ← 纯数据，不落笔
builder.draw_notes_items(items, x=..., y=..., target=layout)   # 落笔
```

这样才能「按行清单切片 → 每片落到不同图幅」。
`_paginate_items(items, max_h)` 做贪心填充 + 标题孤儿回退。

---

## 五、成品图幅渲染（新能力）

### 5.1 用法

```python
DXFToImage().export("x.dxf", "png", {"space": "paper"})                 # 自动挑带视口的布局
DXFToImage().export("x.dxf", "png", {"space": "paper", "layout": "GB_A3_说明2"})
```

- `space='model'`（默认）→ 看**图形本体**（干净，无图框无说明）
- `space='paper'` → 看**打印出来的样子**（图框 + 标题栏 + 说明栏 + 视口里的图形）

新增 `_pick_paper_layout(doc, name)`：优先挑带 `VIEWPORT` 的布局，
退到最后一个非 Model 布局；显式给名字则按名字取（`'Model'` 不算图纸空间）。

### 5.2 ⚠️ 第二个坑：ezdxf 会跳过 `status==1` 的视口

```python
# ezdxf/addons/drawing/frontend.py :: _draw_viewports()
if viewports[0].dxf.get("status", 1) == 1:
    viewports.pop(0)          # ← 把"活动视口"当成整张布局的代表，直接跳过不画
```

所以单视口图纸空间渲染出来**只有图框**。**渲染前把 status 临时抬到 2 即可正常绘制**；
代码里只改**内存副本**、从不写盘，磁盘上的 DXF 不受影响（`status=1` 是 AutoCAD 的标准值，保持不变）。

### 5.3 流水线新增 `[6b]` 步骤

`do_render=True` 时，除 `render.png`（模型空间）外，对每个说明图幅各渲染一张：
`sheet.png`、`sheet2.png`。新增配置 `do_sheet_render=True` + CLI `--no-sheet-render`。

---

## 六、验证总账（294 项全绿）

### 6.1 新增套件 `examples/verify_layout_notes.py` · **69 / 69**

| 组 | 内容 | 结果 |
|---|---|---|
| [1] 说明栏几何 | A3/A4/A2/A1 × 4 项：在内框内、不压视口、不压标题栏、面积可用 | PASS |
| [2] 视口换算 | `view_height`/`get_scale`/`modelspace_limits` 三者自洽；`fit_scale` 单调；`scale_label` | PASS |
| [3] 说明落点 | 落点=layout；模型空间 bbox <25000mm；说明栏内 45 条文字；模型空间仍留 23 条标注 | PASS |
| [4] 分页 | 页数=布局数；**字高全 ≥2.5mm**；续页无视口；续页有正文 | PASS |
| [5] 成品图幅渲染 | 布局选择器 4 项 + 两空间渲染 + PNG 体积 | PASS |
| [6] 向后兼容 | `add_sheet=False` / `notes_in_layout=False` 仍走模型空间 | PASS |
| [7] auto_fit | 生效 / 不跌破下限 / 下限处不硬缩 / 关掉时如实溢出 | PASS |
| [8] 主链集成 | pipeline 报告 + `to_dict` + `manifest` 带落点/页数/图幅 | PASS |

### 6.2 全量回归

| 脚本 | 结果 |
|---|---|
| `verify_layout_notes.py`（新） | **69 / 69** |
| `verify_v114.py` | **60 / 60** |
| `verify_pipeline_v115.py` | **57 / 57**（原 55，见下） |
| `verify_nl.py` | **46 / 46** |
| `verify_v115.py` | **37 / 37** |
| `verify_interfaces.py` | **21 / 21** |
| `verify_pipeline.py`（v1.12 端到端渲染） | **4 / 4**（glyph missing=0） |

**合计 294 项，零 FAIL。**

### 6.3 ⚠️ 诚实披露：改了一条断言

`verify_pipeline_v115.py` 里原有的 `PNG 体积 > 50KB` 断言**被改了判据**。

- 原断言的**隐含前提**是"模型空间含巨型文字柱"（文字柱让 PNG 涨到 377KB）。
- 说明书搬走后模型空间渲染降到 **48 KB** —— 因为**图形反而占满画面**了，是变好不是回归。
- 新判据换成**内容相关**的：`20KB < PNG < 3000KB` + **模型 bbox 高度 < 25000mm**
  （直接编码"文字柱已消除"这件事）+ 报告记录落点。断言数 55 → **57**。

> 这条必须写出来：**为了通过测试而放宽阈值**和**因为被测行为变好而改判据**是两回事，
> 后者需要给出可验证的替代判据。上面给了。

---

## 七、交付物

### 技能内（新增 / 修改）

| 文件 | 说明 |
|---|---|
| `scripts/gb_standards.py` | 新增 `paper_notes_rect` / `viewport_size` / `fit_scale` / `scale_label` / `_msp_center`；**修 view_height bug**；`add_gb_sheet` 增 `view_center=None` 自动居中、`with_viewport` |
| `scripts/natural_language_engine.py` | 顺序倒置（先图框后说明）；新增 `_add_notes_to_sheet` / `_add_notes_to_model` / `_add_notes_to_sheet` 分页 / `_paginate_items` / `_is_heading` / `_draw_notes_pages`；`notes_in_layout` 参数 |
| `scripts/construction_notes.py` | 抽出 `_notes_line_items`（行清单）+ `draw_notes_items`（落笔）；`auto_fit` / `max_height` / `min_text_height=2.5` |
| `scripts/construction_codes.py` | 字高参数化（`base_height`，默认 5.0 向后兼容）；`auto_fit` / `max_height` |
| `scripts/interfaces.py` | **图纸空间渲染**：`space='paper'`、`_pick_paper_layout`、视口 status 临时提升；文本绘制泛化到任意容器 |
| `scripts/pipeline.py` | `[6b]` 成品图幅渲染；报告/`to_dict`/`manifest` 增加 落点/页数/图幅/比例/模型尺寸 |
| `examples/verify_layout_notes.py` | **新增验证 69 项** |
| `examples/verify_pipeline_v115.py` | PNG 体积断言改判据（+2 项） |
| `examples/probe_paperspace_render.py` | 图纸空间渲染能力探针（诊断用） |
| `SKILL.md` / `功能表.md` | 同步 v1.17.0（新增第十八章） |

### 桌面（可直接双击）

| 文件 | 说明 |
|---|---|
| `图纸工坊_v1.17.0_完成报告.md` | 本报告 |
| `图纸工坊_v1.17.0_成品图幅.png` | **成品图幅预览**：图框+标题栏+说明栏+视口图形（160dpi） |
| `图纸工坊_v1.17.0_说明续页.png` | **说明续页**：证明自动分页（纯说明页，不重复画图形） |
| `图纸工坊_v1.17.0_流水线报告.txt` | 流水线实跑文本报告 |

---

## 八、诚实的边界

| 能做到 | 做不到 |
|---|---|
| 一句话自动定比例 + 居中 + 说明入说明栏 | ❌ **说明内容不会自动精简**：条数多就分页，页数由内容量决定 |
| 装不下自动分页出「说明续页」图幅 | ❌ 续页是**独立图幅**，不是多页 PDF（DXF 本身无"页"概念） |
| 成品图幅渲染出"打印效果图" | ❌ 渲染仍是 matplotlib 光栅，**非矢量出图** |
| 说明书全自动排版 | ❌ 说明栏是**固定 180mm 宽**的右侧竖带；要改版式得改 `paper_notes_rect` |

**剩余待办**：① 标准图册（16G101 平法节点库）② 识图通用化（第三方 DXF）
③ Scrapling `scrapling install` 下浏览器内核 ④ Scrapling 备份路落到 `fetch_draws.py`

---

## 附：本次一句话总结

**说明书写进了它该在的地方（图纸空间说明栏），顺带发现"图纸空间从来没画对过"——
`add_viewport` 第 4 个参数是 view_height 不是比例，从 v1.14 起就是坏的，现在修好了。**
