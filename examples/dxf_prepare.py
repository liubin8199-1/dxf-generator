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
     修复后 7/8 可读（剩 1 张是 3D 网格模型，另有更深的问题）。
     → 由 `repair_missing_seqend()` 机械补回。

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


def repair_missing_seqend(pairs):
    """补回 `BLOCKS` 段子实体序列漏写的终止标记 SEQEND（aspose 的 bug）。

    需处理两类序列（只在这两类"确实有子实体"时才补，不多补）：
      · `POLYLINE` + `VERTEX`*  → 结束于 `SEQEND`
      · `INSERT`   + `ATTRIB`*  → 结束于 `SEQEND`（无属性的 INSERT 不需要 SEQEND）

    ⚠️ 实现要点：跳过实体自身组码时必须 **先 append 再前进**（见 `take`）。
       上个版本用"只前进不写出"的写法，把实体自身组码（句柄/坐标/图层）全吞了，
       `平立剖面图1` 直接丢 119,188 行（35%），且 ezdxf 照常能读、**不报错**。

    返回 (新 pairs, 补 POLYLINE 处数, 补 INSERT 处数)。
    """
    out = []
    i = 0
    n = len(pairs)
    add_poly = add_ins = 0

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
            out.append(pairs[i])
            i = take(i + 1)
            n_att = 0
            while i < n and pairs[i][0] == "0" and pairs[i][1].strip() == "ATTRIB":
                out.append(pairs[i])
                i = take(i + 1)
                n_att += 1
            if n_att:                      # 只有带属性的 INSERT 才需要 SEQEND
                if i < n and pairs[i][0] == "0" and pairs[i][1].strip() == "SEQEND":
                    out.append(pairs[i])
                    i = take(i + 1)
                else:
                    out.append(("0", "SEQEND"))
                    add_ins += 1
            continue

        out.append(pairs[i])
        i += 1
    return out, add_poly, add_ins


def prepare(src, dst):
    """预处理：删 OBJECTS 段 + 修畸形表记录 + 补漏写的 SEQEND。

    自带**组数守恒断言**（按 (code,value) 组记账，精确到组）：
        输出组数 == 输入组数 - 删的 OBJECTS 组 - 删的畸形表记录组 + 补的 SEQEND 组
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
    pairs, add_poly, add_ins = repair_missing_seqend(pairs)
    out_pairs = len(pairs)
    seqend_added = add_poly + add_ins

    expect = in_pairs - obj - bad_pairs + seqend_added
    if out_pairs != expect:
        raise AssertionError(
            "dxf_prepare 组数不守恒：输入 %d 组 → 输出 %d 组（差 %+d），"
            "但按账应为 %d 组（-OBJECTS %d -表记录 %d +SEQEND %d）。"
            "修复逻辑吃/造了数据，拒绝写出。"
            % (in_pairs, out_pairs, out_pairs - in_pairs, expect,
               obj, bad_pairs, seqend_added))

    out_lines = _to_lines(pairs)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    return {"src_lines": n0, "dst_lines": len(out_lines),
            "objects_removed": obj, "records_dropped": bad,
            "seqend_polyline": add_poly, "seqend_insert": add_ins,
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
