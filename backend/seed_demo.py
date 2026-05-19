"""
FraudLens 演示数据种子脚本
注入20+条案情到数据库, 让看板/列表/详情页都有内容可展示
"""
import sys, os, uuid, json
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db, init_db
from flask import Flask as _Flask

DB_URI = 'mysql+pymysql://root:20051223@localhost:3306/fraudlens?charset=utf8mb4'
_flask_app = _Flask(__name__)
_flask_app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
_flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_db(_flask_app)

with _flask_app.app_context():
    from database.models import Case, Gang, GangCaseRelation, AnalysisSession

    # ---- 1. 创建分析会话 ----
    session_id = 'demo_session_' + datetime.now().strftime('%Y%m%d')
    existing = AnalysisSession.query.filter_by(session_id=session_id).first()
    if existing:
        print("⚠️ 演示数据已存在，跳过")
        sys.exit(0)

    sess = AnalysisSession(
        session_id=session_id,
        status='completed',
        total_cases=25,
        total_gangs=5,
        raw_input={'source': 'demo_data'},
        processing_info={'processing_time_ms': 8500, 'model': 'deepseek-v4-flash'}
    )
    db.session.add(sess)
    db.session.flush()

    # ---- 2. 注入25条案情 ----
    demo_cases = [
        # 团伙1: 冒充京东客服 (7条)
        {"title": "假冒京东客服征信诈骗案", "victim": "王芳", "amount": 125800, "type": "冒充客服", "desc": '接到自称京东客服电话，称其京东金条利率过高需注销，否则影响征信。对方引导下载"瞩目"APP并开启屏幕共享，以验证资金为由骗取转账。'},
        {"title": "注销京东金条诈骗案", "victim": "李强", "amount": 89600, "type": "冒充客服", "desc": "骗子冒充京东金融客服，称其开通了京东金条需注销。要求将所有资金转入银监会安全账户验证，承诺验证后返还。"},
        {"title": "京东白条利率调整诈骗", "victim": "张丽", "amount": 234000, "type": "冒充客服", "desc": "对方自称京东客服，称白条利率高于国家规定需调整。诱导下载腾讯会议开启共享屏幕，指导其在各网贷平台借款后转账。"},
        {"title": "冒充京东客服注销账户", "victim": "陈刚", "amount": 56700, "type": "冒充客服", "desc": "骗子声称京东账户存在异常需要注销，要求配合操作。通过共享屏幕获取银行卡信息，远程操作转走卡内余额。"},
        {"title": "京东金条征信修复诈骗", "victim": "刘洋", "amount": 178900, "type": "冒充客服", "desc": "冒充京东客服以征信修复为由，诱导受害人下载指定APP并开启屏幕共享。共骗取受害人通过银行转账和网贷借款方式转出资金。"},
        {"title": "冒充金融客服注销贷款", "victim": "赵敏", "amount": 312000, "type": "冒充客服", "desc": "对方自称京东金融客服，称其名下有多笔贷款需要注销。要求将资金转入指定账户进行流水验证，先后转账5笔。"},
        {"title": "京东金条年费取消诈骗", "victim": "孙伟", "amount": 45600, "type": "冒充客服", "desc": "骗子谎称京东金条产生年费需取消，否则影响征信。要求下载第三方会议软件并共享屏幕，通过远程操作转走资金。"},

        # 团伙2: 冒充公检法 (6条)
        {"title": "冒充公检法洗钱案", "victim": "周秀英", "amount": 458000, "type": "冒充公检法", "desc": "接到自称某市公安局电话，称其涉嫌洗钱犯罪。要求配合调查并通过资金审查证明清白，将所有资金转入安全账户。"},
        {"title": "冒充检察院案件核查", "victim": "吴建国", "amount": 289000, "type": "冒充公检法", "desc": "骗子冒充检察院工作人员，称其涉及一起重大经济案件。通过伪造的逮捕令和冻结令恐吓受害人，诱导其转账。"},
        {"title": "冒充公安涉黑诈骗", "victim": "郑晓燕", "amount": 156700, "type": "冒充公检法", "desc": "对方自称某地公安民警，称其账户涉嫌为黑社会组织洗钱。要求其配合制作笔录，并缴纳保证金到指定账户。"},
        {"title": "冒充法院传票诈骗", "victim": "钱德明", "amount": 92300, "type": "冒充公检法", "desc": "接到冒充法院的电话，称其有传票未领取，涉及合同诈骗案。要求缴纳担保金到法院指定账户。"},
        {"title": "冒充警方资金核查", "victim": "林小红", "amount": 67800, "type": "冒充公检法", "desc": "骗子冒充反诈中心民警，称其银行卡被用于电信诈骗，要求配合资金核查。下载指定APP后远程控制手机转走资金。"},
        {"title": "冒充公安出入境诈骗", "victim": "黄大明", "amount": 345000, "type": "冒充公检法", "desc": "对方冒充出入境管理局和公安民警，称其护照被用于非法入境，涉嫌重大犯罪。要求缴纳取保候审保证金。"},

        # 团伙3: 刷单返利 (5条)
        {"title": "刷单返利连环诈骗案", "victim": "何小燕", "amount": 87600, "type": "刷单返利", "desc": "在微信群看到刷单兼职广告，添加客服后开始做任务。前几单小额返利成功后，被诱导做大额任务，后无法提现。"},
        {"title": "抖音点赞刷单诈骗", "victim": "宋玉兰", "amount": 34500, "type": "刷单返利", "desc": "在抖音上看到点赞赚钱广告，下载指定APP后开始做任务。前期获得小额返利，后期被要求预付垫资后无法提现。"},
        {"title": "淘宝刷单虚假交易", "victim": "韩文强", "amount": 120000, "type": "刷单返利", "desc": "通过短信链接添加刷单客服，按要求在淘宝下单但不在平台付款，直接转账到对方提供的账户。累计刷单20余笔后发现被骗。"},
        {"title": "兼职刷单连环套", "victim": "曹雪梅", "amount": 234500, "type": "刷单返利", "desc": "在网络招聘平台看到高薪兼职，添加对方后开始刷单。被诱导进入VIP群做联单任务，投入大量资金后平台关闭。"},
        {"title": "购物平台刷信誉诈骗", "victim": "许志强", "amount": 67800, "type": "刷单返利", "desc": "冒充电商平台客服邀请刷信誉，称可返利15%。前期小额获利后，被诱导做大额刷单任务，最终被骗。"},

        # 团伙4: 投资理财 (4条)
        {"title": "虚假投资理财平台诈骗", "victim": "马晓东", "amount": 567000, "type": "投资理财", "desc": "在社交平台认识陌生好友，推荐投资数字货币平台。前期小额盈利并成功提现，后追加投入大额资金，平台无法登录。"},
        {"title": "股票推荐杀猪盘", "victim": "胡建军", "amount": 890000, "type": "投资理财", "desc": "被拉入股票交流群，群内老师推荐某投资平台。初次投资盈利后追加投入，后发现平台无法提现，群也被解散。"},
        {"title": "虚拟货币投资诈骗", "victim": "彭丽华", "amount": 234000, "type": "投资理财", "desc": "通过婚恋网站认识对象，对方称有虚拟货币内幕消息。引导在某平台投资USDT，前期盈利后期无法提现。"},
        {"title": "外汇投资骗局", "victim": "余志远", "amount": 445000, "type": "投资理财", "desc": "接到投资顾问电话推荐外汇投资，承诺月收益20%。下载MT4平台后投入资金，盈利后申请出金被拒。"},

        # 团伙5: 冒充熟人/领导 (3条)
        {"title": "冒充领导借款诈骗", "victim": "杨国平", "amount": 280000, "type": "冒充熟人", "desc": "接到冒充乡镇领导的微信好友申请，对方以需要转账但自己不方便操作为由，要求代转账。通过银行转账被骗。"},
        {"title": "冒充子女要学费诈骗", "victim": "王秀兰", "amount": 45600, "type": "冒充熟人", "desc": "接到冒充在外地上大学的儿子的电话，称学校需要缴纳培训费。因声音相似未怀疑，转账后联系儿子才发现被骗。"},
        {"title": "冒充公司老板诈骗财务", "victim": "张敏", "amount": 650000, "type": "冒充熟人", "desc": "公司财务接到冒充老板的QQ消息，称急需支付一笔合同款。因头像和昵称一致未核实，通过公司对公账户转账。"},
    ]

    from database.models import Person, Account, Phone
    import random

    case_objects = []
    for i, cd in enumerate(demo_cases):
        case_id = f"FC{datetime.now().strftime('%Y%m%d')}{i+1:03d}"
        risk_scores = [75, 82, 68, 90, 78, 85, 72, 88, 76, 80, 70, 86, 74, 79, 83, 71, 87, 73, 81, 69, 84, 77, 89, 67, 91]
        risk_score = risk_scores[i]
        if risk_score >= 85:
            risk_level, risk_label, risk_type = 'HIGH', '高风险', 'danger'
        elif risk_score >= 70:
            risk_level, risk_label, risk_type = 'MEDIUM', '中风险', 'warning'
        else:
            risk_level, risk_label, risk_type = 'LOW', '低风险', 'info'

        case = Case(
            case_id=case_id, session_id=session_id,
            title=cd['title'],
            scam_type=cd['type'],
            risk_level=risk_level, risk_label=risk_label, risk_type=risk_type,
            risk_score=risk_score,
            victim_name=cd['victim'],
            victim_age=str(random.randint(22, 65)),
            victim_gender='男' if random.random() > 0.5 else '女',
            amount=str(cd['amount']), amount_value=float(cd['amount']),
            description=cd['desc'],
            status='已立案', source='文本',
            keywords=[cd['type'], '诈骗', '转账', '冒充'],
            created_at=datetime.now() - timedelta(days=random.randint(1, 60), hours=random.randint(0, 23))
        )
        db.session.add(case)
        case_objects.append(case)
    db.session.flush()

    # ---- 3. 注入5个团伙 ----
    gang_data = [
        {'name': '京东客服诈骗团伙', 'level': 'S', 'score': 92, 'tech': '高', 'script': '冒充京东金融客服话术', 'member': '10-15人', 'amount': 1042600},
        {'name': '公检法冒充团伙', 'level': 'A', 'score': 85, 'tech': '高', 'script': '冒充公检法恐吓话术', 'member': '8-12人', 'amount': 1408800},
        {'name': '刷单返利团伙', 'level': 'B', 'score': 72, 'tech': '中', 'script': '刷单返利话术', 'member': '6-10人', 'amount': 544400},
        {'name': '虚假投资理财团伙', 'level': 'A', 'score': 88, 'tech': '高', 'script': '投资理财虚假平台', 'member': '15-20人', 'amount': 2136000},
        {'name': '冒充熟人诈骗团伙', 'level': 'B', 'score': 70, 'tech': '中', 'script': '冒充领导熟人话术', 'member': '5-8人', 'amount': 975600},
    ]

    gang_objects = []
    gang_case_mapping = [
        list(range(0, 7)),    # 团伙1 -> 案件1-7 (冒充京东客服)
        list(range(7, 13)),   # 团伙2 -> 案件8-13 (冒充公检法)
        list(range(13, 18)),  # 团伙3 -> 案件14-18 (刷单返利)
        list(range(18, 22)),  # 团伙4 -> 案件19-22 (投资理财)
        list(range(22, 25)),  # 团伙5 -> 案件23-25 (冒充熟人)
    ]

    for gi, gd in enumerate(gang_data):
        gang_id = f"GANG{datetime.now().strftime('%Y%m%d')}{gi+1:03d}"
        gang = Gang(
            gang_id=gang_id, session_id=session_id,
            gang_name=gd['name'],
            risk_level=gd['level'], risk_label={'S':'极危','A':'高危','B':'中危'}[gd['level']],
            risk_type='danger' if gd['level'] in ['S','A'] else 'warning',
            threat_level=gd['level'],
            comprehensive_score=gd['score'], confidence=gd['score'] - random.randint(5, 10),
            member_count_estimate=gd['member'],
            tech_level=gd['tech'], script_type=gd['script'],
            total_cases=len(gang_case_mapping[gi]),
            total_amount=str(gd['amount']), total_amount_value=float(gd['amount']),
            description=f"{gd['name']}，威胁等级{gd['level']}级，成员{gd['member']}人，涉案金额约{gd['amount']}元",
            fingerprint=[gd['name'][:4], gd['script'][:6], f'{gd["level"]}级威胁'],
            steps=['引流', '话术洗脑', '诱导转账', '资金转移'],
            radar_data={'tech': 85, 'org': 80, 'anti': 75, 'harm': 90, 'spread': 70},
            created_at=datetime.now() - timedelta(days=random.randint(1, 45))
        )
        db.session.add(gang)
        gang_objects.append(gang)
    db.session.flush()

    # ---- 4. 建立 团伙-案件 关联 ----
    for gi, case_indices in enumerate(gang_case_mapping):
        for ci in case_indices:
            rel = GangCaseRelation(
                gang_id=gang_objects[gi].gang_id,
                case_id=case_objects[ci].case_id,
                similarity=round(random.uniform(0.6, 0.95), 2)
            )
            db.session.add(rel)

    # ---- 5. 注入资金流向数据 ----
    from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
    bank_accounts = [
        ("622202****1234", "工商银行", "621700****5678", "招商银行"),
        ("621790****9012", "建设银行", "621226****3456", "农业银行"),
        ("622848****7890", "中国银行", "621558****2345", "交通银行"),
        ("621700****6789", "招商银行", "622202****8901", "工商银行"),
        ("621226****4567", "农业银行", "621790****0123", "建设银行"),
    ]
    flow_records = []
    for i in range(15):
        case_obj = case_objects[i % len(case_objects)]
        src, src_bank, tgt, tgt_bank = bank_accounts[i % len(bank_accounts)]
        amount = round(random.uniform(5000, 150000), 2)
        flow = CapitalFlow(
            case_id=case_obj.case_id,
            source_account=src, target_account=tgt,
            bank_name=src_bank,
            amount=amount,
            transaction_time=datetime.now() - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23)),
            direction='out' if i % 3 != 0 else 'in',
            level=random.randint(1, 3),
            annotation=f"第{i+1}级资金流转"
        )
        db.session.add(flow)
        flow_records.append(flow)
    print(f"   资金流向: {len(flow_records)} 条")

    # ---- 6. 注入派单数据 ----
    depts = ["刑侦大队", "网安大队", "辖区派出所", "反诈中心", "经侦大队"]
    officers = ["张明", "李华", "王强", "赵刚", "刘伟"]
    statuses = ["pending", "signed", "completed"]
    dispatch_records = []
    for i in range(8):
        case_obj = case_objects[i % len(case_objects)]
        dispatch = DispatchOrder(
            alert_id=f"ALT202605{i+1:03d}",
            case_id=case_obj.case_id,
            assigned_dept=random.choice(depts),
            assigned_officer=random.choice(officers),
            status=random.choice(statuses),
            dispatch_time=datetime.now() - timedelta(days=random.randint(1, 15)),
            sign_time=datetime.now() - timedelta(days=random.randint(0, 10)),
            feedback="已处置完毕" if random.random() > 0.5 else "",
            deadline=datetime.now() + timedelta(days=random.randint(1, 7)),
            created_by=1
        )
        db.session.add(dispatch)
        dispatch_records.append(dispatch)
    print(f"   派单: {len(dispatch_records)} 条")

    # ---- 7. 注入重点人员数据 ----
    person_types = ["前科人员", "高危人员", "涉诈重点人", "两卡人员"]
    identities = ["430****1234", "420****5678", "410****9012", "440****3456", "450****7890"]
    phones = ["138****1234", "139****5678", "150****9012", "186****3456", "137****7890"]
    risk_level_map = {"S": "极危", "A": "高危", "B": "中危", "C": "低危"}
    person_records = []
    for i in range(10):
        rl = random.choice(["S", "A", "B", "C"])
        person = KeyPerson(
            name=["刘某", "张某", "王某", "李某", "赵某", "陈某", "周某", "吴某", "郑某", "何某"][i],
            id_number=identities[i % len(identities)],
            phone=phones[i % len(phones)],
            person_type=random.choice(person_types),
            risk_level=rl,
            risk_label=risk_level_map[rl],
            bank_account=f"6222{random.randint(100000,999999)}",
            address=f"湖北省武汉市{random.choice(['江岸区','武昌区','洪山区','江汉区','硚口区'])}某某小区",
            case_ids=[case_objects[i % len(case_objects)].case_id],
            notes=f"涉及{random.choice(['冒充客服','刷单返利','投资理财','冒充公检法'])}类诈骗，有前科记录"
        )
        db.session.add(person)
        person_records.append(person)
    print(f"   重点人员: {len(person_records)} 条")

    db.session.commit()
    print(f"✅ 演示数据注入完成!")
    print(f"   会话: {session_id}")
    print(f"   案件: {len(case_objects)} 条")
    print(f"   团伙: {len(gang_objects)} 个")
    print(f"   关联: {sum(len(x) for x in gang_case_mapping)} 条")