# -*- coding: utf-8 -*-
"""
按效果图还原：12m 面宽 二层农村小别墅 施工图（GB/T 国标）
产出：一层平面图 / 二层平面图 / 南立面图 / 1-1剖面图，各套 A3 图框+标题栏+1:100视口
对应效果图特征：深灰坡屋顶、白色外墙、二层南向玻璃护栏阳台、一层大落地窗+黑色双开门
"""
import sys, os

SKILL = r"C:\Users\binliu8199\.workbuddy\skills\dxf-generator"
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from dxfkit import GBDxfBuilder   # 国标构建器（自带中文字体 + 施工说明 + 规范引用）
import archkit
import templates_arch as ta

# ---------------- 设计参数（由效果图推定） ----------------
W, D = 12000, 10200      # 面宽 12.0m  进深 10.2m
T = 240                  # 外墙厚
TI = 200                 # 内墙厚
MID_Y = 5100             # 南北分界内墙
H1, H2, RH = 3000, 2900, 2200   # 一层/二层层高、坡屋顶高
OUT = r"C:\Users\binliu8199\Desktop\别墅施工图_12m二层"
os.makedirs(OUT, exist_ok=True)


def room(b, x0, y0, x1, y1, name, area, h=240):
    """房名+面积双行居中（字高小，避免北排四间互相挤压）"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    b.text(name, cx, cy + 220, h=h)
    b.text(area, cx, cy - 220, h=h)


def dims(b, title_data, scale=1 / 100):
    """公共：轴线 + 三道尺寸 + 图框 + 施工说明"""
    # 轴网
    for i, x in enumerate([0, 6000, 12000], start=1):
        archkit.axis(b, x, -1400, x, D + 1400, label=str(i))
    for i, y in enumerate([0, MID_Y, D], start=1):
        archkit.axis(b, -1400, y, W + 1400, y, label=chr(64 + i))
    # 尺寸（国标，1:100）
    b.add_gb_dimension(0, -900, W, -900, scale=100)
    b.add_gb_dimension(0, D + 900, W, D + 900, scale=100)
    b.add_gb_dimension(-900, 0, -900, D, scale=100)
    # 指北针 + 标高
    archkit.compass(b, W + 2200, D - 800, size=900)
    archkit.elevation_mark(b, -1800, 0, elev=0.0)


def sheet(b, code, title, sub=""):
    lay = b.add_gb_sheet(
        "A3",
        title_data={"project": "12m二层农村小别墅", "title": title,
                    "scale": "1:100", "drawing_no": code},
        view_center=(W / 2, D / 2), scale=1 / 100, name=code)
    b.add_construction_notes_by_discipline(
        "architectural", target=lay, x=232, y=283, width=175,
        text_height=2.5, line_spacing=3.5, title_height=4.0)
    return lay


# =============== 1. 一层平面图 ===============
def floor1(path):
    b = GBDxfBuilder(style="gb_architectural")
    b.set_project_info("12m二层农村小别墅", "一层平面图", "建施-01")
    # 外墙（自动留门窗洞口）
    b.wall_h(0, 0, W, openings=[(300, 3300, "win"), (3900, 5700, "door"),
                                (6600, 9000, "win"), (9600, 11400, "win")])
    b.wall_h(D, 0, W, openings=[(1500, 3300, "win"), (7200, 8700, "win")])
    b.wall_v(0, 0, D, openings=[(6300, 7500, "win")])
    b.wall_v(W, 0, D, openings=[])
    # 内墙
    archkit.wall(b, 0, MID_Y, W, MID_Y, thickness=TI)
    archkit.wall(b, 6000, 0, 6000, MID_Y, thickness=TI)
    for x in (4200, 6600, 9000):
        archkit.wall(b, x, MID_Y, x, D, thickness=TI)
    # 楼梯
    archkit.stair(b, 9400, 5600, width=1200, height=3600, steps=12)
    room(b, 0, 0, 6000, MID_Y, "客厅", "33.6m2")
    room(b, 6000, 0, W, MID_Y, "老人房", "26.5m2")
    room(b, 0, MID_Y, 4200, D, "餐厅", "21.4m2")
    room(b, 4200, MID_Y, 6600, D, "厨房", "12.2m2")
    room(b, 6600, MID_Y, 9000, D, "卫生间", "12.2m2")
    room(b, 9000, MID_Y, W, D, "楼梯间", "15.3m2")
    b.text("M-1 入户门 1800x2400", 4800, -1900, h=300)
    dims(b, "建施-01")
    sheet(b, "建施-01", "一层平面图")
    return b.save(path)


# =============== 2. 二层平面图 ===============
def floor2(path):
    b = GBDxfBuilder(style="gb_architectural")
    b.set_project_info("12m二层农村小别墅", "二层平面图", "建施-02")
    b.wall_h(0, 0, W, openings=[(2100, 3900, "door"), (4800, 7200, "win"),
                                (7800, 10200, "win")])
    b.wall_h(D, 0, W, openings=[(1500, 3300, "win"), (7200, 8700, "win")])
    b.wall_v(0, 0, D, openings=[(6300, 7500, "win")])
    b.wall_v(W, 0, D, openings=[])
    archkit.wall(b, 0, MID_Y, W, MID_Y, thickness=TI)
    archkit.wall(b, 6000, 0, 6000, MID_Y, thickness=TI)
    for x in (4200, 6600, 9000):
        archkit.wall(b, x, MID_Y, x, D, thickness=TI)
    archkit.stair(b, 9400, 5600, width=1200, height=3600, steps=12)
    # 南向阳台（挑出 1500，玻璃护栏双线）
    bx0, bx1, by = 1200, 7200, -1500
    b.rect(bx0, by, bx1, 0, layer="G_WALL")
    b.line(bx0 + 80, by + 80, bx1 - 80, by + 80, layer="G_WINDOW")
    b.line(bx0 + 80, -80, bx1 - 80, -80, layer="G_WINDOW")
    b.text("阳台（玻璃护栏 H=1100）", (bx0 + bx1) / 2, by / 2, h=300)
    room(b, 0, 0, 6000, MID_Y, "主卧", "33.6m2")
    room(b, 6000, 0, W, MID_Y, "次卧", "26.5m2")
    room(b, 0, MID_Y, 4200, D, "卧室三", "21.4m2")
    room(b, 4200, MID_Y, 6600, D, "书房", "12.2m2")
    room(b, 6600, MID_Y, 9000, D, "卫生间", "12.2m2")
    room(b, 9000, MID_Y, W, D, "楼梯间", "15.3m2")
    dims(b, "建施-02")
    sheet(b, "建施-02", "二层平面图")
    return b.save(path)


# =============== 3. 南立面图（对应效果图） ===============
def elev(path):
    b = GBDxfBuilder(style="gb_architectural")
    b.set_project_info("12m二层农村小别墅", "南立面图", "建施-03")
    ta.elevation(b, ta.ElevationParams(
        width=W, height=H1 + H2 + RH, direction="front", floors=2,
        floor_height=H1, window_width=2400, window_height=2100,
        window_count_per_floor=3, window_sill=500,
        roof_type="pitched", roof_height=RH,
        has_door=True, door_width=1800, door_height=2400))
    b.text("深灰色沥青瓦坡屋面", W / 2, H1 + H2 + RH + 900, h=350)
    b.text("白色外墙涂料", W + 700, H1 + H2, h=300)
    b.text("二层玻璃护栏阳台", W / 2, H1 + 700, h=300)
    b.text("入户门 1800x2400（深灰）", W / 2, -900, h=300)
    b.add_gb_dimension(0, -1200, W, -1200, scale=100)
    b.add_gb_dimension(-900, 0, -900, H1 + H2 + RH, scale=100)
    sheet(b, "建施-03", "南立面图")
    return b.save(path)


# =============== 4. 1-1 剖面图 ===============
def sect(path):
    b = GBDxfBuilder(style="gb_architectural")
    b.set_project_info("12m二层农村小别墅", "1-1剖面图", "建施-04")
    ta.section(b, ta.SectionParams(
        width=D, floors=2, floor_height=H1, roof_type="pitched",
        roof_height=RH, foundation_depth=1500, foundation_type="strip",
        slab_thickness=120, beam_height=500))
    b.text("1-1剖面图  1:100", D / 2, -2000, h=400)
    sheet(b, "建施-04", "1-1剖面图")
    return b.save(path)


if __name__ == "__main__":
    jobs = [("建施-01 一层平面图.dxf", floor1), ("建施-02 二层平面图.dxf", floor2),
            ("建施-03 南立面图.dxf", elev), ("建施-04 1-1剖面图.dxf", sect)]
    for name, fn in jobs:
        p = os.path.join(OUT, name)
        try:
            rep = fn(p)
            bb = rep.get("bbox") or [0, 0, 0, 0, 0, 0]
            print(f"OK  {name:28s} 实体{rep['entities']:>4d}  图层{len(rep['layers']):>2d}  "
                  f"X[{bb[0]:.0f},{bb[3]:.0f}] Y[{bb[1]:.0f},{bb[4]:.0f}]")
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print("OUT =", OUT)
