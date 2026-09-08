---
name: dxf-generator
description: 用自然语言生成 DXF 矢量图纸的 Skill。封装 ezdxf 核心能力（文档/模型空间/图元/图层/保存/图纸空间），提供高层绘图库 dxfkit.py，让 Agent 把"画一个XX平面图/零件图/布置图/电气图"直接转成可打开的 .dxf 文件。无需安装 AutoCAD。支持五大功能：导入修改、参数化模板、批量处理、样式系统、自然语言分发；扩展模块含 geomkit 高级几何（齿轮/螺旋/贝塞尔）、archkit 建筑标准（轴网/双线墙/门窗/楼梯/图框/户型生成器）、budget 造价预算与采购清单、templates_arch 建筑专业（立面/剖面/节点大样/楼梯详图）、templates_struct 结构专业（钢筋符号/柱/板/基础/楼梯配筋）、templates_mep 机电专业（电气符号/电气图例/照明平面）；**GB/T 国标标准化**：gb_standards.py 提供 48 个国标图层、标准线型/线宽、符号/文字/图框标准与 GBDxfBuilder（A0~A4 图框+标题栏+1:100 视口，可直接出全套施工图）；**中文字体支持**：font_manager.py 自动注册 GB_CHINESE/GB_TITLE/GB_MULTILINE 样式（gbenor.shx + gbcbig.shx），所有含 CJK 的 TEXT/MTEXT 实体自动绑定中文样式，杜绝「中文显示为 ??」乱码；**施工说明模块**：construction_notes.py 按 GB 系列规范自动生成各专业施工说明（一般/土方/基础/主体/砌体/屋面/装饰/给排水/电气/暖通/消防/安全），一行 API 即可把说明写入图纸空间说明栏或模型空间；**施工规范引用模块**：construction_codes.py 内置 GB/JGJ 规范库 64 条×13 类，按图纸类型/专业自动匹配 强条/推荐/参考，CodeAwareDxfBuilder 一行把规范清单画进图纸空间或模型空间；**图纸管理全套**：drawing_management.py（图纸编号系统/目录/图签+会签栏/门窗表/材料做法表/结构设计说明/设备材料表/工程量清单 + CompleteDrawingManager 一键出全部表格）；**高级专业模板**：templates_advanced.py 十个模块——总平面图、防火分区·消防疏散图、空调系统图、防排烟系统图、雨水系统图、火灾报警系统图、智能化系统图、施工进度横道图、施工总平面图、钢结构详图（钢柱/钢梁）；**图纸审查系统**：v1.8.0 起 drawing_review.py 对图纸做 图层/图框/文字/尺寸/完整性/规范引用 六项自动检查，出 A~D 评级报告（文本 + 写入 DXF），ReviewAwareDxfBuilder 支持一行 .review()，BatchReviewer 批量汇总；**自然语言生成图纸**：v1.9.0 起 natural_language_engine.py 把中文描述（如「12x8 米三层住宅平面图带客厅厨房卧室」）按规则解析 → dispatch 到 19 类真实模板函数 → 一键出图，NLAwareDxfBuilder 提供 `generate_from_text(text)`/`parse_text(text)` 入口。
category: engineering-cad
version: 1.13.1
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
