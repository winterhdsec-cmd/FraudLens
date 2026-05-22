"""
FastAPI application for FraudLens.
Replaces the original Flask app.py with a modern ASGI architecture.
"""
import os
import sys
import json
import time
import uuid
import asyncio
import traceback
import threading
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from flask import Flask as _Flask
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), 'key.env')
load_dotenv(dotenv_path)

from database import db, init_db
from tools.response import logger

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "20051223")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")
DB_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

_flask_app = _Flask(__name__)
_flask_app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
_flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
_flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'charset': 'utf8mb4'},
    'pool_pre_ping': True,
    'pool_recycle': 3600
}
init_db(_flask_app)
_flask_app.app_context().push()

from database import db as _sqlalchemy_db
with _flask_app.app_context():
    _sqlalchemy_db.session.execute(_sqlalchemy_db.text("SET NAMES utf8mb4"))
    _sqlalchemy_db.session.execute(_sqlalchemy_db.text("SET CHARACTER SET utf8mb4"))
    _sqlalchemy_db.session.execute(_sqlalchemy_db.text("SET character_set_connection=utf8mb4"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("AI 反诈研判官系统 v3.0 (FastAPI) 启动")
    logger.info("=" * 60)
    from database.models import User
    from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', display_name='系统管理员', role='admin', department='反诈中心')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logger.info("默认管理员账号已创建 (admin/admin123)")
    try:
        from tools.engine import engine as _engine
        global fraud_engine
        fraud_engine = _engine
        logger.info("反诈引擎初始化成功")
    except Exception as e:
        logger.error(f"反诈引擎初始化失败: {e}")
        fraud_engine = None
    try:
        from tools.ocr import get_reader as _get_ocr_reader
        _get_ocr_reader()
        logger.info("EasyOCR 模型预热完成")
    except Exception as e:
        logger.warning(f"EasyOCR 预热跳过: {e}")
    try:
        from tools.embedding_utils import get_embedding_model as _get_bge
        _get_bge()
        logger.info("BGE 嵌入模型预热完成")
    except Exception as e:
        logger.warning(f"BGE 模型预热跳过: {e}")
    logger.info(f"数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info("=" * 60)

    try:
        from database.models import AlertRecord
        if AlertRecord.query.count() == 0:
            now = datetime.utcnow()
            demo_alerts_data = [
                ('phone_match', 'FC20260519001', 'FC20260519002', ['138****1234', '139****5678'], 0.85),
                ('bank_match', 'FC20260519007', 'FC20260519003', ['6222****1234'], 0.72),
                ('phone_match', 'FC20260519008', 'FC20260519009', ['150****9012'], 0.68),
                ('app_match', 'FC20260519010', 'FC20260519011', ['腾讯会议', '瞩目'], 0.91),
                ('ip_match', 'FC20260519014', 'FC20260519015', ['192.168.1.*'], 0.63),
                ('bank_match', 'FC20260519019', 'FC20260519020', ['6217****5678', '6228****9012'], 0.78),
                ('phone_match', 'FC20260519022', 'FC20260519023', ['137****7890'], 0.71),
                ('app_match', 'FC20260519004', 'FC20260519005', ['腾讯会议'], 0.80),
            ]
            for at, cid, mcid, entities, conf in demo_alerts_data:
                record = AlertRecord(
                    alert_type=at, case_id=cid, matched_case_id=mcid,
                    matched_entities=entities, confidence=conf, created_at=now
                )
                db.session.add(record)
            db.session.commit()
            logger.info(f"演示预警数据已注入: {len(demo_alerts_data)} 条")
            from tools.redis_utils import alert_store_set
            for record in AlertRecord.query.all():
                alert_store_set(record.id, record.to_dict())
            logger.info("预警数据已同步到 Redis")
        else:
            logger.info(f"预警数据已存在: {AlertRecord.query.count()} 条")
            from tools.redis_utils import alert_store_set
            for record in AlertRecord.query.all():
                alert_store_set(record.id, record.to_dict())
            logger.info("预警数据已同步到 Redis")
    except Exception as e:
        logger.warning(f"预警数据注入跳过: {e}")

    try:
        import random
        from database.models import Case as _Case
        _all_cases = _Case.query.all()
        if CapitalFlow.query.count() <= 2:
            for i in range(min(8, len(_all_cases))):
                c = _all_cases[i]
                flow = CapitalFlow(case_id=c.case_id,
                    source_account=f"6222{random.randint(100000,999999)}",
                    target_account=f"6217{random.randint(100000,999999)}",
                    bank_name=random.choice(["工商银行","建设银行","农业银行"]),
                    amount=round(random.uniform(5000, 150000), 2),
                    direction='out' if i % 3 != 0 else 'in', level=random.randint(1, 3))
                db.session.add(flow)
            logger.info("资金流向数据已注入")
        if DispatchOrder.query.count() <= 1:
            for i in range(min(6, len(_all_cases))):
                d = DispatchOrder(case_id=_all_cases[i].case_id,
                    assigned_dept=random.choice(["刑侦大队","网安大队","辖区派出所","反诈中心"]),
                    status=random.choice(["pending","signed","completed"]))
                db.session.add(d)
            logger.info("派单数据已注入")
        if KeyPerson.query.count() <= 1:
            for i in range(8):
                p = KeyPerson(name=["刘某","张某","王某","李某","赵某","陈某","周某","吴某"][i],
                    id_number=f"420{random.randint(100000,999999)}",
                    phone=f"138{random.randint(10000000,99999999)}",
                    person_type=random.choice(["前科人员","高危人员","涉诈重点人"]),
                    risk_level=random.choice(["S","A","B"]),
                    bank_account=f"6222{random.randint(100000,999999)}")
                db.session.add(p)
            db.session.commit()
            logger.info("重点人员数据已注入")
    except Exception as e:
        logger.warning(f"P1演示数据注入跳过: {e}")

    try:
        from database.models import Gang, GangCaseRelation
        existing_gang_case = set(r.case_id for r in GangCaseRelation.query.all())
        orphan_cases = [c for c in _all_cases if c.case_id not in existing_gang_case]
        if orphan_cases:
            created = 0
            name_counters = {}
            for c in orphan_cases:
                base = c.scam_type or '未知类型'
                name_counters[base] = name_counters.get(base, 0) + 1
                victim_name = c.victim_name or c.title or ''
                unique_name = f'{base}案{name_counters[base]}-{victim_name[:6]}' if victim_name else f'{base}案{name_counters[base]}'
                solo_gang = Gang(
                    gang_id=f'SOLO_{c.case_id}',
                    gang_name=unique_name,
                    risk_level=c.risk_level or 'C',
                    risk_label={'HIGH': '高风险', 'MEDIUM': '中风险', 'LOW': '低风险', 'UNKNOWN': '未知'}.get(c.risk_level, '低风险'),
                    risk_type={'HIGH': 'danger', 'MEDIUM': 'warning', 'LOW': 'info', 'UNKNOWN': 'info'}.get(c.risk_level, 'info'),
                    threat_level={'HIGH': 'S', 'MEDIUM': 'A', 'LOW': 'B', 'UNKNOWN': 'C'}.get(c.risk_level, 'C'),
                    comprehensive_score=c.risk_score or 0,
                    total_cases=1,
                    total_amount=c.amount or '0',
                    total_amount_value=float(c.amount_value or 0),
                    fingerprint=[c.scam_type or '未知类型', '独立案件'],
                    description=f'基于{c.scam_type or "未知"}诈骗手法识别的独立案件',
                )
                db.session.add(solo_gang)
                db.session.flush()
                rel = GangCaseRelation(gang_id=solo_gang.gang_id, case_id=c.case_id, similarity=1.0)
                db.session.add(rel)
                created += 1
            db.session.commit()
            logger.info(f"独立团伙创建完成: {created} 个")
    except Exception as e:
        logger.warning(f"独立团伙创建跳过: {e}")
        db.session.rollback()

    try:
        from database.models import Case as _CaseModel
        if _CaseModel.query.count() < 10:
            import random as _rd
            now = datetime.utcnow()
            _seed_cases = [
                {"title":"假冒京东客服征信诈骗案","victim":"王芳","amount":125800,"type":"冒充客服","desc":"接到自称京东客服电话，称其京东金条利率过高需注销，否则影响征信。对方引导下载瞩目APP并开启屏幕共享，以验证资金为由骗取转账。"},
                {"title":"注销京东金条诈骗案","victim":"李强","amount":89600,"type":"冒充客服","desc":"骗子冒充京东金融客服，称其开通了京东金条需注销。要求将所有资金转入银监会安全账户验证，承诺验证后返还。"},
                {"title":"京东白条利率调整诈骗","victim":"张丽","amount":234000,"type":"冒充客服","desc":"对方自称京东客服，称白条利率高于国家规定需调整。诱导下载腾讯会议开启共享屏幕，指导其在各网贷平台借款后转账。"},
                {"title":"冒充公检法洗钱案","victim":"周秀英","amount":458000,"type":"冒充公检法","desc":"接到自称某市公安局电话，称其涉嫌洗钱犯罪。要求配合调查并通过资金审查证明清白，将所有资金转入安全账户。"},
                {"title":"冒充检察院案件核查","victim":"吴建国","amount":289000,"type":"冒充公检法","desc":"骗子冒充检察院工作人员，称其涉及一起重大经济案件。通过伪造的逮捕令和冻结令恐吓受害人，诱导其转账。"},
                {"title":"刷单返利连环诈骗案","victim":"何小燕","amount":87600,"type":"刷单返利","desc":"在微信群看到刷单兼职广告，添加客服后开始做任务。前几单小额返利成功后，被诱导做大额任务，后无法提现。"},
                {"title":"抖音点赞刷单诈骗","victim":"宋玉兰","amount":34500,"type":"刷单返利","desc":"在抖音上看到点赞赚钱广告，下载指定APP后开始做任务。前期获得小额返利，后期被要求预付垫资后无法提现。"},
                {"title":"虚假投资理财平台诈骗","victim":"马晓东","amount":567000,"type":"投资理财","desc":"在社交平台认识陌生好友，推荐投资数字货币平台。前期小额盈利并成功提现，后追加投入大额资金，平台无法登录。"},
                {"title":"股票推荐杀猪盘","victim":"胡建军","amount":890000,"type":"投资理财","desc":"被拉入股票交流群，群内老师推荐某投资平台。初次投资盈利后追加投入，后发现平台无法提现，群也被解散。"},
                {"title":"冒充领导借款诈骗","victim":"杨国平","amount":280000,"type":"冒充熟人","desc":"接到冒充乡镇领导的微信好友申请，对方以需要转账但自己不方便操作为由，要求代转账。"},
                {"title":"冒充子女要学费诈骗","victim":"王秀兰","amount":45600,"type":"冒充熟人","desc":"接到冒充在外地上大学的儿子的电话，称学校需要缴纳培训费。因声音相似未怀疑，转账后联系儿子才发现被骗。"},
                {"title":"冒充天猫客服退款诈骗","victim":"林志强","amount":82300,"type":"冒充客服","desc":"接到冒充天猫客服电话，称其购买的商品存在质量问题可双倍退款。诱导添加QQ好友后发送钓鱼链接，填写银行卡信息后被转走余额。"},
                {"title":"冒充快递客服理赔诈骗","victim":"邓丽华","amount":45600,"type":"冒充客服","desc":"接到自称中通快递客服电话，称其快递丢失可理赔198元。要求下载佳信通APP并开启屏幕共享，指导在支付宝备用金操作。"},
                {"title":"冒充银行客服调额诈骗","victim":"郭建华","amount":128000,"type":"冒充客服","desc":"接到冒充招商银行客服电话，称可提升信用卡额度至20万。要求提供短信验证码和CVV码，随后信用卡被盗刷。"},
                {"title":"冒充公安涉黑诈骗","victim":"郑晓燕","amount":156700,"type":"冒充公检法","desc":"对方自称某地公安民警，称其账户涉嫌为黑社会组织洗钱。要求其配合制作笔录，并缴纳保证金到指定账户。"},
                {"title":"冒充法院传票诈骗","victim":"钱德明","amount":92300,"type":"冒充公检法","desc":"接到冒充法院的电话，称其有传票未领取，涉及合同诈骗案。要求缴纳担保金到法院指定账户。"},
                {"title":"刷单做任务连环诈骗","victim":"邹文强","amount":345000,"type":"刷单返利","desc":"在58同城看到高薪兼职信息，添加对方QQ后开始刷单。被诱导连做三单大额任务，每单垫付5-10万，完成后被告知系统冻结需继续充值解冻。"},
                {"title":"视频号点赞刷单诈骗","victim":"熊丽萍","amount":23400,"type":"刷单返利","desc":"在微信视频号看到点赞赚钱广告，点击链接下载百事通APP。完成点赞任务后获得小额返利，后被诱导购买VIP会员做高额任务。"},
                {"title":"期货投资诈骗","victim":"贺志明","amount":780000,"type":"投资理财","desc":"在微信认识自称期货分析师的人，被拉入期货交流群。群里每天发送盈利截图，诱导下载华信期货APP入金操作。前期盈利后追加投资，申请出金时平台要求缴纳20%保证金。"},
                {"title":"黄金投资诈骗","victim":"龚文强","amount":456000,"type":"投资理财","desc":"通过婚恋平台认识自称从事黄金交易的女友，推荐下载金鑫国际APP炒黄金。前期小额盈利可提现，后投入45.6万时平台显示爆仓无法操作。"},
                {"title":"冒充亲戚借钱诈骗","victim":"蔡丽华","amount":125000,"type":"冒充熟人","desc":"接到冒充在外地做生意的侄子的电话，称急需一笔货款周转。因声音相似未起疑心，通过银行柜台转账到指定账户，后联系真侄子发现被骗。"},
                {"title":"冒充朋友急事诈骗","victim":"丁建平","amount":67800,"type":"冒充熟人","desc":"收到冒充好友的微博私信，称在国外手机丢失无法使用银行卡，请求帮忙购买机票。转账到提供的账户后，联系好友本人发现账号被盗。"},
                {"title":"网贷保证金诈骗","victim":"沈玉兰","amount":25600,"type":"网络贷款","desc":"在网上搜索贷款信息后接到冒充贷款平台客服电话，称可提供10万无抵押贷款。要求先缴纳5%的保证金验证还款能力，转账后对方称流水不足需继续缴费。"},
                {"title":"网贷解冻费诈骗","victim":"黎志强","amount":48900,"type":"网络贷款","desc":"下载速易贷APP申请贷款5万元，平台显示放款成功但银行卡号填写错误导致冻结。客服要求缴纳解冻费和解绑费，多次转账后平台无法打开。"},
                {"title":"冒充公安协查诈骗","victim":"傅晓峰","amount":389000,"type":"冒充公检法","desc":"接到冒充武汉市刑侦支队电话，称其身份证被用于洗钱案。要求添加QQ视频做笔录，展示伪造的逮捕令和警官证，恐吓后要求转账到安全账户。"},
                {"title":"冒充检察院资金清查","victim":"白桂英","amount":512000,"type":"冒充公检法","desc":"接到冒充最高人民检察院工作人员电话，称其涉嫌一起非法集资案。要求登录伪造的最高检资金清查平台网站，输入银行卡号和密码后资金被转走。"},
                {"title":"快手点赞刷单诈骗","victim":"范晓东","amount":56700,"type":"刷单返利","desc":"在快手看到点赞赚钱广告，添加对方微信后被拉入任务群。前5单每单返利5元，后要求下载创益APP做联单任务，充值后无法提现。"},
                {"title":"公众号关注刷单诈骗","victim":"廖雪梅","amount":78900,"type":"刷单返利","desc":"在短信中看到关注公众号赚钱信息，添加客服后开始关注任务。前期获得返利89元，后被诱导做垫付任务，转账后客服失联。"},
                {"title":"原油投资诈骗","victim":"沈丽萍","amount":623000,"type":"投资理财","desc":"接到投资顾问电话推荐原油期货投资，承诺月收益30%。下载万利金融平台后入金操作，前两周账户盈利丰厚，月底申请提现时被告知账户异常需缴纳解冻费。"},
                {"title":"股票投资杀猪盘诈骗","victim":"肖建华","amount":912000,"type":"投资理财","desc":"被拉入股票交流群，群内有百余人。群主推荐某涨停板股票并要求统一在指定平台买入。大量资金入市后股票暴跌，平台关闭群聊解散。"},
                {"title":"冒充领导送礼诈骗","victim":"毛桂英","amount":185000,"type":"冒充熟人","desc":"接到冒充单位领导的电话，称需要给上级送礼但自己不方便出面，要求代转账。先后分两次转账到指定账户，后与领导本人核实发现被骗。"},
                {"title":"冒充同事借款诈骗","victim":"邱晓峰","amount":45600,"type":"冒充熟人","desc":"收到冒充公司同事的钉钉消息，称急需借钱周转。对方头像和姓名与同事一致，未电话核实直接转账，后发现同事账号被盗。"},
                {"title":"网贷刷流水诈骗","victim":"冯晓燕","amount":72300,"type":"网络贷款","desc":"接到贷款推销电话称可办理30万大额贷款，要求提供银行卡刷流水提高贷款额度。按对方指示向多个账户转账后，对方电话关机。"},
                {"title":"网贷提额诈骗","victim":"韦建华","amount":34500,"type":"网络贷款","desc":"收到冒充正规贷款平台的短信称可提升额度至50万，点击链接进入仿冒平台。填写资料后被告知需缴纳手续费和提额服务费，转账后平台无法访问。"},
                {"title":"冒充警方资金核查","victim":"林小红","amount":67800,"type":"冒充公检法","desc":"骗子冒充反诈中心民警，称其银行卡被用于电信诈骗，要求配合资金核查。下载指定APP后远程控制手机转走资金。"},
                {"title":"冒充公安出入境诈骗","victim":"黄大明","amount":345000,"type":"冒充公检法","desc":"对方冒充出入境管理局和公安民警，称其护照被用于非法入境，涉嫌重大犯罪。要求缴纳取保候审保证金。"},
                {"title":"冒充京东客服注销账户","victim":"陈刚","amount":56700,"type":"冒充客服","desc":"骗子声称京东账户存在异常需要注销，要求配合操作。通过共享屏幕获取银行卡信息，远程操作转走卡内余额。"},
                {"title":"冒充金融客服注销贷款","victim":"赵敏","amount":312000,"type":"冒充客服","desc":"对方自称京东金融客服，称其名下有多笔贷款需要注销。要求将资金转入指定账户进行流水验证，先后转账5笔。"},
                {"title":"刷单返利APP诈骗","victim":"金志明","amount":167800,"type":"刷单返利","desc":"通过陌生好友邀请下载淘客联盟APP，平台客服引导做刷单任务。前期成功提现300元，后做大额任务时提示操作失误需补单，多次转账后平台关闭。"},
                {"title":"刷单平台充值诈骗","victim":"魏小燕","amount":289000,"type":"刷单返利","desc":"被网友推荐下载星耀刷单平台，称充值越多返利越高。首次充值5000元返利600元并成功提现，随后充值10万元发现平台无法登录。"},
                {"title":"数字藏品投资诈骗","victim":"卢志远","amount":234000,"type":"投资理财","desc":"在社群中看到数字藏品投资机会，平台宣称每件藏品限量发行且可增值百倍。购买多件藏品后平台推出二级交易市场，挂单出售后资金无法提现。"},
                {"title":"虚拟货币挖矿诈骗","victim":"尹晓东","amount":567000,"type":"投资理财","desc":"在币圈社群认识好友推荐云挖矿项目，称购买矿机算力每日分红。投入巨资购买算力合约，前几个月正常分红后平台以系统升级为由停止运营。"},
                {"title":"冒充老师收费诈骗","victim":"顾志强","amount":29800,"type":"冒充熟人","desc":"收到冒充孩子班主任的QQ消息，称学校需缴纳补习费和资料费。对方发来支付宝收款码，扫码支付后联系班主任核实发现被骗。"},
                {"title":"冒充同学借钱诈骗","victim":"程小燕","amount":34500,"type":"冒充熟人","desc":"收到冒充初中同学的微信好友申请，通过后对方称家人生病急需用钱。视频通话仅3秒后挂断称信号不好，要求转账到银行卡，转账后对方失联。"},
                {"title":"冒充公安断卡行动诈骗","victim":"谭志强","amount":167000,"type":"冒充公检法","desc":"接到冒充深圳市公安局电话，称其银行卡涉嫌参与电信诈骗洗钱。要求下载安全防护APP并开启远程控制，手机被操控转走资金。"},
                {"title":"冒充网警反诈诈骗","victim":"崔丽华","amount":89400,"type":"冒充公检法","desc":"在网络上搜索反诈咨询电话，找到冒充网警的联系方式。对方称其账户有风险需将资金转入警方安全账户保管，转账后被拉黑。"},
                {"title":"冒充电信客服升级套餐诈骗","victim":"唐玉兰","amount":28600,"type":"冒充客服","desc":"接到冒充中国电信客服电话，称可以免费升级5G套餐并赠送礼品。要求提供身份证号和银行卡号进行登记，随后发现银行卡被盗刷。"},
                {"title":"冒充支付宝客服修改信息诈骗","victim":"姚国平","amount":94500,"type":"冒充客服","desc":"接到自称支付宝客服电话，称其个人信息过期需更新否则账户冻结。引导登录钓鱼网站填写支付宝账号密码和支付密码，账户内余额被转走。"},
                {"title":"微商刷单诈骗","victim":"侯桂芳","amount":45600,"type":"刷单返利","desc":"在朋友圈看到微商招刷手广告，添加后按要求下单但不付款，直接转账到对方微信。前两单返利后信任对方，第三单转账后对方拉黑。"},
                {"title":"刷单赚佣金诈骗","victim":"龙建华","amount":92300,"type":"刷单返利","desc":"收到兼职短信称刷单赚佣金日入300元，添加QQ后被拉入任务群。完成小单后获得佣金15元，后被引导做预付任务，通过手机银行转账后无法联系客服。"},
                {"title":"基金投资诈骗","victim":"倪桂芳","amount":345000,"type":"投资理财","desc":"在抖音看到基金投资广告，添加对方微信后被拉入投资群。群内老师推荐购买某私募基金产品，声称年化收益35%。转账后收到电子合同，三个月后发现平台失联。"},
                {"title":"虚拟货币投资诈骗","victim":"彭丽华","amount":234000,"type":"投资理财","desc":"通过婚恋网站认识对象，对方称有虚拟货币内幕消息。引导在某平台投资USDT，前期盈利后期无法提现。"},
                {"title":"冒充公司老板诈骗财务","victim":"张敏","amount":650000,"type":"冒充熟人","desc":"公司财务接到冒充老板的QQ消息，称急需支付一笔合同款。因头像和昵称一致未核实，通过公司对公账户转账。"},
                {"title":"冒充公安社保诈骗","victim":"汤美琴","amount":278000,"type":"冒充公检法","desc":"接到冒充上海社保局电话，称其社保卡在上海异地报销涉嫌骗保。转接冒充公安的电话后，被要求缴纳取保候审保证金。"},
                {"title":"冒充经侦资金核查诈骗","victim":"雷玉兰","amount":198000,"type":"冒充公检法","desc":"接到冒充经济侦查支队民警电话，称其银行卡被犯罪团伙利用需进行资金核查。要求将所有存款集中到一张卡并告知短信验证码，资金随即被转走。"},
                {"title":"冒充公安洗钱案协查诈骗","victim":"万晓燕","amount":445000,"type":"冒充公检法","desc":"接到冒充北京市公安局电话，称其账户涉嫌为境外诈骗团伙洗钱。要求下载公安远程办案APP并输入银行卡信息，卡内资金被分批转至多个境外账户。"},
                {"title":"冒充国安调查诈骗","victim":"康建华","amount":567000,"type":"冒充公检法","desc":"接到冒充国家安全部门电话，称其涉嫌泄露国家机密需配合调查。要求购买新手机并保持通话不间断，诱导在多个网贷平台借款后转账到安全账户。"},
                {"title":"抖音商城会员取消诈骗","victim":"曾志伟","amount":38900,"type":"冒充客服","desc":"接到冒充抖音商城客服电话，称其账号被误开通了直播会员每月扣费500元。要求转账到指定账户进行身份验证才能取消。"},
                {"title":"京东金条年费取消诈骗","victim":"孙伟","amount":45600,"type":"冒充客服","desc":"骗子谎称京东金条产生年费需取消，否则影响征信。要求下载第三方会议软件并共享屏幕，通过远程操作转走资金。"},
                {"title":"冒充淘宝客服退货诈骗","victim":"潘美琴","amount":156700,"type":"冒充客服","desc":"接到冒充淘宝客服电话，称其购买的护肤品有质量问题可退一赔三。诱导下载钉钉开启屏幕共享，以退款需要资金验证为由骗取转账。"},
                {"title":"冒充拼多多客服退款诈骗","victim":"苏建军","amount":51200,"type":"冒充客服","desc":"接到自称拼多多商家电话，称其购买的商品缺货可退款。要求添加微信并扫描二维码填写退款信息，银行卡随即被盗刷。"},
                {"title":"冒充保险客服退保诈骗","victim":"董小燕","amount":198000,"type":"冒充客服","desc":"接到冒充平安保险客服电话，称其投保的保险产品利率过高可办理退保。诱导下载全视通APP进行视频面签，骗取银行卡信息和验证码。"},
                {"title":"冒充携程客服取消订单诈骗","victim":"梁晓峰","amount":73400,"type":"冒充客服","desc":"收到冒充携程的短信称酒店订单异常需取消，拨打客服热线后对方要求提供银行卡号进行退款验证。按指示操作后卡内资金被转走。"},
                {"title":"冒充微信客服百万保障诈骗","victim":"罗永明","amount":67500,"type":"冒充客服","desc":"接到自称微信客服电话，称其开通了微信百万保障服务即将扣费。要求下载远程协助APP取消服务，远程操控手机转走资金。"},
                {"title":"刷单垫付诈骗","victim":"陶国平","amount":67800,"type":"刷单返利","desc":"在兼职猫平台看到垫付刷单招聘，添加对方微信后开始做任务。垫付第一单返利后连续垫付多单，对方失联。"},
                {"title":"刷单连环任务诈骗","victim":"姜丽华","amount":156000,"type":"刷单返利","desc":"在豆瓣看到兼职招聘信息，添加对方QQ后下载飞讯APP。被分配连环任务需完成多单才能结算，每单垫付金额递增，完成后平台提示系统维护无法提现。"},
                {"title":"购物平台刷信誉诈骗","victim":"许志强","amount":67800,"type":"刷单返利","desc":"冒充电商平台客服邀请刷信誉，称可返利15%。前期小额获利后，被诱导做大额刷单任务，最终被骗。"},
                {"title":"兼职刷单连环套","victim":"曹雪梅","amount":234500,"type":"刷单返利","desc":"在网络招聘平台看到高薪兼职，添加对方后开始刷单。被诱导进入VIP群做联单任务，投入大量资金后平台关闭。"},
                {"title":"外汇投资骗局","victim":"余志远","amount":445000,"type":"投资理财","desc":"接到投资顾问电话推荐外汇投资，承诺月收益20%。下载MT4平台后投入资金，盈利后申请出金被拒。"},
                {"title":"电影投资诈骗","victim":"蒋雪梅","amount":890000,"type":"投资理财","desc":"接到影视投资公司电话，推荐投资即将上映的大片，声称票房收益可达3倍。签订电子合同后转账，电影上映后票房惨淡公司失联。"},
                {"title":"冒充亲戚借钱诈骗","victim":"蔡丽华","amount":125000,"type":"冒充熟人","desc":"接到冒充在外地做生意的亲戚的电话，称急需资金周转。声音相似未起疑心，转账后联系本人发现被骗。"},
                {"title":"冒充熟人代购诈骗","victim":"丁建华","amount":67800,"type":"冒充熟人","desc":"收到冒充朋友的私信，称急需帮忙代购物品。转账后联系朋友发现账号被盗。"},
                {"title":"冒充法院执行诈骗","victim":"严志伟","amount":134500,"type":"冒充公检法","desc":"收到冒充法院的执行通知书短信，称其有案件进入执行阶段需立即缴纳执行款。按预留电话联系后，对方要求将执行款转入法院对公账户。"},
                {"title":"冒充公安洗钱案调查","victim":"万晓燕","amount":445000,"type":"冒充公检法","desc":"接到冒充北京市公安局电话，称其账户涉嫌为境外诈骗团伙洗钱。要求下载远程办案APP并输入银行卡信息。"},
                {"title":"冒充电信客服升级套餐","victim":"唐玉兰","amount":28600,"type":"冒充客服","desc":"接到冒充中国电信客服电话，称可免费升级5G套餐。要求提供身份证号登记，后银行卡被盗刷。"},
                {"title":"京东金条征信修复诈骗","victim":"刘洋","amount":178900,"type":"冒充客服","desc":"冒充京东客服以征信修复为由，诱导受害人下载指定APP并开启屏幕共享。共骗取受害人通过银行转账和网贷借款方式转出资金。"},
            ]
            session_id = f'auto_seed_{now.strftime("%Y%m%d_%H%M%S")}'
            for i, cd in enumerate(_seed_cases):
                risk_score = _rd.randint(65, 95)
                risk_level = 'HIGH' if risk_score >= 85 else 'MEDIUM' if risk_score >= 70 else 'LOW'
                case = _CaseModel(
                    case_id=f"FC{now.strftime('%Y%m%d')}{i+1:03d}",
                    session_id=session_id, title=cd['title'],
                    scam_type=cd['type'],
                    risk_level=risk_level,
                    risk_label={'HIGH':'高风险','MEDIUM':'中风险','LOW':'低风险'}.get(risk_level,''),
                    risk_type={'HIGH':'danger','MEDIUM':'warning','LOW':'info'}.get(risk_level,''),
                    risk_score=risk_score,
                    victim_name=cd['victim'],
                    victim_age=str(_rd.randint(22, 65)),
                    victim_gender='男' if _rd.random() > 0.5 else '女',
                    amount=str(cd['amount']), amount_value=float(cd['amount']),
                    description=cd['desc'],
                    status='已立案', source='文本',
                    keywords=[cd['type'], '诈骗', '转账'],
                    created_at=now - timedelta(days=_rd.randint(1, 60), hours=_rd.randint(0, 23))
                )
                db.session.add(case)
            db.session.commit()
            logger.info(f"✅ 演示案件数据注入成功: {len(_seed_cases)} 条")
    except Exception as e:
        logger.warning(f"演示案件数据注入跳过: {e}")

    yield
    logger.info("服务关闭")


app = FastAPI(title="FraudLens AI 反诈研判官系统", version="3.0", lifespan=lifespan)

from database.p1_routes import router as p1_router
app.include_router(p1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "type": type(exc).__name__}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

from routes.auth import router as auth_router
from routes.cases import router as cases_router
from routes.gangs import router as gangs_router
from routes.sessions import router as sessions_router
from routes.alerts import router as alerts_router
from routes.dashboard import router as dashboard_router
from routes.searches import router as searches_router
from routes.reports import router as reports_router
from routes.merges import router as merges_router
from routes.files import router as files_router
from routes.system import router as system_router

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(gangs_router)
app.include_router(sessions_router)
app.include_router(alerts_router)
app.include_router(dashboard_router)
app.include_router(searches_router)
app.include_router(reports_router)
app.include_router(merges_router)
app.include_router(files_router)
app.include_router(system_router)

if __name__ == '__main__':
    import uvicorn
    logger.info("=" * 60)
    logger.info("AI 反诈研判官系统 v3.0 (FastAPI)")
    logger.info("=" * 60)
    logger.info("   POST /agent-analyze   (智能研判分析)")
    logger.info("   GET  /health          (健康检查)")
    logger.info("   GET  /api/cases       (案件列表)")
    logger.info("   WS   /ws/{session_id} (实时进度)")
    logger.info("=" * 60)
    uvicorn.run(app, host='0.0.0.0', port=5003)