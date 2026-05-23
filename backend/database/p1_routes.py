from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database.p1_crud import (
    save_capital_flow, get_capital_flows, get_capital_flow_graph,
    create_dispatch, sign_dispatch, complete_dispatch,
    get_dispatch_orders, get_dispatch_by_id,
    save_key_person, get_key_persons, get_key_person_by_id,
    search_key_persons_by_phone_or_account, delete_key_person,
    collision_check
)
from database import db
from routes.deps import get_current_user

router = APIRouter()


# ========== Pydantic Schemas ==========

class CapitalFlowCreate(BaseModel):
    case_id: str
    source_account: str = ''
    target_account: str = ''
    bank_name: str = ''
    amount: float = 0.0
    transaction_time: Optional[datetime] = None
    direction: str = 'out'
    level: int = 1
    annotation: str = ''


class DispatchCreate(BaseModel):
    alert_id: str = ''
    case_id: str
    assigned_dept: str = ''
    assigned_officer: str = ''
    deadline: Optional[datetime] = None
    created_by: Optional[int] = None


class DispatchComplete(BaseModel):
    feedback: str


class KeyPersonCreate(BaseModel):
    name: str = ''
    id_number: str
    gender: str = ''
    age: str = ''
    phone: str = ''
    bank_account: str = ''
    address: str = ''
    risk_level: str = 'B'
    risk_label: str = '中风险'
    person_type: str = '前科人员'
    tags: list = []
    case_ids: list = []
    source: str = ''
    notes: str = ''


class CheckPersonsItem(BaseModel):
    name: str = ''
    phone: str = ''
    bank_account: str = ''
    id_number: str = ''


class CheckPersonsRequest(BaseModel):
    persons: list[CheckPersonsItem]


# ========== Capital Flow Routes ==========

@router.post('/api/capital/flows')
async def api_create_capital_flow(data: CapitalFlowCreate):
    try:
        result = save_capital_flow(data.dict())
        return {'success': True, 'flow': result}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


# ========== Seed Data ==========

@router.post('/api/seed')
async def api_seed_data(current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'admin':
        return JSONResponse(status_code=403, content={"success": False, "error": "仅管理员可执行数据注入"})
    try:
        from database.models import db as _db, Case, Gang, GangCaseRelation, AlertRecord
        from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
        import random
        from datetime import datetime, timedelta

        _db.session.query(GangCaseRelation).delete()
        _db.session.query(AlertRecord).delete()
        _db.session.query(CapitalFlow).delete()
        _db.session.query(DispatchOrder).delete()
        _db.session.query(KeyPerson).delete()
        _db.session.query(Case).delete()
        _db.session.query(Gang).delete()
        _db.session.commit()

        seed_cases = [
            {'case_id': 'CASE-2024-0001', 'title': '冒充电商客服诈骗案', 'scam_type': '冒充电商客服', 'risk_level': 'HIGH', 'risk_label': '高风险', 'risk_score': 85, 'victim_name': '张丽', 'victim_gender': '女', 'victim_age': 35, 'victim_phone': '138****6723', 'victim_job': '行政专员', 'victim_address': '广东省深圳市南山区', 'description': '### 案件定性\n\n1. 被害人张丽接到自称京东客服电话\n2. 对方称需关闭京东白条否则影响征信\n3. 被害人按要求转账至"安全账户"\n4. 涉案金额达23.6万元\n\n### 风险评估\n{"风险评估": "高风险", "诈骗手段": "冒充电商客服诱导转账", "涉案金额": 236000, "受害人群": "35岁职场女性"}', 'amount': '23.6万元', 'amount_value': 236000},
            {'case_id': 'CASE-2024-0002', 'title': '刷单返利诈骗案', 'scam_type': '刷单返利', 'risk_level': 'HIGH', 'risk_label': '高风险', 'risk_score': 82, 'victim_name': '李明', 'victim_gender': '男', 'victim_age': 28, 'victim_phone': '139****4532', 'victim_job': '外卖骑手', 'victim_address': '广东省广州市天河区', 'description': '### 案件定性\n\n1. 被害人李明被拉入刷单兼职群\n2. 前期小额返利取得信任\n3. 后期以"联单任务"为由诱骗大额投入\n4. 累计被骗18.2万元\n\n### 风险评估\n{"风险评估": "高风险", "诈骗手段": "虚假刷单返利", "涉案金额": 182000, "受害人群": "28岁男性务工人员"}', 'amount': '18.2万元', 'amount_value': 182000},
            {'case_id': 'CASE-2024-0003', 'title': '杀猪盘交友诈骗案', 'scam_type': '杀猪盘', 'risk_level': 'CRITICAL', 'risk_label': '极高风险', 'risk_score': 95, 'victim_name': '王芳', 'victim_gender': '女', 'victim_age': 42, 'victim_phone': '137****1098', 'victim_job': '财务主管', 'victim_address': '广东省珠海市香洲区', 'description': '### 案件定性\n\n1. 被害人王芳通过婚恋平台结识诈骗分子\n2. 建立感情后诱导投资虚假数字货币平台\n3. 前期可小额提现获取信任\n4. 最终被骗156万元\n\n### 风险评估\n{"风险评估": "极高风险", "诈骗手段": "杀猪盘诱导虚假投资", "涉案金额": 1560000, "受害人群": "42岁单身女性"}', 'amount': '156万元', 'amount_value': 1560000},
            {'case_id': 'CASE-2024-0004', 'title': '冒充公检法诈骗案', 'scam_type': '冒充公检法', 'risk_level': 'CRITICAL', 'risk_label': '极高风险', 'risk_score': 93, 'victim_name': '陈建国', 'victim_gender': '男', 'victim_age': 68, 'victim_phone': '136****7821', 'victim_job': '退休教师', 'victim_address': '广东省佛山市顺德区', 'description': '### 案件定性\n\n1. 被害人陈建国接到自称公安局电话\n2. 对方称其涉嫌洗钱需配合调查\n3. 要求将所有存款转入"安全账户"自证清白\n4. 被骗金额89万元\n\n### 风险评估\n{"风险评估": "极高风险", "诈骗手段": "冒充公检法恐吓转账", "涉案金额": 890000, "受害人群": "68岁退休人员"}', 'amount': '89万元', 'amount_value': 890000},
            {'case_id': 'CASE-2024-0005', 'title': '虚假投资理财诈骗案', 'scam_type': '虚假投资理财', 'risk_level': 'HIGH', 'risk_label': '高风险', 'risk_score': 88, 'victim_name': '赵雪梅', 'victim_gender': '女', 'victim_age': 45, 'victim_phone': '135****3467', 'victim_job': '个体商户', 'victim_address': '广东省东莞市长安镇', 'description': '### 案件定性\n\n1. 被害人赵雪梅被拉入股票交流群\n2. 群内"老师"推荐虚假外汇交易平台\n3. 初期盈利后追加投入\n4. 平台突然无法提现\n\n### 风险评估\n{"风险评估": "高风险", "诈骗手段": "虚假投资理财平台", "涉案金额": 520000, "受害人群": "45岁个体商户"}', 'amount': '52万元', 'amount_value': 520000},
            {'case_id': 'CASE-2024-0006', 'title': '网络贷款诈骗案', 'scam_type': '网络贷款', 'risk_level': 'MEDIUM', 'risk_label': '中风险', 'risk_score': 65, 'victim_name': '刘强', 'victim_gender': '男', 'victim_age': 33, 'victim_phone': '138****9012', 'victim_job': '快递员', 'victim_address': '广东省惠州市惠城区', 'description': '### 案件定性\n\n1. 被害人刘强收到贷款短信\n2. 下载虚假贷款APP后申请贷款\n3. 以"保证金""解冻费"为由多次要求转账\n4. 累计被骗8.5万元\n\n### 风险评估\n{"风险评估": "中风险", "诈骗手段": "虚假网络贷款诱导转账", "涉案金额": 85000, "受害人群": "33岁务工人员"}', 'amount': '8.5万元', 'amount_value': 85000},
            {'case_id': 'CASE-2024-0007', 'title': '冒充领导诈骗案', 'scam_type': '冒充领导熟人', 'risk_level': 'HIGH', 'risk_label': '高风险', 'risk_score': 80, 'victim_name': '周文涛', 'victim_gender': '男', 'victim_age': 39, 'victim_phone': '139****5678', 'victim_job': '公司会计', 'victim_address': '广东省中山市东区', 'description': '### 案件定性\n\n1. 被害人周文涛被拉入假冒公司工作群\n2. 群内"老板"要求紧急转账到指定账户\n3. 未经核实即转账\n4. 损失45万元\n\n### 风险评估\n{"风险评估": "高风险", "诈骗手段": "冒充公司领导诱导转账", "涉案金额": 450000, "受害人群": "39岁公司会计"}', 'amount': '45万元', 'amount_value': 450000},
            {'case_id': 'CASE-2024-0008', 'title': '虚假征信诈骗案', 'scam_type': '虚假征信', 'risk_level': 'MEDIUM', 'risk_label': '中风险', 'risk_score': 70, 'victim_name': '吴敏', 'victim_gender': '女', 'victim_age': 26, 'victim_phone': '137****2345', 'victim_job': '银行柜员', 'victim_address': '广东省江门市蓬江区', 'description': '### 案件定性\n\n1. 被害人吴敏接到自称支付宝客服电话\n2. 称需更新学生身份信息否则影响征信\n3. 引导下载会议APP进行屏幕共享\n4. 被骗金额12.3万元\n\n### 风险评估\n{"风险评估": "中风险", "诈骗手段": "虚假征信诱导屏幕共享", "涉案金额": 123000, "受害人群": "26岁年轻女性"}', 'amount': '12.3万元', 'amount_value': 123000},
            {'case_id': 'CASE-2024-0009', 'title': '虚假购物服务诈骗案', 'scam_type': '虚假购物服务', 'risk_level': 'MEDIUM', 'risk_label': '中风险', 'risk_score': 60, 'victim_name': '黄晓明', 'victim_gender': '男', 'victim_age': 22, 'victim_phone': '136****8901', 'victim_job': '大学生', 'victim_address': '广东省汕头市金平区', 'description': '### 案件定性\n\n1. 被害人黄晓明在二手平台看到低价手机\n2. 卖家要求私下交易可再优惠\n3. 付款后被拉黑\n4. 被骗金额1.2万元\n\n### 风险评估\n{"风险评估": "中风险", "诈骗手段": "虚假购物诱导私下交易", "涉案金额": 12000, "受害人群": "22岁大学生"}', 'amount': '1.2万元', 'amount_value': 12000},
            {'case_id': 'CASE-2024-0010', 'title': '刷单返利诈骗案-系列2', 'scam_type': '刷单返利', 'risk_level': 'HIGH', 'risk_label': '高风险', 'risk_score': 84, 'victim_name': '杨丽丽', 'victim_gender': '女', 'victim_age': 30, 'victim_phone': '135****6789', 'victim_job': '全职妈妈', 'victim_address': '广东省湛江市赤坎区', 'description': '### 案件定性\n\n1. 被害人杨丽丽在宝妈群看到兼职广告\n2. 下载刷单APP做任务赚佣金\n3. 充值升级VIP后才能提现\n4. 被骗金额15.8万元\n\n### 风险评估\n{"风险评估": "高风险", "诈骗手段": "刷单返利诱导充值升级", "涉案金额": 158000, "受害人群": "30岁全职妈妈"}', 'amount': '15.8万元', 'amount_value': 158000},
            {'case_id': 'CASE-2024-0011', 'title': '冒充客服退款诈骗案', 'scam_type': '冒充电商客服', 'risk_level': 'HIGH', 'risk_label': '高风险', 'risk_score': 80, 'victim_name': '马骏', 'victim_gender': '男', 'victim_age': 31, 'victim_phone': '138****3456', 'victim_job': '程序员', 'victim_address': '广东省深圳市宝安区', 'description': '### 案件定性\n\n1. 被害人马骏接到自称淘宝客服电话\n2. 称其购买的商品有质量问题需退款\n3. 引导开通备用金并转账"多余款项"\n4. 被骗金额7.6万元\n\n### 风险评估\n{"风险评估": "高风险", "诈骗手段": "冒充客服退款诈骗", "涉案金额": 76000, "受害人群": "31岁程序员"}', 'amount': '7.6万元', 'amount_value': 76000},
            {'case_id': 'CASE-2024-0012', 'title': '网络赌博诱导诈骗案', 'scam_type': '网络赌博', 'risk_level': 'CRITICAL', 'risk_label': '极高风险', 'risk_score': 91, 'victim_name': '孙大海', 'victim_gender': '男', 'victim_age': 52, 'victim_phone': '139****0123', 'victim_job': '企业主', 'victim_address': '广东省广州市番禺区', 'description': '### 案件定性\n\n1. 被害人孙大海被诱导进入网络赌博网站\n2. 前期小额赢钱可提现\n3. 后期大额投注全部亏损\n4. 被骗金额210万元\n\n### 风险评估\n{"风险评估": "极高风险", "诈骗手段": "网络赌博诱导大额投注", "涉案金额": 2100000, "受害人群": "52岁企业主"}', 'amount': '210万元', 'amount_value': 2100000},
            {'case_id': 'CASE-2024-0013', 'title': '虚假中奖诈骗案', 'scam_type': '虚假中奖', 'risk_level': 'LOW', 'risk_label': '低风险', 'risk_score': 40, 'victim_name': '钱芳芳', 'victim_gender': '女', 'victim_age': 55, 'victim_phone': '136****4567', 'victim_job': '退休工人', 'victim_address': '广东省茂名市茂南区', 'description': '### 案件定性\n\n1. 被害人钱芳芳收到中奖短信\n2. 对方要求先缴纳"个人所得税"\n3. 多次转账"手续费"后无法联系\n4. 被骗金额2.8万元\n\n### 风险评估\n{"风险评估": "低风险", "诈骗手段": "虚假中奖诱导缴纳税费", "涉案金额": 28000, "受害人群": "55岁退休人员"}', 'amount': '2.8万元', 'amount_value': 28000},
            {'case_id': 'CASE-2024-0014', 'title': '游戏账号交易诈骗案', 'scam_type': '游戏交易', 'risk_level': 'LOW', 'risk_label': '低风险', 'risk_score': 35, 'victim_name': '朱浩然', 'victim_gender': '男', 'victim_age': 18, 'victim_phone': '137****8901', 'victim_job': '高中学生', 'victim_address': '广东省清远市清城区', 'description': '### 案件定性\n\n1. 被害人朱浩然在游戏交易平台出售账号\n2. 买家称需通过指定平台交易\n3. 平台客服以"账户冻结"要求充值解冻\n4. 被骗金额0.6万元\n\n### 风险评估\n{"风险评估": "低风险", "诈骗手段": "游戏交易虚假平台诈骗", "涉案金额": 6000, "受害人群": "18岁学生"}', 'amount': '0.6万元', 'amount_value': 6000},
            {'case_id': 'CASE-2024-0015', 'title': '冒充公检法诈骗案-系列2', 'scam_type': '冒充公检法', 'risk_level': 'CRITICAL', 'risk_label': '极高风险', 'risk_score': 94, 'victim_name': '胡桂英', 'victim_gender': '女', 'victim_age': 72, 'victim_phone': '135****2345', 'victim_job': '退休医生', 'victim_address': '广东省广州市越秀区', 'description': '### 案件定性\n\n1. 被害人胡桂英接到自称检察院电话\n2. 对方称其涉嫌参与洗钱犯罪\n3. 发送"通缉令"图片恐吓\n4. 骗走养老金存款180万元\n\n### 风险评估\n{"风险评估": "极高风险", "诈骗手段": "冒充公检法伪造通缉令", "涉案金额": 1800000, "受害人群": "72岁独居老人"}', 'amount': '180万元', 'amount_value': 1800000},
        ]
        case_objs = []
        status_options = ['已立案', '已立案', '侦办中', '已结案', '已立案', '侦办中', '已立案', '已立案', '侦办中', '已结案', '已立案', '侦办中', '已立案', '已立案', '已结案']
        for i, c in enumerate(seed_cases):
            case = Case(
                case_id=c['case_id'], title=c['title'], scam_type=c['scam_type'],
                risk_level=c['risk_level'], risk_label=c['risk_label'], risk_score=c['risk_score'],
                risk_type='danger' if c['risk_level'] == 'CRITICAL' else ('warning' if c['risk_level'] == 'HIGH' else 'info'),
                victim_name=c['victim_name'], victim_gender=c['victim_gender'],
                victim_age=c['victim_age'], victim_phone=c['victim_phone'],
                victim_job=c['victim_job'], victim_address=c['victim_address'],
                description=c['description'], amount=c['amount'], amount_value=c['amount_value'],
                number=i + 1, status=status_options[i],
                created_at=datetime.now() - timedelta(days=random.randint(1, 90))
            )
            _db.session.add(case)
            case_objs.append(case)
        _db.session.commit()

        gangs_data = [
            {'gang_id': 'GANG-001', 'gang_name': '东南亚冒充客服团伙', 'risk_level': 'CRITICAL', 'comprehensive_score': 92,
             'fingerprint': '["冒充客服", "虚假征信", "屏幕共享", "安全账户", "京东白条"]', 'location': '柬埔寨/缅甸', 'scale': '12人', 'abilities': '{"技术": 85, "组织": 90, "反侦察": 80, "社会危害": 95}',
             'case_ids': ['CASE-2024-0001', 'CASE-2024-0011', 'CASE-2024-0008']},
            {'gang_id': 'GANG-002', 'gang_name': '虚假投资诈骗团伙', 'risk_level': 'CRITICAL', 'comprehensive_score': 90,
             'fingerprint': '["虚假投资", "高收益", "虚拟货币", "杀猪盘", "外汇平台"]', 'location': '菲律宾/马来西亚', 'scale': '18人', 'abilities': '{"技术": 80, "组织": 95, "反侦察": 85, "社会危害": 95}',
             'case_ids': ['CASE-2024-0003', 'CASE-2024-0005', 'CASE-2024-0012']},
            {'gang_id': 'GANG-003', 'gang_name': '冒充公检法诈骗团伙', 'risk_level': 'CRITICAL', 'comprehensive_score': 93,
             'fingerprint': '["冒充公检法", "通缉令", "安全账户", "洗钱", "配合调查"]', 'location': '老挝/泰国', 'scale': '9人', 'abilities': '{"技术": 75, "组织": 90, "反侦察": 90, "社会危害": 98}',
             'case_ids': ['CASE-2024-0004', 'CASE-2024-0015']},
            {'gang_id': 'GANG-004', 'gang_name': '刷单返利诈骗团伙', 'risk_level': 'HIGH', 'comprehensive_score': 78,
             'fingerprint': '["刷单返利", "兼职", "宝妈群", "联单任务", "VIP充值"]', 'location': '境内/福建', 'scale': '22人', 'abilities': '{"技术": 60, "组织": 75, "反侦察": 65, "社会危害": 80}',
             'case_ids': ['CASE-2024-0002', 'CASE-2024-0010']},
            {'gang_id': 'GANG-005', 'gang_name': '冒充领导财务诈骗团伙', 'risk_level': 'HIGH', 'comprehensive_score': 76,
             'fingerprint': '["冒充领导", "冒充老板", "紧急转账", "公司群", "会计出纳"]', 'location': '境内/广东', 'scale': '7人', 'abilities': '{"技术": 55, "组织": 80, "反侦察": 70, "社会危害": 85}',
             'case_ids': ['CASE-2024-0007']},
        ]
        gang_objs = []
        for g in gangs_data:
            gang = Gang(gang_id=g['gang_id'], gang_name=g['gang_name'], risk_level=g['risk_level'],
                        comprehensive_score=g['comprehensive_score'], fingerprint=g['fingerprint'])
            # location, scale, abilities not in Gang model - stored if needed later
            _db.session.add(gang)
            gang_objs.append(gang)
        _db.session.commit()

        for g in gangs_data:
            for cid in g['case_ids']:
                _db.session.add(GangCaseRelation(gang_id=g['gang_id'], case_id=cid))
        _db.session.commit()

        alert_types = ['高危预警', '预警提醒', '关注提示', '紧急预警', '高危预警', '预警提醒', '紧急预警', '关注提示']
        for i, c in enumerate(case_objs[:8]):
            alert = AlertRecord(alert_type=alert_types[i], case_id=c.case_id,
                                matched_case_id=c.case_id, matched_entities=[],
                                confidence=random.randint(60, 98),
                                created_at=datetime.now() - timedelta(days=random.randint(1, 30)))
            _db.session.add(alert)
        _db.session.commit()

        accounts = ['6222****1234', '6217****5678', '6228****9012', '6214****3456', '6221****7890',
                     '6230****2345', '6212****6789', '6226****0123']
        for i in range(12):
            flow = CapitalFlow(case_id=random.choice(seed_cases)['case_id'],
                               source_account=random.choice(accounts),
                               target_account=random.choice([a for a in accounts if a != accounts[i % 8]]),
                               amount=random.randint(1000, 500000), level=random.randint(1, 5),
                               annotation=random.choice(['境内转账', '境外转账', '境内转账', '第三方支付', '境外取现']))
            _db.session.add(flow)
        _db.session.commit()

        dispatch_statuses = ['pending', 'signed', 'completed']
        for i in range(8):
            dispatch = DispatchOrder(case_id=seed_cases[i]['case_id'],
                                     status=dispatch_statuses[i % 3],
                                     assigned_dept=random.choice(['南山分局', '宝安分局', '福田分局', '龙岗分局', '罗湖分局']),
                                     assigned_officer=random.choice(['张警官', '李警官', '王警官', '陈警官']),
                                     alert_id='ALT-'+str(seed_cases[i]['case_id']),
                                     dispatch_time=datetime.now() - timedelta(days=random.randint(1, 30)))
            _db.session.add(dispatch)
        _db.session.commit()

        key_persons_data = [
            {'name': '陈志强', 'phone': '138****1111', 'id_card': '4403**********1234', 'type': '前科人员',
             'risk_level': 'HIGH', 'tags': '["诈骗前科", "冒充公检法", "洗钱"]'},
            {'name': '李伟明', 'phone': '139****2222', 'id_card': '4401**********5678', 'type': '在逃人员',
             'risk_level': 'CRITICAL', 'tags': '["网上追逃", "电信诈骗", "组织偷渡"]'},
            {'name': '王丽红', 'phone': '137****3333', 'id_card': '4403**********9012', 'type': '高危人员',
             'risk_level': 'HIGH', 'tags': '["多次出境", "资金异常", "关联诈骗"]'},
            {'name': '张建辉', 'phone': '136****4444', 'id_card': '4419**********3456', 'type': '前科人员',
             'risk_level': 'MEDIUM', 'tags': '["帮信罪前科", "出售银行卡"]'},
            {'name': '刘美玲', 'phone': '135****5555', 'id_card': '4401**********7890', 'type': '高危人员',
             'risk_level': 'HIGH', 'tags': '["频繁出入境", "虚拟货币交易", "疑似洗钱"]'},
            {'name': '赵永刚', 'phone': '138****6666', 'id_card': '4403**********2345', 'type': '前科人员',
             'risk_level': 'MEDIUM', 'tags': '["诈骗前科", "网络赌博", "非法经营"]'},
            {'name': '周晓燕', 'phone': '139****7777', 'id_card': '4401**********6789', 'type': '在逃人员',
             'risk_level': 'CRITICAL', 'tags': '["网上追逃", "组织偷渡", "伪造证件"]'},
            {'name': '吴建国', 'phone': '137****8888', 'id_card': '4413**********0123', 'type': '高危人员',
             'risk_level': 'HIGH', 'tags': '["关联多个诈骗账号", "资金异常频繁"]'},
        ]
        for p in key_persons_data:
            person = KeyPerson(name=p['name'], phone=p['phone'], id_number=p['id_card'], person_type=p['type'],
                               risk_level=p['risk_level'], tags=p['tags'],
                               created_at=datetime.now() - timedelta(days=random.randint(1, 180)))
            _db.session.add(person)
        _db.session.commit()

        return {'success': True, 'message': '示例数据已加载',
                'counts': {'cases': len(seed_cases), 'gangs': len(gangs_data),
                           'alerts': 8, 'capital_flows': 12, 'dispatches': 8, 'key_persons': len(key_persons_data)}}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/capital/flows')
async def api_list_capital_flows(case_id: Optional[str] = Query(None)):
    try:
        flows = get_capital_flows(case_id)
        return {'success': True, 'flows': flows, 'total': len(flows)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/capital/graph/{case_id}')
async def api_capital_flow_graph(case_id: str):
    try:
        graph = get_capital_flow_graph(case_id)
        return {'success': True, 'graph': graph}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/capital/stats')
async def api_capital_flow_stats():
    try:
        from database.p1_models import CapitalFlow
        from sqlalchemy import func
        total_amount = db.session.query(func.sum(CapitalFlow.amount)).scalar() or 0
        total_accounts = db.session.query(func.count(func.distinct(CapitalFlow.source_account))).scalar() or 0
        max_level = db.session.query(func.max(CapitalFlow.level)).scalar() or 0
        overseas_count = db.session.query(func.count(CapitalFlow.id)).filter(CapitalFlow.annotation.ilike('%境外%')).scalar() or 0
        total_flows = db.session.query(func.count(CapitalFlow.id)).scalar() or 0
        overseas_pct = round(overseas_count / total_flows * 100) if total_flows > 0 else 0
        return {
            'success': True,
            'stats': {
                'total_amount': round(total_amount, 2),
                'total_accounts': total_accounts,
                'max_level': max_level,
                'overseas_pct': overseas_pct,
                'total_flows': total_flows
            }
        }
    except Exception as e:
        from fastapi.responses import JSONResponse as _JR
        return _JR(status_code=500, content={'success': False, 'error': str(e)})


# ========== Dispatch Routes ==========

@router.post('/api/dispatch/create')
async def api_create_dispatch(data: DispatchCreate):
    try:
        result = create_dispatch(data.dict())
        return {'success': True, 'dispatch': result}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.put('/api/dispatch/{dispatch_id}/sign')
async def api_sign_dispatch(dispatch_id: int):
    try:
        result = sign_dispatch(dispatch_id)
        return {'success': True, 'dispatch': result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.put('/api/dispatch/{dispatch_id}/complete')
async def api_complete_dispatch(dispatch_id: int, data: DispatchComplete):
    try:
        result = complete_dispatch(dispatch_id, data.feedback)
        return {'success': True, 'dispatch': result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/dispatch/list')
async def api_list_dispatch(status: Optional[str] = Query(None)):
    try:
        orders = get_dispatch_orders(status)
        return {'success': True, 'orders': orders, 'total': len(orders)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/dispatch/{dispatch_id}')
async def api_get_dispatch(dispatch_id: int):
    try:
        order = get_dispatch_by_id(dispatch_id)
        if order:
            return {'success': True, 'dispatch': order}
        return JSONResponse(status_code=404, content={'success': False, 'error': '派单不存在'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


# ========== Key Person Routes ==========

@router.post('/api/persons/key')
async def api_create_key_person(data: KeyPersonCreate):
    try:
        result = save_key_person(data.dict())
        return {'success': True, 'person': result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/persons/key')
async def api_list_key_persons(
    search: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    person_type: Optional[str] = Query(None)
):
    try:
        persons = get_key_persons(search, risk_level, person_type)
        return {'success': True, 'persons': persons, 'total': len(persons)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/persons/key/{person_id}')
async def api_get_key_person(person_id: int):
    try:
        person = get_key_person_by_id(person_id)
        if person:
            return {'success': True, 'person': person}
        return JSONResponse(status_code=404, content={'success': False, 'error': '重点人员不存在'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.delete('/api/persons/key/{person_id}')
async def api_delete_key_person(person_id: int):
    try:
        result = delete_key_person(person_id)
        return {'success': True, **result}
    except ValueError as e:
        return JSONResponse(status_code=404, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/persons/collision')
async def api_collision_check(
    phone: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    id_number: Optional[str] = Query(None)
):
    try:
        result = collision_check(phone, account, id_number)
        return {'success': True, **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


# ========== Intrusion Detection during analysis ==========

@router.post('/api/analyze/check-persons')
async def api_check_extracted_persons(data: CheckPersonsRequest):
    try:
        all_matches = []
        for person in data.persons:
            p = person.dict()
            result = collision_check(
                phone=p.get('phone'),
                account=p.get('bank_account'),
                id_number=p.get('id_number')
            )
            if result['matched']:
                all_matches.append({
                    'input_person': p,
                    'matches': result['matches']
                })

        return {
            'success': True,
            'has_match': len(all_matches) > 0,
            'results': all_matches,
            'total_checked': len(data.persons),
            'total_matched': len(all_matches)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})