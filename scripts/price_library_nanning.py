# -*- coding: utf-8 -*-
"""price_library_nanning — 广西南宁单价库（增强2 · v1.17.11）

数据来源：南宁建设工程造价信息 2026 年第 1 期（人工）+ 我的钢铁网南宁行情 2026-09（材料）。
⚠️ 市场参考价，非官方定额价；正式造价须用广西 2026 版《预算清单综合单价组价表》。

⚠️ 接入约定：本库的「name」字段 = budget.py 的 UNIT_PRICES 键（材料名），
这样 to_budget_prices() 才能正确覆盖。单位也与 budget.py 保持一致：
  - 中砂：南宁市场报 70 元/t，budget 按 m³ 计量 → 按 1.5 t/m³ 折算 ≈ 105 元/m³。
  - 商品混凝土 C30：取泵送价 420 元/m³（裸混凝土约 300 元/m³，已在 note 注明）。

人工 / 机械条目也入库（便于搜索与导出的完整性），但 budget.py 当前人工是
「建筑面积 × 平准人工费」的单一常数（LABOR_PER_SQM），不按工种逐项计费，
故人工/机械条目**不参与**本版预算计算（仅材料单价覆盖生效）。
"""
from price_library import PriceLibrary, PriceItem


def create_nanning_library() -> PriceLibrary:
    """创建南宁单价库（材料名对齐 budget.py UNIT_PRICES）。"""
    lib = PriceLibrary(name="广西南宁市场价（2026-09）")

    # ============================================================
    # 材料（name 必须 == budget.py UNIT_PRICES 的键）
    # ============================================================
    materials = [
        # (code, name, unit, price, note)
        ('M005', '钢筋 HRB400',        't',  3400, '我的钢铁网南宁2026-09（HRB400E）'),
        ('M006', '商品混凝土 C30',     'm3', 420,  '泵送价；裸混凝土约300元/m3'),
        ('M002', '水泥 42.5',          't',  317,  '我的钢铁网南宁2026-09（P.O42.5散）'),
        ('M003', '中砂',               'm3', 105,  '机制砂70元/t × 1.5t/m3 折算'),
    ]
    for code, name, unit, price, note in materials:
        lib.add(PriceItem(code=code, name=name, unit=unit, price=price,
                          category='材料', source='南宁市场价2026-09', note=note))

    # ============================================================
    # 人工（仅供参考，不参与本版预算）
    # ============================================================
    labors = [
        ('L001', '建筑、装饰普工', '工日', 275, '南宁造价信息2026-01中值'),
        ('L002', '木工（模板工）', '工日', 325, '南宁造价信息2026-01中值'),
        ('L003', '钢筋工',         '工日', 305, '南宁造价信息2026-01中值'),
        ('L004', '混凝土工',       '工日', 305, '南宁造价信息2026-01中值'),
        ('L005', '架子工',         '工日', 365, '南宁造价信息2026-01中值'),
        ('L006', '抹灰工',         '工日', 300, '南宁造价信息2026-01中值'),
        ('L007', '镶贴工',         '工日', 305, '南宁造价信息2026-01中值'),
        ('L008', '装饰木工',       '工日', 325, '南宁造价信息2026-01中值'),
        ('L009', '防水工',         '工日', 300, '南宁造价信息2026-01中值'),
        ('L010', '管工',           '工日', 300, '南宁造价信息2026-01中值'),
        ('L011', '电工',           '工日', 300, '南宁造价信息2026-01中值'),
        ('L012', '电焊工',         '工日', 325, '南宁造价信息2026-01中值'),
        ('L013', '起重工',         '工日', 300, '南宁造价信息2026-01中值'),
    ]
    for code, name, unit, price, source in labors:
        lib.add(PriceItem(code=code, name=name, unit=unit, price=price,
                          category='人工', source=source,
                          note='不参与本版预算（budget人工为平准常数）'))

    # ============================================================
    # 机械（仅供参考，不参与本版预算）
    # ============================================================
    machines = [
        ('E001', '塔吊',       '台班', 800,  '市场参考'),
        ('E002', '挖掘机',     '台班', 1200, '市场参考'),
        ('E003', '混凝土泵车', '台班', 2000, '市场参考'),
    ]
    for code, name, unit, price, source in machines:
        lib.add(PriceItem(code=code, name=name, unit=unit, price=price,
                          category='机械', source=source,
                          note='不参与本版预算'))

    return lib


if __name__ == '__main__':
    lib = create_nanning_library()
    print(f"南宁单价库: {len(lib.items)} 项")
    print(f"  材料: {len(lib.list_by_category('材料'))}")
    print(f"  人工: {len(lib.list_by_category('人工'))}")
    print(f"  机械: {len(lib.list_by_category('机械'))}")

    print("\n【材料单价（将覆盖 budget）】")
    for i in lib.list_by_category('材料'):
        print(f"  {i.code} {i.name:<14} {i.unit} {i.price}  ({i.note})")

    print("\n【to_budget_prices 样例】")
    for k, v in lib.to_budget_prices().items():
        print(f"  {k} -> {v}")
