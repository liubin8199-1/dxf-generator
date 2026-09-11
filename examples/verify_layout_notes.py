# -*- coding: utf-8 -*-
"""v1.17.0 验证：施工说明移入图纸空间说明栏 + 视口修复 + 成品图幅渲染。

覆盖 8 组：
  [1] 说明栏几何（A3/A4/A2）：在图框内、避开视口与标题栏
  [2] 视口换算：view_height / get_scale / modelspace_limits 三者自洽
  [3] 说明落点：进图纸空间、模型空间不再有文字柱
  [4] 分页：超出说明栏自动生成「说明续页」图幅，字高不退化
  [5] 成品图幅渲染：space='paper' 出图、layout 选择器
  [6] 向后兼容：add_sheet=False / notes_in_layout=False 仍走模型空间
  [7] auto_fit：max_height 生效且不跌破 min_text_height
  [8] 主链集成：pipeline 报告与 manifest 带图幅/页数信息

用法：python examples/verify_layout_notes.py
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

OUT = os.path.join(HERE, "out_verify_v117")
PASS = 0
FAIL = 0
FAILED = []


def check(cond, label, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % label)
    else:
        FAIL += 1
        FAILED.append(label)
        print("  [FAIL] %s %s" % (label, extra))


def section(title):
    print("\n" + "-" * 74)
    print(title)
    print("-" * 74)


def main():
    global PASS, FAIL
    # ⚠️ 不要用 shutil.rmtree 清目录：本脚本会产出 50+ 个文件，
    # 批量删除会触发沙箱的 **批量删除安全闸门**（[SAFE_DELETE_BULK_CONFIRM_REQUIRED]）
    # 导致整个验证跑不起来。同名文件原地覆盖即可，残留文件无害。
    os.makedirs(OUT, exist_ok=True)

    import ezdxf
    from dxfkit import NLAwareDxfBuilder
    from gb_standards import BorderStandard
    from interfaces import DXFToImage
    from pipeline import PipelineConfig, pipeline

    # ==========================================================
    # [1] 说明栏几何
    # ==========================================================
    section("[1] 说明栏几何")

    for paper in ("A3", "A4", "A2", "A1"):
        try:
            nx, ny, nw, nh = BorderStandard.paper_notes_rect(paper)
            w, h = BorderStandard.SIZES[paper]
            m = BorderStandard.MARGINS[paper]
            tb = BorderStandard.TITLE_BLOCK
            vp_w, vp_h = BorderStandard.viewport_size(paper)
            inner_x0, inner_y0 = m["left"], m["bottom"]
            inner_x1, inner_y1 = w - m["right"], h - m["top"]
            # 在内容框内
            inside = (nx >= inner_x0 - 1e-6 and ny >= inner_y0 - 1e-6 and
                      nx + nw <= inner_x1 + 1e-6 and
                      ny + nh <= inner_y1 + 1e-6)
            check(inside, "%s 说明栏落在内框内 (%.0f,%.0f,%.0f,%.0f)"
                  % (paper, nx, ny, nw, nh))
            # 不与视口重叠（视口在左侧竖条，说明栏在右侧）
            vp_x1 = inner_x0 + vp_w
            check(nx >= vp_x1, "%s 说明栏不压视口（视口右边界 %.0f ≤ 栏左 %.0f）"
                  % (paper, vp_x1, nx))
            # 不与标题栏重叠（标题栏在右下角）
            tb_x0 = inner_x1 - tb["width"]
            tb_y1 = inner_y0 + tb["height"]
            overlap = not (nx >= tb_x0 + tb["width"] or
                           nx + nw <= tb_x0 or
                           ny >= tb_y1 or ny + nh <= inner_y0)
            check(not overlap, "%s 说明栏不与标题栏重叠" % paper)
            # 有实际可用面积
            check(nw > 60 and nh > 80, "%s 说明栏可用面积 %.0f×%.0fmm"
                  % (paper, nw, nh))
        except Exception as e:
            check(False, "%s 说明栏几何" % paper, repr(e))

    # ==========================================================
    # [2] 视口换算（v1.17.0 修的核心 bug）
    # ==========================================================
    section("[2] 视口换算")

    b = NLAwareDxfBuilder(style="gb_architectural")
    dxf1 = os.path.join(OUT, "viewport.dxf")
    gen = b.generate_from_text("12x8米三层住宅平面图带客厅厨房卧室", dxf1,
                               add_sheet=True, paper_size="A3")
    check(gen.get("ok"), "NL 生成成功")
    doc = ezdxf.readfile(dxf1)
    lay = doc.layouts.get("GB_A3")
    check(lay is not None, "存在 GB_A3 图纸空间布局")
    vps = [e for e in lay if e.dxftype() == "VIEWPORT"]
    check(len(vps) == 1, "GB_A3 有且仅有 1 个视口")
    vp = vps[0]
    vp_w, vp_h = BorderStandard.viewport_size("A3")
    _scale = gen["result"].get("view_scale", "")
    # view_height 应为 视口高 / 比例
    exp_ratio = 1.0 / float(_scale.split(":")[1]) if ":" in _scale else 1 / 100
    check(abs(vp.dxf.view_height - vp_h / exp_ratio) < 1e-6,
          "view_height = 纸高/比例（%.1f，比例 %s）"
          % (vp.dxf.view_height, _scale))
    # get_scale 回读应与声明比例一致
    got = vp.get_scale()
    check(abs(got - exp_ratio) < 1e-9,
          "get_scale() 回读 = %s（期望 %.4f）"
          % (BorderStandard.scale_label(got), exp_ratio))
    # 旧 bug 的特征：get_scale 会飙到 27200
    check(got < 1.0, "get_scale() 已不是旧 bug 的 27200（实测 %.4f）" % got)
    # modelspace_limits 必须能覆盖整个模型（否则看到的是一刀切片）
    try:
        lim = vp.get_modelspace_limits()
        mw = gen["result"].get("model_extents") or [0, 0]
        span_x = lim[2] - lim[0]
        span_y = lim[3] - lim[1]
        check(span_x >= mw[0] and span_y >= mw[1],
              "视口可见范围 %.0f×%.0f 覆盖模型 %.0f×%.0f"
              % (span_x, span_y, mw[0], mw[1]))
    except Exception as e:
        check(False, "get_modelspace_limits 可用", repr(e))

    # fit_scale 单调性：模型越大比例越小（分母越大）
    r_small = BorderStandard.fit_scale(3000, 2000, "A3")
    r_big = BorderStandard.fit_scale(60000, 40000, "A3")
    check(r_small > r_big, "fit_scale 随模型增大而缩小（%s > %s）"
          % (BorderStandard.scale_label(r_small),
             BorderStandard.scale_label(r_big)))
    check(BorderStandard.scale_label(0.01) == "1:100", "scale_label(0.01)='1:100'")
    check(BorderStandard.scale_label(1 / 50) == "1:50", "scale_label(1/50)='1:50'")

    # ==========================================================
    # [3] 说明落点
    # ==========================================================
    section("[3] 说明落点")

    check(gen["result"].get("notes_target") == "layout",
          "说明落点 = layout（图纸空间）")
    msp = doc.modelspace()
    from ezdxf import bbox as _bbox
    ext = _bbox.extents(msp)
    msp_h = ext.extmax.y - ext.extmin.y
    # 旧行为会把说明按 scale=100 放大 → 模型空间高 34500mm
    check(msp_h < 25000,
          "模型空间包围盒高度 %.0fmm（旧行为 34500+，说明已搬走）" % msp_h)
    nx, ny, nw, nh = BorderStandard.paper_notes_rect("A3")
    in_col = 0
    msp_txt = 0
    for e in lay:
        if e.dxftype() == "TEXT":
            p = e.dxf.insert
            if nx - 3 <= p.x <= nx + nw + 3 and ny - 3 <= p.y <= ny + nh + 3:
                in_col += 1
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            msp_txt += 1
    check(in_col > 8, "说明栏内有 %d 条文字" % in_col)
    check(msp_txt > 0, "模型空间仍保留图纸本体标注 %d 条" % msp_txt)
    # 说明栏内不应出现「施工说明」以外的内容错位（抽查首行是全角标题）
    titles = [e.dxf.text for e in lay
              if e.dxftype() == "TEXT" and "施 工 说 明" in str(e.dxf.text)]
    check(len(titles) >= 1, "说明栏含「施 工 说 明」标题")

    # ==========================================================
    # [4] 分页
    # ==========================================================
    section("[4] 分页（说明续页）")

    pages = gen["result"].get("notes_pages", 0)
    lays = gen["result"].get("notes_layouts") or []
    check(pages >= 1, "报告页数 %d" % pages)
    check(len(lays) == pages, "布局数与页数一致（%d）" % len(lays))
    # 所有说明文字的字高必须 ≥ 2.5mm（不许靠缩字硬塞）
    bad = []
    for lname in lays:
        lg = doc.layouts.get(lname)
        if lg is None:
            bad.append((lname, "缺失"))
            continue
        for e in lg:
            if e.dxftype() == "TEXT":
                p = e.dxf.insert
                if nx - 3 <= p.x <= nx + nw + 3 and ny - 3 <= p.y <= ny + nh + 3:
                    hh = float(e.dxf.height or 0)
                    # 说明正文/标题；规范的标题按 base_height*1.0 也可能 ≥2.5
                    if hh < 2.49 and not str(e.dxf.text).startswith("注:"):
                        bad.append((lname, round(hh, 2), str(e.dxf.text)[:14]))
    check(not bad, "说明栏字高全部 ≥2.5mm（可读下限）", str(bad[:3]))
    if pages > 1:
        cont = doc.layouts.get(lays[1])
        check(cont is not None, "续页布局存在：%s" % lays[1])
        vps2 = [e for e in cont if e.dxftype() == "VIEWPORT"] if cont else [1]
        check(len(vps2) == 0, "续页是纯说明页（无视口，不重复画图形）")
        # 续页应有正文
        n2 = sum(1 for e in cont if e.dxftype() == "TEXT"
                 and float(e.dxf.height or 0) >= 2.49) if cont else 0
        check(n2 > 3, "续页含 %d 行说明正文" % n2)

    # ==========================================================
    # [5] 成品图幅渲染
    # ==========================================================
    section("[5] 成品图幅渲染")

    img = DXFToImage()
    # 默认挑带视口的布局
    picked = DXFToImage._pick_paper_layout(doc, None)
    check(picked is not None and picked.name == "GB_A3",
          "自动挑中带视口的布局（%s）" % (picked.name if picked else None))
    # 续页布局名随 v1.17.3 命名模板化改为默认 GB_A3_notes_2（旧 GB_A3_说明2 仅在传 template 覆盖时回退）
    # 这里直接取生成结果里的真实续页名，验证「按名字指定布局」选择器对任意命名都生效
    cont_layouts = [l for l in (gen["result"].get("notes_layouts") or []) if l != "GB_A3"]
    cont_name = cont_layouts[0] if cont_layouts else "GB_A3_notes_2"
    check(cont_name == "GB_A3_notes_2",
          "默认续页命名遵循模板 GB_A3_notes_2（v1.17.3 续页命名模板化）")
    picked2 = DXFToImage._pick_paper_layout(doc, cont_name)
    check(picked2 is not None and picked2.name == cont_name,
          "按名字指定布局可用（%s）" % cont_name)
    check(DXFToImage._pick_paper_layout(doc, "不存在") is None,
          "指定不存在的布局返回 None")
    check(DXFToImage._pick_paper_layout(doc, "Model") is None,
          "'Model' 不算图纸空间布局")

    r1 = img.export(dxf1, "png", {"output": os.path.join(OUT, "model_prev"),
                                  "dpi": 100, "space": "model"})
    check(r1.get("success") and r1.get("space") == "model",
          "模型空间渲染 OK")
    check(os.path.getsize(r1["file"]) > 3000 if r1.get("success") else False,
          "模型空间 PNG 体积正常（%d KB）"
          % (os.path.getsize(r1["file"]) // 1024 if r1.get("success") else 0))
    r2 = img.export(dxf1, "png", {"output": os.path.join(OUT, "sheet_prev"),
                                  "dpi": 100, "space": "paper"})
    check(r2.get("success") and r2.get("space") == "paper",
          "图纸空间渲染 OK")
    check(os.path.getsize(r2["file"]) > 5000 if r2.get("success") else False,
          "成品图幅 PNG 体积正常（%d KB）"
          % (os.path.getsize(r2["file"]) // 1024 if r2.get("success") else 0))
    # 图纸空间实体数应多于模型空间（多了图框/标题栏/说明）
    check(r2.get("entities", 0) != r1.get("entities", 0),
          "两个空间的实体数不同（model %s vs paper %s）"
          % (r1.get("entities"), r2.get("entities")))

    # ==========================================================
    # [6] 向后兼容
    # ==========================================================
    section("[6] 向后兼容")

    # 6a. add_sheet=False → 无图框，说明退回模型空间
    b2 = NLAwareDxfBuilder(style="gb_architectural")
    dxf2 = os.path.join(OUT, "no_sheet.dxf")
    g2 = b2.generate_from_text("12x8米三层住宅平面图带客厅厨房卧室", dxf2,
                               add_sheet=False)
    check(g2.get("ok"), "add_sheet=False 仍能出图")
    d2 = ezdxf.readfile(dxf2)
    msp2 = d2.modelspace()
    e2 = _bbox.extents(msp2)
    h2 = e2.extmax.y - e2.extmin.y
    check(h2 > 25000, "无图框时说明写回模型空间（高度 %.0fmm，含文字柱）" % h2)
    check(not g2["result"].get("sheet_layout"), "无图框时未创建布局")

    # 6b. notes_in_layout=False → 有图框但强制说明留模型空间
    b3 = NLAwareDxfBuilder(style="gb_architectural")
    dxf3 = os.path.join(OUT, "force_model.dxf")
    g3 = b3.generate_from_text("12x8米三层住宅平面图带客厅厨房卧室", dxf3,
                               add_sheet=True, notes_in_layout=False)
    check(g3.get("ok") and g3["result"].get("notes_target") != "layout",
          "notes_in_layout=False 强制说明留模型空间")
    check(g3["result"].get("sheet_layout") == "GB_A3",
          "同时仍创建了图框布局")

    # ==========================================================
    # [7] auto_fit
    # ==========================================================
    section("[7] auto_fit（自动适配）")

    b4 = NLAwareDxfBuilder(style="gb_architectural")
    lay4 = b4.add_gb_sheet("A3", title_data={"project": "t", "title": "t"})
    # 起点用大字号（4.0mm）才谈得上"压缩"：若起点就是 2.5mm 下限，
    # auto_fit 正确地不做任何事（宁可不达标也不缩到读不出）。
    end_y = b4.add_construction_notes_by_discipline(
        "architectural", x=234, y=283, width=172, target=lay4,
        line_spacing=6.0, text_height=4.0, title_height=7.0,
        max_height=80.0, auto_fit=True)
    used = 283 - end_y
    check(used <= 82.0, "max_height=80 生效（实占 %.1fmm）" % used)
    hs = [float(e.dxf.height) for e in lay4 if e.dxftype() == "TEXT"]
    check(hs and min(hs) >= 2.49,
          "压缩后未跌破 min_text_height=2.5（最小 %.2f）"
          % (min(hs) if hs else -1))
    check(hs and max(hs) < 6.99,
          "字高确实被压小（最大 %.2f < 起始 7.0）"
          % (max(hs) if hs else -1))
    # 起点已在下限（2.5mm）时：auto_fit 如实不动，交给调用方分页
    b4b = NLAwareDxfBuilder(style="gb_architectural")
    lay4b = b4b.add_gb_sheet("A3", title_data={"project": "t", "title": "t"})
    endb = b4b.add_construction_notes_by_discipline(
        "architectural", x=234, y=283, width=172, target=lay4b,
        line_spacing=3.8, text_height=2.5, title_height=4.5,
        max_height=40.0, auto_fit=True)
    check((283 - endb) > 42.0,
          "字号已在下限时 auto_fit 不硬缩（实占 %.1fmm，交由分页处理）"
          % (283 - endb))
    # auto_fit=False 时应该如实溢出
    b5 = NLAwareDxfBuilder(style="gb_architectural")
    lay5 = b5.add_gb_sheet("A3", title_data={"project": "t", "title": "t"})
    end5 = b5.add_construction_notes_by_discipline(
        "architectural", x=234, y=283, width=172, target=lay5,
        line_spacing=6.0, text_height=4.0, title_height=7.0,
        max_height=80.0, auto_fit=False)
    check((283 - end5) > 82.0,
          "auto_fit=False 时不压缩（实占 %.1fmm）" % (283 - end5))

    # ==========================================================
    # [8] 主链集成
    # ==========================================================
    section("[8] 主链集成（pipeline）")

    pdir = os.path.join(OUT, "pipe")
    cfg = PipelineConfig(output_dir=pdir, do_render=True, render_dpi=90)
    pr = pipeline("12x8米三层住宅平面图带客厅厨房卧室", pdir, cfg)
    check(pr.success, "流水线跑通")
    check(pr.notes_target == "layout", "报告记录说明落点 = layout")
    check(pr.notes_pages >= 1, "报告记录图幅数 %d" % pr.notes_pages)
    check(bool(pr.view_scale), "报告记录视口比例 %s" % pr.view_scale)
    check(bool(pr.sheet_layouts), "报告记录布局 %s" % pr.sheet_layouts)
    check(len(pr.sheet_render_files) >= 1,
          "产出成品图幅预览 %d 张" % len(pr.sheet_render_files))
    check(all(os.path.exists(f) for f in pr.sheet_render_files),
          "成品图幅文件都真实存在")
    check(pr.review_grade.startswith("A"),
          "审查未因说明书搬位置而退化（%s）" % pr.review_grade)
    d = pr.to_dict()
    check(d["notes"]["target"] == "layout" and d["notes"]["pages"] >= 1,
          "to_dict 含 notes.target / notes.pages")
    check("sheet" in d and d["sheet"]["layouts"],
          "to_dict 含 sheet 段")
    check("sheet_files" in d["render"], "to_dict 含 render.sheet_files")
    txt = pr.to_text()
    check("落点" in txt and "图幅" in txt and "成品图幅" in txt,
          "文本报告含 落点/图幅/成品图幅 字段")
    # manifest 落盘
    man = os.path.join(pdir, "manifest.json")
    check(os.path.exists(man), "manifest.json 落盘")

    # ---- 汇总 ----
    print("\n" + "=" * 74)
    print("验证完成：PASS %d / FAIL %d" % (PASS, FAIL))
    if FAILED:
        print("失败项：")
        for f in FAILED:
            print("  · %s" % f)
    print("=" * 74)
    print("产出目录：%s" % OUT)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
