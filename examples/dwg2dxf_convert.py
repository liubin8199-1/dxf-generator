# -*- coding: utf-8 -*-
"""② 识图通用化 —— DWG→DXF 转换器（跑在 cadconv venv / aspose-cad）

两个关键结论（探针实测得出，是本脚本存在的理由）：
  1. 必须用 CadOutputMode.CONVERT，不能用默认的 RENDER。
     RENDER 会把所有对象"渲染成线段"→ 文字炸成 POLYLINE、体积涨 ~49 倍；实测 0.26MB→12.7MB。
     CONVERT "保留原对象"→ 文字仍是 TEXT/MTEXT、体积只 6 倍；实测 0.26MB→1.59MB，0.4 秒。
  2. aspose 写的 OBJECTS 段含 ezdxf 无法解析的实体（VISUALSTYLE 的 291 组码、
     XRECORD 缺 y 坐标）。这些与图纸内容无关，**剥掉 OBJECTS 段**后 ezdxf 可正常读取。

产物：
  out_dxf/<name>.dxf        aspose CONVERT 的原始输出（未处理，ezdxf 读不了）
  out_dxf/p_<name>.dxf      预处理后（剥 OBJECTS + 删缺名表记录），ezdxf 可直接读
"""
import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
OUT = os.path.join(HERE, "out_dxf")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
from dxf_prepare import prepare  # noqa: E402  （同一份预处理器，口径统一）


def main():
    import aspose.cad as cad
    from aspose.cad.imageoptions import DxfOptions, CadOutputMode

    files = sorted(glob.glob(os.path.join(SRC, "*.dwg")),
                   key=lambda p: os.path.getsize(p))
    print("=== ② DWG→DXF（CONVERT 模式）===")
    print("样本 %d 个\n" % len(files), flush=True)

    rows = []
    t_all = time.time()
    for p in files:
        fn = os.path.basename(p)
        stem = os.path.splitext(fn)[0]
        src_mb = os.path.getsize(p) / 1048576
        r = {"file": fn, "src_mb": round(src_mb, 2)}
        t0 = time.time()
        try:
            img = cad.Image.load(file_path=p)
            r["load_s"] = round(time.time() - t0, 1)

            opt = DxfOptions()
            opt.output_mode = CadOutputMode.CONVERT     # ← 关键
            raw = os.path.join(OUT, stem + ".dxf")
            t1 = time.time()
            img.save(raw, opt)
            r["save_s"] = round(time.time() - t1, 1)

            clean = os.path.join(OUT, "p_" + stem + ".dxf")
            t2 = time.time()
            st = prepare(raw, clean)
            r["stripped"] = st["objects_removed"]
            r["records_dropped"] = st["records_dropped"]
            r["strip_s"] = round(time.time() - t2, 1)

            r["dxf_mb"] = round(os.path.getsize(raw) / 1048576, 2)
            r["clean_mb"] = round(os.path.getsize(clean) / 1048576, 2)
            r["ratio"] = round(r["dxf_mb"] / max(src_mb, 0.01), 1)
            r["ok"] = True
        except Exception as e:
            r["ok"] = False
            r["err"] = repr(e)[:160]
        r["total_s"] = round(time.time() - t0, 1)
        rows.append(r)

        if r["ok"]:
            print("  %-34s %5.2fMB → %6.2fMB(%4.1fx)  load%5.1fs save%5.1fs strip%4.1fs"
                  "  总%5.1fs" % (fn, r["src_mb"], r["dxf_mb"], r["ratio"],
                                 r["load_s"], r["save_s"], r["strip_s"], r["total_s"]),
                  flush=True)
        else:
            print("  %-34s FAIL %s" % (fn, r["err"]), flush=True)

    ok = [r for r in rows if r.get("ok")]
    print("\n=== 汇总 ===")
    print("成功 %d / %d，总耗时 %.1f 秒" % (len(ok), len(rows), time.time() - t_all))
    if ok:
        avg = sum(r["total_s"] for r in ok) / len(ok)
        print("平均 %.1fs/文件 → 182 个文件约 %.0f 分钟"
              % (avg, avg * 182 / 60))
        print("平均膨胀 %.1fx；平均 DXF %.1fMB → 182 个约 %.1fGB"
              % (sum(r["ratio"] for r in ok) / len(ok),
                 sum(r["dxf_mb"] for r in ok) / len(ok),
                 sum(r["dxf_mb"] for r in ok) / len(ok) * 182 / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
