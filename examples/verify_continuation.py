# -*- coding: utf-8 -*-
"""verify_continuation — 续页图幅命名模板化验证（v1.17.3）

覆盖：
  · 默认模板 {base}_notes_{n} → 'GB_A3_notes_2'
  · 向后兼容模板 GB_{paper}_说明{n} → 'GB_A3_说明2'
  · 变量 {name} 透传
  · BorderStandard.note_sheet_name 类方法等价
  · natural_language_engine 调用点已替换（可正常 import，无残留硬编码 GB_%s_说明%d）
用法：python verify_continuation.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from gb_standards import (
    NOTE_SHEET_NAME_TEMPLATE, get_note_sheet_name, BorderStandard)

PASS = 0
FAIL = 0
def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % msg)
    else:
        FAIL += 1
        print("  [FAIL] %s" % msg)


def main():
    print("=" * 60)
    print("verify_continuation  续页命名模板化")
    print("=" * 60)

    # 1. 默认模板
    s = get_note_sheet_name("GB_A3", "A3", 2)
    check(s == "GB_A3_notes_2", "默认模板 → '%s'" % s)

    # 2. 向后兼容模板
    s = get_note_sheet_name("GB_A3", "A3", 2, template="GB_{paper}_说明{n}")
    check(s == "GB_A3_说明2", "旧模板 GB_{paper}_说明{n} → '%s'" % s)

    # 3. name 变量透传（默认模板不含 name，应忽略）
    s = get_note_sheet_name("GB_A3", "A3", 2, title="施工说明")
    check(s == "GB_A3_notes_2", "含 name 不影响默认模板 → '%s'" % s)

    # 4. 自定义模板可用 name
    s = get_note_sheet_name("GB_A3", "A3", 2, title="说明续",
                            template="{base}_notes_{n}_{name}")
    check(s == "GB_A3_notes_2_说明续", "自定义模板用 name → '%s'" % s)

    # 5. 类方法等价
    s1 = BorderStandard.note_sheet_name("GB_A3", "A3", 3)
    s2 = get_note_sheet_name("GB_A3", "A3", 3)
    check(s1 == s2 == "GB_A3_notes_3", "类方法 == 函数 → '%s'" % s1)

    # 6. NL 引擎调用点已替换（import 正常 + 无残留硬编码）
    import natural_language_engine as nl
    src = open(nl.__file__, "r", encoding="utf-8", errors="ignore").read()
    check("name='GB_%s_说明%d'" not in src,
          "natural_language_engine 无残留硬编码 GB_%s_说明%d")
    check("note_sheet_name(" in src, "natural_language_engine 调用点已改用 note_sheet_name")

    print("\n" + "=" * 60)
    print("verify_continuation  通过 %d / 失败 %d" % (PASS, FAIL))
    print("=" * 60)
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
