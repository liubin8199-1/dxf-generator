# -*- coding: utf-8 -*-
"""实例：15m 面宽三层别墅方案平面图（用 dxfkit 生成）。
运行：python villa_demo.py  →  输出 villa_15m.dxf（与本 skill 同目录）
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from dxfkit import DxfBuilder

W, BODY_D, PORCH_D = 15000, 8000, 4000
TOTAL_D = PORCH_D + BODY_D  # 12000

def build_floor(b, oy, rooms, label):
    b.wall_h(oy+0,        0, W, [(1500,3500,"door"),(11500,13500,"door")])   # 南
    b.wall_h(oy+TOTAL_D,  0, W, [(1500,2500,"win"),(11500,13500,"win")])    # 北
    b.wall_v(0,  oy+0, oy+TOTAL_D, [(2000,3500,"win"),(10000,11500,"win")]) # 西
    b.wall_v(W,  oy+0, oy+TOTAL_D, [(2000,3500,"win"),(10000,11500,"win")]) # 东
    b.wall_h(oy+PORCH_D, 0, W, [(2500,3500,"door"),(7000,8200,"door")])    # 门廊/主体分隔
    b.wall_v(5000,  oy+PORCH_D, oy+TOTAL_D, [(6000,6800,"door")])
    b.wall_v(10000, oy+PORCH_D, oy+TOTAL_D, [(6000,6800,"door")])
    b.wall_h(oy+9000, 0, W, [(2500,3300,"door"),(7500,8300,"door"),(12500,13300,"door")])
    b.rect(0, oy+0, W, oy+PORCH_D, "AUX")
    b.text("门廊 PORCH 4.0m", W/2, oy+1500, h=300, layer="AUX", align="CENTER")
    b.stair(6500, oy+4400, 8500, oy+7600)
    for nm,(rx,ry) in rooms.items():
        b.text(nm, rx, oy+ry, h=320, layer="TXT", align="CENTER")
    b.dim_h(oy+0, 0, W, "15000 (15.0m)", off=oy-1200)
    b.dim_v(0, oy+0, oy+TOTAL_D, "12000 (12.0m)", off=-1200)
    b.text(label, W/2, oy+TOTAL_D+700, h=600, layer="TITLE", align="CENTER")

R1 = {"车库":(2500,6500),"门厅":(7500,6500),"客厅":(12500,6500),
      "厨房":(2500,10500),"餐厅":(7500,10500),"老人房+卫":(12500,10500)}
R2 = {"主卧套间":(2500,6500),"楼梯/家庭厅":(7500,6500),"次卧套间":(12500,6500),
      "公卫":(2500,10500),"书房":(12500,10500)}
R3 = {"客房":(2500,6500),"楼梯/走廊":(7500,6500),"健身":(12500,6500),
      "公卫":(2500,10500),"大露台":(12500,10500)}

GAP = 4000
b = DxfBuilder()
build_floor(b, 2*(TOTAL_D+GAP), R1, "一 层 (1F)")
build_floor(b, 1*(TOTAL_D+GAP), R2, "二 层 (2F)")
build_floor(b, 0*(TOTAL_D+GAP), R3, "三 层 (3F)")
top = 3*(TOTAL_D+GAP) - GAP
b.text("15m 面宽 · 三层简欧别墅 · 方案平面图（1:100 示意）", W/2, top+2000, h=700, layer="TITLE", align="CENTER")
b.text("AI 辅助生成 · 施工前须经注册结构/建筑工程师复核", W/2, top+400, h=300, layer="AUX", align="CENTER")

out = os.path.join(os.path.dirname(__file__), "villa_15m.dxf")
rep = b.save(out)
print("SAVED:", out)
print("L3:", rep)
