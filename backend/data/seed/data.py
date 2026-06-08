"""种子数据定义"""

# ============ HS 编码（前6位国际通用码） ============
# 来源：中国海关进出口税则（2024版）
HS_CODES = [
    # ---- 第84章 机械设备 ----
    dict(code="84713010", description="重量≤10公斤的便携式自动数据处理设备（平板电脑、笔记本）", chapter="84", heading="8471", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="84714100", description="自动数据处理设备（台式机、一体机），含中央处理器和输入输出部件", chapter="84", heading="8471", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="84715000", description="数据处理设备（服务器），同一机壳内至少含一个CPU和一个输入输出部件", chapter="84", heading="8471", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="84433210", description="激光打印机", chapter="84", heading="8443", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),

    # ---- 第85章 电机、电气设备 ----
    dict(code="85171210", description="智能手机（含4G/5G通讯模块）", chapter="85", heading="8517", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="85176290", description="路由器/交换机（网络通信设备）", chapter="85", heading="8517", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="85183000", description="耳机、耳塞（有线/无线）", chapter="85", heading="8518", country="CN", base_rate=0.0, vat_rate=13.0, unit="副"),
    dict(code="85182100", description="单喇叭音箱", chapter="85", heading="8518", country="CN", base_rate=5.0, vat_rate=13.0, unit="个"),
    dict(code="85182200", description="多喇叭音箱（含蓝牙/Wi-Fi智能音箱）", chapter="85", heading="8518", country="CN", base_rate=5.0, vat_rate=13.0, unit="个"),
    dict(code="85285212", description="液晶显示器（≤24英寸）", chapter="85", heading="8528", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="85423100", description="集成电路（处理器/控制器）", chapter="85", heading="8542", country="CN", base_rate=0.0, vat_rate=13.0, unit="个"),

    # ---- 第61章 针织服装 ----
    dict(code="61091000", description="棉制T恤衫、汗衫", chapter="61", heading="6109", country="CN", base_rate=6.0, vat_rate=13.0, unit="件"),
    dict(code="61102000", description="棉制套头衫、开襟衫", chapter="61", heading="6110", country="CN", base_rate=6.0, vat_rate=13.0, unit="件"),

    # ---- 第62章 非针织服装 ----
    dict(code="62046200", description="棉制女式长裤", chapter="62", heading="6204", country="CN", base_rate=6.0, vat_rate=13.0, unit="条"),
    dict(code="62052000", description="棉制男式衬衫", chapter="62", heading="6205", country="CN", base_rate=6.0, vat_rate=13.0, unit="件"),
    dict(code="62104000", description="化纤制男式防寒外套", chapter="62", heading="6210", country="CN", base_rate=10.0, vat_rate=13.0, unit="件"),

    # ---- 第64章 鞋靴 ----
    dict(code="64039900", description="橡胶/塑料底皮革面鞋靴（运动鞋等）", chapter="64", heading="6403", country="CN", base_rate=10.0, vat_rate=13.0, unit="双"),

    # ---- 第73章 钢铁制品 ----
    dict(code="73269090", description="其他钢铁制品（五金件）", chapter="73", heading="7326", country="CN", base_rate=5.0, vat_rate=13.0, unit="千克"),

    # ---- 第87章 车辆 ----
    dict(code="87032341", description="仅装点燃式发动机的小轿车（1500ml＜排量≤2000ml）", chapter="87", heading="8703", country="CN", base_rate=15.0, vat_rate=13.0, unit="辆"),

    # ---- 第90章 光学、医疗仪器 ----
    dict(code="90138000", description="液晶显示器件（LCD）", chapter="90", heading="9013", country="CN", base_rate=3.0, vat_rate=13.0, unit="个"),

    # ---- 第94章 家具 ----
    dict(code="94036010", description="红木家具", chapter="94", heading="9403", country="CN", base_rate=10.0, vat_rate=13.0, unit="件"),
    dict(code="94036090", description="其他木质家具（桌椅柜等）", chapter="94", heading="9403", country="CN", base_rate=0.0, vat_rate=13.0, unit="件"),
    dict(code="94049000", description="床垫、被褥、靠垫等寝具", chapter="94", heading="9404", country="CN", base_rate=10.0, vat_rate=13.0, unit="千克"),

    # ---- 第95章 玩具 ----
    dict(code="95045000", description="视频游戏控制器（含游戏主机）", chapter="95", heading="9504", country="CN", base_rate=0.0, vat_rate=13.0, unit="台"),
    dict(code="95030089", description="其他玩具（塑料/电子玩具）", chapter="95", heading="9503", country="CN", base_rate=0.0, vat_rate=13.0, unit="个"),

    # ---- 第39章 塑料及其制品 ----
    dict(code="39269090", description="其他塑料制品（塑料配件、外壳）", chapter="39", heading="3926", country="CN", base_rate=10.0, vat_rate=13.0, unit="千克"),

    # ---- 第42章 皮革制品 ----
    dict(code="42022200", description="塑料/纺织材料作面的手提包", chapter="42", heading="4202", country="CN", base_rate=10.0, vat_rate=13.0, unit="个"),

    # ---- 第16章 食品 ----
    dict(code="16010000", description="肉、杂碎或动物血制成的香肠及类似产品", chapter="16", heading="1601", country="CN", base_rate=12.0, vat_rate=9.0, unit="千克"),
]

# ============ 关税税率表（按目标国 + HS前缀） ============
TARIFF_SCHEDULES = [
    # 美国 —— 一般关税
    dict(country="US", hs_code_prefix="8471", base_rate=0.0, vat_rate=0.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="笔记本电脑/平板，美国信息技术协定(ITA)免税"),
    dict(country="US", hs_code_prefix="8517", base_rate=0.0, vat_rate=0.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="智能手机/通信设备，ITA免税"),
    dict(country="US", hs_code_prefix="8518", base_rate=2.5, vat_rate=0.0, anti_dumping_rate=0.0, preferential_rate=0.0, fta_name="USMCA", notes="音箱/耳机，符合USMCA可免基础关税"),
    dict(country="US", hs_code_prefix="6204", base_rate=8.5, vat_rate=0.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="棉制女裤，美国对中国可能有额外301条款关税(+7.5%)"),
    dict(country="US", hs_code_prefix="8703", base_rate=2.5, vat_rate=0.0, anti_dumping_rate=0.0, preferential_rate=0.0, fta_name="USMCA", notes="乘用车，美国对中国额外加征25%关税（232条款）"),

    # 欧盟 —— 一般关税
    dict(country="EU", hs_code_prefix="8471", base_rate=0.0, vat_rate=19.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="笔记本电脑，欧盟ITA免税，增值税按进口国税率"),
    dict(country="EU", hs_code_prefix="8518", base_rate=2.0, vat_rate=19.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="音箱类商品"),
    dict(country="EU", hs_code_prefix="9403", base_rate=0.0, vat_rate=19.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="木质家具，零基础关税"),
    dict(country="EU", hs_code_prefix="6403", base_rate=8.0, vat_rate=19.0, anti_dumping_rate=0.0, preferential_rate=None, fta_name=None, notes="皮鞋类，欧盟对中国鞋类有关税配额限制"),

    # 东盟（以越南为例）
    dict(country="VN", hs_code_prefix="8471", base_rate=0.0, vat_rate=10.0, anti_dumping_rate=0.0, preferential_rate=0.0, fta_name="RCEP", notes="笔记本电脑，RCEP零关税"),
    dict(country="VN", hs_code_prefix="8517", base_rate=0.0, vat_rate=10.0, anti_dumping_rate=0.0, preferential_rate=0.0, fta_name="RCEP", notes="智能手机，RCEP零关税"),
    dict(country="VN", hs_code_prefix="6204", base_rate=5.0, vat_rate=10.0, anti_dumping_rate=0.0, preferential_rate=0.0, fta_name="RCEP", notes="服装类，RCEP后可降至0%（逐年降税）"),
    dict(country="VN", hs_code_prefix="8703", base_rate=30.0, vat_rate=10.0, anti_dumping_rate=0.0, preferential_rate=15.0, fta_name="RCEP", notes="汽车，RCEP优惠税率"),
]

# ============ 制裁实体清单（示例） ============
SANCTIONS = [
    dict(entity_name="示例制裁实体A（军工企业）", country="XX", list_type="OFAC", restriction_type="prohibited", notes="禁止所有美国相关贸易"),
    dict(entity_name="示例限制实体B", country="YY", list_type="CN", restriction_type="restricted", notes="需商务部出口许可证"),
    dict(entity_name="示例受限技术公司C", country="ZZ", list_type="UN", restriction_type="license_required", notes="涉及军民两用技术出口需审批"),
]
