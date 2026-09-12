# -*- coding: utf-8 -*-
"""DXF 预处理层（纯标准库，无第三方依赖，两个 venv 都能跑）。

**为什么需要它**：aspose-cad 转出的 DXF 有 3 处 ezdxf 不能直接接受的问题，
全都与图纸内容无关，属于"转换器产物噪声"，必须在读取前清掉：

  ① OBJECTS 段畸形 —— 含 VISUALSTYLE 的 291 组码、XRECORD 缺 y 坐标。
     严格模式与 recover 模式都会在此报错。整段删除（内容不需要）。
  ② 表记录缺名字 —— 实测 `05 2F.dxf` 有一个无名字的 STYLE 记录和一个空
     BLOCK_RECORD，导致 ezdxf 在**加载阶段**抛
     DXFTypeError("name has to be a string")。删掉这类畸形记录。
  ③ 中文名用 `\\U+XXXX` 转义 —— 图层名/文字会写成 `IRC\\U+5929\\U+82B1`，
     ezdxf 不解码，关键词匹配全部失效 → 读取侧解码。

⚠️ 一个必须遵守的实现细节（踩过坑）：
   DXF 的行是 **code/value 成对** 的，而"值"本身完全可以是 `0`
   （实测有 `281`/`0`、`90`/`0`、`1071`/`0`）。
   所以判断"记录边界"绝不能写 `if line == "0"` —— 那会把值行误当记录头，
   把记录切错位，进而报 `Invalid group code "Continuous"`。
   **必须按 (code, value) 成对解析。**

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
    """删掉 TABLES 段里"缺名字"的表记录。

    在 (code,value) 序列上做，只在 `0 <NAMED_TABLES 之一>` 处切记录 ——
    因为只有 code==0 才是记录头，值行再怎么等于 "0" 也不会被误切。
    """
    span = _find_section(pairs, "TABLES")
    if span is None:
        return 0
    a, b = span
    seg = pairs[a:b + 1]
    # 记录头索引
    heads = [i for i in range(len(seg) - 1)
             if seg[i][0] == "0" and seg[i][1].strip() in NAMED_TABLES]
    if not heads:
        return 0
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
    return dropped


def prepare(src, dst):
    """预处理：删 OBJECTS 段 + 修畸形表记录。返回统计 dict。"""
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip("\r\n") for l in f]
    n0 = len(lines)
    pairs = _to_pairs(lines)
    obj = strip_section(pairs, "OBJECTS")
    bad = repair_table_records(pairs)
    lines = _to_lines(pairs)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {"src_lines": n0, "dst_lines": len(lines),
            "objects_removed": obj, "records_dropped": bad}


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
