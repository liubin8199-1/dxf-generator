# -*- coding: utf-8 -*-
"""DXF 预处理层（纯标准库，无第三方依赖，两个 venv 都能跑）。

**为什么需要它**：aspose-cad 转出的 DXF 有 4 处 ezdxf 不能直接接受的问题，
全都与图纸内容无关，属于"转换器产物噪声"，必须在读取前清掉：

  ① OBJECTS 段畸形 —— 含 VISUALSTYLE 的 291 组码、XRECORD 缺 y 坐标。
     严格模式与 recover 模式都会在此报错。整段删除（内容不需要）。
  ② 表记录缺名字 —— 实测 `05 2F.dxf` 有一个无名字的 STYLE 记录和一个空
     BLOCK_RECORD，导致 ezdxf 在**加载阶段**抛
     DXFTypeError("name has to be a string")。删掉这类畸形记录。
  ③ 中文名用 `\\U+XXXX` 转义 —— 图层名/文字会写成 `IRC\\U+5929\\U+82B1`，
     ezdxf 不解码，关键词匹配全部失效 → 读取侧解码。
  ④ ★ `BLOCKS` 段的子实体序列**漏写终止标记 SEQEND**（2026-09-12 定位）。
     aspose 把 `POLYLINE + VERTEX*` 和 `INSERT + ATTRIB*` 写进块定义时，
     结尾的 `0 SEQEND` 只写进了 ENTITIES 段、BLOCKS 段全漏 → ezdxf 抛
     `DXFStructureError("Expected DXF entity POLYLINE or SEQEND")`，
     **严格与 recover 两种模式都读不了**。
     实测别墅图纸 8 张里有 3 张（37.5%）因此完全打不开；
     修复后 7/8 可读（剩 1 张是 3D 网格模型，另有更深的问题 —— 见 ⑤）。
     → 由 `repair_missing_seqend()` 机械补回。

  ⑤ ★ `INSERT` 声明了 `66=1`（attribs_follow，"后面有属性"）却**一个 ATTRIB
     都没写、也没有 SEQEND**（2026-09-12 定位，`三维模型.dwg` 独有）。
     ezdxf 加载时按 `attribs_follow` 进入子实体循环，期望 ATTRIB/SEQEND，
     却撞见下一个实体 → 抛 `DXFStructureError("Expected DXF entity INSERT or
     SEQEND")`（`ezdxf/entities/subentity.py:184`，消息里的类型是**实际撞到的**实体）。
     ⚠️ 这类**不能**靠"看到 ATTRIB 才补"来修 —— 它一个 ATTRIB 都没有。
     判据必须是 **`66=1` 这个声明本身**。实测 24 个别墅文件里只有这 1 个有此缺陷
     （3 处，全在 ENTITIES 段），这就是它单独读不了的原因。

  ⑥ ★ XDATA 二进制块写成 **带横线的十六进制**（`28-00-00-00-20-…`）。
     这是 AutoCAD `.pat`/打印格式，不是 DXF 格式；DXF 的 1004/310 要求**纯十六进制**。
     ezdxf 直接抛 `DXFStructureError("Invalid binary data near line: N")`，
     **严格与 recover 都读不了**。实测 `E立面.dwg` 有 85 处，全部挂在
     APPID `CONTENTBLOCKICON` 下 —— 是**块缩略图图标**（非图纸内容），
     既读不了又占体积，**整块删除**；其余残留的横线块做**去横线归一化**。

⚠️ 一个必须遵守的实现细节（踩过坑）：
   DXF 的行是 **code/value 成对** 的，而"值"本身完全可以是 `0`
   （实测有 `281`/`0`、`90`/`0`、`1071`/`0`）。
   所以判断"记录边界"绝不能写 `if line == "0"` —— 那会把值行误当记录头，
   把记录切错位，进而报 `Invalid group code "Continuous"`。
   **必须按 (code, value) 成对解析。**

⚠️ 第二个必须遵守的实现细节（修 ④ 时踩的坑，代价很大）：
   **遍历实体自身组码时，必须"先写出、再前进"**。写成"只前进不写出"的
   `skip_tag_block` 会把实体的句柄/坐标/图层全吞掉——实测 `平立剖面图1`
   因此丢了 **119,188 行（35% 的内容）**，而且 ezdxf 仍能读出文件，
   **不报错**（只是内容静默变少）。所以 `prepare()` 必须自带**行数守恒断言**：
   `输出行数 - 输入行数 == 2 × 补的 SEQEND 个数`。

用法：
    from dxf_prepare import prepare, decode_unicode_escapes, load_dxf
    stats = prepare("raw.dxf", "clean.dxf")
"""
import re

RE_UESC = re.compile(r"\\U\+([0-9A-Fa-f]{4})")

NAMED_TABLES = ("LAYER", "LTYPE", "STYLE", "BLOCK_RECORD",
                "VPORT", "APPID", "DIMSTYLE", "UCS")

# 只做缩略图/图标、不含图纸内容的 XDATA APPID —— 连同其 1004 二进制块一起删。
# CONTENTBLOCKICON 是 AutoCAD 给块存的预览图，实测 `E立面.dwg` 里 85 处
# 带横线二进制（见 docstring ⑥）全挂在它下面。
ICON_XDATA_APPIDS = ("CONTENTBLOCKICON",)

# 文档定义为"二进制块"的组码：310~319（实体二进制块）、1004（XDATA 二进制块）。
# 1005 是句柄字符串、1000 是普通串，都不在此列，别误伤。
BINARY_GROUP_CODES = frozenset(["310", "311", "312", "313", "314",
                                "315", "316", "317", "318", "319", "1004"])

# `28-00-00-00-20-...` 这种"横线分隔十六进制"（每段恰好 2 位）
RE_DASH_HEX = re.compile(r"^[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2})+$")

# XDATA 的组码范围（1000~1071），用于界定"一个 APPID 的 xdata 到哪儿结束"
def _is_xdata_code(code):
    return code.isdigit() and 1000 <= int(code) <= 1071


def decode_unicode_escapes(s):
    """把 DXF 的 `\\U+5929` 转义解成真字符。非字符串返回空串。"""
    if not isinstance(s, str):
        return ""
    return RE_UESC.sub(lambda m: chr(int(m.group(1), 16)), s)


# ---------------- code/value 成对解析 ----------------
def _to_pairs(lines):
    """把行列表转为 [(code, value)]。行数为奇数时丢掉最后一行。"""
    pairs = []
    for i in range(0, len(lines) - 1, 2):
        pairs.append((lines[i].strip(), lines[i + 1]))
    return pairs


def _to_lines(pairs):
    out = []
    for c, v in pairs:
        out.append(c)
        out.append(v)
    return out


def _find_section(pairs, name):
    """返回 (SECTION 的 pair 索引, ENDSEC 的 pair 索引)，找不到 None。"""
    n = len(pairs)
    for i in range(n - 1):
        if pairs[i][0] == "0" and pairs[i][1].strip() == "SECTION":
            for j in range(i + 1, min(i + 4, n)):
                if pairs[j][0] == "2":
                    if pairs[j][1].strip() == name:
                        for k in range(j + 1, n):
                            if pairs[k][0] == "0" and pairs[k][1].strip() == "ENDSEC":
                                return (i, k)
                    break
    return None


def strip_section(pairs, name):
    """整段删除。返回删掉的 pair 数。"""
    span = _find_section(pairs, name)
    if span is None:
        return 0
    a, b = span
    del pairs[a:b + 1]
    return b + 1 - a


def repair_table_records(pairs):
    """删掉 TABLES 段里"缺名字"的表记录。返回删掉的记录数（兼容旧调用）。"""
    dropped, _ = _repair_table_records(pairs)
    return dropped


def _repair_table_records(pairs):
    """删掉 TABLES 段里"缺名字"的表记录。

    在 (code,value) 序列上做，只在 `0 <NAMED_TABLES 之一>` 处切记录 ——
    因为只有 code==0 才是记录头，值行再怎么等于 "0" 也不会被误切。

    返回 (删掉的记录数, 删掉的 pair 数)。
    """
    span = _find_section(pairs, "TABLES")
    if span is None:
        return 0, 0
    a, b = span
    seg = pairs[a:b + 1]
    # 记录头索引
    heads = [i for i in range(len(seg) - 1)
             if seg[i][0] == "0" and seg[i][1].strip() in NAMED_TABLES]
    if not heads:
        return 0, 0
    out = []
    dropped = 0
    prev = 0
    for idx, h in enumerate(heads):
        end = heads[idx + 1] if idx + 1 < len(heads) else len(seg)
        out.extend(seg[prev:h])          # 记录之前的非记录内容原样保留
        rec = seg[h:end]
        has_name = any(rec[p][0] == "2" and rec[p][1].strip()
                       for p in range(1, len(rec)))
        if has_name:
            out.extend(rec)
        else:
            dropped += 1
        prev = end
    out.extend(seg[prev:])
    pairs[a:b + 1] = out
    return dropped, len(seg) - len(out)


def strip_icon_xdata(pairs, appids=ICON_XDATA_APPIDS):
    """删掉指定 APPID 的整块 XDATA（内含 ezdxf 读不了的带横线二进制块）。

    一个 XDATA 块的边界：`1001 <APPID>` 起，到下一个 `0`（下个实体）或
    下一个 `1001`（另一个 APPID）为止，中间的组码都在 1000~1071。

    返回 (删掉的块数, 删掉的组数)。
    """
    out = []
    i = 0
    n = len(pairs)
    blocks = 0
    while i < n:
        c, v = pairs[i]
        if c == "1001" and v.strip() in appids:
            i += 1
            while i < n and _is_xdata_code(pairs[i][0]):
                i += 1
            blocks += 1
            continue
        out.append(pairs[i])
        i += 1
    pairs[:] = out
    return blocks, n - len(out)


def normalize_binary_chunks(pairs):
    """把"横线分隔十六进制"的二进制块归一成 DXF 要求的纯十六进制。

    只动 `310~319` / `1004` 且**形如** `xx-xx-xx` 的值；原地替换，
    **不增删组**（因此不影响守恒账）。返回修正的组数。
    """
    fixed = 0
    for idx, (c, v) in enumerate(pairs):
        if c in BINARY_GROUP_CODES:
            s = v.strip()
            if RE_DASH_HEX.match(s):
                pairs[idx] = (c, s.replace("-", ""))
                fixed += 1
    return fixed


def repair_missing_seqend(pairs):
    """补回 `BLOCKS` 段子实体序列漏写的终止标记 SEQEND（aspose 的 bug）。

    需处理两类序列（只在这两类"确实需要收尾"时才补，不多补）：
      · `POLYLINE` + `VERTEX`*  → 结束于 `SEQEND`
      · `INSERT`  + `ATTRIB`*  → 结束于 `SEQEND`；**或** `INSERT` 带 `66=1`
        （attribs_follow）声明即使没有 ATTRIB 也必须有 `SEQEND`（见 docstring ⑤）

    ⚠️ 实现要点：跳过实体自身组码时必须 **先 append 再前进**（见 `take`）。
       上个版本用"只前进不写出"的写法，把实体自身组码（句柄/坐标/图层）全吞了，
       `平立剖面图1` 直接丢 119,188 行（35%），且 ezdxf 照常能读、**不报错**。

    返回 (新 pairs, 补 POLYLINE 处数, 补 INSERT 处数, 其中因 66=1 声明而补的处数)。
    """
    out = []
    i = 0
    n = len(pairs)
    add_poly = add_ins = add_ins_declared = 0

    def take(i):
        """把当前实体的自身组码全部**写出**并前进到下一个记录头。"""
        while i < n and pairs[i][0] != "0":
            out.append(pairs[i])
            i += 1
        return i

    while i < n:
        c, v = pairs[i]
        head = v.strip() if c == "0" else None

        if head == "POLYLINE":
            out.append(pairs[i])
            i = take(i + 1)
            while i < n and pairs[i][0] == "0" and pairs[i][1].strip() == "VERTEX":
                out.append(pairs[i])
                i = take(i + 1)
            if i < n and pairs[i][0] == "0" and pairs[i][1].strip() == "SEQEND":
                out.append(pairs[i])
                i = take(i + 1)
            else:
                out.append(("0", "SEQEND"))
                add_poly += 1
            continue

        if head == "INSERT":
            start = i
            out.append(pairs[i])
            i = take(i + 1)
            # ★ 判据必须是 `66=1` 这个【声明】本身，不能只看"有没有 ATTRIB"——
            #   声明了 66=1 却一个 ATTRIB 都没写的 INSERT，同样需要 SEQEND 收尾，
            #   但它没有 ATTRIB 可供触发，只看 n_att 会整类漏掉（见 docstring ⑤）。
            declared_attribs = any(
                pairs[k][0] == "66" and pairs[k][1].strip().split(".")[0] == "1"
                for k in range(start + 1, i))
            n_att = 0
            while i < n and pairs[i][0] == "0" and pairs[i][1].strip() == "ATTRIB":
                out.append(pairs[i])
                i = take(i + 1)
                n_att += 1
            if n_att or declared_attribs:   # 带属性 / 声明带属性 → 都要 SEQEND
                if i < n and pairs[i][0] == "0" and pairs[i][1].strip() == "SEQEND":
                    out.append(pairs[i])
                    i = take(i + 1)
                else:
                    out.append(("0", "SEQEND"))
                    add_ins += 1
                    if not n_att:
                        add_ins_declared += 1
            continue

        out.append(pairs[i])
        i += 1
    return out, add_poly, add_ins, add_ins_declared


def prepare(src, dst):
    """预处理：删 OBJECTS 段 + 修畸形表记录 + 删图标 XDATA + 归一二进制块 + 补漏写的 SEQEND。

    自带**组数守恒断言**（按 (code,value) 组记账，精确到组）：
        输出组数 == 输入组数 - 删的 OBJECTS 组 - 删的畸形表记录组
                              - 删的图标 XDATA 组 + 补的 SEQEND 组
    （`normalize_binary_chunks` 只改值不加删组，故不进账。）
    不成立说明本函数吃/造了数据（历史上真发生过，见模块 docstring 的代价说明），
    此时抛 AssertionError 而不是静默产出坏文件。
    """
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip("\r\n") for l in f]
    n0 = len(lines)
    pairs = _to_pairs(lines)
    in_pairs = len(pairs)

    obj = strip_section(pairs, "OBJECTS")               # 返回删掉的组数
    bad, bad_pairs = _repair_table_records(pairs)
    icon_blocks, icon_pairs = strip_icon_xdata(pairs)   # 缩略图 XDATA（含非法二进制）
    binary_fixed = normalize_binary_chunks(pairs)       # 横线十六进制 → 纯十六进制
    pairs, add_poly, add_ins, add_ins_declared = repair_missing_seqend(pairs)
    out_pairs = len(pairs)
    seqend_added = add_poly + add_ins

    expect = in_pairs - obj - bad_pairs - icon_pairs + seqend_added
    if out_pairs != expect:
        raise AssertionError(
            "dxf_prepare 组数不守恒：输入 %d 组 → 输出 %d 组（差 %+d），"
            "但按账应为 %d 组（-OBJECTS %d -表记录 %d -图标XDATA %d +SEQEND %d）。"
            "修复逻辑吃/造了数据，拒绝写出。"
            % (in_pairs, out_pairs, out_pairs - in_pairs, expect,
               obj, bad_pairs, icon_pairs, seqend_added))

    out_lines = _to_lines(pairs)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    return {"src_lines": n0, "dst_lines": len(out_lines),
            "objects_removed": obj, "records_dropped": bad,
            "icon_xdata_blocks": icon_blocks, "icon_xdata_pairs": icon_pairs,
            "binary_chunks_fixed": binary_fixed,
            "seqend_polyline": add_poly, "seqend_insert": add_ins,
            "seqend_insert_declared": add_ins_declared,
            "seqend_added": seqend_added,
            "pairs_in": in_pairs, "pairs_out": out_pairs,
            "pairs_check": expect}


# ---------------- 容错加载（推荐入口） ----------------
def load_dxf(path, audit=False):
    """容错加载 DXF：严格 → recover。

    返回 ezdxf Drawing；audit=True 时返回 (doc, auditor)。
    """
    import ezdxf
    from ezdxf import recover
    try:
        doc = ezdxf.readfile(path)
        return (doc, None) if audit else doc
    except Exception:
        doc, aud = recover.readfile(path)
        return (doc, aud) if audit else doc


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(prepare(sys.argv[1], sys.argv[2]), ensure_ascii=False))
