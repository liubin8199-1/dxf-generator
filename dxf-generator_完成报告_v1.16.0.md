# dxf-generator Skill 完成报告 v1.16.0

| 项 | 内容 |
|---|---|
| 技能名 | `dxf-generator` 图纸工坊 |
| 版本 | **v1.16.0**（v1.15.0 → v1.16.0） |
| 技术栈 | 纯 Python / 离线 / ezdxf 1.4.4 |
| 报告日期 | 2026-09-10 |
| 主题 | **一键流水线（A＋B 任务：Scrapling MCP 试点 / 出图→算量→说明全链贯通）** |
| 状态 | ✅ C 落地验证 **55/55**；✅ B 试点跑通（MCP 13 工具 + 真实数据源实测）；⚠️ 附一起共享 venv 事故（已修复） |

---

## 一、任务来源

主人点名两个方向：

- **B. Scrapling MCP 试点** —— 治开奖数据回填「源站改版即失效」的老毛病，挂进 WorkBuddy
- **C. 一键流水线** —— 出图 → 算量 → 说明 全链贯通（对应《一键流水线.txt》）

两条线并进：C 是纯本地代码，先做完；B 依赖装包，丢后台并行。

---

## 二、C · 一键流水线（`scripts/pipeline.py`）

### 2.1 做了什么

把已有能力串成一条链，一句话跑完八步：

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

**实测**：`pipeline("12x8米三层住宅平面图带客厅厨房卧室")` → **2.58 秒**，产出 **12 个文件**。

### 2.2 四个设计决策（都不是拍脑袋，是踩坑换的）

| # | 决策 | 原因 |
|---|---|---|
| 1 | **识图前置**到算量/说明之前 | 施工说明的话术要按识图结果匹配，比 NL 解析的图别更贴近实际图形 |
| 2 | 除"出图"外**任何一步失败都不中断** | 失败写进该步状态、最后汇总列出，单点故障不毁掉整包 |
| 3 | 出图文件用**输入语义命名**，不再统一 `drawing.dxf` | 识图的图别推断里"文件名"权重最高(0.8)，固定名字等于自废武功 |
| 4 | **渲染默认关**（300dpi 约 5~7 秒），1~5 + 3D 默认开 | 3D 是纯 Python（几十毫秒），渲染是 matplotlib 大头 |

产物清单落 `manifest.json`（相对路径 + 字节数），便于整包归档交付。

### 2.3 入口

```python
from dxfkit import pipeline, pipeline_batch

r = pipeline("12x8米三层住宅平面图", "out/")            # 一句话全链
r = pipeline("6米框架梁配筋图", "out/", do_render=True) # 开渲染
rs = pipeline_batch(["12x8米住宅平面图", "配电系统图"], "batch/")
```

```bash
python scripts/pipeline.py "12x8米住宅平面图" -o out/ [--render] [--no-review] [--no-3d] [--no-sheet] [--paper A4]
python scripts/pipeline.py --batch texts.txt -o out_batch/ --no-review
```

### 2.4 验证（`examples/verify_pipeline_v115.py` · **55/55 PASS**）

| 组 | 内容 | 结果 |
|---|---|---|
| [1] 单条全链 | 8 步槽位齐全、四处产物、报告可回读 | PASS |
| [2] 批量 | 5 种图别全成功、专业有区分度 | PASS |
| [3] 配置变体 | 只出图 / 裁剪 BOM 格式 / 关 3D / 不加图框 | PASS |
| [4] 产物完整性 | manifest 逐项落地校验、关键产物存在 | PASS |
| [5] 主链集成 | dxfkit 导出 5 个新符号 | PASS |
| [6] 字体体检 + 渲染 | 各字号出字、未选点阵位图字体、PNG 落地 | PASS |

---

## 三、顺带挖出并修掉的 4 个真 bug

做 C 的过程中触发了一连串**不报错但结果错**的老问题。这些比流水线本身更值钱。

### 3.1 中文"静默丢字"（最严重 · 影响所有渲染）

`SimSun`（`simsun.ttc`）含**点阵位图**，matplotlib/Agg 在约 **5~6pt 字号带**把整行中文渲染成
**空白**（黑像素 = 0），ASCII 正常、且**不抛任何异常**。施工说明那类密排小字正好落在这个
字号带 → 中文凭空消失。

实测各字号黑像素（字符串"本工程图纸尺寸"）：

| 字体 | 3pt | 4pt | 5pt | 6pt | 7pt | 8pt | 10pt |
|---|---|---|---|---|---|---|---|
| **simsun.ttc** | 20 | 92 | **0** | **0** | 331 | 567 | 885 |
| msyh.ttc | 121 | 210 | 426 | 686 | 745 | 1088 | 1463 |
| simhei.ttf | 120 | 213 | 360 | 535 | 602 | 891 | 1434 |

**修复**：
- `_MPL_CJK_CANDIDATES` 把 SimSun 从**首位降到末位兜底**，优先 msyh → simhei → Deng → simkai → simfang
- 新增体检函数 `interfaces.check_cjk_font_sizes()`，把"静默丢字"变成**可断言检查**（已接入验证脚本第 6 组作回归防线）

### 3.2 文字尺寸失配（说明栏糊成一团）

`_to_raster` 的字号换算原用 `fig_h`（整图高度），但 `set_aspect('equal', adjustable='box')`
会把坐标轴盒子**缩小** → 真实"数据→英寸"比例小于 `fig_h/range` → 字号被整体放大（实测 **2.3 倍**），
密排行距被吃掉，看起来糊成一团。

**修复**：先 `fig.canvas.draw()` 完成布局，再量**实际坐标轴高度**（`ax.get_window_extent()`）算 `pts_per_unit`。

### 3.3 说明/规范落点（NL 自动追加）

| 原行为 | 后果 |
|---|---|
| 施工说明按 1:100 放大画在 `(23200, 28300)`，但 `width` 换行宽度**不参与缩放** | 字高 250mm 却按 175mm 换行 → **每行一个字**竖着糊成一列 |
| 执行规范默认 `(0,0)` | **直接压在图形上** |

**修复**：`natural_language_engine.generate()` 先用 `ezdxf.bbox.extents` 量图形包围盒，
换算成"图纸毫米"坐标把两段文字块放到**图形右侧空白区**；`scale=100` 交给方法内部
（同比例放大 x/y/字高，width 保持图纸毫米），规范清单接在说明下方。
**注意**：不要传 `scale=1.0`——`add_code_references` 字高是**硬编码** 5/3.5/2.8，只受 scale 缩放，
`scale=1.0` 会把字高缩成 5mm，审查立刻报 16 条「字高偏小」（我踩了，已修）。

修完审查从 `B(良好) 16 问题` 回到 **`A(优秀) 0 问题`**。

### 3.4 电气图例 `'str' object is not callable`

`templates_mep.electrical_legend()` 要的是 `(名称, 可调用对象, 说明)` 三元组，而 NL 引擎传的是
`{'sym': 'sym_lamp_ceiling'}` **字符串** → **任何电气类 NL 请求都直接报错**。
（该分支从未跑通；46/46 的 `verify_nl` 没覆盖到，是测试盲区。）

**修复**：新增 `normalize_legend_item()` 兼容三元组与字典两种写法 + `_SYMBOL_REGISTRY`
（符号名 → 绘制适配器）自动解析字符串符号名。

---

## 四、B · Scrapling MCP 试点（已完成）

### 4.1 摸底结论

| 项 | 结果 |
|---|---|
| 本机已有配置 | `~/.workbuddy/mcp.json` 里**已有一条 `scrapling`**，指向 `deepseek-vision/venv`，`disabled: true` |
| 旧版可用性 | 该 exe **不认 `--version`**（老版本），且**没有 `mcp` 子命令** → 旧配置是死的 |
| 新装版本 | **`scrapling 0.4.15` + `[ai]` 扩展**（独立 venv，43 个包，Python 3.13.14） |
| 起不来的根因 1 | `ModuleNotFoundError: No module named 'mcp'` —— base 包不含 MCP 依赖 |
| 起不来的根因 2 | `playwright` / `patchright` / `curl_cffi` 是**硬依赖**（连静态抓取都要 import） |
| 起不来的根因 3 | PyPI 官方源**极慢**（playwright 38MB 卡 4 分钟不下）→ 换**清华镜像**秒装 |

### 4.2 MCP 服务实测

stdio 握手成功，返回 **13 个工具**：

| 类别 | 工具 |
|---|---|
| 会话 | `open_session`、`open_request_session`、`close_session`、`list_sessions` |
| 静态请求 | `make_request`、`bulk_get`、`session_make_request` |
| 浏览器 | `fetch`、`bulk_fetch`、`stealthy_fetch`、`bulk_stealthy_fetch`、`session_fetch` |
| 截图 | `screenshot` |

已写入 `~/.workbuddy/mcp.json`（指向独立 venv，`disabled: false`）——
**需在连接器管理页右上角「自定义连接器」对 `scrapling` 点「信任」才会生效**。

### 4.3 真实数据源对照（`璇玑V2/xuanji/scripts/fetch_draws.py`）

数据源：`POST https://iframe.99kj99.app:3210/lsjl/kj` body `{"g":"am","s":N}`

| 路径 | 结果 |
|---|---|
| A. 现行 urllib | ✅ 200，65029 字符，2.27s |
| B. **Scrapling Fetcher**（`impersonate="chrome"`） | ✅ 200，2.23s，**带 TLS 指纹伪装** |

→ 抓取当天数据：期号 **253**、日期 2026-09-10、号码 `05,35,15,28,13,49,16`。

### 4.4 自适应解析能力实测（改版梯度）

| 档位 | 改版方式 | 普通 css | adaptive | 结果 |
|---|---|---|---|---|
| L0 | 原样 | ✅ | ✅ | ✅ 正确 |
| L1 | **加包装层**（前端组件化） | ✅ | ✅ | ✅ 正确 |
| L2 | **class 改名** `num→num-value` | ❌ 失效 | ✅ | ✅ 正确 |
| L3 | **标签换** `td→p` | ❌ 失效 | ✅ | ✅ 正确 |
| L4 | **整块重写**（激进） | ❌ | ❌ | ❌ 未命中 |

**结论：能自动救回「加层 / 改名 / 换标签」三类（L1~L3），整块重写仍需人工改选择器。**

### 4.5 两个必须记住的坑

1. **`adaptive` 必须在初始化时开启**：`Selector(html, adaptive=True)` /
   `Fetcher.get(url, adaptive=True)`。调用时传 `adaptive=True` 会被**静默忽略**
   （只打一条 WARNING），表现为"自适应完全没用"。
2. **自适应会静默匹配到错误元素**：测试中 L3 曾返回期号 `253` 而不是号码。
   自适应是"安全网"，不是"正确性保证"——**落库前必须做业务值校验**
   （例：号码必须能切成 7 个 01~49 的整数）。

### 4.6 对"源站改版即失效"的实际价值判断

- 用户的数据源是 **JSON API**，不是 HTML 页面 → 自适应选择器**用不上**；
  真正的风险是**加反爬（Cloudflare/TLS 指纹）**和**接口字段改名**。
- Scrapling 在这个场景的最大价值 = **TLS 指纹伪装 + 会话保持**（`impersonate="chrome"`），
  正好治"换 UA/加盾后 urllib 被拦"。
- 自适应解析是**为将来换 HTML 源预留**的能力。

### 4.7 补充安装（可选）

浏览器类工具（`fetch` / `stealthy_fetch` / `screenshot`）需先下载浏览器内核：

```bash
C:/Users/binliu8199/.workbuddy/binaries/python/envs/scrapling/Scripts/scrapling.exe install
```

静态类工具（`make_request` / `bulk_get`）**无需**此步，当前已可用。

---

## 五、⚠️ 事故与修复：共享 venv 被装包搞坏

**这是个真事故，必须记录。**

### 经过

在共享托管 venv（`binaries/python/envs/default`）里反复安装 Scrapling 依赖时，
pip 的依赖解析反复调整版本，配合 `--ignore-installed` 导致**大量包的文件被删除但
dist-info 元数据残留** → pip 认为"已安装"，永远不补。

**受害范围**（体检发现）：`ezdxf`（！）、`certifi`、`python-dateutil`、`cycler`、
`defusedxml`、`charset_normalizer`、`httpx`、`httpx2`、`python-dotenv`、`python-docx`、
`pycryptodome`、`huggingface_hub`、`protobuf`、`opencv-python-headless` 等。

### 修复

1. 写了**空壳包扫描器**（按 RECORD 逐文件核对存在率，<90% 判为残缺）
   → `outputs/scan_hollow_packages.py`
2. 用 `pip install --ignore-installed --no-deps -i 清华镜像 <包>` 逐个补文件
3. 复扫结果：**194 完整 / 0 空壳 / 0 残缺**，关键工具链全部恢复
4. 技能回归重跑：**46/46、21/21、60/60、37/37、55/55 全绿**（零损伤）

### 教训（写进流程）

- **重型/冲突依赖栈绝不装共享 venv** → 一律建独立 venv（本次已为 Scrapling 建好）
- 装包**优先用国内镜像**（官方源实测卡死）
- 装完**必须显式体检** `import` 关键包，不能只看 pip 的 "Successfully installed"

---

## 六、验证总账（全绿）

| 脚本 | 结果 |
|---|---|
| `verify_pipeline_v115.py`（新） | **55 / 55** |
| `verify_nl.py` | **46 / 46** |
| `verify_interfaces.py` | **21 / 21** |
| `verify_v114.py` | **60 / 60** |
| `verify_v115.py` | **37 / 37** |
| `verify_pipeline.py`（v1.12 端到端渲染） | **4 / 4**（glyph 校验 PASS，missing=0） |

合计 **223 项**，零 FAIL，零回归。

---

## 七、交付物

### 技能内

| 文件 | 说明 |
|---|---|
| `scripts/pipeline.py` | 一键流水线（新增） |
| `examples/verify_pipeline_v115.py` | 流水线验证（新增，55 项） |
| `examples/probe_mcp_stdio.py` | MCP server stdio 握手探测工具（新增，B 用） |
| `scripts/interfaces.py` | 字体优先级 + 字号换算 + `check_cjk_font_sizes()` |
| `scripts/natural_language_engine.py` | 文字块落点 |
| `scripts/templates_mep.py` | 图例项归一化 |
| `scripts/dxfkit.py` | 主链集成（追加 pipeline 导入块） |
| `SKILL.md` / `功能表.md` | 同步 v1.16.0 |

### B 试点（`WorkBuddy/2026-09-05-14-12-23/outputs/`）

| 文件 | 说明 |
|---|---|
| `scrapling_pilot.py` | 三路对照（urllib / Fetcher / 自适应）实测脚本 |
| `scrapling_drift_ladder.py` | 改版梯度测试（L0~L4，含正确性校验） |
| `scan_hollow_packages.py` | **空壳包扫描器**（venv 体检工具，建议长期保留） |

### 环境

- 新建独立 venv：`binaries/python/envs/scrapling`（scrapling 0.4.15 + `[ai]`，43 包）
- `~/.workbuddy/mcp.json`：`scrapling` 条目重指向独立 venv 并启用

### 桌面（可直接双击）

- `图纸工坊_v1.16.0_完成报告.md`
- `图纸工坊_v1.16.0_渲染样例.png`（平面图 + 施工说明 + 执行规范，验证字体修复）
- `图纸工坊_v1.16.0_流水线报告.txt`
- `图纸工坊_v1.16.0_3D体量样例.html`

---

## 八、诚实的边界

| 能做到 | 做不到 |
|---|---|
| 一句话 2.6 秒出 12 件套 | ❌ 施工说明**直接印在图上**（现在画在模型空间图形右侧；规范做法是放进图纸空间说明栏，待办） |
| 识图→说明自动联动匹配话术 | ❌ 识图对**第三方 DXF**（非本库产物）未验证 |
| 3D 体量 + 浏览器可转 | ❌ 门窗不开洞、非工程级 BIM |
| 字体静默丢字可自动体检 | ❌ 渲染仍是 matplotlib 光栅，非矢量出图 |

**待办**：① 说明栏移入图纸空间 Layout（`target=layout`，消除模型空间 34500mm 高的文字柱）
② 识图通用化（第三方 DXF）③ 标准图册（16G101 平法节点库）④ Scrapling MCP 实测收尾
