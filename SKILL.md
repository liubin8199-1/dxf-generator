---
name: dxf-generator
description: 用自然语言生成 DXF 矢量图纸的 Skill。封装 ezdxf 核心能力（文档/模型空间/图元/图层/保存/图纸空间），提供高层绘图库 dxfkit.py，让 Agent 把"画一个XX平面图/零件图/布置图/电气图"直接转成可打开的 .dxf 文件。无需安装 AutoCAD。支持五大功能：导入修改、参数化模板、批量处理、样式系统、自然语言分发；扩展模块含 geomkit 高级几何（齿轮/螺旋/贝塞尔）、archkit 建筑标准（轴网/双线墙/门窗/楼梯/图框/户型生成器）、budget 造价预算与采购清单、templates_arch 建筑专业（立面/剖面/节点大样/楼梯详图）、templates_struct 结构专业（钢筋符号/柱/板/基础/楼梯配筋）、templates_mep 机电专业（电气符号/电气图例/照明平面）；**GB/T 国标标准化**：gb_standards.py 提供 48 个国标图层、标准线型/线宽、符号/文字/图框标准与 GBDxfBuilder（A0~A4 图框+标题栏+1:100 视口，可直接出全套施工图）；**中文字体支持**：font_manager.py 自动注册 GB_CHINESE/GB_TITLE/GB_MULTILINE 样式（gbenor.shx + gbcbig.shx），所有含 CJK 的 TEXT/MTEXT 实体自动绑定中文样式，杜绝「中文显示为 ??」乱码；**施工说明模块**：construction_notes.py 按 GB 系列规范自动生成各专业施工说明（一般/土方/基础/主体/砌体/屋面/装饰/给排水/电气/暖通/消防/安全），一行 API 即可把说明写入图纸空间说明栏或模型空间；**施工规范引用模块**：construction_codes.py 内置 GB/JGJ 规范库 64 条×13 类，按图纸类型/专业自动匹配 强条/推荐/参考，CodeAwareDxfBuilder 一行把规范清单画进图纸空间或模型空间；**图纸管理全套**：drawing_management.py（图纸编号系统/目录/图签+会签栏/门窗表/材料做法表/结构设计说明/设备材料表/工程量清单 + CompleteDrawingManager 一键出全部表格）；**高级专业模板**：templates_advanced.py 十个模块——总平面图、防火分区·消防疏散图、空调系统图、防排烟系统图、雨水系统图、火灾报警系统图、智能化系统图、施工进度横道图、施工总平面图、钢结构详图（钢柱/钢梁）；**图纸审查系统**：v1.8.0 起 drawing_review.py 对图纸做 图层/图框/文字/尺寸/完整性/规范引用 六项自动检查，出 A~D 评级报告（文本 + 写入 DXF），ReviewAwareDxfBuilder 支持一行 .review()，BatchReviewer 批量汇总；**自然语言生成图纸**：v1.9.0 起 natural_language_engine.py 把中文描述（如「12x8 米三层住宅平面图带客厅厨房卧室」）按规则解析 → dispatch 到 26 类真实模板函数（含 ③ 层 7 类节点大样：16G101 混凝土 4 类「梁柱节点/楼梯节点/基础节点/桩基节点」+ GB 50017 钢结构 3 类「钢柱脚/钢梁柱栓焊混接/钢梁拼接」）→ 一键出图，NLAwareDxfBuilder 提供 `generate_from_text(text)`/`parse_text(text)` 入口；**识图评测集** `benchmarks/`（v1.17.6 起）：真实图纸真值表（含 `provenance` 来源字段）+ `eval.py` 报「严格/宽松/拒识/空答/**认错**」五口径并**按来源分组**（认错率只认 `external` 真实出图样本）+ `check_provenance.py` 来源取证闸门（用 `$LASTSAVEDBY` 识别自产样本，防止稀释指标；对 `aspose` 等**抹掉元数据的转换产物**另有**结构指纹兜底**：`$ACADVER` + 实体量级 + 图层数）；**DWG→DXF 预处理** `examples/dxf_prepare.py`（v1.17.8）：剥 OBJECTS 段 / 删畸形表记录 / 剥离缩略图 XDATA / 二进制块归一 / **补三处结构缺陷**（漏写的 `SEQEND`，含 `66=1` 声明但无 ATTRIB 的情形）/ **补未闭合 SECTION 的 `ENDSEC`** / **删空句柄组**，自带**组数守恒断言 + 两道结构自检**，不守恒即抛错拒写；**统一验证入口** `examples/verify_all.py`（v1.17.5）：一句话跑完全部 verify 套件并汇总；**一键流水线**：v1.16.0 起 pipeline.py 把「出图→识图→算量→施工说明→审查→渲染→3D体量→汇总」串成一条链，`pipeline("一句话", out_dir)` 一次产出全套交付包（DXF + 工程量清单 4 格式 + 施工说明 + 识图报告 + 审查报告 + 3D 模型/HTML + manifest 清单），单条约 2.7 秒；**v1.17.0 起施工说明自动写入图纸空间说明栏**（按国标图框几何算出，装不下自动分页为「说明续页」图幅），模型空间保持干净；新增**成品图幅渲染**（`space='paper'`，出图框+标题栏+说明栏+视口图形的打印效果图），并修复 `add_gb_sheet` 从 v1.14 起就存在的**视口比例 bug**（`add_viewport` 第 4 参是 view_height 不是比例，导致视口只看到 0.01mm 切片）；**v1.17.1 起识图读取通用化**：`drawing_reader` 增加容错加载（严格失败自动退 recover）与 `\U+XXXX` 中文转义解码（外部软件转出的真实图纸图层名常写成 `IRC\U+5929\U+82B1`，不解码会让按图层名匹配的规则静默失效），并容忍无名图层；配套 `examples/dxf_prepare.py` 做 DXF 预处理（剥 OBJECTS 段 + 删缺名字的表记录），`examples/dwg2dxf_convert.py` 用 aspose-cad 的 `CadOutputMode.CONVERT` 把 DWG 忠实转 DXF。**v1.17.9 起识图支持「弃权」**：`DrawingInfo` 新增 `type_margin`（决策裕度 = top1-top2）/ `abstained` / `abstain_reason`，低置信或**并列**时拒绝作答并把图别回退为占位符 `"未识别"`（保持字符串契约、不写 None，避免下游崩）；配套 `score_drawing_types()` / `infer_drawing_type_ex()` / `set_abstain_thresholds()`，`eval.py` 新增 `--abstain-conf` / `--abstain-margin` / `--sweep`。★ 实证结论：**置信度阈值是空操作**（conf 仅 {0.0,0.5,0.7} 三档且对错两组完全重叠，0.3/0.4/0.5 与关闭逐桶相同），**决策裕度 margin 才有判别力**（margin≥0.2 → 自信答错 16→3 且严格正确零损失）；门槛**默认关闭**以保基线可复现，翻转前须先把 external 扩到 ≥30 张。
category: engineering-cad
version: 1.17.12
author: 小海(WorkBuddy)
---

# DXF 生成器（自然语言 → DXF）

把用户的自然语言绘图需求转成真实可打开的 DXF 文件。底层用 `ezdxf` 纯 Python 离线生成，不需要 AutoCAD。

## 何时使用
- 用户说"生成/画一个 DXF""出一张平面图/户型图/零件图/布置图/电气图/电路板"
- 需要矢量交换文件（给 CAD 软件、激光切割、数控、打印）
- 任何"把图形保存为 .dxf"的需求
- 需要"读一张已有的 DXF 改一改""批量出图""换配色风格"

## 依赖
- `ezdxf`：`pip install ezdxf`（装在隔离 venv 内，已验证 1.4.4）。
- 本 skill 自带 `scripts/dxfkit.py`（高层绘图库）+ `scripts/templates.py`（模板+自然语言分发）。

## 调用流程
1. **理解需求**：尺寸（mm）、面宽/进深、层数、房间/构件清单、门窗位置、是否需要尺寸标注、是否读旧图改、要不要批量、想要什么风格。
2. **加载工具库**：
   ```python
   import sys, os
   sys.path.insert(0, os.path.join(<skill_dir>, "scripts"))
   from dxfkit import DxfBuilder, batch, STYLES
   from templates import rect_with_mounting_holes, three_room_flat, circuit_board, random_dots, nl_dispatch
   ```
3. **建图 / 导入**：
   - 新建：`b = DxfBuilder(style="architectural")`（自动建好该风格图层）。
   - 导入修改：`b = DxfBuilder.from_file("old.dxf")`（在其上继续画/追加）。
4. **按描述画**（见下方 API）。
5. **保存 + L3 验证**：`rep = b.save(path)` → 检查 `rep["layers"]` 关键图层齐全、`rep["bbox"]` 尺寸与需求一致。
6. **交付**：告知路径 + 图层数 + 外包盒尺寸；提示"AI 生成，专业图纸须经注册工程师复核"。

---

## 五大功能

### ① 自然语言分发（`templates.nl_dispatch` + `natural_language_engine.NLAwareDxfBuilder`）
把口语指令直接转成 DXF，覆盖用户示例：
```python
from templates import nl_dispatch
nl_dispatch("生成一个 100x50 的矩形带四个安装孔", "out/rect.dxf")        # 矩形+四角安装孔
nl_dispatch("创建一个三室一厅的平面布局图",    "out/flat.dxf")            # 三室一厅户型
nl_dispatch("生成 1000 个随机分布的圆点",      "out/dots.dxf")            # 1000 随机点
```
内部用正则解析尺寸/数量，分发到对应参数化模板；识别不了会抛 `ValueError` 提示改用模板函数。

### ② 参数化模板（`templates.py`）
同一模板传不同参数出不同规格，典型模板：
- `rect_with_mounting_holes(b, w=100, h=50, hole_d=5, margin=10, layer="WALL")` — 矩形四角安装孔（机械面板）。
- `three_room_flat(b, w=12000, d=10000)` — 三室一厅户型（客厅+三卧+门窗+隔墙+尺寸）。
- `circuit_board(b, w=100, h=80, pads=20, seed=0)` — 板框+随机焊盘/过孔（style="electronics"）。
- `random_dots(b, n=1000, w=200, h=200, seed=0, layer="AUX", kind="point"|"circle")` — 随机分布点/小圆。
参数化是核心卖点：改 `w/h/pads/seed/style` 即换规格，无需重写绘图代码。

### ③ 样式系统（`DxfBuilder(style=...)` + `STYLES`）
预设四套图层/颜色/线宽组合，一键切换配色风格：
| style | 用途 | 图层 |
|---|---|---|
| `architectural` | 建筑/户型 | WALL/DOOR/WIN/STAIR/DIM/TXT/AUX/TITLE |
| `mechanical` | 机械零件 | PART/HIDDEN/CENTER/DIM/TXT/CUT/THREAD/AUX |
| `electronics` | 电路板 | BOARD/COPPER/PAD/SILK/VIA/DIM/TXT/KEEPOUT |
| `blueprint` | 蓝图（浅色细线） | OBJ/DIM/TXT/AUX |
`b = DxfBuilder(style="electronics")` 建图即带对应图层。图层约定：颜色号按 AutoCAD 标准（7白/6品红/4青/2黄/1红/5蓝/8灰），线宽单位 1/100mm。

### ④ 批量处理（`dxfkit.batch`）
一次生成多张 DXF：
```python
from dxfkit import batch
def mk(b, spec):
    rect_with_mounting_holes(b, w=spec["w"], h=spec["h"], hole_d=spec["hole_d"], layer="PART")
batch([{"name":"A","style":"mechanical","w":80,"h":40,"hole_d":4},
       {"name":"B","style":"mechanical","w":120,"h":60,"hole_d":5},
       {"name":"C","style":"mechanical","w":160,"h":80,"hole_d":6}],
      "out/", mk)   # 返回每张的 save() 报告列表
```
`spec` 里 `style/name` 为保留字段，其余透传给 `maker(b, spec)`。

### ⑤ 导入修改（`DxfBuilder.from_file`）
读已有 DXF 在其上追加/修改（不丢原内容）：
```python
from dxfkit import DxfBuilder
b = DxfBuilder.from_file("old.dxf")
b.text("MODIFIED", 50, 30, h=6, layer="AUX", align="CENTER")  # 追加文字
b.save("old_modified.dxf")
```
`_init_layers(style=None)` 时沿用 architectural 默认图层，新引用的图层会按需懒创建（`_ensure_layer`）。

---

## 扩展模块（v1.2.0 新增）
| 模块 | 内容 | 入口 |
|---|---|---|
| `scripts/geomkit.py` | 高级几何：椭圆、参数化齿轮、阿基米德螺旋线、贝塞尔曲线（de Casteljau，含控制多边形） | `geomkit.gear(b, cx, cy, R, Z)` 等 |
| `scripts/archkit.py` | 建筑标准构件：轴网/轴线、双线墙、标准门(弧线开启)/窗(四线)、楼梯、标高符号、指北针、柱(填充)/梁、A0~A4 图框+标题栏、标准户型生成器 | `archkit.residential_layout(b, w, d)` |
| `scripts/budget.py` | 工程量估算→造价预算→采购清单，导出 CSV/JSON/Excel/Markdown | `QuantityCalculator` / `BudgetGenerator` / `procurement_list()` |
| `scripts/templates_arch.py` | **建筑专业**：立面图（平/坡屋顶）、剖面图（基础/楼板/梁/楼梯/图例）、节点大样（构造层做法）、**楼梯详图**（平面+剖面+参数表+2h+b 校核） | `ElevationParams` / `SectionParams` / `DetailParams` / `StairDetailParams` |
| `scripts/templates_struct.py` | **结构专业**：钢筋通用符号（`bar`/`bar_label`/`bar_mark`/`hook`）、柱配筋、板配筋、基础（条形/独立）、楼梯配筋 | `ColumnRebarParams` / `SlabRebarParams` / `FoundationParams` / `StairRebarParams` |
| `scripts/templates_mep.py` | **机电专业**：10 种电气符号（灯具/开关/插座/配电箱/接地/弱电）、**电气图例表**、简易照明平面布置 | `electrical_legend()` / `lighting_plan()` |

专业模板统一签名 `func(b, params, x=0, y=0)`，参数用 dataclass 承载（改字段即换规格）。

统一约定：所有函数第一个参数是 `b`（DxfBuilder 实例），即 `func(b, ...)`。

---

## GB/T 国标标准化（v1.4.0 新增）

把全部图层 / 线型 / 线宽 / 符号 / 文字 / 图框统一到中国国家建筑制图标准。
核心文件 `scripts/gb_standards.py`，通过 `GBDxfBuilder` 启用：

```python
import sys, os
sys.path.insert(0, os.path.join(<skill_dir>, "scripts"))
from dxfkit import GBDxfBuilder          # 国标模式构建器

b = GBDxfBuilder(style="gb_architectural")
# 1) 标准 A3 图框 + 标题栏（图纸空间，含 1:100 视口出图）
b.add_gb_sheet("A3", title_data={"project":"15m别墅","title":"一层平面图",
                                  "scale":"1:100","drawing_no":"建施-01"})
# 2) 标准轴线 / 符号 / 尺寸（在 1:1 模型空间用于 1:100 出图时传 scale=100）
b.add_gb_axis(0, 0, 12000, 0, label1="1", label2="")
b.add_gb_symbol(5000, -100, "标高", value="+0.000")
b.add_gb_dimension(0, -50, 12000, -50)
# 3) 平面等几何照常画（archkit / templates_*，已统一为 GB 图层）
import archkit
archkit.residential_layout(b, width=12000, depth=8000)
b.save("gb_plan.dxf")
```

### 国标配置（gb_standards.py 七类标准）
| 类 | 标准依据 | 关键内容 |
|---|---|---|
| `LayerStandard` | GB/T 50001-2017 | 48 个国标图层：`G_*`建筑 / `S_*`结构 / `P_*`给排水 / `E_*`电气 + `BORDER`/`TITLE_BLOCK`；专业代码_构件名 |
| `LineTypeStandard` | GB/T 50001-2017 | 线宽等级 粗0.50/中0.35/细0.18/特细0.13；线型 实线/虚线(DASHED)/点划线(CENTER)/双点划线(PHANTOM)/折断线(DIVIDE) |
| `SymbolStandard` | GB/T 50162-92 | 轴号圆/索引圆/标高/剖切等符号尺寸；钢筋等级符号 φ/Φ |
| `TextStandard` | GB/T 50103-2014 | 图名7 / 子图名5 / 尺寸数字3.5 / 轴号3.5（图纸毫米）等；字体 gbcbig.shx/gbenor.shx/romans.shx |
| `BorderStandard` | GB/T 50001-2017 | A0~A4 图幅；装订边统一左25其余10；标题栏 180×56、4 行、列宽 [45,30,30,30,45] |
| `DrawingStandard` | GB/T 50104-2014 | 比例序列与常用比例；尺寸标注（箭头2.5/字高3.5/偏移5） |
| `LegendStandard` | — | 建筑/结构/给排水/电气分类图例 |

### GBDxfBuilder 新增方法
- `add_gb_axis(x1,y1,x2,y2,label1,label2,scale=100)` — CENTER 点划线轴线 + 两端轴号圆。
- `add_gb_symbol(x,y,symbol_type,value,scale=100)` — `轴号`/`标高`/`索引`/`剖切` 国标符号。
- `add_gb_dimension(x1,y1,x2,y2,offset,scale=100)` — 国标对齐尺寸（尺寸线+界线+起止短线+数字）。
- `add_gb_border(paper_size, title_data, layout=None)` — 国标图框（外框+内框）+ 标题栏（可指定画在图纸空间 layout）。
- `add_gb_sheet(paper_size, title_data, view_center, scale=1/100, name)` — **在图纸空间新建 A3 图幅**：画图框+标题栏，并加一个显示模型、比例为 `scale` 的视口，使 1:1 模型正确出图（这才是符合国标「模型 1:1 + 图纸空间视口」的标准做法）。

`GB_STYLES` 提供四种专业风格预设（gb_architectural / gb_structural / gb_plumbing / gb_electrical），已并入 `dxfkit.STYLES`，
故 `DxfBuilder(style="gb_architectural")` 也能直接用。普通 `DxfBuilder` 仍向后兼容，未受影响。

### 图层命名已统一（archkit / templates_*）
archkit 与三个专业模板已全部改用国标图层名：`G_WALL`/`G_DOOR`/`G_WINDOW`/`G_AXIS`/`G_DIM`/`G_TEXT`/`G_STAIR`/`G_SECTION`/`G_DETAIL`/`G_HATCH`/`G_ELEVATION`/`G_ROOF`（建筑），`S_REBAR`/`S_COLUMN`/`S_FOUNDATION`/`S_SLAB`/`S_HATCH`/`S_TEXT`（结构），`E_LIGHT`/`E_SWITCH`/`E_SOCKET`/`E_WIRE`/`E_EQUIPMENT`/`E_GROUND`/`E_TEXT`（电气）。颜色/线宽按国标取值。

```python
import sys, os
sys.path.insert(0, os.path.join(<skill_dir>, "scripts"))
from dxfkit import DxfBuilder
import geomkit, archkit
from budget import QuantityCalculator, BudgetGenerator, procurement_list

b = DxfBuilder(style="architectural")
archkit.residential_layout(b, width=12000, depth=8000, title="标准层平面图", elev=3.0)
b.save("flat.dxf")
```

⚠️ **比例陷阱**：`archkit.border/title_block` 按**纸张毫米**绘制（A3=420×297），
平面图是 **1:1 实际毫米**（如 12000×8000）。两者**不要画在同一张模型空间图**，
否则会出现「12000mm 平面塞进 420mm 图框」的比例错误。
**正确做法（国标）**：平面/立面/剖面等画在**模型空间 1:1**，用 `GBDxfBuilder.add_gb_sheet("A3", ...)`
在**图纸空间**放图框+标题栏+**1:100 视口**来出图——`add_gb_sheet` 已自动处理好缩放与布局。

⚠️ **双线墙偏移**：`archkit.wall()` 以轴线为中心向两侧各偏 `thickness/2`，
故 WALL 图层外包盒比轴线矩形外扩 t/2（如 t=240 → 外扩 120），校验时要算进去。

⚠️ 预算模块是**方案阶段数量级估算**，单价/含量均为可配置经验系数常量
（`UNIT_PRICES` / `QUANTITY_PER_SQM` / `LABOR_PER_SQM` 等），
**不能**作为招标控制价/合同价/结算依据，正式造价须由注册造价工程师编制。

## 中文字体支持（v1.5.0 新增 · 解决中文显示 ?? 乱码）

**问题**：用 ezdxf 直接 `msp.add_text("客厅")` 生成的 DXF，在 AutoCAD/中望/浩辰里打开时中文会显示为 `??` 或方块——因为默认 STYLE 没有中文大字体（DXF 组码 107 / `bigfont` 属性）。

**解决**：`scripts/font_manager.py` + `dxfkit.py` 自动注入（无需任何用户改动）。

```python
from dxfkit import DxfBuilder, GBDxfBuilder
b = GBDxfBuilder(style='gb_architectural')  # 自动注册 GB_CHINESE/GB_TITLE/GB_MULTILINE
b.text("客厅", 0, 0, h=300)               # 自动绑定 GB_CHINESE (gbenor.shx+gbcbig.shx)
b.add_multiline_text(0, 1000, "技术要求：\n1. 墙厚 200mm", width=300, height=300)
b.save("room.dxf")
```

### 字体映射（按优先级自动检索）
| 类别 | 字体 |
|---|---|
| ASCII | `gbenor.shx` / `txt.shx` / `Arial.ttf` |
| 中文 | `gbcbig.shx` / `chinese.shx` / `SimSun.ttc` / `SimHei.ttf` / `NotoSansCJK-Regular.ttc` |
| 搜索路径 | `C:\Windows\Fonts`、`/usr/share/fonts`、`/Library/Fonts`、AutoCAD/ZWSOFT 安装目录（`*.shx`） |

### 三种 GB 文字样式
| 样式 | dxf.font | dxf.bigfont | 用途 |
|---|---|---|---|
| `GB_CHINESE` | `gbenor.shx` | `gbcbig.shx` | 普通中文标注、标题栏 |
| `GB_TITLE` | `gbenor.shx` | `gbcbig.shx` | 大字高（7.0）图名/标题 |
| `GB_MULTILINE` | `gbenor.shx` | `gbcbig.shx` | MTEXT 多行说明 |

### 验证与诊断
```bash
python examples/verify_fonts.py     # 生成测试图 + 校验 100% 中文绑定 GB_CHINESE
python -c "from font_manager import FontInstaller; FontInstaller.report()"
```

输出示例（本机实测）：
```
🔍 中文字体检索结果（按优先级）:
  ✅ gbcbig.shx          ← 本机有
  ✅ simsun.ttc          ← Windows 系统字体
  ✅ simhei.ttf
  ✅ simfang.ttf
→ 默认字体组合: ASCII=gbenor.shx  CJK=gbcbig.shx
```

### 关键 API
| 类/函数 | 说明 |
|---|---|
| `FontConfig.find_font(name)` | 跨路径检索字体文件，返回绝对路径或 None |
| `FontConfig.has_cjk(s)` | 判断字符串是否含中文字符 |
| `TextStyleManager(doc).setup_all()` | 在 doc 上注册三个 GB 样式 |
| `apply_font_awareness(cls)` | 返回带字体感知的 DxfBuilder 子类（包装而非继承，避免循环依赖） |
| `FontInstaller.check_chinese_fonts()` | 检查中文字体可用性，返回 `[(name, found),...]` |
| `FontInstaller.create_font_mapping_file()` | 生成 `acad.fmp`（AutoCAD 字体映射文件） |

### 重要约束
- ezdxf 的 STYLE 实体中文大字体属性叫 `bigfont`（**小写无下划线**），不是 `big_font`；DXF 组码 107
- MTEXT 实体字高属性叫 `char_height`（**不是 `height`**），否则 `DXFAttributeError`
- `set_placement(align=...)` 仍需传 `TextEntityAlignment` 枚举（字符串会 AssertionError）
- 没有 gbcbig.shx 时降级用 SimSun.ttc/SimHei.ttf，但仍写入 `bigfont=gbcbig.shx`（DXF 规范名），AutoCAD 找不到时会弹字体映射对话框

### 11 张全套施工图验证结果（实测）
```
Drawing                      GB_styles  CJK TEXT   all GB_CHINESE?
建施-01 一层平面图.dxf       Y          13         ✅ 13/13
建施-02 二层平面图.dxf       Y          13         ✅ 13/13
建施-03 三层平面图.dxf       Y          13         ✅ 13/13
建施-04 正立面图.dxf         Y          10         ✅ 10/10
建施-05 1-1剖面图.dxf       Y          19         ✅ 19/19
建施-06 楼梯详图.dxf         Y          18         ✅ 18/18
电施-01 电气图例.dxf         Y          31         ✅ 31/31
电施-02 照明平面图.dxf       Y          10         ✅ 10/10
结施-01 柱配筋图.dxf         Y          7          ✅ 7/7
结施-02 板配筋图.dxf         Y          9          ✅ 9/9
结施-03 基础平面图.dxf       Y          7          ✅ 7/7
TOTAL: 150 CJK texts, 150 routed to GB_CHINESE (100%)
```

## 施工说明模块（v1.6.0 新增 · 按 GB 规范自动生成说明）

**问题**：施工图右下角/右侧说明栏需写"施工说明"，逐条手敲既慢又易漏规范条款。

**解决**：`scripts/construction_notes.py`（纯逻辑 + `ConstructionNoteMixin` 混入，无循环依赖）。
`GBDxfBuilder` 已通过多重继承获得 `add_construction_notes` / `add_construction_notes_by_discipline` /
`set_project_info`，开箱即用。

```python
from dxfkit import GBDxfBuilder
b = GBDxfBuilder(style="gb_architectural")
b.set_project_info("15m别墅", "一层平面图", "建施-01")
layout = b.add_gb_sheet("A3", title_data={...}, view_center=(6000,4000), scale=1/100, name="建施-01")
# 建筑专业全套施工说明 → 直接画进图纸空间右侧说明栏（图纸毫米）
b.add_construction_notes_by_discipline("architectural", target=layout,
                                        x=232, y=283, width=175,
                                        text_height=2.5, line_spacing=3.5, title_height=4.0)
b.save("plan.dxf")
```

### 数据模型与模板
| 类 | 说明 |
|---|---|
| `ConstructionPhase` | 12 个施工阶段枚举：GENERAL/EARTHWORK/FOUNDATION/STRUCTURE/MASONRY/ROOF/FINISHING/PLUMBING/ELECTRICAL/HVAC/FIRE/SAFETY |
| `ConstructionNote` / `ConstructionNotes` | 单条说明（阶段/内容/优先级/规范号）/ 说明集合（一般+专项+引用规范+特殊要求） |
| `NoteTemplates` | 12 阶段模板库（含 GB 规范编号，如 GB 50204-2015 混凝土、GB 50303-2015 电气、JGJ 80-2016 安全）+ `BY_DISCIPLINE` 按专业分组的说明清单 |
| `ConstructionNoteGenerator` | `generate_notes(discipline, phases?, custom_notes?)` → `ConstructionNotes`；`format_notes()` → 纯文本/Markdown |
| `get_notes_for_drawing_type(type)` | 按图纸类型（floor_plan/elevation/section/beam_rebar/...）返回推荐 `{discipline, phases}` |

### 专业 → 说明映射（BY_DISCIPLINE）
| 专业 discipline | 包含的说明阶段 |
|---|---|
| `architectural` | 一般 + 土方 + 基础 + 主体 + 砌体 + 屋面 + 装饰 + 安全 |
| `structural` | 一般 + 基础 + 主体 + 安全 |
| `plumbing` | 一般 + 给排水 + 消防 + 安全 |
| `electrical` | 一般 + 电气 + 安全 |

### 关键 API（GBDxfBuilder 已具备）
| 方法 | 说明 |
|---|---|
| `set_project_info(name, drawing, no="")` | 设置工程/图名/图号，注记到说明抬头 |
| `add_construction_notes(notes, x, y, width, line_spacing, text_height, title_height, scale, target, layer, title_layer)` | 把 `ConstructionNotes` 画到 `target`（图纸空间 Layout → 图纸毫米；None → 模型空间按 `scale` 放大） |
| `add_construction_notes_by_discipline(discipline, custom_notes, x, y, width, line_spacing, text_height, title_height, scale, target, ...)` | 按专业快捷生成并绘制（默认 A3 说明栏坐标 x=232,y=283,width=175） |

### 重要约束（已对原始方案纠错）
- 本模块**不 import dxfkit**，靠 `ConstructionNoteMixin` 多重继承注入，避免循环依赖（与 font_manager 同思路）。
- `_wrap_text` 按**显示宽度**逐字换行（CJK≈1.0×字高、ASCII≈0.55×字高），原方案用空格 split 会让中文溢出宽度。
- 阶段→键映射用 `PHASE_TO_KEY` 显式字典（原方案字符串 replace 推导会得到中文键，匹配不到 `BY_DISCIPLINE` 的英文键）。
- 图纸空间说明栏用**图纸毫米**坐标（`text_height=2.5/line_spacing=3.5`）；模型空间要按 `scale`（默认 100，对应 1:100）放大才可见——直接写 `height=3` 在 1:100 下只有 0.03mm 看不见。
- 说明文字自动走 `GB_CHINESE`，标题/阶段名走 `GB_TITLE`（由 font_manager 注入），中文字体不乱码。
- `gb_full_set.py` 已对 11 张图按专业写入说明：建施→architectural、结施→structural、电施→electrical。

### 全套施工图说明栏验证结果（实测）
```
Drawing                    discipline     图纸空间说明 TEXT  样式
建施-01 一层平面图.dxf     architectural   107            GB_CHINESE+GB_TITLE
建施-02 二层平面图.dxf     architectural   107
建施-03 三层平面图.dxf     architectural   107
建施-04 正立面图.dxf       architectural    95
建施-05 1-1剖面图.dxf     architectural   100
建施-06 楼梯详图.dxf       architectural   100
结施-01 柱配筋图.dxf       structural       56
结施-02 板配筋图.dxf       structural       58
结施-03 基础平面图.dxf     structural       53
电施-01 电气图例.dxf       electrical       67
电施-02 照明平面图.dxf     electrical       46
TOTAL: 896 TEXT, 100% 走 GB_CHINESE/GB_TITLE（无 Standard 回退）
```

## 施工规范引用模块（v1.7.0 落地 · 规范库 64 条 × 13 类）

**问题**：施工图说明栏需列出"本图执行规范"，逐条手敲易漏且编号易错。

**解决**：`scripts/construction_codes.py`（数据模型 + 纯逻辑 + `_CodeAwareMixin` 混入，无循环依赖）。
`CodeAwareDxfBuilder = _CodeAwareMixin + GBDxfBuilder`，已同时具备 字体感知 + 施工说明 + 规范引用。

```python
from dxfkit import CodeAwareDxfBuilder
b = CodeAwareDxfBuilder(style="gb_architectural")
layout = b.add_gb_sheet("A3", title_data={...})            # 图纸空间图框
b.add_code_references("structural", target=layout,          # 图纸空间（纸毫米）
                      x=232, y=160, width=175, line_spacing=3.0)
b.add_code_references("structural", target=None, x=0, y=0,  # 或模型空间（自动 ×100）
                      scale=100.0, width=5000, line_spacing=350)
```

| 类 / 函数 | 说明 |
|---|---|
| `CodeReference` / `CodeList` | 单条规范（编号/名称/类别/适用图纸/优先级）/ 按图纸类型聚合清单（强条/推荐/参考） |
| `CodeDatabase` | 静态规范库 **64 条 × 13 类**（综合/地基基础/混凝土/钢筋/砌体/钢结构/屋面防水/装饰/给排水/电气/暖通/消防/安全）；`get_codes_by_drawing_type()` / `get_codes_by_category()` / `search_codes()` / `get_code_by_number()` |
| `CodeFormatter` | `format_code_list()` 纯文本；`format_for_dxf()` 限量排版（强条全列，推荐/参考限量） |
| `CodeReferenceTemplates` | 按 drawing_type（floor_plan/elevation/section/beam_rebar/...）预置模板 |
| `CodeAwareDxfBuilder` | `add_code_references(drawing_type,x,y,width,line_spacing,target,scale,...)` / `add_full_code_reference()` / `get_code_summary()` |
| `search_code()` / `list_codes_by_category()` | 命令行/脚本辅助 |

**纠错记录**：`_CodeAwareMixin.__init__(*args, **kwargs)` 透明透传（原方案固定 `(filename=None, style=...)` 会把 filename 绑到 style 上出错）。默认**不替换**全局 `DxfBuilder`，`CodeAwareDxfBuilder` 是独立新类，向后兼容 style='mechanical' 等旧示例。

## 图纸管理全套（v1.7.0 落地 · 编号→目录→图签→表格 一键出）

**解决**：`scripts/drawing_management.py` —— 纯数据编排类，全部 `add_to_dxf(builder, ...)` **显式注入 builder**（不需 builder 状态，与 mixin 相反的封装策略）。

```python
from dxfkit import GBDxfBuilder, DrawingDiscipline
from drawing_management import CompleteDrawingManager, DoorWindowItem, BillItem
b = GBDxfBuilder(style="gb_architectural"); b.add_gb_border("A2", title_data={...})
m = CompleteDrawingManager(); m.setup_project("某项目", "某院")
m.add_drawing(DrawingDiscipline.ARCHITECTURAL, "一层平面图", "1:100", "A2")
m.door_window.add(DoorWindowItem("M-01", "门", 900, 2100, 2, "木门", "", "入户门"))
m.boq.add(BillItem("010101", "平整场地", "m²", 240, 8.5))
m.generate_all_documents(b)          # 目录/图签/门窗/材料/结构说明/设备/工程量 → DXF+dict
print(m.boq.format_bill())           # 纯文本打印
```

| 类 | 功能 |
|---|---|
| `DrawingDiscipline` | 专业常量：建施/结施/水施/电施/暖施/消施/景施/内施 |
| `DrawingInfo` / `DrawingNumberSystem` | 图纸信息 / 按专业自动编号（建施-01…），`find_by_no`/`get_by_discipline` |
| `DrawingCatalog` | 图纸目录自动生成 + 画入 DXF |
| `SignatureBlock(Generator)` | 国标图签（4 行 5 列）/ 多专业会签栏 |
| `DoorWindowSchedule` | 门窗表（型号/规格/数量汇总 M/C 计数） |
| `MaterialSchedule` | 标准做法库 地面1/地面2/墙面1/墙面2/屋面1 + 构造层表 |
| `StructuralDesignNote` | 结构设计说明 5 段模板（总则/基础/结构/监测/特殊） |
| `EquipmentSchedule` | 设备材料表（按专业） |
| `BillOfQuantities` | 工程量清单（分部分项，总价自动=数量×单价） |
| `CompleteDrawingManager` | 总编排：项目→图纸→目录→图签→门窗→材料→结构说明→设备，一键生成 |

## 高级专业模板（v1.8.0 新增 · 最后一批补齐 10 模块）

`scripts/templates_advanced.py`：统一签名 `func(b, params, x=0, y=0)`，自带专业前缀图层（SP_/FS_/HVAC_/SE_/RW_/FA_/IS_/SCH_/CS_/ST_），不 import dxfkit。

| 专业 | 模板函数 | Params |
|---|---|---|
| 建筑 | `site_plan` 总平面图（场地/环路/绿化/停车/指北针） | `SitePlanParams` |
| 建筑 | `fire_safety` 防火分区·消防疏散图（分区/防火墙/出口/路线/设施） | `FireSafetyParams` |
| 暖通 | `hvac_system` 空调系统图（室外机/冷媒立管/室内机/新风/排风） | `HVACParams` |
| 暖通 | `smoke_exhaust_system` 防排烟系统图（排烟竖井/加压送风/70℃阀） | `SmokeExhaustParams` |
| 给排水 | `rain_water_system` 雨水系统图（天沟/87型雨水斗/立管/检查井） | `RainWaterParams` |
| 电气 | `fire_alarm_system` 火灾报警系统图（控制室/总线/烟感温感/手报声光） | `FireAlarmParams` |
| 电气 | `intelligent_system` 智能化系统图（管理中心+5 子系统+终端） | `IntelligentSystemParams` |
| 施工 | `schedule_gantt` 施工进度计划横道图（周轴/工序条/关键线路） | `ScheduleParams` |
| 施工 | `construction_site` 施工总平面图（围挡/道路/塔吊覆盖/临建） | `ConstructionSiteParams` |
| 结构 | `steel_structure` 钢结构详图（member_type=column/beam，栓/焊连接） | `SteelStructureParams` |

```python
import sys; sys.path.insert(0, <skill>/scripts)
from dxfkit import DxfBuilder
import templates_advanced as adv
b = DxfBuilder(style="architectural")
adv.fire_safety(b, adv.FireSafetyParams(fire_zones=2, exits=4))   # 画进模型空间
adv.ADVANCED_TEMPLATES["gantt"](b, adv.ScheduleParams())           # 或走注册表/自然语言分发
b.save("out.dxf")
```

**注意**：这些是**模板级出图**（模型空间内容，本身不带图框）；正式出图请配 `GBDxfBuilder + add_gb_sheet(...)`（参考 `gb_full_set.py` 模式）。

## 图纸审查模块（v1.8.0 新增 · 六项自动检查 + 批量 + 评级）

`scripts/drawing_review.py`：纯逻辑，不 import dxfkit；与 `dxfkit.py` 通过末尾 try/except 接线。
审图不替换全局 `DxfBuilder`，而是新增 `ReviewAwareDxfBuilder = integrate_review_to_builder(CodeAwareDxfBuilder)`。

```python
from dxfkit import ReviewAwareDxfBuilder
b = ReviewAwareDxfBuilder(style="gb_architectural", discipline="architectural")
b.add_gb_sheet("A3", title_data={...})          # 标准图框 + 1:100 视口
b.add_rectangle(0, 0, 12000, 8000, layer="G_WALL")  # 画内容…
result = b.review("一层平面图")                   # -> ReviewResult
print(b.reviewer.generate_report(result))        # 文本报告（A~D 评级）
b.generate_review_report(result, target=layout, x=45, y=175)  # 报告写进图纸
```

| 检查项 | 内容 | 严重度 |
|---|---|---|
| 图层 | 必需图层缺失 / 颜色建议 / 系统保留层 | ERROR/WARNING/INFO |
| 图框 | A 系列图框检测（跨模型+图纸空间）/ 标题栏 | ERROR/WARNING |
| 文字 | 字高按空间分阈值（纸 1.5~12mm / 模型 150~3000）+ 中文字体 | WARNING/INFO |
| 尺寸 | 尺寸标注完整性（DIMENSION + *_DIM 手绘层） | WARNING |
| 完整性 | 图名 / 比例 / 规范编号 | WARNING/INFO |
| 规范引用 | GB/JGJ 编号存在性 | INFO |

`ReviewResult`：`grade`（A 优秀/B 良好/C 合格/D 不合格）、`is_approved`、`errors/warnings/info/passed`。
`BatchReviewer.review_multiple(builders, names, disciplines)` → 汇总 + `generate_summary_report()`。

**纠错记录（相对原稿）**：① 补 `from datetime import datetime`；② dataclass 缺 `default_factory` 会 TypeError → 已修；③ ezdxf rect 是 **5 顶点闭环**，原稿 4 顶点判定永远找不到图框 → 改为跨空间扫 A 系列宽高比(≈√2) 闭合矩形；④ 图框常画在**图纸空间**而 msp 无 → 检查需遍历 layouts；⑤ 文字高度阈值原稿按"图纸毫米"一刀切，对 1:1 模型空间(mm)不适用 → 按空间分档；⑥ `LayerReviewRules` 扩展到高级模板专业键（site_plan/construction_site/fire_safety/hvac/smoke_exhaust/rain_water/fire_alarm/intelligent/schedule/steel）。

**实测结果**（examples/drawing_review_demo.py）：合格图（图框+标题+尺寸+规范）→ **A (优秀) 0 错 0 警**；坏图（无图框/无比例/少尺寸）→ **C (合格)** 2 错 3 警，能正确拦下；批量审 6 张高级模板（模板本身无图框 → 全部报 BORDER 错误，属预期，正式出图时由 sheet() 补图框后再审）。

## 自然语言生成图纸（v1.9.0 新增 · 中文描述 → DXF）

把「12x8 米三层住宅平面图带客厅厨房卧室」这种口语指令直接转成 DXF。入口：builder 调 `generate_from_text(text, filename)`，或先 `parse_text(text)` 拿解析结构再看要不要继续。

### 4 个核心组件

| 类 / 函数 | 职责 | 关键方法 |
|---|---|---|
| `NLPParser` | 正则解析中文文本 → `{drawing_type, dimensions, quantities, style, materials, rooms, openings, features, confidence}` | `parse(text) -> Dict`，`get_confidence_text(c)` |
| `NaturalLanguageGenerator` | 19 类 dispatch 表 → 调真实模板函数 → 自动追加施工说明/规范 → 落盘 | `generate(text, filename) -> Dict` |
| `NLInterface` | 命令行交互提示（帮助/示例） | `show_help()`, `show_examples()` |
| `integrate_nl_to_builder(cls)` | mixin 注入 NL 能力 → 返回 `NLAwareXxxBuilder` | 新增 `generate_from_text`, `parse_text`, `nl_parser` |

### 19 类 dispatch 映射（已实测，全部能跑）

| drawing_type | 真实模板函数（来源） | 说明 |
|---|---|---|
| `floor_plan` | `archkit.residential_layout` | 真实户型（含客厅/卧室布局 + 外门窗 + 尺寸标注） |
| `elevation` | `templates_arch.elevation` | 立面 + 楼层 + 窗户 |
| `section` | `templates_arch.section` | 剖面 + 基础 + 屋顶 |
| `stair` | `templates_arch.stair_detail` | 楼梯详图 + 踏面/踢面 |
| `detail` | `templates_arch.detail` | 节点大样（按"檐口/勒脚/变形缝/女儿墙"挑 detail_type） |
| `site_plan` | `templates_advanced.site_plan` | 总平面 + 道路 + 建筑轮廓 |
| `fire_safety` | `templates_advanced.fire_safety` | 防火分区 + 安全出口 |
| `hvac` | `templates_advanced.hvac_system` | 空调系统 + 风管 |
| `fire_alarm` | `templates_advanced.fire_alarm_system` | 火灾报警 + 控制器 |
| `intelligent` | `templates_advanced.intelligent_system` | 智能化系统 |
| `smoke_exhaust` | `templates_advanced.smoke_exhaust_system` | 防排烟系统 |
| `rain_water` | `templates_advanced.rain_water_system` | 雨水系统 |
| `schedule` | `templates_advanced.schedule_gantt` | 施工进度横道图 |
| `construction_site` | `templates_advanced.construction_site` | 施工总平面 + 塔吊/仓库/材料堆场 |
| `steel` | `templates_advanced.steel_structure` | 钢柱/钢梁详图 |
| `foundation` | `templates_struct.foundation` | 基础平面 |
| `electrical` | `templates_mep.electrical_legend` / `lighting_plan` / `sym_weak` | 按文本挑照明/弱电/插座/默认强电 |
| `plumbing` | `archkit` 拼装 + `templates_advanced.rain_water_system` 代用 | 卫生间自拼；给水/排水复用雨水拓扑（**水专业待补模板**） |
| `structural` | `templates_struct.{bar, hook, column_rebar, slab_rebar, foundation}` 拼装 | 按"梁/柱/板/默认"派发 |

### 关键 API（`NLAwareDxfBuilder`，继承链 9 层）

```python
from dxfkit import NLAwareDxfBuilder  # 等价于 integrate_nl_to_builder(ReviewAwareDxfBuilder)
b = NLAwareDxfBuilder(style='gb_architectural')

# 1) 一句话出图（默认自动套 GB_A3 国标图框 + 标题栏 + 1:100 视口）
result = b.generate_from_text(
    '生成 12x8 米三层住宅平面图带客厅厨房卧室',
    'nl_house.dxf'
)
# → {'ok': True, 'drawing_type': 'floor_plan',
#    'result': {..., 'sheet_layout': 'GB_A3', 'paper_size': 'A3'}}

# 不要图框？传 add_sheet=False
b.generate_from_text(text, 'raw.dxf', add_sheet=False)
print(result['drawing_type'], result['parsed']['confidence_label'])
# → floor_plan 中 (基本理解)

# 2) 先解析再决定
parsed = b.parse_text('生成 50x40 米总平面图带 4 个安全出口')
print(parsed['drawing_type'], parsed['dimensions'], parsed['quantities'])
# → site_plan {'width': 50.0, 'depth': 40.0} {'count': 4}
if parsed['confidence'] >= 0.4:
    b.generate_from_text(text, 'site.dxf')
```

### 置信度规则（实测上限 ≈0.55）

- 高 ≥0.40：drawing_type + 尺寸 + 房间/材料/风格全覆盖（如「12x8 米三层住宅平面图带客厅厨房卧室 现代风格混凝土」= 0.52）
- 中 0.20~0.40：drawing_type + 部分参数（如「6 层楼空调系统图」= 0.30）
- 低 <0.20：drawing_type 缺失或参数极少

### 重要约束（已对原始方案纠错）

- ❌ 原稿 `from templates.three_room_flat` / `from templates_architectural` / `from templates_professional` / `from templates_structural` / `from templates_mep.*_template` —— **这些模块/函数名在我们项目里不存在**，已全部改用真实函数名。
- ❌ 原稿 `DxfBuilder = integrate_nl_to_builder(ReviewAwareBuilder)` —— **会替换全局 DxfBuilder**，破坏 `style='mechanical'` 等老示例。已改为新增 `NLAwareDxfBuilder` 别名，**不动全局**。
- ❌ 原稿 `SectionParams(height=...)` / `StairDetailParams(total_height=..., flight_type=...)` —— 真实字段是 `floor_height` / `total_rise`，且 `stair_detail` 无 `flight_type`，已修正。
- ⚠️ 中文数字（「三层」「四层」）暂不识别，请用阿拉伯数字（「3 层」「4 层」）；尺寸必须含单位"米/m/厘米/mm"或用 `NxM` 格式。
- ⚠️ **plumbing 类**只有"卫生间自拼"和"雨水系统代用"是真实可达路径；给水/排水专用系统图模板**待补**（已 TODO 标 stub）。

### 实测结果（examples/verify_nl.py 46/46 全 PASS，v1.10.1 起 36→46）

| 检查项 | 期望 | 实测 |
|---|---|---|
| 14+ 类关键词解析 | 19 类全命中 | 19/19 ✓ |
| 10 个真实用例生成 DXF | 文件存在 + 实体 >0 | 10/10 ✓（实体 68~203/张，KB 42~76）|
| `NLAwareDxfBuilder` 是 CodeAware 子类 | True | True ✓（MRO 9 层完整）|
| **自动套 GB_A3 国标图框**（v1.10.1 修复裸图问题）| 每张含 GB_A3 layout + 1 视口 + ≥5 标题文字 | **10/10 ✓**（17 实体/1 视口/6 标题文字）|
| 置信度高/中/低三分档 | ≥0.40 / 0.20~0.40 / <0.20 | 0.52 / 0.30 / 0.0 ✓ |

## 接口层（v1.10.0 新增 · 把 Skill 从工具升级为生态组件）

DXF Skill v1.10.0 起把自身能力通过 4 个独立组件开放，**允许被其它工具/Agent/前端**调用，无需关心 ezdxf 内部实现。

### 4 个组件（全部从 `dxfkit` 顶层导出）

| 组件 | 入口 | 用途 | 关键技术 |
|---|---|---|---|
| **DXFToImage** | `dk.DXFToImage().export(dxf, fmt, cfg)` | DXF → PNG/SVG/PDF/JPG/WEBP | **v1.12.0 起** `ezdxf.addons.drawing` 全实体渲染（POLYLINE/ARC/ELLIPSE/SPLINE/HATCH…），`TextPolicy.IGNORE` 跳过 SHX 自渲染 + CJK 手绘文本（数据单位→pt 换算），中文零 tofu；matplotlib 直出 PDF，无 cairosvg |
| **DXFTo3D** | `dk.DXFTo3D().export(dxf, fmt, cfg)` | DXF → OBJ/STL/PLY | 纯 Python + `struct.pack`；仅闭合轮廓扇形三角化，开口/圆周只导 edges |
| **DXFCLI** | `python interfaces.py generate\|export\|batch ...` | 命令行 3 子命令 | argparse，自动接 NLAwareDxfBuilder |
| **SimpleAPI** | `dk.SimpleAPI.run(port=5566)` | REST API 4 端点 | Flask；端口 5566 避 OneDrive 5000 冲突 |

### 关键 API

```python
from dxfkit import DXFToImage, DXFTo3D, NLAwareDxfBuilder

# 1) 图像
img = DXFToImage()
img.export('plan.dxf', 'png',  {'output': 'plan', 'dpi': 300})   # → plan.png
img.export('plan.dxf', 'svg')                                    # → plan.svg
img.export('plan.dxf', 'pdf')                                    # → plan.pdf

# 2) 3D
d3 = DXFTo3D()
d3.export('plan.dxf', 'obj')   # → plan.obj  （Blender/3ds Max 可入）
d3.export('plan.dxf', 'stl')   # → plan.stl  （二进制，3D 打印）
d3.export('plan.dxf', 'ply')   # → plan.ply  （ASCII）

# 3) CLI（终端）
# python interfaces.py generate "12x8 米住宅平面图" -o out.dxf
# python interfaces.py export out.dxf -f png -o out
# python interfaces.py batch config.json

# 4) REST API（其它程序/前端调用）
# python interfaces.py api                  # 默认 5566
# python interfaces.py api --port 6000
# curl -X POST http://127.0.0.1:5566/api/generate \
#   -H "Content-Type: application/json" \
#   -d '{"text":"12x8 米住宅平面图","output":"api.dxf"}'
```

### 4 个 REST API 端点

| 端点 | 方法 | 参数 | 返回 |
|---|---|---|---|
| `/api/health` | GET | — | `{status,version,components}` |
| `/api/generate` | POST | `{text, output}` | `{success, drawing_type, confidence}` |
| `/api/export` | POST | `{dxf_file, format, output}` | `{success, file, entities}` |
| `/api/download/<file>` | GET | — | 文件下载 |

### 关键设计取舍（与原稿纠错）

| 原稿 | 修正 |
|---|---|
| `DxfBuilder(style='gb_architectural')` | 改 `NLAwareDxfBuilder(style=...)`（v1.9.0 才有 `generate_from_text`） |
| LWPOLYLINE 全部扇形三角化（开口也三角化） | 仅**闭合**扇形（flag 或首末重合）；开口/CIRCLE 只导 edges |
| PDF 走 cairosvg 重依赖 | 改 matplotlib 直出，无须额外装包 |
| Flask 端口 5000 撞 OneDrive | 改 **5566** |
| `DXFToImage.export(dxf, fmt, config)` 旧签名 | 改为 `export(dxf, fmt, config=None)` + `config.get('output')` |

### 实测结果（`examples/verify_interfaces.py` 21/21 PASS）

| 组件 | 测项 | 结果 |
|---|---|---|
| DXFToImage | PNG/SVG/PDF/JPEG/WEBP 5 格式导出 | 全部非空 (15~700KB) |
| DXFTo3D | OBJ/STL/PLY 3 格式 | STL 含 14 三角面（闭合轮廓），OBJ 含 27 面 + 73 edges |
| NLAwareDxfBuilder | MRO 9 层完整 | NLAware→CodeAware→GBDxfBuilder→...→NLMixin |
| DXFCLI | argparse help 可打印 | ✓ |
| SimpleAPI | 默认端口 5566 | ✓ |

CLI 实测：`generate`/`export png`/`export obj` 三子命令全通过。

## 核心 API（`DxfBuilder`）
- 基础：`line / rect / add_circle / add_point / add_polyline(pts, closed=) / text(s,x,y,h,align) / arc(cx,cy,r,a0,a1)`
- 建筑：`wall_h(y,x0,x1,openings) / wall_v(x,y0,y1,openings)`，`openings=[(s,e,"door"|"win"),...]` 自动留洞口+画符号；`stair(x0,y0,x1,y1)`
- 标注：`dim_h(y,x0,x1,label) / dim_v(x, y0,y1,label)`
- 工具：`save(path) -> {path,entities,layers,bbox}`；`_ensure_layer(name)` 懒建图层
- 模块级：`batch(specs, outdir, maker)`；`STYLES`（四套预设）

## ⚠️ 必踩 API 坑（已验证，别重写）
- `add_text` **无 `set_height`**：高度走 `dxfattribs={"height":h}`。
- `set_placement(align=...)` 必须传 `TextEntityAlignment` **枚举**，字符串会 `AssertionError`。
- modelspace **无 `add_arrow`**：用两条短线手绘 chevron。
- 字体警告 `cannot open font 'mstmc.ttf'`：非中文系统缺该 CJK 字体，**无害**，不影响生成/打开。
- 线宽 `lineweight` 单位 1/100mm（35 = 0.35mm）。
- `bbox.extents` 必须传**实体列表** `bbox.extents(list(msp))`，传 Layout 本身会 `AttributeError`。
- `add_hatch(pts, pattern, scale, angle, layer)` **第 4 个位置参数是 `angle` 不是 `layer`**！
  想指定图层必须写关键字 `layer="CONC"`，写成 `add_hatch(pts, "AR-CONC", 40, "CONC")` 会
  `TypeError: must be real number, not str`。
- 便捷别名：`add_layer(name, color)` 建图层；`add_rectangle(x, y, w, h)` 是**左下角+宽高**，
  与 `rect(x0, y0, x1, y1)` 的**角点-角点**不同，别混用。
- 1:100 出图的平面图，模型里字高要取 **250~600**（打印后才 2.5~6mm）；
  照搬"height=40"之类的经验值在 1:100 下只有 0.4mm，根本看不见。
- ezdxf STYLE 实体的中文大字体属性叫 `dxf.bigfont`（**小写无下划线**），不是 `big_font`；DXF 组码 107。
- MTEXT 实体字高属性叫 `dxf.char_height`（**不是 `height`**），否则 `DXFAttributeError: Invalid DXF attribute "height" for entity MTEXT`。
- 中文显示 ??：默认 STYLE 没设置 `bigfont`；用 `GBDxfBuilder` 或显式调 `TextStyleManager(doc).setup_all()`。
- 不要在 `style.dxf.weight` 上写粗体——ezdxf STYLE 没有这个属性，会 `DXFAttributeError`。

## 图层约定（国标）
默认风格 `architectural` 仍用近似色（WALL 白7/DOOR 品红6/WIN 青4/STAIR 黄2/DIM 红1/TXT 蓝5/AUX 灰8/TITLE 白7）。
**国标模式**（`GBDxfBuilder`）改用规范命名与色：建筑 `G_*`(白/黄/红/青)、结构 `S_*`(红/青)、电气 `E_*`(红/青/品红)、通用 `BORDER`/`TITLE_BLOCK`(白)，
线宽按 粗0.50/中0.35/细0.18/特细0.13（1/100mm）。完整定义见 `gb_standards.LayerStandard.LAYERS`（48 个）。

## L3 验证（保存后必做，别只看"没报错"）
`save()` 返回报告：`entities` 实体数、`layers` 各图层计数、`bbox` 几何外包盒（**6 元素** `[minx,miny,minz,maxx,maxy,maxz]`，取 XY 水平范围即 `bbox[0],bbox[1],bbox[3],bbox[4]`）。
- 关键图层 WALL/DIM/TXT/STAIR/DOOR/WIN（建筑）或对应风格图层应齐全且非空；
- `maxx-minx` 应≈面宽、`maxy-miny` 应≈总高。不符则回查坐标。
- 例：`rect_holes` bbox=`[0,0,0,100,50,0]` → XY 范围 0~100 × 0~50，与 100×50 一致 ✅。

## 实例
- `examples/villa_demo.py`：15m 面宽三层别墅**总图**——三层竖向堆叠在**同一个**模型空间（一张图看全貌），已通过 L3 验证。
- `examples/villa_floors.py`：同一别墅**拆成三层独立成图**——1F/2F/3F 各一个 DXF，各自原点 (0,0)，互不干扰，便于分别打印/深化/交付。用 `batch()` 一次性生成，产物落 `examples/out_floors/`，桌面归档名 `别墅X层平面图_15m.dxf`。
- `examples/showcase.py`：综合验证五大功能（自然语言三示例 + 参数化 PCB + 四风格 + 批量面板 + 导入修改），产物落 `examples/out/`。
- `examples/extensions_showcase.py`：一次跑通三大扩展模块（geomkit 几何 + archkit 建筑标准 + budget 造价），产物落 `examples/out_ext/`。
- `examples/pro_templates.py`：建筑/结构/机电**专业模板**一次全出（立面/剖面/节点大样/楼梯详图 + 钢筋符号/柱/板/基础/楼梯配筋 + 电气图例/照明平面，共 12 张），产物落 `examples/out_pro/`。
- `examples/gb_full_set.py`：**GB/T 全套施工图**——15m 别墅 11 张图（建施01-06 平面/立面/剖面/楼梯详图、结施01-03 柱/板/基础、电施01-02 电气图例/照明），每张用 `GBDxfBuilder` + A3 图纸空间图框+标题栏+1:100 视口，产物落 `examples/out_gb/`，桌面归档名 `建施-01 一层平面图.dxf` 等。
- `examples/verify_fonts.py`：**字体配置验证**——生成含中文轴号/标高/索引/标题栏/多行说明的 GB 图，自动校验三种 GB 样式建立、所有 CJK 文本实体 100% 绑定 GB_CHINESE、报告本机可用中文字体。产物落 `examples/out/verify_fonts.dxf`。
- `examples/construction_notes_demo.py`：**施工说明模块独立演示**——A3 图幅，模型空间画一个简单户型，图纸空间右侧说明栏写入建筑专业全套施工说明（含纯文本 Markdown 打印）。产物落 `examples/out/construction_notes_demo.dxf`。
- `examples/verify_notes_fullset.py`：**施工说明全套校验**——遍历 `out_gb/*.dxf`，统计每张图纸空间说明 TEXT 数、校验样式 100% 走 GB_CHINESE/GB_TITLE（无 Standard 回退）。
- `examples/construction_codes_demo.py`：**规范引用模块演示**——A3 图纸空间右侧说明栏写规范清单 + 模型空间整段规范，纯文本摘要打印。产物 `out/construction_codes_demo.dxf`。
- `examples/drawing_management_demo.py`：**图纸管理全套演示**——编号/目录/图签/门窗/材料/结构说明/设备/工程量清单 一键出 + 五份文本打印。产物 `out/drawing_management_demo.dxf`。
- `examples/complete_drawing_demo.py`：**三合一演示**——CodeAwareDxfBuilder（施工说明+规范引用）+ CompleteDrawingManager（图纸表格）+ 户型，一张 A2 全要素图。产物 `out/complete_drawing_demo.dxf`。
- `examples/templates_advanced_demo.py`：**高级专业模板 10 模块一次全出**（总平面/防火疏散/空调/防排烟/雨水/火灾报警/智能化/横道图/施工总平面/钢结构柱+梁 共 11 张），产物落 `examples/out_adv/`。
- `examples/drawing_review_demo.py`：**审图模块演示**——合格图 A 级（0 错 0 警）+ 坏图 C 级 + BatchReviewer 汇总 + 报告写入图纸。产物落 `examples/out_adv/review_*.dxf`。
- `examples/verify_full_extension.py`：**规范引用 + 图纸管理收尾回归**（CodeAware 三能力 / 64 条×13 类 / 自动编号 / CompleteDrawingManager 7 键 / 3 demo 产物非零）。
- `examples/verify_advanced_review.py`：**最后一批端到端校验**（10 模块注册 / out_adv 13 产物 / 审图数据模型 / ReviewAware MRO / 批量审 6 图 / gb_full_set 11 张回归）。**v1.10.2 起新增**：3 个老 demo (`drawing_management_demo` / `complete_drawing_demo` / `templates_advanced_demo`) 都自动套上 GB_A2/GB_A3 国标图框（17 实体 / 1 视口 / 6 标题文字），可直接打开交付。
- `examples/nl_demo.py`：**自然语言生成 10 用例**（floor_plan/elevation/section/stair/site_plan/fire_safety/hvac/steel/schedule/electrical），DXF 落 `out_nl/` 实体 68~203/张，KB 42~76；每条打印置信度 + 落盘状态。
- `examples/verify_nl.py`：**自然语言全链路 36 项断言**（19 类关键词命中 / dispatch 覆盖 / NLAware MRO / 10 个真实用例生成 / 置信度高/中/低三分档）。
- `examples/interfaces_demo.py`：**接口层演示**——4 用例（NL→DXF、DXF→PNG/SVG/PDF、DXF→OBJ/STL/PLY、批量 JSON 驱动），产物落 `out_intf/`。
- `examples/verify_interfaces.py`：**接口层端到端 21 项断言**（4 组件顶层导出 / 5 图像格式 / 3 3D 格式含 STL ≥1 面 / NLAware MRO 完整 / CLI help / API 端口 5566）。
- `examples/verify_pipeline.py`：**v1.12.0 端到端一键验证**——一句话 → NL 生成 DXF → drawing addon 渲染白底 PNG → 中文结构校验（实体/图层/CJK 文本数）→ TTF glyph 覆盖校验（`auto_fix_cjk.verify_glyph_coverage`），4 步全绿退出码 0。

## 渲染引擎升级（v1.11.0 → v1.12.0 · 中文零 tofu + 全实体）

### v1.11.0：中文字体三件套
- `interfaces.py`：`get_cjk_font_path()` / `get_cjk_font_properties()` / `cjk_font_family()`——按 SimSun→SimHei→MSYaHei 优先级定位系统 CJK 字体，rcParams + FontProperties 双保险。
- 根目录 `auto_fix_cjk.py`：独立工具——`auto_fix_dxf_styles()` 把所有 CJK TEXT/MTEXT 强制绑 GB_CHINESE 样式；`verify_glyph_coverage(ttf, texts)` 用 FT2Font 逐字检查缺字；`export_png()` / `run_pipeline()` 一键修复+渲染+校验。

### v1.12.0：DXFToImage 换 `ezdxf.addons.drawing` 全实体渲染
旧版手写循环只认 LINE/LWPOLYLINE/CIRCLE/TEXT，ARC/SPLINE/POLYLINE/HATCH 全丢。新版：
1. **几何**：`Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp)` 全实体支持；
2. **文本策略**：`Configuration(text_policy=TextPolicy.IGNORE)` 让 drawing 跳过 SHX 文本自渲染（matplotlib 不认 gbcbig.shx 会 tofu），CJK 文本由我们用 `ax.text(fontproperties=…)` 单独画；
3. **字号换算**（关键教训）：DXF `height` 是**数据单位**（如图名 300mm），直接当 pt 用会爆炸成满屏巨字。必须换算 `fontsize_pt = height × 72 × fig_h_in ÷ y_range`；
4. **MTEXT 支持**：文本在 `e.text`（不是 `e.dxf.text`），高 `char_height`；内联格式码 `\P`→换行、`\A..\H..\W..;` 正则剥离；
5. **对齐/旋转**：TEXT 有 halign/valign 时用 `align_point` + ha 映射，`rotation` 透传。

### 实测（2026-09-08）
- 建施-01 一层平面图 PNG：轴网圈号/房间名（主卧次卧书房厨房客厅餐厅）/12000 尺寸/指北针/±0.000 标高全部清晰，中文零 tofu；
- 批量回归 6 图（剖面/柱配筋/照明/横道图/e2e/齿轮）6/6 PASS，无 aspect 警告；
- `verify_pipeline.py` 4/4：NL 生成 115 实体 14 图层 7 中文文本 → PNG 47KB → glyph PASS（sample 34 字 missing 0）。


## 给排水专业 + 梁配筋（v1.13.0 新增 · 消灭"代用/示意"实现）

### scripts/templates_plumbing.py（新建 · 4 模板）
| 模板 | 内容 | 图层 |
|---|---|---|
| `bathroom_detail` | 卫生间大样：坐便器/洗手盆/淋浴间/地漏图例 + 给水支管 De25/De20 + 排水 De110/De50 + 坡度 i=0.02 箭头 + 带管径图例 | P_WALL/P_FIXTURE/P_SUPPLY/P_DRAIN |
| `water_supply_system` | 给水系统图：立管 JL-1 De32 + 各层支管 De25 + 用水点 De20×n + 楼层标高圈 + 阀门/自动排气阀 | P_SUPPLY/P_DIM |
| `drainage_system` | 排水系统图：立管 WL-1 De110 + 存水弯 + 坡度 i=0.026 + 检查口/清扫口 + 通气帽伸出屋面 700 | P_DRAIN/P_DIM |
| `fire_fighting_plan` | `mode='sprinkler'` 消防喷淋平面：喷头 ≤3.6m 网格 + 主管 DN100 + 支管 DN25 + 信号阀/水流指示器/末端试水；`mode='hydrant'` 消火栓系统图：消防立管 + 消火栓箱沿墙 + 屋顶水箱 + 水泵接合器 + 图例 | P_FIRE/P_WALL |

### templates_struct 新增 `beam_rebar`（替换旧"示意梁"）
KL 框架梁配筋图：上/下通长筋 + 支座负筋（伸入 ln/3 端部下弯）+ 箍筋加密区 1.5h@100/非加密区@200 + 断面 1-1 跨中 / 2-2 支座 + 钢筋表（编号/规格/等级/根数/长度）+ 尺寸。参数 `BeamRebarParams`。

### NL 路由修复（关键词表新增）
- 复合优先层：`消防喷淋/喷淋平面/喷淋系统/自动喷淋/消防平面/消火栓`、`给水系统/供水系统/排水系统/污水系统/给水立管/排水立管` → plumbing
- 弱匹配层扩充：`卫生间/浴室/卫浴/给水/排水/供水` → plumbing
- `_gen_plumbing` 分支：`卫生间/浴室`→bathroom、`消火栓`→fire_fighting_plan(hydrant)、`消防/喷淋`→fire_fighting_plan(sprinkler)、`给水/供水`→water_supply、`else`→drainage（旧版给水/排水复用雨水拓扑的"代用"已删除）；`_gen_structural` 梁分支走 `beam_rebar`（旧 beam_schematic 已删除）

### 实测（examples/out_v113/，5 张全过 + 旧回归 46/46）
一句话 → 出图 → PNG 渲染三步验证；卫生间 60 实体 / 给水 78 / 排水 59 / 消防 77 / 梁配筋 135；verify_nl.py 46/46、verify_pipeline.py 4/4 零回归。

## v1.13.1 修复（NL 国标图框断链 + 消火栓路由）

### 问题 1：NL 一句话生成的图纸缺国标图框（审查判 C 级）
`demo_natural_language` 旧版用 `integrate_nl_to_builder(DxfBuilder)` 这条**残缺链**，链里没有 `add_gb_sheet`，且 `generate` 里的 `hasattr(self.builder, 'add_gb_sheet')` 守卫对基础 `DxfBuilder` 恒为 `False` → 静默跳过图框，产出"裸图"。
**修复**：`demo_natural_language` 改用 `dxfkit.NLAwareDxfBuilder(style='gb_architectural')`（NL→Review→Code→GB 完整链），并显式 `generate_from_text(text, filename, add_sheet=True)`。国标图框落在 `GB_A3` 图纸空间布局（图框/标题栏/1:100 视口齐全），与 `out_gb`/`out_nl` 一致。
> 注：`add_gb_sheet` 仅 `GBDxfBuilder`（及派生的 `NLAwareDxfBuilder`）具备，**基础 `DxfBuilder` 没有**——所有"成品图" demo 脚本须用 `GBDxfBuilder`。

### 问题 2：输入"消火栓系统图"掉进排水分支，画出错误排水图
`DRAWING_TYPE_PATTERNS` 已把 `消火栓` 路由到 `plumbing`，但 `消火栓` 不含子串 `消防`，`_gen_plumbing` 原有 `elif '消防' in t or '喷淋' in t` 分支匹配不到 → 落入 `else` 排水分支。
**修复**：
- `FireFightingParams` 增加 `mode: str = "sprinkler" | "hydrant"`；
- `fire_fighting_plan` 在 `mode=='hydrant'` 时分派到新增 `_fire_fighting_hydrant`（消防立管 + 消火栓箱沿墙布置 + 消防管 + 屋顶水箱 + 水泵接合器 + 图例）；
- `_gen_plumbing` 新增 `elif '消火栓' in t` 分支，传 `mode='hydrant'`。

### 成品图 demo 补齐国标图框（审查 C 级清零行动）
基础 `DxfBuilder` 无 `add_gb_sheet`，下列 demo 改用 `GBDxfBuilder` 并在 `save` 前调 `add_gb_sheet`，重跑后产出带框成品：
- `examples/pro_templates.py`（out_pro，12 张专业模板）
- `examples/villa_floors.py`（out_floors，3 张别墅分层平面）
- `examples/extensions_showcase.py`（out_ext，5 张高级几何/建筑标准）
- `examples/interfaces_demo.py` / `verify_pipeline.py`（走已修复的 NL 链）
- `examples/regen_v113.py`：用修复后完整链重生成 out_v113（5 张）

### 全量审查结果（examples/review_all.py）
- 修复前：99 张 → A18 / B34 / **C47**，TOP 错误 `46× 未检测到标准图框`、`41× 缺少 BORDER 层`；
- 修复后：104 张 → **A29 / B59 / C16**，TOP 错误降至 `16× 未检测到标准图框`。
- 剩余 16 个 C 级均为 `examples/out/` 下的**单特性 API / 风格 / PCB 演示**（panel / pcb / style_* / font 等）和审查器**故意保留的负面夹具** `out_adv/review_缺图框坏图.dxf`，以及个别独立 demo（root `villa_15m.dxf`、`out_intf/cli_test.dxf`）——均非"成品图纸"，按设计不带国标图框。

## 进阶技巧：按图层回读校验（比全局 bbox 更严格）
全局 `bbox` 会包含标注线、文字、门窗符号的外伸，**不能直接用来断言主体尺寸**。
要精确校验某一类构件的尺寸，回读 DXF 按图层算外包盒：
```python
import ezdxf
from ezdxf import bbox as _bbox
def layer_extents(path, layer):
    doc = ezdxf.readfile(path)
    ents = [e for e in doc.modelspace() if e.dxf.layer == layer]
    if not ents:
        return None
    ext = _bbox.extents(ents)
    return [ext.extmin[0], ext.extmin[1], ext.extmax[0], ext.extmax[1]]

wall = layer_extents("villa_1F.dxf", "WALL")
assert abs(wall[2] - 15000) < 1 and abs(wall[3] - 12000) < 1   # 墙体核心 15m × 12m
```
实例中 WALL 图层实测 `maxx=15000 / maxy=12000 / min=(0,0)`，而全局 bbox 是 `x[-1783,15060]`（多出的 60 是窗符号外伸、1783 是左侧尺寸标注），**两者不可混用**。

---

## 识图引擎（v1.14.0 新增 · 图 → 结构化理解）

此前所有能力都是"出图"（语言/参数 → DXF）。**识图是反方向**：给一张 DXF，把它读懂。

| 能力 | 说明 |
|---|---|
| 文件元信息 | DXF 版本 / 单位 / 全部布局名 |
| 图层清单 | 按国标专业归类（G 建筑 / S 结构 / P 给排水 / E 电气 / 图框 / 自定义） |
| 实体分类统计 | 线/圆/弧/多段线/文字/标注/块引用/填充，按类型 + 按空间分布 |
| 文字内容提取 | 按图层聚合 TEXT / MTEXT（MTEXT 自动剥离格式码） |
| 块引用统计 | 块名 → 引用次数 |
| 尺寸标注提取 | 全部 DIMENSION 的测量值（范围 / 平均） |
| 几何量算 | 各图层线长、闭合面积、块数量 + 模型空间 extents |
| 图纸类型推断 | **三信号源加权**：文件名 0.8 > 图内文字 0.7/0.5 > 图层特征 0.4 |
| 完整性体检 | 图框 / 标题栏 / 文字层 / 标注层 / 中文样式 / 量纲一致性 |

```python
from drawing_reader import read, describe
info = read("某图.dxf")
print(info.drawing_type, info.type_confidence)      # 梁配筋图 0.6
print(info.completeness)                            # 体检字典
print(info.to_markdown())                           # 完整识别报告
info.to_json()                                      # 机读 JSON
```

**关键认知（踩过的坑）**：
- **图层声明 ≠ 图层有实体**。国标图纸一次性声明 48+ 图层，大量为空。类型推断必须只用 `entity_count > 0` 的图层，否则"电气图"会把柱配筋图抢走。
- **文件名是最强信号**。工程图文件名通常就是图名，权重给到 0.8，可纠正图内文字缺失的情况。
- **量纲启发式**。部分文件 `$INSUNITS` 标为"米"但实际按毫米绘制；用模型空间 extents 反推（A3 图框约 420×297），矛盾时出警告。

## 清单统计（v1.14.0 新增 · 图 → 工程量表）

`bom.py`：遍历实体 → 按国标图层归并 → 工程量清单，导出 CSV / JSON / Excel / Markdown。

```python
from bom import generate_bom
rep = generate_bom("某图.dxf", "out/")   # 一次导出 4 种格式
print(rep.to_text())
print(rep.summary())                      # {'墙体': 136.0, '门窗': 94.8, ...}
```

归并规则（`LAYER_BOM_RULES`，28 类）：墙体 / 门窗 / 楼梯 / 钢筋 / 梁 / 柱 / 板 / 基础 / 给水管 / 排水管 / 消防管 / 强电 / 照明 / 电线 / 防雷接地 / 标注 / 图框 …

- 线状实体累计**长度**（m）、闭合多段线与圆累计**面积**（m²）、块与文字累计**个数**
- 单位换算按毫米制（mm → m / m²），与 dxfkit 出图单位一致
- `classify_layer(name)` 可单独调用，供其他模块复用图层归类

> 与 `drawing_management.QuantityList` 的分工：那个是**手工填数**的清单表骨架；`bom.py` 是**从图纸自动算量**。两者互补，不重复。

## 施工说明 v2（v1.14.0 新增 · 按图纸类型匹配话术）

`construction_notes_v2.py`：**28 类图纸 / 143 条条款 / 43 部规范**。

```python
from construction_notes_v2 import get_construction_notes, ProfessionalPhraseLibrary
print(get_construction_notes("beam_rebar"))          # 梁配筋施工说明
key = ProfessionalPhraseLibrary.match_by_drawing_type(info.drawing_type)  # 识图→说明联动
```

> 与 `construction_notes.py` 的分工：老模块按 **GB 系列专业**（土方/基础/主体…）生成；v2 按 **图纸类型**（梁配筋/防排烟/配电…）精确匹配。两者并存，v2 供"识图驱动说明"的场景。

## 电气 / 暖通专业洞（v1.14.0 补齐）

此前电气只有图例+照明平面、暖通只有空调系统图；本次补 4 个真模板：

| 模板 | 函数 | 图层 |
|---|---|---|
| 配电系统图（单线图） | `dist_power_system(Params)` | E_MAIN/E_BUS/E_BREAKER/E_CABLE/E_EQUIP |
| 防雷接地图 | `lightning_grounding(Params)` | E_LIGHTNING/E_GROUND/E_DOWN |
| 空调水系统图 | `chilled_water_system(Params)` | HVAC_CHILLER/HVAC_PUMP/HVAC_PIPE/HVAC_RISER/HVAC_TOWER |
| 风管平面图 | `duct_plan(Params)` | HVAC_DUCT/HVAC_DUCT_BRANCH/HVAC_OUTLET/HVAC_EQUIP |

统一注册表 `dxfkit.SPECIALTY_TEMPLATES = {key: (函数, 参数类)}`。

> **API 坑（务必注意）**：外部参考代码常写成 `b.rectangle(...)` / `b.circle(...)` / `b.line(..., linewidth=2)`——**本库没有这些**。真实接口是：
> - `b.add_rectangle(x, y, w, h, layer=)` —— 左下角 + 宽高（**不是** x0,y0,x1,y1）
> - `b.add_circle(cx, cy, r, layer=)`
> - `b.line(x1, y1, x2, y2, layer=)` —— **不接受** `linewidth` / `linetype` 参数，线型靠图层控制
> - `b.text(s, x, y, h=, layer=)` —— 文字内容在前
> - `b.rect(x0, y0, x1, y1, layer=)` —— 这个是右上角式，与 `add_rectangle` 语义不同

## v1.14.0 验证（examples/verify_v114.py · 60 项全过）

```
[1] 识图引擎     15 张全识别 · Markdown/JSON 可导出 · extents 已采集
[2] 清单统计     10 张全出清单 · CSV/JSON/MD/Excel 四格式落盘 · 图层归类正确
[3] 施工说明 v2  28/28 类可生成 · 识图→说明联动正确 · 143 条款 / 43 规范
[4] 电气专业洞   配电 113 实体 / 防雷 46 实体 · 均带国标图框存盘
[5] 暖通专业洞   空调水 80 实体 / 风管 69 实体 · 均带国标图框存盘
[6] 主链集成     dxfkit 导出 20 个新符号全部就位
------------------------------------------------------------
PASS 60 / FAIL 0
```

全量分析（`examples/analyze_all.py`，97 张 DXF）：

| 指标 | 结果 |
|---|---|
| 识图成功 | **97/97** |
| 清单统计成功 | **97/97** |
| 含国标图框 | 81 |
| 图别识别覆盖 | 平面图21 / 结构配筋9 / 剖面6 / 电气6 / 机械零件5 / 钢结构4 / 立面4 / 电子3 / 防火分区3 / 空调3 … 未识别 8（均为 `out/` 单特性 API 演示件，按设计无图名） |

报告：`examples/out_v114/_full_analysis.json` / `_full_analysis.md`

---

## DXF → 3D 体量挤出（v1.15.0 新增 · 平面图变能转着看的立体模型）

**和已有的 `DXFTo3D` 不是一回事**，别搞混：

| | `interfaces.DXFTo3D`（旧） | `extrude3d`（新） |
|---|---|---|
| 原理 | 闭合轮廓 → **z=0 平面三角化** | 闭合轮廓 → **底面+顶面+侧面** |
| 产物 | 平面薄片（无厚度、无高度） | 真体块（有厚度、有层高） |
| 多楼层 | ❌ | ✅ 按标高叠加 |
| 预览 | ❌ | ✅ Three.js HTML，可拖拽旋转 |

### 核心：三类几何都能挤出

```python
from extrude3d import ExtrudeBuilder, ExtrudeParams, MultiFloorBuilder, export_viewer_html

# 单层
b = ExtrudeBuilder(ExtrudeParams(wall_height=3000))
mesh = b.build('平面图.dxf')
b.export_mesh(mesh, 'stl', 'out/model')          # model.stl / model.obj
export_viewer_html(mesh, 'out/model.html')       # 浏览器双击即可转着看

# 多楼层（层高 3000、板厚 200）
mf = MultiFloorBuilder(floor_height=3000, slab_thickness=200)
mesh = mf.build([('1F.dxf', 0), ('2F.dxf', 3200), ('3F.dxf', 6400)])
```

### ⚠️ 最关键的两个坑（务必记住）

**坑 1：本库的墙是「双线 LINE」，不是闭合多段线。**
`wall_h` / `wall_v` 画出来的是两条平行线（各偏 120mm）+ 无封口，端点度数是 `{1: 28, 2: 4}`——**根本不闭合**。
所以既要"闭环重建"也要"平行线配对"：
- `pair_parallel_lines(segs)` —— 把两条平行线配对成矩形轮廓（**主力**，命中 21 对）
- `rebuild_loops(segs)` —— 线段链闭环重建（兜底）

不做这一步，墙体一个都挤不出来（只会挤出柱子）。

**坑 2：STL 头必须精确 80 字节。**
`b"DXF Skill extrude3d"` 是 18 字符，补 60 个 `\x00` 只有 78 字节 → **用 `.ljust(80, b"\x00")`**。

### 图层高度表（`DEFAULT_LAYER_HEIGHTS`）

墙体 3000 / 柱 3000 / 梁 500 / 板 200 / 基础 600 / 门 3000 / 窗 3000；
管道 200 / 设备 800 / 电线 100。
图框 / 标注 / 文字 / 轴线 / 填充 / 符号（`SKIP_LAYER_PREFIXES`）**自动跳过**不挤出。

### 验证（examples/verify_v115.py · 37 项全过）

```
[1] 轮廓提取   双线配对正确 · 不等长/超间距不误配 · 闭环重建
[2] 单层挤出   STL(体积符合 84+50n) · OBJ · 索引合法 · 高度 3000
[3] 多楼层     三层总高 9400mm 精确 · 180 三角面
[4] HTML 预览  Three.js + OrbitControls + Z-up
[5] 主链集成   dxfkit 导出 10 个新符号
--------------------------------------------------------
PASS 37 / FAIL 0
```

**端到端实测**：`"画一个三层住宅平面图"` → 201 实体 2D 施工图 → 324 三角面 3D → 可旋转页面。

### 诚实的边界

- 出的是**体量模型**（有厚度、有层高、能转），**不是工程级 BIM**
- **门窗洞口不会自动开洞**（窗做了实心体块，未挖洞）
- 多楼层是**机械叠加**，楼层间未做构件对齐校验
- 精确深化仍需在 Blender / SketchUp 里精修

---

## 一键流水线（v1.16.0 新增 · 一句话出完整交付包）

`scripts/pipeline.py` 把已有能力串成一条链：

```
一句话
  ↓ [1] 出图   <语义名>.dxf                  NLAwareDxfBuilder.generate_from_text
  ↓ [2] 识图   understanding.json / .md      drawing_reader.DrawingReader
  ↓ [3] 算量   bom/bom.{csv,json,xlsx,md}    bom.generate_bom
  ↓ [4] 说明   construction_notes.md         construction_notes_v2（按识图结果匹配话术）
  ↓ [5] 审查   review.md（A~D 级）           drawing_review.DrawingReviewer
  ↓ [6] 渲染   render.png（可选）            interfaces.DXFToImage
  ↓ [7] 3D     model.{stl,obj,html}          extrude3d.ExtrudeBuilder
  ↓ [8] 汇总   pipeline_report.{txt,json} + manifest.json
```

```python
import sys, os
sys.path.insert(0, os.path.join(<skill_dir>, "scripts"))
from dxfkit import pipeline, pipeline_batch

r = pipeline("12x8米三层住宅平面图带客厅厨房卧室", "out/")   # 约 2.7 秒
print(r.to_text())

r = pipeline("6米框架梁配筋图", "out/", do_render=True)      # 开渲染（慢，约 7 秒）
rs = pipeline_batch(["12x8米住宅平面图", "配电系统图"], "batch/")
```

命令行：

```bash
python scripts/pipeline.py "12x8米住宅平面图" -o out/ [--render] [--no-review] [--no-3d] [--no-sheet]
python scripts/pipeline.py --batch texts.txt -o out_batch/ --no-review
```

**四个设计要点（踩过坑才这么定的）**：

1. **识图前置到算量/说明之前**——施工说明的话术要按识图结果匹配（比 NL 解析的图别更贴近实际图形）。
2. 除"出图"外**任何一步失败都不中断**，失败写进该步状态，最后汇总列出（便于定位）。
3. 出图文件用**输入语义命名**，不再统一叫 `drawing.dxf`——识图的图别推断里"文件名"权重最高(0.8)，
   固定成 `drawing.dxf` 等于自废武功。
4. **渲染默认关**（300dpi 约 5~7 秒）；1~5 + 3D 默认开（3D 是纯 Python，几十毫秒）。

产物清单落 `manifest.json`（相对路径 + 字节数），便于整包归档。

### 验证（`examples/verify_pipeline_v115.py` · 55 项全过）

```
[1] 单条全链     8 步槽位齐全 · 四处产物 · 报告可回读
[2] 批量         5 种图别全成功 · 专业有区分度
[3] 配置变体     只出图 / 裁剪 BOM 格式 / 关 3D / 不加图框
[4] 产物完整性   manifest 逐项落地 · 关键产物存在
[5] 主链集成     dxfkit 导出 5 个新符号
[6] 字体体检+渲染 各字号出字 · 未选点阵位图字体 · PNG 落地
--------------------------------------------------------
PASS 55 / FAIL 0
```

---

## 渲染层四个老 bug 的修复（v1.16.0）

改渲染前请先读这段，都是**不报错但结果错**的坑。

### 1. 中文"静默丢字"（最严重 · 影响所有渲染）

`SimSun`（`simsun.ttc`）含**点阵位图**，matplotlib/Agg 在约 **5~6pt 的字号带**会把整行中文
渲染成**空白**（黑像素 = 0），而 ASCII 正常、**不抛任何异常**。施工说明那类密排小字正好落在该
字号带 → 中文凭空消失，肉眼极难发现。

实测各字号黑像素（字符串"本工程图纸尺寸"）：

| 字体 | 3pt | 4pt | 5pt | 6pt | 7pt | 8pt | 10pt |
|---|---|---|---|---|---|---|---|
| **simsun.ttc** | 20 | 92 | **0** | **0** | 331 | 567 | 885 |
| msyh.ttc | 121 | 210 | 426 | 686 | 745 | 1088 | 1463 |
| simhei.ttf | 120 | 213 | 360 | 535 | 602 | 891 | 1434 |

**修复**：`_MPL_CJK_CANDIDATES` 把 SimSun 从首位**降到末位兜底**，优先 msyh → simhei → Deng →
simkai → simfang；并新增体检函数 `interfaces.check_cjk_font_sizes()`，把"静默丢字"变成
**可断言检查**（已接入 `verify_pipeline_v115.py` 第 6 组，作回归防线）。

### 2. 文字尺寸失配（说明栏糊成一团）

`_to_raster` 的字号换算原本用 `fig_h`（整图高度），但 `set_aspect('equal', adjustable='box')`
会把坐标轴盒子**缩小**，真实"数据→英寸"比例小于 `fig_h/range` → 字号被整体放大（实测 2.3 倍），
密排行距被吃掉，渲染出来糊成一团。

**修复**：先 `fig.canvas.draw()` 完成布局，再量 **实际坐标轴高度**（`ax.get_window_extent()`）
来算 `pts_per_unit`，不能用 `fig_h`。

### 3. 说明/规范落点（NL 自动追加的）

原行为：施工说明按 1:100 放大后画在 `(23200, 28300)`，但 `width`（换行宽度）**不参与缩放**
→ 字高 250mm 却按 175mm 换行，**每行一个字**竖着糊成一列；执行规范更糟，默认 `(0,0)`
**直接压在图形上**。

**修复**：`natural_language_engine.generate()` 先用 `ezdxf.bbox.extents` 量图形包围盒，
把两段文字块放到**图形右侧空白区**，`width`/行距/字高**按同一比例缩放**，规范清单接在说明下方。

### 4. 电气图例 `'str' object is not callable`

`templates_mep.electrical_legend()` 要的是 `(名称, 可调用对象, 说明)` 三元组，而 NL 引擎传的
是 `{'sym': 'sym_lamp_ceiling'}` **字符串** → **任何电气类 NL 请求都直接报错**（该分支从未跑通；
46/46 的 `verify_nl` 没覆盖到）。

**修复**：新增 `normalize_legend_item()` 兼容三元组与字典两种写法 + `_SYMBOL_REGISTRY`
（符号名 → 绘制适配器）自动解析字符串符号名。

### 本库 API 备忘（外部参考代码经常对不上）

| 你以为 | 实际 |
|---|---|
| `DrawingReader().read(path)` | `DrawingReader(path).read()` ← **路径在构造函数** |
| `b.rectangle(...)` | `add_rectangle(x, y, w, h)` ← 左下角 + **宽高** |
| `b.circle(...)` | `add_circle(cx, cy, r)` |
| `b.line(x1,y1,x2,y2, linewidth=2)` | `line()` **不吃线宽/线型**（靠图层控制） |
| `report = generate_bom(...)` 再自己导 | `generate_bom(dxf, out_dir)` **一次导出 4 种格式**（`{base}_bom.*`） |
| `electrical_legend(items=[{'sym':'sym_x'}])` | 现在两种都行（v1.16.0 起） |
| `DXFTo3D` 出体块 | 那是 z=0 薄片；**体块要用 `extrude3d.ExtrudeBuilder`** |

---

## 施工说明移入图纸空间说明栏 + 视口修复（v1.17.0）

### 一句话

施工说明不再画在模型空间（那是 34500mm 高的文字柱），而是**写进图纸空间图幅的说明栏**；
装不下自动分页出「说明续页」图幅。顺带修掉一个从 v1.14 就存在的**视口比例 bug**。

### 用法（全自动，无需改调用）

```python
b = NLAwareDxfBuilder()
b.generate_from_text("12x8米三层住宅平面图带客厅厨房卧室", "out.dxf", add_sheet=True)
# → 说明自动进 GB_A3 的说明栏；不够则自动建 GB_A3_说明2
# → 视口比例自动挑（1:100），标题栏同步
```

强制/关闭：

```python
b.generate_from_text(text, path, add_sheet=True, notes_in_layout=False)  # 说明留模型空间
b.generate_from_text(text, path, add_sheet=False)                        # 无图框 → 说明回模型空间
```

### 三个新 API

| API | 作用 |
|---|---|
| `BorderStandard.paper_notes_rect(paper)` | 说明栏矩形 (x, y, w, h)，**图纸毫米**；A3 = (230, 71, 180, 216) |
| `BorderStandard.viewport_size(paper)` | 视口 (宽, 高)，与 `add_gb_sheet` 同源 |
| `BorderStandard.fit_scale(w, h, paper)` / `scale_label(s)` | 挑标准比例 / `0.01 → "1:100"` |
| `ConstructionNoteMixin.draw_notes_items(items, x, y, target=)` | 把行清单落笔（分页用） |
| `ConstructionNoteMixin._notes_line_items(...)` | 说明 → 行清单 `[(dx, dy, text, h, layer, style)]` |

### ⚠️ 三个必须记住的坑

1. **`Layout.add_viewport(center, size, view_center, view_height)` 第 4 参是
   view_height（模型单位），不是比例！** 传 `1/100` 会让视口只看到 0.01mm 切片
   （`get_scale()` 返回 27200）。正确：`view_height = 视口高(纸mm) / scale`。
2. **ezdxf 渲染会跳过 `status==1` 的视口**（当成"正在编辑的活动视口"）
   → 图纸空间只出图框、视口里空白。渲染前把 status 临时改成 **2**（只改内存，不写盘）。
3. **不要靠缩字号硬塞说明**。一页 A3 说明栏只有 ~55 行容量，整套建筑说明 100+ 行；
   压到 1.8mm 是"页面不溢出但印出来读不出"的假达标。正确做法是**分页**（下限 2.5mm）。

### 成品图幅预览

```python
DXFToImage().export("x.dxf", "png", {"space": "paper"})              # 自动挑带视口的布局
DXFToImage().export("x.dxf", "png", {"space": "paper", "layout": "GB_A3_说明2"})
```

`space='model'`（默认）看图形本体；`space='paper'` 看**打印出来的样子**。
流水线 `do_render=True` 时两者都出（`render.png` + `sheet.png` / `sheet2.png`）。

### 验证

`examples/verify_layout_notes.py` —— **69 项全过**（8 组：说明栏几何 / 视口换算 / 落点 /
分页 / 成品图幅渲染 / 向后兼容 / auto_fit / 主链集成）。

### 历史断点：`verify_pipeline_v115` 的 PNG 体积断言已改判据

原断言 `>50KB` 是按"模型空间含巨型文字柱"校准的；说明书搬走后渲染从 ~377KB 降到 ~48KB
（图形反而占满画面）——是变好不是回归。现改为「体积落在区间 + 模型 bbox 高度 <25000mm」。

---

## 图纸空间渲染的布局选取 + 识图读取通用化（v1.17.1）

### 一、布局选取规则（`interfaces.DxfRenderer._pick_paper_layout`）

渲染 `space='paper'` 时按以下**固定优先级**挑布局，规则写死、不随调用变化：

| 顺序 | 条件 | 结果 |
|---|---|---|
| 1 | 显式传入 `layout='名字'` 且该布局存在 | 用它 |
| 2 | 显式传入名字但**找不到** | 返回 `None` → 上游回退到模型空间渲染 |
| 3 | 未传名字，且存在**带 VIEWPORT** 的布局 | 取第一个带视口的（那才是真正出图的图幅） |
| 4 | 未传名字，且没有任何带视口的布局 | 取**最后一个非 Model 布局** |
| 5 | 一个非 Model 布局都没有 | 返回 `None` |

要点：
- `doc.layouts` 的第一个永远是 `'Model'`，它**不是**图纸空间，必须排除。
- 判据是"**有没有 VIEWPORT 实体**"，不是布局名字/顺序——图纸空间可以有很多个
  （本技能的分页说明续页就是），靠名字猜会挑错。

### 二、⚠️ 视口 `status==1` 会被渲染器丢掉（已核对源码）

ezdxf 渲染器**不画** `status==1` 的视口，表现为：图纸空间只出图框、视口内一片空白。

出处（ezdxf 1.4.4 逐行核对）：
`ezdxf/addons/drawing/frontend.py :: _draw_viewports()`

```python
viewports.sort(key=lambda e: e.dxf.status)
viewports = [vp for vp in viewports if vp.dxf.status > 0]
if viewports[0].dxf.get("status", 1) == 1:
    viewports.pop(0)          # ← 就是这一行丢掉了 status==1 的视口
```

其上方原注释说明：`status==1` 表示 *the active viewport*，它
*determines how the paperspace layout is presented as a whole*，
所以 ezdxf 认为不必再单独绘制。**但 `1` 恰恰是磁盘上 AutoCAD 标准文件的正常值。**

**处理方式**：仅在**内存副本**中临时把 `status` 抬到 `2` 让渲染器愿意画它。
渲染结束不回写、不保存 —— 磁盘 DXF 保持 `status=1`，
AutoCAD 及其他软件打开行为不受影响。

### 三、识图读取通用化（外部真实图纸）

面对外部软件转出的真实 DXF，`drawing_reader` 做了三项健壮性修复：

| 问题 | 现象 | 处理 |
|---|---|---|
| 中文名被写成 `\U+XXXX` 转义 | 图层名变成 `IRC\U+5929\U+82B1`，按图层名匹配的规则**静默全不中**（不报错） | `_decode_uesc()` 解码 |
| 无名图层 / 缺名字的表记录 | ezdxf 加载阶段直接抛 `DXFTypeError`，**读不了** | 跳过无名图层；加载失败自动退 `recover` 模式 |
| 畸形的 OBJECTS 段 | 严格与 recover 都报错 | `examples/dxf_prepare.py` 剥段预处理 |

配套脚本：
- `examples/dwg2dxf_convert.py` —— DWG→DXF。**必须用 `CadOutputMode.CONVERT`**；
  默认的 `RENDER` 会把所有对象渲染成线段（文字炸成 POLYLINE、体积涨约 49 倍）。
- `examples/dxf_prepare.py` —— DXF 预处理。内部**按 (code, value) 成对解析**，
  因为 DXF 的"值"行本身可以是 `0`（实测 `281`/`0`、`90`/`0`），
  按行内容判记录边界会把记录切错位。

### 四、待办

1. **续页图幅命名模板化**：目前硬编码 `'GB_%s_说明%d'`（中文后缀）。应抽成可配置模板
   （如 `{base}_notes_{n}`），并允许通过参数覆盖命名规则，便于非中文环境/自定义图号体系。
2. 见文末「② 识图通用化」章节的结论与后续选项。

---

## ② 识图通用化：外部真实图纸实测结论（2026-09-11）

### 样本

素材库 `2026农村自建房别墅设计素材合集` 中随机取 **7 个真实 DWG**（同一套室内设计图，
含材料表 / 通用剖面图 / 1F / -1F / 2F / 3F / 中央空调新风地暖施工图），
人工标注图别真值后做评测。

### 一、能做的（已打通，v1.17.1 已落地）

| 环节 | 结论 |
|---|---|
| DWG→DXF | ✅ `CadOutputMode.CONVERT`。平均 **8.6 秒/文件**、体积膨胀 **7.8 倍**（均值 21.8MB）→ 182 个文件约 **26 分钟 / 3.9GB** |
| DXF→可读 | ✅ 预处理 + 容错加载后 **7/7 全部可读**（修复前 2/7 崩或残） |
| 图层/文字 | ✅ 取出真实图层（120~469 个）与真 TEXT 实体（含坐标） |

> ⚠️ 反面结论：默认的 `CadOutputMode.RENDER` **不可用** —— 会把所有对象渲染成线段，
> 文字炸成 POLYLINE（图内文字从此只能靠 `get_strings()`），体积 0.26MB→12.7MB（**49 倍**）。

### 二、不能做的（诚实结论）：**识别率不可用**

用技能现成的 `infer_drawing_type` 打这 7 张真实图纸：

| 口径 | 结果 |
|---|---|
| 严格正确 | **0 / 7 = 0%** |
| 宽松正确（同族近似） | **1 / 7 = 14%** |
| 认错 | **6 / 7 = 86%** ← 识图里最该压到 0 的指标 |

典型错法：材料表→火灾报警图、各层平面→火灾报警图、暖通图→节点大样图。

**⚠️ 一个必须记住的度量教训**：旧口径"识别成功 100%"是**假指标** ——
它只统计"有没有输出"，不统计"输出对不对"。本样本里它给 100%，
而真实严格正确率是 0%。**识图评测必须报"认错率"，不能只报"有没有识别"。**

### 三、根因（三条，均已用数据确认）

1. **规则只认自家图层命名**：`TYPE_BY_LAYERS` 匹配的是 `G_WALL`/`G_DOOR` 这套
   （本技能自己的输出约定），真实图纸用的是 `A建墙`/`IRC灯具` → 图层信号**零命中**。
2. **模板图例污染**：这批图纸同出一家设计院模板，**189 行图例文字出现在全部 7 个文件里**
   （火警/排烟/空调风/总平面/大样…），文字信号被图例主导。
   且**图纸自己的图名"首层平面图"本身就是模板行**（7/7 都有）——
   批量去模板会把正确答案一起删掉，这是结构性矛盾。
3. **图层是"文档级"而非"图纸级"**：AutoCAD 图层在整个 DWG 里定义一次，
   实测 6 张图各带 120~469 个图层且**共享同一套**。
   所以图层名只能判"这是室内设计图纸集"，**判不出是平面还是剖面**。

### 四、可判别信号在哪（下一步的方向）

在**版式/几何**，不在关键词：

- `01 材料表` 模型空间只有 **262** 个实体（主体在 Layout1 的 734 个）；
  `03 1F` 模型空间有 **29,361** 个实体 → **实体数量级本身就是强信号**。
- 材料表 = 表格线框；剖面 = 水平构造层 + 引出线；平面 = 闭合墙线 + 轴网。
  需要 `LWPOLYLINE`/`HATCH` 的几何统计，本技能已具备（`read()` 有几何量算）。

**但**：调阈值必须建立在足够样本上。**7 张样本调出来的阈值一定是过拟合**，
需要先抽 **30~50 张**建评测集（统一放 `benchmarks/`），再动规则。

### 五、边界（对外承诺时必须写清）

- ✅ 可承诺：**读得进**外部 DWG/DXF（转换 + 容错加载 + 中文转义解码）。
- ❌ 不可承诺：**认得出**外部图纸的图别（当前 0~14%，且 86% 会自信认错）。
- 对自家产物（`dxfkit` 生成、用 `G_*` 图层体系）识别率不受影响，仍按原规则工作。

## 标准图册 templates_atlas 包（v1.17.2 新增 · 扩「能画什么」）

包位置 `scripts/templates_atlas/`（`__init__.py` / `rebar_calc.py` / `pingfa.py`）。
地基是 `rebar_calc.py`（钢筋计算，按 GB 50010-2010 / 16G101-1 算锚固/搭接/弯钩/保护层/箍筋），
上层是 `pingfa.py`（平法标注生成器）。后续模块 `node_beam_column / node_stair / node_foundation / node_steel` 按同样模式加。

> `scripts/templates_pingfa.py` 已改为 **`templates_atlas.pingfa` 的薄再导出层**（单一真相源，避免双份实现发散）；其公开 API 名全部保留，examples/verify_pingfa.py 与 SKILL.md 引用不变。

### 〇、三层架构（与 `templates_struct.py` 的分工边界 · 已拍板）

结构施工图「钢筋相关」其实分三层，不要混：

| 层 | 模块 | 画什么 | 标准 |
|---|---|---|---|
| ① 通用构件配筋 | `templates_struct.py`（既有） | 把钢筋一根根画出来（单构件：柱/梁/板/基础/楼梯） | GB/T 50105-2010 |
| ② 平法注写 | `templates_atlas/pingfa.py`（本包） | 把国标注写符号标在平面上，**不画钢筋** | 16G101-1/2/3 |
| ③ 标准节点大样 | `templates_atlas/node_*.py`（规划中） | 16G101 规定的**连接构造**（梁柱节点钢筋排布、楼梯梯板配筋、基础插筋锚固、桩基） | 16G101-1/2/3 |

- ① 是「这个构件里钢筋怎么摆」（任意尺寸都能画，通用）。
- ② 是「图上那串代号是什么意思」（标注语言，不画钢筋）。
- ③ 是「标准连接处钢筋怎么交圈」（特定节点，强调锚固/搭接/排布构造）。
三者互补：一张真实结构图通常同时需要 ①构件配筋 + ②平法标注 + ③节点大样。

### 一、六大平法节点（② 层，均按 16G101 规则编码）

| 节点 | 函数 | 国标依据 | 关键注写 |
|---|---|---|---|
| 柱 KZ | `column_pingfa_note(ColumnPingfaParams)` | 16G101-1 柱表 | 柱号 / 标高 / `b×h b1 b2 h1 h2` / 角筋 / b边中部筋 / h边中部筋 / 箍筋类型号 `1(4×4)` / 箍筋 |
| 梁 KL | `beam_pingfa_note(BeamPingfaParams)` | 16G101-1 平面注写 | `KL2(2A) 300×700` / `Φ8@100/200(2)` / `2Φ25` / `G4Φ12` / `(-0.100)` + 原位 `6Φ25 4/2` |
| 板 LB | `slab_pingfa_note(SlabPingfaParams)` | 16G101-1 板块集中标注 | `LB1 h=120` / `B:X&Y Φ10@200` / `T:X&Y Φ10@200` / 支座原位筋 |
| 剪力墙 Q | `wall_pingfa_note(WallPingfaParams)` | 16G101-1 墙身 | `Q1 200` / 水平分布筋 / 竖向分布筋 / 拉筋 |
| 楼梯 AT | `stair_pingfa_note(StairPingfaParams)` | 16G101-2 | `AT1 h=120` / `1800/12=150` / 下部·上部·分布筋 |
| 独立基础 DJ | `found_pingfa_note(FoundPingfaParams)` | 16G101-3 | `DJj1 2400×2400` / `B:X&Y Φ14@200` / 基础底标高 |

统一签名 `func(b, params, x=0, y=0)`，图层用 `S_PINGFA`(注写) / `S_BEAM` / `S_COLUMN` / `S_SLAB` / `S_WALL` / `S_STAIR` / `S_FOUND`；钢筋符号用 `Φ`。
梁注写可选 `show_anchor=True`，附 `rebar_calc` 实算的 `laE=`（抗震锚固长度）标注。

### 二、钢筋计算器 `rebar_calc.py`（①/③ 层的地基）

按 16G101-1 第 8.3/8.4 节：
- `anchorage_length(d, grade, concrete, seismic, level)` → `lab/la/laE`（基本/锚固/抗震锚固）。
  公式 `lab = α·(fy/ft)·d`，α=0.14(带肋)/0.16(光圆)。
- `lap_length` → `ll/llE`（搭接，ζl: ≤25%→1.2 / 50%→1.4 / 100%→1.6）。
- `hook_length` → 弯钩（90°=12d，135°箍筋=max(10d,75)+1.9d，180°=3d+6.25d）。
- `cover_thickness` → 保护层（16G101-1 表 8.2.1，一类板15/梁20 … 三b 板40/梁50）。
- `stirrup_length` → 箍筋下料（内皮周长 + 两钩）。
- 验证：`examples/verify_rebar_calc.py` **26/26 全 PASS**（逐条核对锚固/搭接/弯钩/保护层/箍筋合 GB 50010-2010 / 16G101-1）。

### 三、内置 16G101 自洽校验（返回 `(ok, issues)`）

`validate_column / validate_beam / validate_slab / validate_wall / validate_stair / validate_found`
能抓出的典型违规（均已写进 `examples/verify_pingfa.py` 53/53 断言）：

- 柱：`b1+b2 ≠ b`、`h1+h2 ≠ h`、箍筋类型号格式非 `类型(列×行)`、角筋格式错。
- 梁：跨数 <1、箍筋肢数 <2、悬挑标识非 `none/A/B`、**支座上部筋上下排合计 < 上部通长筋根数**、支座筋缺 `上排/下排` 格式。
- 板：板厚 ≤0、底部/顶部未标双向 `X&Y`、钢筋格式错。
- 墙：墙厚 ≤0、分布筋格式错。
- 梯：踏步级数 <1、踏步高越界（不在 100~230）、纵筋格式错。
- 基：编号非 `DJj/DJp+序号`、底边非正、底部未标双向 `X&Y`。

### 四、节点库（③ 层）设计结论（已拍板 · Q1-Q3）

**Q1 分工边界**：不是「节点大样 vs 配筋图」的二分，而是三层架构（见本节〇）：
`templates_struct`=通用构件配筋；`pingfa`=平法注写；`node_*.py`=标准连接节点大样。各管一段、互补。

**Q2 复用现有 API**：③ 层节点大样**直接复用** `templates_struct` 的
`bar()`（双线钢筋）/ `bar_label()`（钢筋标注）/ `hook()`（弯钩）/ `bar_mark()`（编号圈）作基元；
节点 = bar 排布 + hook 锚固弯折 + bar_label 标注 + 复合箍（bar 画矩形箍+拉筋）。
不预建新基元；只有某个 16G101 构造确实缺（并筋/螺旋箍/锚固区箍筋加密/柱插筋基础锚固）时，才用现有基元组合或补 1~2 个 helper，缺啥补啥。

**Q3 挂在哪条链**：③ 层节点 = **builder-agnostic 独立函数 `func(b, params, x, y)`**，与 ①/② 一致。
- 不绑 NL 模糊路由（节点是精确构造，应显式调用 `node_*.draw(b, params, x, y)`）；NL 路由（"画一个300×600框架梁柱节点"→指向 node_*.py）是未来便利项，非 v1 必需。
- 不绑 `GBDxfBuilder`——国标图框是**输出承载层**、与节点内容正交：调用方想出标准图幅时，传一个 GBDxfBuilder（或先建再往上画节点）即可，节点模板本身不依赖它。
- 注册表 `PINGFA_NODES` / `PINGFA_VALIDATORS`（③ 层同理加 `NODE_*` 注册表）供 pipeline / NL dispatch 后续发现。

### 五、注册表 & 实测

- `PINGFA_NODES`：`{key: (函数, 参数类)}`，含 6 类；`PINGFA_VALIDATORS` 一一对应；`demo_all(b,x,y)` 一键画全六类。
- `examples/pingfa_demo.py` → `out_pingfa/pingfa_综合标注.dxf`(98 实体) + `pingfa_全节点.dxf`(98 实体，含 laE 标注)。
- `examples/verify_pingfa.py` → **53/53**；`examples/verify_rebar_calc.py` → **26/26**。
- 未改 `dxfkit.py` 与既有模板，**294 项历史验证零回归**（v1.17.2 仅增量）。

---

## ③ 层节点大样收尾 + 续页命名模板化（v1.17.3 收尾）

v1.17.3 干两件事：**把 ③ 层四个节点大样补齐并交付**，以及**把说明续页图幅命名抽成可配置模板**。

### 一、③ 层节点大样（v1.17.2 已建包，v1.17.3 补齐四节点并交付）

`scripts/templates_atlas/` 下四个 `node_*.py`，均为 **builder-agnostic 独立函数** `func(b, params, x=0, y=0)`，
复用 `templates_struct.bar()/hook()/bar_label()/bar_mark()` 作基元，锚固长度 `laE` 实算自 `rebar_calc.anchorage_length`：

| 节点 | 函数 | 国标 | 画什么 |
|---|---|---|---|
| 框架梁柱节点 | `node_beam_column.node_beam_column(BeamColumnNodeParams)` | 16G101-1 | 柱纵筋(四角+四周)+核心区箍筋+梁上下纵筋(端部 15d 弯锚)+laE 标注 |
| AT 梯板支承 | `node_stair.stair_node(StairNodeParams)` | 16G101-2 | 斜梯板+平台梁+下部筋贯通(两端锚入梁)+分布筋+laE |
| 柱基础插筋 | `node_foundation.foundation_node(FoundationNodeParams)` | 16G101-3 | 独立基础+柱插筋(底部 15d 弯折 a)+laE |
| 桩基承台锚固 | `node_steel.pile_node(PileNodeParams)` | 16G101-3 | 承台+桩(圆)+桩顶伸入承台(灌注50/预制100)+锚固筋 laE |

`梁柱节点` 是重头戏，参数 `BeamColumnNodeParams` 按桌面规格重写：
- 节点类型 `node_type`：`middle`(中柱) / `edge`(边柱) / `corner`(角柱) / `top_end`(顶层端) / `top_middle`(顶层中柱)；
- 截面用 `column_width`/`column_depth`（柱宽/柱深），梁用 `beam_left_*`/`beam_right_*`/`beam_top_*`/`beam_bottom_*`（左/右/上/下四向梁宽高）；
- 快捷函数 `middle_node(b,cw,cd,bw,bh)` / `edge_node(...)` / `corner_node(...)` 一键出对应节点；
- `NODE_TEMPLATES` 字典聚合 5 个入口（`node_beam_column`/`beam_column_node`/`middle_node`/`edge_node`/`corner_node`）；
- `validate_beam_column(p)` 抓柱纵筋非 4 倍数、抗震等级越界(0~4)、节点类型未知等。

**API 适配说明（桌面规格用了 3 个不存在的 builder 名，已按 dxfkit 真实 API 改写）**：
- 填充：`b.add_hatch(pts, pattern, scale, angle, layer)`（**第 4 参是 angle 不是 layer**，指定图层必须 `layer=` 关键字）；
- 线段：`b.line(x1,y1,x2,y2,layer=)`（**不是** `add_line`）；
- 尺寸：`b.dim_h(y,x0,x1,label,off,layer)` / `b.dim_v(x,y0,y1,label,off,layer)`（**不是** `add_dimension`）。

`templates_atlas.NODES` 注册表聚合四节点：`{key:(draw, Params, validate, doc)}`（`beam_column`/`stair`/`foundation`/`pile`），供 pipeline / NL 后续发现。
`examples/node_demo.py` → `out_nodes/nodes_综合大样.dxf`（四节点同图，216 实体）；
`examples/verify_nodes.py` → **29/29**；`examples/verify_node_beam_column.py` → 节点类型/参数/laE 三组全过。

### 二、续页命名模板化（① · 替掉硬编码中文后缀）

`scripts/gb_standards.py` 现在暴露：
- 模块级模板 `NOTE_SHEET_NAME_TEMPLATE = "{base}_notes_{n}"`（默认 → `GB_A3_notes_2`）；
- 模块函数 `get_note_sheet_name(base, paper, n, title="", template=None)`；
- 类方法 `BorderStandard.note_sheet_name(cls, base, paper, n, title="", template=None)`。

`natural_language_engine._draw_notes_pages` 已从硬编码 `'GB_%s_说明%d' % (paper, idx+1)` 改为调用
`BorderStandard.note_sheet_name(base="GB_%s"%paper, paper=paper, n=idx+1, title=td.get('title',''))`。
支持通过 `template=` 覆盖命名规则（向后兼容：传 `template="GB_{paper}_说明{n}"` 即回退旧中文命名 `GB_A3_说明2`），
便于非中文环境 / 自定义图号体系。`examples/verify_continuation.py` → **7/7**。

### 三、总验证（v1.17.3 零回归）

```
294（历史：verify_layout_notes 69 / verify_v114 60 / verify_pipeline_v115 57 /
     verify_nl 46 / verify_v115 37 / verify_interfaces 21 / verify_pipeline 4）
+ 53（verify_pingfa）
+ 26（verify_rebar_calc）
+ 29（verify_nodes）
+  7（verify_continuation）
+  verify_node_beam_column（节点类型/参数/laE 三组）
= 402+ 项零 FAIL
```

> ⚠️ `node_beam_column` 直跑脚本时原 `from .rebar_calc` 相对导入会失败；文件已加
> `try: from .rebar_calc ... except ImportError: from templates_atlas.rebar_calc ...` 兜底，
> 且 `__main__` 的 `sys.path` 已指向包根，故 `python node_beam_column.py` 可直跑自测（中柱 55 / 边柱 53 / 角柱 41 实体）。

---

## ③ 层节点大样接入自然语言路由（v1.17.4 收尾）

v1.17.3 把 ③ 层四个标准节点大样**画出来了**；v1.17.4 把它们**接进了 NL 引擎**——
现在一句「画一个 600x600 柱 300x600 梁的中柱节点」就能直接出图，无需手写 Python。

### 一、接入点（全部落在 `natural_language_engine.py`，不动 builder 继承链）

| 接入位置 | 内容 |
|---|---|
| `NLPParser.DRAWING_TYPE_PATTERNS` | 新增 4 条节点关键词（**类属性**，非模块级变量）|
| `DEFAULT_DIMS_MM` | 新增 4 个 `node_*` 默认尺寸（图框自适应比例用）|
| `NaturalLanguageGenerator._dispatch` | 新增 4 个 `node_*` → handler 映射（**实例字典**，非 `NL_DISPATCH` 模块变量）|
| `discipline_map` | 4 个 `node_*` → `structural`（决定自动追加哪套施工说明/规范）|

关键词表（先匹配先赢，**必须排在「基础平面/梁配筋/节点大样」等弱匹配之前**）：

| drawing_type | 触发词 |
|---|---|
| `node_beam_column` | 梁柱节点 / 框架梁柱节点 / 框架节点 / 梁柱连接 / 柱梁节点 / 中柱节点 / 边柱节点 / 角柱节点 / 顶层端节点 / 顶层中柱节点 |
| `node_stair` | 楼梯节点 / 梯板配筋 / 梯板支承 / AT型楼梯 / 梯段节点 |
| `node_foundation` | 基础节点 / 独立基础 / 承台插筋 / 柱插筋 / 基础插筋 / 基础大样 |
| `node_pile` | 桩基节点 / 桩基锚固 / 桩承台 / 桩头锚固 / 桩基大样 |

### 二、参数从原文解析（`_parse_node_text`）——柱/梁尺寸的语序问题

中文里柱梁截面有两种写法，且**尺寸对可能被相邻名词夹住**：
- 「600x600柱300x600梁」← 尺寸在名词**前**（柱被夹在 600x600 与 300x600 之间）
- 「柱800×800 梁400×800」← 尺寸在名词**后**

**不能用「名词最近中心距」**——第一例里 `柱` 距 `300x600` 更近，会把柱判成 300x600。
采用的规则是**零间隔相邻 + 尺寸在名词前优先**：
1. 找出所有 `数x数` 尺寸对及其起止位置；
2. 对每个尺寸对，判断它与 `柱/KZ`、`梁/KL` 是否**零间隔相邻**（中间无任何字符）；
3. 一个尺寸对若同时贴着两个名词（如「柱300x600梁」），取「尺寸在名词前」的那个（中文工程简写 `300x600梁` = 梁 300x600）。

其余参数：`node_type`（中柱/边柱/角柱/顶层端/顶层中柱 → middle/edge/corner/top_end/top_middle）、
`seismic_level`（一~四级/1~4）、`concrete_grade`（C30…）、`rebar_grade`（HRB400…）按正则抽取。

### 三、踩坑与修复（本轮真实报错）

| 坑 | 现象 | 修复 |
|---|---|---|
| **函数名不是 `node_xxx`** | `from templates_atlas.node_stair import node_stair` **ImportError** | 真实函数名是 `stair_node` / `foundation_node` / `pile_node`（`node_beam_column.py` 例外，就叫 `node_beam_column`）|
| **桩基不在 `node_pile.py`** | 无 `node_pile.py` 模块 | 桩基在 **`node_steel.py`**，函数 `pile_node` + `PileNodeParams` |
| dispatch 表位置 | 原以为是模块级 `NL_DISPATCH`（**不存在**）| 实为 `NaturalLanguageGenerator.__init__` 里的实例字典 `self._dispatch` |
| 关键词表位置 | 原以为是模块级 `DRAWING_TYPE_PATTERNS` | 实为 **`NLPParser` 的类属性** |
| 尺寸串字 | 「600x600柱300x600梁」柱被判 300x600 | 改零间隔相邻 + 前置优先（见上）|

> **`pipeline` 无需改**：`SPECIALTY_TEMPLATES` 是空字典且**不在生成路径上**，
> pipeline 走的是 `generate_from_text` —— 节点接进 NL 引擎即自动覆盖 pipeline。
> 故桌面规格里的 `nl_router_patch.py` / `pipeline_patch.py` 属于**死代码**，未采用；
> 改为直接进 `natural_language_engine.py`，复用 `templates_atlas` 单一真相源，无循环导入风险。

### 四、验证

`examples/verify_node_routing.py`（新增）四组共 **23 项断言**全绿：

| 组 | 内容 | 结果 |
|---|---|---|
| [1] 路由 | 5 句中文 → 正确 drawing_type + 有效 DXF | 5/5 ✅ |
| [2] 参数 | 柱/梁尺寸两种语序 + 节点类型 | 5/5 ✅ |
| [3] 注册 | `_dispatch` 4 键 + `NLPParser.DRAWING_TYPE_PATTERNS` 4 键 | 8/8 ✅ |
| [4] 不破坏既有 | 平面/梁配筋/钢柱/檐口大样/U 型楼梯详图 仍正常路由 | 5/5 ✅ |

示例：`画一个600x600柱300x600梁的中柱节点` → `node_beam_column`，柱 600x600 / 梁 300x600 / 中柱。
`生成边柱梁柱节点` → `node_beam_column`（边柱）；`AT型楼梯节点` → `node_stair`；
`独立基础柱插筋节点` → `node_foundation`；`桩基锚固节点` → `node_pile`。

---

## 钢结构节点扩展 + 识图评测集 + 统一验证入口（v1.17.4 · B/C/D 路线）

### D · 钢结构连接节点 `templates_atlas/node_steel_v2.py`

补 `node_pile.py`（只有混凝土桩基承台；**原名 `node_steel.py`，v1.17.5 重命名为 `node_pile.py` 以消除「steel 名却装桩基」的混名**）的缺口，新增**钢结构三类常用连接节点**，
约定与 ③ 层一致（builder-agnostic 独立函数 + dataclass 参数 + `validate_*`）：

| 节点 | 函数 / 参数 | 依据 | 画什么 |
|---|---|---|---|
| 钢柱脚 | `steel_column_base(SteelColumnBaseParams)` | GB 50017-2017 / 16G519 | 底板 + 二次浇筑层 + 工字形柱身 + 加劲肋（刚接）+ 锚栓（铰接 4 栓 / 刚接 8 栓）+ 锚固段 |
| 钢梁柱节点 | `steel_beam_column(SteelBeamColumnParams)` | GB 50017-2017 / 16G519 | 工字形柱 + 工字形梁 + 端板 + 翼缘焊缝（全/部分熔透）+ 腹板高强螺栓双列 |
| 钢梁拼接 | `steel_beam_splice(SteelBeamSpliceParams)` | GB 50017-2017 / 16G519 | 左右两段工字形梁 + 翼缘/腹板拼接板 + 高强螺栓（翼缘两列 + 腹板一排） |

- 注册表 **`STEEL_NODES`**（3 项）**独立于 `NODES`** —— 因为 `verify_nodes.py` 断言 `len(NODES)==4`，
  并入会破坏既有验证；`templates_atlas.STEEL_NODES` 已导出。
- **NL 路由**：新增 3 类图别 `node_steel_base` / `node_steel_beam_column` / `node_steel_splice`。
  ⚠️ **顺序敏感**：钢结构规则必须**先于混凝土节点**，因为「钢梁柱节点」含子串「梁柱节点」，
  否则会被 `node_beam_column` 抢走（实测踩过）。
- `examples/verify_steel_nodes.py` → **24/24**；`python scripts/templates_atlas/node_steel_v2.py` 可直跑自测
  （实体 27/29/31，反例各抓 ≥3 条）。

### B · 识图评测集 `benchmarks/`

| 文件 | 作用 |
|---|---|
| `benchmarks/ground_truth.json` | 真值表：`file / type / family(同族) / oov(是否在类型域) / **provenance(来源)** / source` |
| `benchmarks/eval.py` | 评测脚本，用真实 API `drawing_reader.read(path).drawing_type`；**按来源分组报数** |
| `benchmarks/check_provenance.py` | **来源取证闸门**：用 `$LASTSAVEDBY` + 内嵌自述判定样本是真实出图还是脚本自产 |
| `benchmarks/import_samples.py` | 把外部 DXF 按逻辑名拷进 `raw/`（`raw/` 已 .gitignore，136MB 不入库） |
| `benchmarks/README.md` | 口径、基线、根因、边界 |

**五口径**：严格正确 / 宽松正确（**不含严格**，保证各桶互斥）/ 正确拒识 / 空答 / **认错**。
> ⚠️ **度量纪律 #1**：旧口径「识别成功 100%」是**假指标**（只数"有没有输出"，不数"对不对"）——
> 本项目实测可同时成立「识别成功 100%」与「严格正确 0%」。改规则必须给 before/after **认错率**。
> ⚠️ **度量纪律 #2**：`read()` 低置信时返回占位符 `"未识别"`（非空）→ 旧口径 `refused` 桶**结构性恒为 0**
> （"正确拒识 0%"是假数字），且"如实说不知道"与"自信答错"被记成同一种错。
> 现把占位符视同**弃权**并单列 `abstain`（认错 = 自信答错 + 空答）。
> ⚠️ **度量纪律 #3**：**自产样本会稀释认错率**（系统认自己画的图必然更准）。已引入 provenance 字段 +
> 强制分组，**认错率只认 `external` 分组**。
> 脚本内置自洽校验 `strict+loose+refused+abstain+errored+wrong == n`。

**★ 校正基线（`--external-only`，8 张真实出图）**：严格 **0/8 (0%)** · 宽松 1/8 · **认错 7/8 (87.5%)**。
自产 13 张对照：严格 5/13 (38.5%) · 认错 8/13 (61.5%)。
根因：① 规则只认自家图层命名（真实图纸用 `A建墙`/`IRC灯具` → 零命中）；
② 模板图例污染（189 行图例文字出现在全部 7 个文件，且图名"首层平面图"本身是模板行）；
③ 图层是"文档级"判不出图纸级；④ **系统从不弃权**（拒识率恒 0，是认错率的主要上游原因）。
**可判别信号在版式/几何**：外部真实图纸 **10,027~29,361 实体** vs 自产 **56~375 实体**，差两个数量级。
> 样本 <30 张时任何阈值都是过拟合 → **先扩样本（30~50 张）再改规则**。
> **扩样本 SOP**：`import_samples.py` 导入 → `check_provenance.py --apply` 归类 → `--gate` 确认 →
> 才允许 `eval.py`。**未经取证的样本不得进入评测集。**

### C · 统一验证入口 `examples/verify_all.py`

```bash
cd C:\Users\binliu8199\.workbuddy\skills\dxf-generator
python examples/verify_all.py              # 全部
python examples/verify_all.py nl nodes     # 只跑名字含 nl / nodes 的
python examples/verify_all.py --list       # 列出
python examples/verify_all.py --json       # 机器可读（CI 用）
```

判定口径（**顺序重要**）：① 显式计数（`PASS n / FAIL m`、`通过 n/m`…）；
② 明确失败语（`存在失败`/`失败 n`/`FAIL n`/`问题项: 有`）；
③ **明确通过语优先于标记计数**（`验证通过`/`全部通过`/`端到端管线健康`）；
④ 兜底数 ✅/❌。
> ⚠️ 第 ③ 条是踩坑后加的：最初只用「数 ❌」，`verify_fonts` 因列出 6 个**本机未安装的字体候选**
> 打了 6 个 ❌ 被误判为 6 项失败（脚本自身输出其实是「✅ 验证通过」）——探测类 ❌ ≠ 失败。
> 自动发现新增 `verify_*.py`（排除自身防递归），rc 也参与判定。

## v1.17.5 收口（E5 规范库 + E4 命名 + 说明栏可读下限修复）

### E5 · 16G101 接入规范引用库（`construction_codes.py`）
- **根因**：旧 `get_codes_by_drawing_type` 只匹配 `'all' in applicability or drawing_type in applicability`，
  具体名图别（`node_beam_column` / `node_pile` / `node_steel_base` …）无法命中**语义标签**
  （`structural`/`beam`/`column`/`foundation`），导致节点图连 GB 50010 / GB 50204 / 16G101 都漏引。
- 新增 `PINGFA_CODES`（16G101-1/2/3 平法图集，priority=1 强条），并入 `ALL_CODES`
  → 规范库 **64 条×13 类 → 67 条×14 类**。
- 新增 `DRAWING_TYPE_ALIASES`，把具体名图别归一为语义标签，匹配逻辑 = `drawing_type` 精确 / `'all'` / 别名 三者任一命中。
- 节点图（梁柱/楼梯/基础/桩基/钢柱脚）生成后「执行规范」自动含 16G101；`examples/verify_e5.py` **21/21**。

### E4 · `node_steel.py` 重命名为 `node_pile.py`
- 该文件装的是**混凝土桩基**节点（函数 `pile_node`/`PileNodeParams`），原名 `node_steel` 与钢结构混名。
- 用 `mv` 改名（非 git 跟踪，避免 `git mv` 报错），同步更新 `templates_atlas/__init__.py`、
  `natural_language_engine.py`、`examples/node_demo.py`、`examples/verify_nodes.py` 共 4 处引用。
- ⚠️ 钢结构节点仍在 `node_steel_v2.py`（`STEEL_NODES` 注册表），**未受影响**。

### 说明栏「执行规范」可读下限回归修复
- **现象**：E5 别名修复后 `floor_plan` 匹配规范从 3 条涨到 20+ 条，`natural_language_engine._add_notes_to_sheet`
  把规范块预留高度封顶 42%（≈90mm，真实 ~105mm），逼 `add_code_references` 的 `auto_fit` 把字高压到 2.2mm（< 2.5mm 可读下限）。
- **修复**：① 预留高度封顶 0.42→0.6，让 `code_h` 贴近真实块高、不再逼压缩；
  ② `add_code_references` 的 `min_base_height` 3.0→**5.0**（规范清单最小字高 = base 的 0.5 倍，
  5.0×0.5=2.5mm 恰为 GB/T 50001 可读下限），从根上守住「宁可截断/分页也不压字到读不出」。
- `examples/verify_layout_notes.py` **70/70**（原 69/70，字高断言修复）。

**最终总验证（v1.17.5）：19 套件全绿 · 469 项可计数断言 · 0 失败**（约 2 分 50 秒）：
续页命名 7 · e5 — · 字体 — · 全量扩展 — · 接口层 21 · 布局+说明栏 70 · 自然语言 46 ·
梁柱节点 12 · 节点路由 23 · ③层节点 29 · 说明全套 — · 平法 53 · 端到端渲染 4 ·
NL 流水线 57 · 钢筋计算 26 · 钢结构节点 24 · 识图/算量/说明 60 · 3D 体量 37 ·
+ 高级模板+审图（无计数，按判定语通过）。

---

## v1.17.6 · B 路线样本污染更正 + 度量口径三修

### 事故：13 张"真实图纸"实为自产，把认错率稀释了

2026-09-12 执行 A 路线（把本机搜出的"确认真实"图纸扩进评测集），导入 13 张桃花源60# 系列
+ 1 张真实 DWG（荣和大地店），样本 7 → 21 张。跑出的总认错率 **85.7% → 71.4%**，看似改善。

逐张取源后发现**那 13 张全是 `ezdxf` 脚本产物**：

| 信号 | 外部真实出图 | 那 13 张"真实图纸" |
|---|---|---|
| `$LASTSAVEDBY` | `Administrator` / `妖怪` / `w`（人名） | **`ezdxf`** |
| 图层数 | 120 ~ 469（设计院模板） | 8 ~ 14（自定层 `AXIS/WALL/AREA/NOTE`） |
| 实体数 | 10,027 ~ 29,361 | 56 ~ 375 |
| 内嵌自述 | 无 | 4 张含『AI 平面示意草图 · 非施工图』『外轮廓按面积 135㎡ 反算』 |

连被当作"真实剖面图"的 `剖面图_1-1.dxf` 同样是 ezdxf 产物（`SEC_*` 自定层）。

> **教训**：光看"图层名不含 `G_` 前缀"判来源会漏判——`AXIS/WALL/AREA/NOTE` 也是脚本层名。
> **`$LASTSAVEDBY` 才是最可靠的单一信号。**

### 校正后的真实基线（没变差，也没变好）

| 分组 | 张数 | 严格正确 | 认错 |
|---|---|---|---|
| **external 真实出图** | 8 | **0 (0%)** | **7 (87.5%)**（自信答错 6 + 空答 1） |
| self_generated 自产 | 13 | 5 (38.5%) | 8 (61.5%) |

**真实识别能力与 v1.17.1 的 0/7、86% 相比没有任何改善**；"改善到 71.4%" 全部来自样本污染。

### 度量口径三修（`benchmarks/eval.py`）

| 修 | 问题 | 处置 |
|---|---|---|
| #1 | 「识别成功 100%」是假指标 | 一律报**认错率**（沿用 v1.17.1） |
| #2 | `refused` 桶**结构性恒为 0**（`read()` 低置信返回占位符 `"未识别"` 而非空值），"如实说不知道"与"自信答错"被记成同罪 | 占位符视同**弃权**并单列 `abstain`；`认错 = 自信答错 + 空答` |
| #3 | `loose` 把 `strict` 重复计入（5+6+0+1+0+14=26 ≠ 21） | `loose` **排除** `strict`；内置自洽校验 `六桶之和 == n` |

新增 `--external-only`：只评真实出图样本 —— **这是唯一能衡量真实识别能力的分母**。

### 新增防复发闸门 `benchmarks/check_provenance.py`

- 自动判定优先级：内嵌自述 > `$LASTSAVEDBY=ezdxf` > 人名 > 空则 `unknown`（须人工归入 `MANUAL`，
  aspose 格式转换会丢 `$LASTSAVEDBY` 与图层表，故 `荣和大地店_平面布置图` 走人工判定）。
- `--apply` 把结论写回真值表；`--gate` 与记录比对，出现 `unknown` 或不符即 `exit 1`。
- 实测 **21/21 全部定性一致，闸门通过**。

### 结论与下一步（优先级已重排）

1. **扩真实样本到 30 张**（必须 `$LASTSAVEDBY != ezdxf`）—— 唯一能让 8 张分母变可信的动作。
2. **给 `read()` 加弃权能力**（低置信返回空值而非 `"未识别"`）—— **优先级高于调关键词**，
   这是把认错率压向 0 的**唯一**路径。
3. 引入几何/版式特征（实体量级、HATCH 占比、闭合墙线数）替代纯关键词投票。

---

## v1.17.6 补 · 修掉 aspose `BLOCKS` 段漏写 SEQEND 的 bug（`examples/dxf_prepare.py`）

### 现象与根因
aspose-cad 转出的 DXF，**3/8 样本 `ezdxf` 严格与 `recover` 两种模式都读不了**：
`DXFStructureError("Expected DXF entity POLYLINE or SEQEND")`。

定位结果：aspose 把 `POLYLINE + VERTEX*` / `INSERT + ATTRIB*` 写进 **`BLOCKS` 段**时
**漏写结尾的 `0 SEQEND`**，而**同一文件的 `ENTITIES` 段写得完好**。
缺 SEQEND 违例数与 BLOCKS 段 POLYLINE 数**完全相等**：

| 样本 | BLOCKS 段 POLYLINE | 缺 SEQEND | ENTITIES 段违例 |
|---|---|---|---|
| 2层坡屋顶别墅建筑施工图 | 33 | 33 | 0 |
| 三维模型 | 15 | 15 | 0 |
| FF08 | 38 | 38 | 0 |
| 节点 / 57 | 0 | 0 | 0 |

→ 完美解释"有的能读、有的读不了"。修：新增 `repair_missing_seqend()` 并接入 `prepare()`，
**可读率 5/8 (62.5%) → 7/8 (87.5%)**（剩 1 张是 3D 网格模型，另有更深问题）。

### ⚠️ 修这个 bug 时踩的坑（代价很大，必须记住）
第一版实现用"**只前进不写出**"的 `skip_tag_block`，把实体自身组码（句柄/坐标/图层）**全吞了**：

| 样本 | 原始 | 有 bug 版 | 正确版 |
|---|---|---|---|
| 平立剖面图1 | 739,594 行 | 620,406（**-35%**） | 739,594（±0） |
| FF08 | 1,586,840 行 | 1,398,300（-11.9%） | 1,586,916（+76） |
| 三维模型 | 163,224 行 | 62,580（**-61.7%**） | 163,254（+30） |

**最危险之处：ezdxf 仍能读出结果文件、且不报任何错**，只是内容静默变少 ——
差一点把"残缺图纸"当成"修复成功"入库。

### 因此给 `prepare()` 加了**组数守恒断言**（按 (code,value) 组精确记账）
```
输出组数 == 输入组数 - 删的 OBJECTS 组 - 删的畸形表记录组 + 补的 SEQEND 组
```
不成立即抛 `AssertionError` **拒绝写出**，绝不静默产出坏文件。
（`repair_table_records` 改为薄包装，新增 `_repair_table_records` 返回 pair 数供记账，外部 API 不变。）
> ⚠️ 该公式在**下一节**又扩了两项（删的图标 XDATA 组）；`normalize_binary_chunks` 只改值不加删组，故不进账。

全量验证：**19/19 套件 · 469 断言 · 0 失败**。

---

## v1.17.7 · 又修两类"彻底读不了"（`examples/dxf_prepare.py`）

上一节的 SEQEND 修复只覆盖了**一半**。第二轮对别墅 24 张做全量排查，又定位并修掉两类，
**全批从"2 张彻底读不了"变成"24 张全部可读"**（严格 21 / 需 recover 3 / 失败 0）。

### ⑤ `INSERT` 声明 `66=1` 却无 ATTRIB —— 判据必须是"声明"本身

`三维模型.dwg` 严格+recover **双失败**：`Expected DXF entity INSERT or SEQEND`。

根因：`INSERT` 带 **`66=1`（attribs_follow，"后面有属性"）**，但**一个 ATTRIB 都没写、也没有 SEQEND**。
ezdxf 按该声明进入子实体循环，期望 ATTRIB/SEQEND 却撞见下一个实体 →
`ezdxf/entities/subentity.py:184` 抛错（报错消息里的类型是**实际撞到的**实体，不是期望的那个，
所以看到 `INSERT` 时要知道"是解析 INSERT 的属性序列时撞见了 INSERT"）。

**⚠️ 关键教训**：这类**不能**靠"看到 ATTRIB 才补 SEQEND"来修 —— 它**一个 ATTRIB 都没有**。
上一版 `repair_missing_seqend()` 用 `if n_att:` 判断，把**整类**漏掉了。
判据必须是 **`66=1` 这个声明本身**。改后 `if n_att or declared_attribs:`。

证据（24 个文件全量排查）：

| 文件 | `66=1` 有 ATTRIB 且收尾 SEQEND | `66=1` 无 ATTRIB 且未收尾 |
|---|---|---|
| 22_三维模型 | 7 | **3 ← 唯一一处** |
| 其余 23 个 | 8 ~ 965 | **0** |

→ 完美解释"为什么只有这一个文件读不了"。修后 **strict ✅**，新增 `ins3(声明3)` 计数可审计。

### ⑥ XDATA 二进制块写成"带横线的十六进制" —— `E立面.dwg`

严格+recover **双失败**：`Invalid binary data near line: 5156`。

根因：组码 **`1004`（XDATA 二进制块）** 的值写成 `28-00-00-00-20-…` ——
这是 AutoCAD **`.pat`/打印格式**，而 DXF 要求**纯十六进制**。
实测 85 处，**全部挂在 APPID `CONTENTBLOCKICON` 下** = **块缩略图图标**（非图纸内容）。

修法（两条，互补）：
- `strip_icon_xdata(pairs)` —— 整块删除 `ICON_XDATA_APPIDS`（默认 `CONTENTBLOCKICON`）的 XDATA：
  `1001 <APPID>` 起，到下一个 `0` 或下一个 `1001` 为止，中间组码都在 1000~1071。
  **既读不了又占体积**，删掉最干净。
- `normalize_binary_chunks(pairs)` —— 兜底：把残留的 `310~319`/`1004` 里**形如** `xx-xx-xx`
  的值去横线归一成纯十六进制。**原地替换、不增删组**，故不影响守恒账。

修后 `E立面` → **recover 可读**（删 5 个图标块 / 95 组）。

### 扩容后的守恒公式
```
输出组数 == 输入组数 - 删的 OBJECTS 组 - 删的畸形表记录组 - 删的图标 XDATA 组 + 补的 SEQEND 组
```
实测 **24/24 全部 ✅**。`prepare()` 新增返回键：
`icon_xdata_blocks` / `icon_xdata_pairs` / `binary_chunks_fixed` / `seqend_insert_declared`。

### 附带发现：3 张需 recover 模式
`03_别墅结构1.09` / `14_E立面` / `19_E门窗` 严格模式读不了、recover 可以。
好在 `drawing_reader._load_dxf_tolerant()` **已内置 strict→recover 兜底**，
所以这 3 张**不会**被误记成"读取异常"（否则会污染认错率的分母口径）。

---

## v1.17.7 · 来源闸门加"结构指纹兜底"（`benchmarks/check_provenance.py`）

### 问题：转换器会无条件抹掉 `$LASTSAVEDBY`
aspose CONVERT 转出的真实图纸，**`$LASTSAVEDBY` 实测 24/24 全空**。
旧闸门规则 4 遇到空值就判 `unknown` 并要求人工补 `MANUAL` ——
**整批真实图纸会被卡死**，等于"闸门太严导致无法扩样本"。

### 解法：结构指纹（两类样本差异是**数量级**级别）

| 指标 | self_generated（13 张实测） | external（真实出图） | 分界余量 |
|---|---|---|---|
| `$ACADVER` | **100% AC1024**（ezdxf 默认） | AC1015 / AC1018 | — |
| 模型空间实体数 | 6 ~ 375 | **1,221 ~ 156,649** | 1000 卡在 375↔1221 |
| 图层数 | 8 ~ 17 | 2 ~ 469 | 20 卡在 17↔20 以上 |

新规则 4：`$ACADVER ∉ {AC1024, AC1027, AC1032}` **且**（`实体 ≥ 1000` **或** `图层 ≥ 20`）→ `external`。
两条件**并联**是为兜住"实体少但图层多"的真实图 —— 修好后的 `三维模型` 只有 277 实体、
却有 35 图层，单看实体会被误判 `unknown`。

**⚠️ 已知局限（故意的失效方向）**：真实图也有实体少、图层也少的（已入库 `01 材料表.dxf` 仅 262 实体）。
这类若又被抹掉 `$LASTSAVEDBY` → 判 `unknown` 卡闸门。
**宁可卡闸门耽误时间，也不误收一张脚本产物** —— 误收正是 2026-09-12 污染事故的形态。遇到就人工补 `MANUAL`。

证据串会把**三项数值全写进 `provenance_evidence`**，便于复核。
✅ 对现有 21 张**零影响**：`external=8 / self_generated=13 / unknown=0`，`--gate` exit 0。

---

## v1.17.7 · 别墅图纸集素材勘察结论（A 方案）

### 家底
`F:\…\30070062\别墅建筑` = 205 文件 / 472 MB，**188 个 DWG**（AC1014/AC1015）。
**全部是别墅建筑**，无工业/市政/机电 → 专业多样性为零。

### ★ 命名可标注性只有 12.8%
| 类别 | 数量 | 说明 |
|---|---|---|
| A 名字能定**单一**图别 | 24 | `结构图.dwg` / `立面图.dwg` / `节点.dwg` … |
| M 名字含 ≥2 个图别 | 5 | `平立剖面图1` / `各层平面立面图` … |
| B 名字表明"整套/方案" | 36 | `别墅全套建筑施工图` / `别墅方案设计` … |
| X 3D/效果图 | 3 | `三维模型` / `透视图` / `鸟瞰图`（天然 **OOV** 样本） |
| C 名字无图别信息 | 117 | `FF08` / `57` / `SG01` … |

### ★ 但 A 类里"名字像单图别、内容其实是整套图"的很多
对 24 张 A 类候选做**内容取证**（扫**模型空间 + 全部块定义 + INSERT 的 ATTRIB**，
并解码 `\U+XXXX` 中文转义；只扫模型空间会**漏掉标题栏块里的图名/图号**，导致图别命中几乎全空）。

结果：**只有 14 张**内容真属单一图别，另外 **5 张**实为多图别套图：

| 剔除的文件 | 证据 |
|---|---|
| `别墅建筑结构全套图纸` | 实体 **156,649**；强命中 平面图22 + 立面图12 + 配筋图4 + 门窗表2 |
| `别墅结构` | 强命中 **12 种**图别；文字含『基础层梁钢筋图/3层板钢筋图』 |
| `钢结构别墅建筑` | 强命中 平面8 + 立面8 + 剖面4 → 建筑全套 |
| `E平面` | 强命中含 剖面14 + 立面8；图框关键词有『**图纸目录×2**』 |
| `平面` | 图框关键词 设计60/比例30/图号30 → **约 30 个图框**，是**图集** |

### ⚠️ 三个方法学陷阱（写进判据，别再踩）
1. **真值不能用文字关键词自动反推** —— 文字正是识别的输入特征，同源标注 = **循环论证**，
   会造出"识别率 100%"的假结果（污染事故的另一形态）。真值必须**人确认**，机器只给"建议+证据"。
2. **图签里的专业名不是内容** —— `2-270-节点大样` 的标题栏块（`tuA2|图签`）里有
   『电气/给排水/建筑/结构/暖通』五个专业名，按关键词计数会误判为多图别。
3. **文件名可以说谎** —— `错层别墅建筑结构施工图.dwg` 的内容实为**平面图**（平面图×33）。
   入库时**保留原名**，正好记录这个真实场景。

### 结论
A 方案落地后 external 真实样本 **8 → 22 张**（离 30 张目标仍有距离）。
B 方案（全批 188 张 + 改框架支持"真值=图别集合"）待 A 落地、真实基线稳定后再议 ——
那 5 张被剔除的套图是它的现成第一批数据。

（→ v1.17.8 已实际落地：**18 张入库，external 8 → 26 张**，见下节。）

---

## v1.17.8 · 别墅样本入库 + 又修两类读不了 + 补上 `dxf_prepare` 的验证空洞

### 一、又修两类「彻底读不了」（`examples/dxf_prepare.py`）

**第 ④ 类：`TABLES` 段失去 `ENDSEC` —— ⚠️ 这一类是我们自己造的**
- **现象**：`18 别墅_别墅结构1.09.dxf` → `DXFStructureError: missing ENDSEC tag.`
- **根因**：`_repair_table_records()` 只按"下一个 `NAMED_TABLES` 记录头"切记录边界。
  排在**表末尾**的那条无名记录，会把紧跟其后的 `0 ENDTAB` / `0 ENDSEC` 一起算进自己的
  记录体；该记录因无名被丢弃时，**段尾标记跟着陪葬** → TABLES 段永久失去 ENDSEC。
- **佐证**：原文件另报 `DXFTypeError: name has to be a string, got <class 'NoneType'>`
  —— 正是触发这一路的条件（**最后一条表记录缺 `2` 名字组**）。
- **修法（双保险）**：
  1. **治本**：记录边界改为在 `ENDTAB`/`ENDSEC`/`TABLE` 处也切断
     （新增 `TABLE_RECORD_HEADS = NAMED_TABLES ∪ {ENDTAB, ENDSEC, TABLE}`）；
  2. **兜底**：新增 `repair_missing_endsec()`，事后给未闭合的 SECTION 补 ENDSEC。
- **修后**：`补ENDSEC=0`（边界修法已从源头保住），strict ✅。

**第 ⑤ 类：`ENDBLK` 空句柄**（`drop_empty_handles()`）
- **现象**：`24 别墅_E门窗.dxf` → `ValueError: Invalid handle .`；
  recover 模式只能刷屏 `skipped invalid handle "" in DXF entity "ENDBLK"`。
- **根因**：`ENDBLK` 的 `5`（句柄）值为**空字符串**。空句柄在 DXF 里**任何情况下都非法**。
- **实测**：`E门窗` **12 处**、`E立面` **19 处** → 两张都从 recover 升到 **strict**。
- **修法**：删掉该 `5` 组，ezdxf 会像处理"无句柄旧版 DXF"一样自动补新句柄。

**副产品：一个"看着像漏修"的噪声**
`E门窗` 的组码 **450~459（MLINE）**有 **91 处**横线十六进制（同第 ③ 类的家族），
但**全部宿主在 OBJECTS 段的 XRECORD 里**，随「整段删 OBJECTS」自然消失（clean 实测 **0 处**）。
**无需新增修复**，已写进注释以防下次误判。

**效果**：别墅 24 张 **严格可读 24 / 需 recover 0 / 失败 0**（v1.17.7 时 21/3/0）。
守恒断言扩容为：
`输出组数 == 输入 - 删OBJECTS - 删畸形表记录 - 删图标XDATA + 补SEQEND + 补ENDSEC - 删空句柄`，
另加两道**结构自检**（每 SECTION 必有 ENDSEC、不得残留空句柄组），任一不满足即 `AssertionError` 拒写。

### 二、★ 补上最大的一块验证空洞：`examples/verify_prepare.py`（53 断言）

> `dxf_prepare` 从 v1.17.6 起累积了 5 类缺陷，却**没有任何套件覆盖它** ——
> 所以第 ④ 类（自己吞掉 ENDSEC）能一直潜伏到这批别墅图才被撞出来。

用**合成 DXF**（ezdxf 生成基线 + 文本层注入缺陷），**不依赖任何外部图纸数据集**。
每类都要过四关：① 注入后**确实读不了**（负向对照）→ ② `prepare` 不抛异常且守恒 →
③ `prepare` 后**严格模式可读** → ④ 关键结构仍在。

**两个注入陷阱**（已写进脚本注释，都是踩过的）：
1. **第 ② 类的基线里，INSERT 后面必须再跟一个实体**。若 INSERT 后面直接是 `0 ENDSEC`，
   ezdxf 的链接子实体循环**自然结束、不报错**，缺陷复现不出来。
2. **第 ④ 类必须"删掉 `2` 组"，不能"置空串"**。空串仍是 `str`，ezdxf 不报错；
   只有组缺失才让 `name` 变成 `None` → 才会报 `DXFTypeError`。

### 三、`benchmarks/eval.py` 修一个会让整批评测崩掉的 bug（度量教训 #4）

- **现象**：OOV 样本的真值写的是 `"type": null`，`truth = s.get("type", "")` 取到的却是 **`None`**
  → 打印时 `truth[:10]` 抛 `TypeError: 'NoneType' object is not subscriptable`，**评测中断**。
- **修**：统一 `(s.get("type") or "").strip()`，显示层用 `(OOV 无对应类)` 标签。
- ⚠️ **教训推广**：`dict.get(k, default)` 的 default **只兜"键缺失"，不兜"值为 null"**。
  读外部 JSON 一律用 `x.get(k) or default`。

### 四、★ 真实基线（`eval.py --external-only`，external n = 8 → **26**）

| 口径 | v1.17.6 (n=8) | **v1.17.8 (n=26)** |
|---|---|---|
| 严格正确 | 0 (0%) | **3 (11.5%)** |
| 宽松正确 | 1 | 1 (3.8%) |
| 正确拒识 | 0（桶**结构性恒为 0**） | **3 (11.5%)** ← 首次出现 |
| **★ 认错** | **7 (87.5%)** | **19 (73.1%)** |
| 　自信答错 | 7 | 16 (61.5%) |
| 　空答/弃权 | 0 | 3 (11.5%) |

⚠️ **87.5% → 73.1% 不是能力提升**，是分母从 8 张换成 26 张（含 14 张新别墅图 + 4 张 OOV）。
**禁止当作改进证据。**

**两个可直接读出的信号**：
1. **首次出现「正确拒识」**：3 张 3D/效果图**真的弃权了** → 待办 P0「给 `read()` 加弃权能力」
   这条路**已被证明可行**（历史上 `refused` 桶恒为 0，因为占位符 `"未识别"` 是非空字符串）。
2. **最大错误簇：5 张被齐刷刷识成 `火灾报警图`**
   （`01 材料表`/`02 通用剖面图`/`03 1F`/`05 2F`/`06 3F`），占 16 处自信答错的 **31%**。
   已知是**模板图例污染** → 压认错率的**第一顺位靶子**，优先于调关键词。

### 五、入库清单（18 张）

- **14 张单图别**：平面图 3 / 立面图 3 / 节点大样图 4 / 结构配筋图 3 / 结构图 1
- **4 张 OOV**：透视图 / 鸟瞰图 / 三维模型 / `E门窗`（词表无「门窗图」类）
- 被剔除 **5 张**（内容实为多图别套图）→ B 方案第一批数据
- `ground_truth.json` v1.3 → **v1.4**，新增 `preprocess_note`（⚠️ raw/ 内预处理状态**不统一**：
  基线 13 张仍带 OBJECTS 段，别墅 18 张已过 `dxf_prepare` —— 因 `read()` 不调 `prepare`）与 `baseline_note`。
- 人读交付：`outputs/别墅样本_入库与真实基线报告.md`

### 六、最终总验证
**20 套件全绿 · 522 项可计数断言 · 0 失败**（约 1 分 21 秒）。
新增 `examples/verify_prepare.py` **53/53**（已注册进 `verify_all.py` 的 `SUITE_NAMES`）。

---

## v1.17.9 · 识图「弃权」能力落地 + 阈值实证（★ 幂等性：默认关闭，基线零变化）

> 承接 v1.17.8 的结论：**识别率不可对外承诺**（external n=26：严格正确 3、★认错 19）。
> 压认错率继续调关键词 = 过拟合小样本，**唯一可行路径是给识图加「弃权」** ——
> 低置信/并列时拒绝作答，把「自信答错」转成「空答」。

### 一、`DrawingInfo` 新增三字段（`scripts/drawing_reader.py`）

| 字段 | 含义 | 默认 |
|---|---|---|
| `type_margin: float` | **决策裕度 = top1 - top2**（"赢得多干净"），**总是**计算 | `0.0` |
| `abstained: bool` | 系统是否拒绝作答（True 时 `drawing_type` 为占位符） | `False` |
| `abstain_reason: str` | 弃权原因（人读，便于复盘） | `""` |

**★ 关键设计决策：弃权时 `drawing_type` 仍写占位符 `"未识别"`，不写 `None`。**
理由：`pipeline.py` / `construction_notes_v2.py` / 各 demo / `to_dict()` / `to_markdown()`
**全部按字符串处理**（`info.drawing_type or "未识别"`、`%s` 格式化）。
改成 `None` 会让这些调用点从"拿不到答案"退化成"崩掉"，而收益（区分"未识别"与"没答案"）
已由 `abstained` 布尔字段提供 —— **占位符保持原样，弃权语义另立字段**。

### 二、新增 API（向后兼容）

- `score_drawing_types(layer, texts, filename="") -> Dict[str, float]`
  —— 返回**全部候选**的得分（原 `infer_drawing_type` 只看 top1，看不到 margin）。
- `infer_drawing_type_ex(...) -> (类型, 置信度, 裕度, 证据)`
  —— 四元组；**旧 `infer_drawing_type` 保持三元组不变**，内部转调 `_ex`。
- `set_abstain_thresholds(conf=..., margin=...)` —— 运行时改门槛（供评测扫阈值，不必改源码）。
- 常量 `PLACEHOLDER_TYPE = "未识别"`、`ABSTAIN_CONF_THRESHOLD`、`ABSTAIN_MARGIN_THRESHOLD`。

### 三、★★ 阈值实证：置信度没用，**决策裕度才是唯一有判别力的信号**

`eval.py --sweep`（external n=26，真实代码路径）：

| 阈值 (conf, margin) | 严格正确 | 宽松 | 拒识 | 空答 | 自信答错 | ★认错 | 危险率 |
|---|---|---|---|---|---|---|---|
| **(0.0, 0.0) 现状** | 3 | 1 | 3 | 3 | **16** | 19 (73.1%) | 61.5% |
| (0.3, 0.0) ← 直觉方案 | 3 | 1 | 3 | 3 | **16** | 19 (73.1%) | 61.5% |
| (0.5, 0.0) | 3 | 1 | 3 | 3 | **16** | 19 (73.1%) | 61.5% |
| (0.6, 0.0) | **1** | 0 | 4 | 16 | 5 | **21 (80.8%)** | 19.2% |
| **(0.0, 0.2)** ← 实测最优 | **3** | 0 | 4 | 16 | **3** | 19 (73.1%) | **11.5%** |
| (0.0, 0.3) | **2** | 0 | 5 | 19 | **0** | 19 (73.1%) | 0.0% |
| (0.7, 0.2) | 1 | 0 | 4 | 18 | 3 | **21 (80.8%)** | 11.5% |

**三条硬结论**：

1. **置信度阈值是空操作**：`conf` 只有 `{0.0, 0.5, 0.7}` 三档，
   3 张严格正确的 conf（0.5/0.5/0.7）与 16 张自信答错的 conf
   （0.0×3 / 0.5×10 / 0.7×3）**完全重叠**。门槛 0.3/0.4/0.5 与"关闭"**逐桶完全相同**
   （因为 `conf<0.3` ⟺ `conf==0` ⟺ 本就已返回占位符）。
   **提到 0.6 反而更差**：把对的也弃了（严格 3→1，未答对 19→21）。
2. **`margin` 才分得开**：`margin ≥ 0.2` → 自信答错 **16→3（-81.3%）**，
   严格正确 **3→3（零损失）**。因为 `margin==0`（并列）是答错高发区：
   26 张里 **20 张 margin==0，其中 16 张（80%）是自信答错**。
   → **"赢得很勉强"比"分数低"更值得警惕。**
3. **弃权不会降低 `★认错`（fail）**：`fail = 自信答错 + 空答 + 读取异常`，
   弃权只是把「危险错误」**搬进**「空答」桶，总数恒为 19。
   → 要看清这一点，必须**单列「危险率（自信答错率）」并把它当第一指标**。

**⚠️ 因此门槛默认 `0.0`（关闭），并在 `verify_abstain.py` 里写死断言锁定默认值** ——
n=26、严格正确仅 3 张时**任何阈值都是过拟合**（`eval.py` 自己也印这句警告）。
**翻转默认值的前置条件：先把 external 扩到 ≥30 张。**

### 四、`benchmarks/eval.py`

- 优先读 `info.abstained`（显式标记），**保留占位符字符串兜底** —— 老版本 reader
  无该字段时 `getattr(..., False)` 取 False，两条路径结果一致（有断言锁定）。
- 新增 `--abstain-conf` / `--abstain-margin`（不改源码扫阈值）、`--sweep`（出对照表）。
- `--sweep` 实现：先按"不弃权"**读一遍**缓存 `(conf, margin)`，再纯模拟各阈值 ——
  弃权规则是 `f(conf, margin)` 的纯函数，没必要为每个阈值重读 26 张图（每遍 2~4 分钟）。
  **模拟保真度已验证**：`--abstain-margin 0.2` **实跑**结果与模拟**逐桶一致**。
- 修一处契约瑕疵：OOV 样本 `truth==""` 时 `truth and truth in inferred` 求值成 `""`
  → JSON 里出现 `"loose": ""`（假值但是字符串）。桶判定靠真值性没错，但契约上应为
  `false` → 六个桶统一套 `bool()`（**度量教训 #5**：置信度不该当门槛，裕度才该）。

### 五、★ 新增 `examples/verify_abstain.py`（53 断言 · 合成 DXF，不依赖外部图纸）

防三类回归：
1. **行为回归**：门槛默认 0.0 时识别结果必须与改动前**逐字一致**（否则 v1.17.8 基线作废）；
2. **泄漏回归**：用**行为**证明文件名没被当信号 —— 造一张名为 `平面图.dxf`
   但图内**零平面图信号**的图，必须**弃权**；若泄漏则会答"平面图"。
   （不靠读源码断言，读源码的断言在重构时会变假阳性。）
   背景：评测集 26 张里 **6 张文件名直接含真值关键词**，
   一传 filename 严格正确就会从 3/26 虚增到 9/26 —— **那是把答案喂给模型**。
3. **契约回归**：三元组/默认值/`to_dict`/`to_markdown`、
   以及不变式「`abstained` ⇔ 占位符」（eval 两条判定路径等价的前提）。

### 六、最终总验证（v1.17.9）
**21 套件全绿 · 575 项可计数断言 · 0 失败**。
新增 `verify_abstain.py` **53/53**（已注册进 `verify_all.py` 的 `SUITE_NAMES`）。
**基线幂等性实证**：改动后 `eval.py --external-only` 与 v1.17.8 基线
**逐桶逐字完全相同**（3 / 1 / 3 / 3 / 16 / 19）。


