# dxf-generator 完成报告 · v1.17.5

> 收口窗口：E5（16G101 接入规范库）+ E4（node_steel.py 改名）+ 说明栏「执行规范」可读下限回归修复 + 文档同步 + GitHub 备份
> 提交：`1490451` · 已推 `origin/main`（github.com/liubin8199-1/dxf-generator）

## 一、E5 · 16G101 接入规范引用库（`scripts/construction_codes.py`）

### 根因（比「缺一条规范」更深）
旧 `get_codes_by_drawing_type` 只匹配 `'all' in applicability or drawing_type in applicability`：
具体名图别（`node_beam_column` / `node_pile` / `node_steel_base` / `node_stair` / `node_foundation` …）
**命中不了语义标签**（`structural`/`beam`/`column`/`foundation`/`slab`），
导致节点图连 GB 50010 / GB 50204 / **16G101** 都漏引——不只是少一条平法图集，
而是整类强条规范被静默丢掉。

### 修复
- 新增 `PINGFA_CODES`（16G101-1 框架/剪力墙/梁/板 · 16G101-2 楼梯 · 16G101-3 基础/桩基），
  `priority=1` 强条，applicability 同时挂**语义标签 + 具体图别名**；并入 `ALL_CODES`。
- 规范库总量 **64 条×13 类 → 67 条×14 类**。
- 新增 `DRAWING_TYPE_ALIASES`：具体名图别 → 语义标签归一，匹配逻辑改为
  `drawing_type` 精确 / `'all'` / 别名 三者任一命中（向后兼容）。
- `add_code_references` 新增 `max_mandatory=12` 限量：强条过多时优先列前 12 条、
  超出标「…共 M 项」，避免撑爆 A3 说明栏。

### 验证：`examples/verify_e5.py` **21/21**
节点图（梁柱/楼梯/基础/桩基/钢柱脚）生成后「执行规范」自动含 16G101；
根因修复断言（node 图命中数 >3 且含 GB 50010）通过；`floor_plan` 等大图向后兼容（≥18 条）。

## 二、E4 · `node_steel.py` 重命名为 `node_pile.py`

- 该文件装的是**混凝土桩基**节点（函数 `pile_node` / `PileNodeParams`），
  原名 `node_steel` 与钢结构（`node_steel_v2.py` 的 `STEEL_NODES`）混名。
- `mv` 改名（非 git 跟踪，绕开 `git mv` 报 "not under version control"），
  同步 4 处引用：`templates_atlas/__init__.py` · `natural_language_engine.py` ·
  `examples/node_demo.py` · `examples/verify_nodes.py`。
- ⚠️ 钢结构三类节点仍在 `node_steel_v2.py`，**未受影响**（`verify_steel_nodes` 24/24 仍绿）。

## 三、说明栏「执行规范」可读下限回归修复（关键）

### 现象
E5 别名修复后 `floor_plan` 匹配规范从 3 条涨到 20+ 条；
`natural_language_engine._add_notes_to_sheet` 把规范块预留高度封顶 `nh*0.42`（≈90mm，真实 ~105mm），
逼 `add_code_references` 的 `auto_fit` 把 `base_height` 从 5.0 压到 ~3.95 →
强条字高 2.2mm、省略号行 1.97mm（**< 2.5mm 可读下限**），`verify_layout_notes` 卡在 69/70。

### 修复（守住「宁可截断/分页也不压字到读不出」）
- `natural_language_engine.py`：预留高度封顶 `0.42 → 0.60`，让 `code_h` 贴近真实块高、不再逼压缩。
- `construction_codes.py` `add_code_references`：`min_base_height` `3.0 → 5.0`
  （规范清单最小字高 = base×0.5，5.0×0.5=2.5mm 恰为 GB/T 50001 可读下限）。

### 验证：`examples/verify_layout_notes.py` **70/70**（原 69/70）

## 四、文档同步（F）
- `SKILL.md`：描述计数 64×13→67×14、版本标记 →v1.17.5；末尾新增「v1.17.5 收口」章节。
- `功能表.md`：补 §20 E5/E4/回归修复 + 最终总验证（19 套件）。

## 五、最终总验证（v1.17.5）
`examples/verify_all.py` → **19 套件全绿 · 469 项可计数断言 · 0 失败**（约 2 分 50 秒）：
续页命名 7 · e5 — · 字体 — · 全量扩展 — · 接口层 21 · 布局+说明栏 70 · 自然语言 46 ·
梁柱节点 12 · 节点路由 23 · ③层节点 29 · 说明全套 — · 平法 53 · 端到端渲染 4 ·
NL 流水线 57 · 钢筋计算 26 · 钢结构节点 24 · 识图/算量/说明 60 · 3D 体量 37 ·
+ 高级模板+审图（无计数，按判定语通过）。

## 六、GitHub 备份（G）
`git push origin main` → `5d4981c..1490451 main -> main`（fast-forward，已上库）。

---
### ⚠️ 本次环境插曲（已排雷，记录备查）
本会话 Bash 环境 `shell-runtime-bash-env.sh` 损坏（`dirname`/`cd` 缺失、`rm` 被 `safe-bin` 拦截缺失脚本），
导致 `git commit` 后 `refs/heads/main` 被写成**全零 SHA（坏引用）**，`show-ref` 为空、所有 git 命令报
"branch appears to be broken"。恢复路径：从 `.git/logs/HEAD` 找到悬空提交
`1490451`（父 `5d4981c`）→ 用绝对路径托管 Python 直接覆写 `.git/refs/heads/main` 为正确 SHA
→ git 恢复正常 → 推送成功。下次遇"reference broken / 全零 SHA"，优先查 reflog + 直写 ref 文件，
别在坏 shim 下反复 `git commit`（会越攒越多悬空提交）。
