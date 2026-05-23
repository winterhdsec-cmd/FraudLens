"""
FraudLens 全面种子数据注入脚本
================================================================
注入内容概览:
  1. 分析会话 (AnalysisSession): 1 条
  2. 诈骗案件 (Case): 75 条（覆盖6大诈骗类型）
  3. 犯罪团伙 (Gang): 11 个（5个主团伙 + 6个按类型独立团伙）
  4. 团伙-案件关联 (GangCaseRelation): 75 条
  5. 资金流向 (CapitalFlow): ~300 条（每案3-5条，含完整银行信息）
  6. 派单记录 (DispatchOrder): 75 条（每案1条，覆盖各级执法部门）
  7. 重点人员 (KeyPerson): 25 条（含前科人员、两卡人员、涉诈重点人等）

案件类型分布:
  - 冒充客服:     19 条 (索引 0-6, 25-36)
  - 冒充公检法:   16 条 (索引 7-12, 47-56)
  - 刷单返利:     15 条 (索引 13-17, 37-46)
  - 投资理财:     12 条 (索引 18-21, 57-64)
  - 冒充熟人:      9 条 (索引 22-24, 65-70)
  - 网络贷款:      4 条 (索引 71-74)

团伙结构:
  - Gang 1:  京东客服诈骗团伙    (S级, 7案, 冒充客服,     索引0-6)
  - Gang 2:  公检法冒充团伙      (A级, 6案, 冒充公检法,   索引7-12)
  - Gang 3:  刷单返利团伙        (B级, 5案, 刷单返利,     索引13-17)
  - Gang 4:  虚假投资理财团伙    (A级, 4案, 投资理财,     索引18-21)
  - Gang 5:  冒充熟人诈骗团伙    (B级, 3案, 冒充熟人,     索引22-24)
  - Gang 6:  冒充客服独立团伙    (A级, 12案, 冒充客服,    索引25-36)
  - Gang 7:  刷单返利独立团伙    (B级, 10案, 刷单返利,    索引37-46)
  - Gang 8:  冒充公检法独立团伙  (A级, 10案, 冒充公检法,  索引47-56)
  - Gang 9:  投资理财独立团伙    (A级, 8案,  投资理财,    索引57-64)
  - Gang 10: 冒充熟人独立团伙    (B级, 6案,  冒充熟人,    索引65-70)
  - Gang 11: 网络贷款独立团伙    (C级, 4案,  网络贷款,    索引71-74)

资金流向设计: 每案3-5条资金流转记录，模拟受害人资金经多层账户洗转
派单设计:     每案1条派单记录，覆盖刑侦、网安、派出所、反诈中心、经侦
重点人员:     25人覆盖前科人员/高危人员/涉诈重点人/两卡人员四种类型

数据库: mysql+pymysql://root:20051223@localhost:3306/fraudlens?charset=utf8mb4
================================================================
"""
import sys, os, uuid, json
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db, init_db
from flask import Flask as _Flask
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'key.env'))

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fraudlens")
DB_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
_flask_app = _Flask(__name__)
_flask_app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
_flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
init_db(_flask_app)

with _flask_app.app_context():
    from database.models import Case, Gang, GangCaseRelation, AnalysisSession
    from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson

    # ---- 1. 创建分析会话 ----
    session_id = 'demo_session_' + datetime.now().strftime('%Y%m%d')
    existing = AnalysisSession.query.filter_by(session_id=session_id).first()
    if existing:
        print("⚠️ 演示数据已存在，跳过")
        sys.exit(0)

    sess = AnalysisSession(
        session_id=session_id,
        status='completed',
        total_cases=75,
        total_gangs=11,
        raw_input={'source': 'demo_data'},
        processing_info={'processing_time_ms': 12000, 'model': 'deepseek-v4-flash'}
    )
    db.session.add(sess)
    db.session.flush()

    # ---- 2. 注入75条案情 ----
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

        # ===== 新增50条独立案件（不归属任何现有团伙） =====

        # --- 冒充客服 (12条) ---
        {"title": "冒充天猫客服退款诈骗案", "victim": "林志强", "amount": 82300, "type": "冒充客服", "desc": "受害人接到+861501234567来电，对方自称天猫商城客服，称其购买的商品存在质量问题可双倍退款。诱导添加QQ好友后发送钓鱼链接，填写银行卡信息后被转走卡内余额。"},
        {"title": "冒充快递客服理赔诈骗案", "victim": "邓丽华", "amount": 45600, "type": "冒充客服", "desc": "接到自称中通快递客服电话，称其快递丢失可理赔198元。要求下载'佳信通'APP并开启屏幕共享，指导在支付宝备用金操作，以退款通道关闭为由骗取转账。"},
        {"title": "冒充银行客服调额诈骗案", "victim": "郭建华", "amount": 128000, "type": "冒充客服", "desc": "接到+860211234567冒充招商银行客服电话，称可提升信用卡额度至20万。要求提供短信验证码和CVV码，随后信用卡被盗刷多笔。"},
        {"title": "冒充微信客服百万保障诈骗案", "victim": "罗永明", "amount": 67500, "type": "冒充客服", "desc": "接到自称微信客服电话，称其开通了微信百万保障服务即将扣费。要求下载'远程协助'APP取消服务，远程操控手机转走资金。"},
        {"title": "冒充航空公司退票诈骗案", "victim": "何桂英", "amount": 234000, "type": "冒充客服", "desc": "收到冒充南方航空的短信称航班取消可退票，拨打预留电话后对方要求提供银行卡号和验证码进行退票验证。随后卡内23.4万被分批转走。"},
        {"title": "冒充抖音客服取消会员诈骗案", "victim": "曾志伟", "amount": 38900, "type": "冒充客服", "desc": "接到+861771234568来电，对方自称抖音商城客服，称其账号被误开通了直播会员每月扣费500元。要求转账到指定账户进行身份验证才能取消。"},
        {"title": "冒充淘宝客服退货诈骗案", "victim": "潘美琴", "amount": 156700, "type": "冒充客服", "desc": "接到冒充淘宝客服电话，称其购买的护肤品有质量问题可退一赔三。诱导下载'钉钉'开启屏幕共享，以退款需要资金验证为由骗取转账。"},
        {"title": "冒充拼多多客服退款诈骗案", "victim": "苏建军", "amount": 51200, "type": "冒充客服", "desc": "接到自称拼多多商家电话，称其购买的商品缺货可退款。要求添加微信并扫描二维码填写退款信息，银行卡随即被盗刷。"},
        {"title": "冒充保险客服退保诈骗案", "victim": "董小燕", "amount": 198000, "type": "冒充客服", "desc": "接到+860108765432冒充平安保险客服电话，称其投保的保险产品利率过高可办理退保。诱导下载'全视通'APP进行视频面签，骗取银行卡信息和验证码。"},
        {"title": "冒充携程客服取消订单诈骗案", "victim": "梁晓峰", "amount": 73400, "type": "冒充客服", "desc": "收到冒充携程的短信称酒店订单异常需取消，拨打客服热线后对方要求提供银行卡号进行退款验证。按指示操作后卡内7.3万元被转走。"},
        {"title": "冒充电信客服升级套餐诈骗案", "victim": "唐玉兰", "amount": 28600, "type": "冒充客服", "desc": "接到+860201234569冒充中国电信客服电话，称可以免费升级5G套餐并赠送礼品。要求提供身份证号和银行卡号进行登记，随后发现银行卡被盗刷。"},
        {"title": "冒充支付宝客服修改信息诈骗案", "victim": "姚国平", "amount": 94500, "type": "冒充客服", "desc": "接到自称支付宝客服电话，称其个人信息过期需更新否则账户冻结。引导登录钓鱼网站填写支付宝账号密码和支付密码，账户内余额被转走。"},

        # --- 刷单返利 (10条) ---
        {"title": "快手点赞刷单诈骗案", "victim": "范晓东", "amount": 56700, "type": "刷单返利", "desc": "在快手看到点赞赚钱广告，添加对方微信后被拉入任务群。前5单每单返利5元，后要求下载'创益'APP做联单任务，充值后无法提现。"},
        {"title": "公众号关注刷单诈骗案", "victim": "廖雪梅", "amount": 78900, "type": "刷单返利", "desc": "在短信中看到关注公众号赚钱信息，添加客服后开始关注任务。前期获得返利89元，后被诱导做垫付任务，转账后客服失联。"},
        {"title": "刷单做任务连环诈骗案", "victim": "邹文强", "amount": 345000, "type": "刷单返利", "desc": "在58同城看到高薪兼职信息，添加对方QQ后开始刷单。被诱导连做三单大额任务，每单垫付5-10万，完成后被告知系统冻结需继续充值解冻。"},
        {"title": "视频号点赞刷单诈骗案", "victim": "熊丽萍", "amount": 23400, "type": "刷单返利", "desc": "在微信视频号看到点赞赚钱广告，点击链接下载'百事通'APP。完成点赞任务后获得小额返利，后被诱导购买平台VIP会员做高额任务，充值后发现被骗。"},
        {"title": "刷单返利APP诈骗案", "victim": "金志明", "amount": 167800, "type": "刷单返利", "desc": "通过陌生好友邀请下载'淘客联盟'APP，平台客服引导做刷单任务。前期成功提现300元，后做大额任务时提示操作失误需补单，多次转账后平台关闭。"},
        {"title": "微商刷单诈骗案", "victim": "侯桂芳", "amount": 45600, "type": "刷单返利", "desc": "在朋友圈看到微商招刷手广告，添加后按要求下单但不付款，直接转账到对方微信。前两单返利后信任对方，第三单转账后对方拉黑。"},
        {"title": "刷单赚佣金诈骗案", "victim": "龙建华", "amount": 92300, "type": "刷单返利", "desc": "收到兼职短信称刷单赚佣金日入300元，添加QQ后被拉入任务群。完成小单后获得佣金15元，后被引导做预付任务，通过手机银行转账后无法联系客服。"},
        {"title": "刷单平台充值诈骗案", "victim": "魏小燕", "amount": 289000, "type": "刷单返利", "desc": "被网友推荐下载'星耀'刷单平台，称充值越多返利越高。首次充值5000元返利600元并成功提现，随后充值10万元发现平台无法登录。"},
        {"title": "刷单垫付诈骗案", "victim": "陶国平", "amount": 67800, "type": "刷单返利", "desc": "在兼职猫平台看到垫付刷单招聘，添加对方微信后开始做任务。垫付第一单2000元返利400元，之后连续垫付三单共计6.78万元，对方失联。"},
        {"title": "刷单连环任务诈骗案", "victim": "姜丽华", "amount": 156000, "type": "刷单返利", "desc": "在豆瓣看到兼职招聘信息，添加对方QQ后下载'飞讯'APP。被分配连环任务需完成6单才能结算，每单垫付金额递增，完成6单后平台提示系统维护无法提现。"},

        # --- 冒充公检法 (10条) ---
        {"title": "冒充公安协查诈骗案", "victim": "傅晓峰", "amount": 389000, "type": "冒充公检法", "desc": "接到+862011234567冒充武汉市刑侦支队电话，称其身份证被用于洗钱案。要求添加QQ视频做笔录，展示伪造的逮捕令和警官证，恐吓后要求转账到安全账户。"},
        {"title": "冒充检察院资金清查诈骗案", "victim": "白桂英", "amount": 512000, "type": "冒充公检法", "desc": "接到冒充最高人民检察院工作人员电话，称其涉嫌一起非法集资案。要求登录伪造的'最高检资金清查平台'网站，输入银行卡号和密码后资金被转走。"},
        {"title": "冒充公安断卡行动诈骗案", "victim": "谭志强", "amount": 167000, "type": "冒充公检法", "desc": "接到+860201234568冒充深圳市公安局电话，称其银行卡涉嫌参与电信诈骗洗钱。要求下载'安全防护'APP并开启远程控制，手机被操控转走资金。"},
        {"title": "冒充网警反诈诈骗案", "victim": "崔丽华", "amount": 89400, "type": "冒充公检法", "desc": "在网络上搜索反诈咨询电话，找到冒充网警的联系方式。对方称其账户有风险需将资金转入警方安全账户保管，转账后被拉黑。"},
        {"title": "冒充刑警调查诈骗案", "victim": "薛建平", "amount": 723000, "type": "冒充公检法", "desc": "接到冒充某地刑警队电话，称其涉及一起重大命案需协助调查。通过视频展示虚假办案现场和通缉令，以调查期间资产冻结为由要求将所有资金转入指定账户。"},
        {"title": "冒充公安社保诈骗案", "victim": "汤美琴", "amount": 278000, "type": "冒充公检法", "desc": "接到+862112345678冒充上海社保局电话，称其社保卡在上海异地报销涉嫌骗保。转接冒充公安的电话后，被要求缴纳取保候审保证金到指定账户。"},
        {"title": "冒充法院执行诈骗案", "victim": "严志伟", "amount": 134500, "type": "冒充公检法", "desc": "收到冒充法院的执行通知书短信，称其有案件进入执行阶段需立即缴纳执行款。按短信预留电话联系后，对方要求将执行款转入'法院对公账户'。"},
        {"title": "冒充公安洗钱案协查诈骗案", "victim": "万晓燕", "amount": 445000, "type": "冒充公检法", "desc": "接到+860101234567冒充北京市公安局电话，称其账户涉嫌为境外诈骗团伙洗钱。要求下载'公安远程办案'APP并输入银行卡信息，卡内资金被分批转至多个境外账户。"},
        {"title": "冒充国安调查诈骗案", "victim": "康建华", "amount": 567000, "type": "冒充公检法", "desc": "接到冒充国家安全部门电话，称其涉嫌泄露国家机密需配合调查。要求购买新手机并保持通话不间断，诱导在多个网贷平台借款后转账到'安全账户'。"},
        {"title": "冒充经侦资金核查诈骗案", "victim": "雷玉兰", "amount": 198000, "type": "冒充公检法", "desc": "接到冒充经济侦查支队民警电话，称其银行卡被犯罪团伙利用需进行资金核查。要求将所有存款集中到一张卡并告知短信验证码，资金随即被转走。"},

        # --- 投资理财 (8条) ---
        {"title": "期货投资诈骗案", "victim": "贺志明", "amount": 780000, "type": "投资理财", "desc": "在微信认识自称期货分析师的人，被拉入期货交流群。群里每天发送盈利截图，诱导下载'华信期货'APP入金操作。前期盈利后追加投资，申请出金时平台要求缴纳20%保证金。"},
        {"title": "基金投资诈骗案", "victim": "倪桂芳", "amount": 345000, "type": "投资理财", "desc": "在抖音看到基金投资广告，添加对方微信后被拉入投资群。群内老师推荐购买某私募基金产品，声称年化收益35%。转账后收到电子合同，三个月后发现平台失联。"},
        {"title": "黄金投资诈骗案", "victim": "龚文强", "amount": 456000, "type": "投资理财", "desc": "通过婚恋平台认识自称从事黄金交易的女友，推荐下载'金鑫国际'APP炒黄金。前期小额盈利可提现，后投入45.6万时平台显示爆仓无法操作。"},
        {"title": "原油投资诈骗案", "victim": "沈丽萍", "amount": 623000, "type": "投资理财", "desc": "接到投资顾问电话推荐原油期货投资，承诺月收益30%。下载'万利金融'平台后入金操作，前两周账户盈利丰厚，月底申请提现时被告知账户异常需缴纳解冻费。"},
        {"title": "股票投资杀猪盘诈骗案", "victim": "肖建华", "amount": 912000, "type": "投资理财", "desc": "被拉入股票交流群，群内有百余人。群主推荐某'涨停板'股票并要求统一在指定平台买入。大量资金入市后股票暴跌，平台关闭群聊解散。"},
        {"title": "虚拟货币挖矿诈骗案", "victim": "尹晓东", "amount": 567000, "type": "投资理财", "desc": "在币圈社群认识好友推荐云挖矿项目，称购买矿机算力每日分红。投入56.7万购买算力合约，前三个月正常分红，第四个月平台以系统升级为由停止运营。"},
        {"title": "电影投资诈骗案", "victim": "蒋雪梅", "amount": 890000, "type": "投资理财", "desc": "接到影视投资公司电话，推荐投资某即将上映的大片，声称票房收益可达3倍。签订电子合同后转账89万，电影上映后票房惨淡，公司失联无法退款。"},
        {"title": "数字藏品投资诈骗案", "victim": "卢志远", "amount": 234000, "type": "投资理财", "desc": "在社群中看到数字藏品投资机会，平台宣称每件藏品限量发行且可增值百倍。购买多件藏品后平台推出二级交易市场，挂单出售后资金无法提现。"},

        # --- 冒充熟人 (6条) ---
        {"title": "冒充亲戚借钱诈骗案", "victim": "蔡丽华", "amount": 125000, "type": "冒充熟人", "desc": "接到冒充在外地做生意的侄子的电话，称急需一笔货款周转。因声音相似未起疑心，通过银行柜台转账12.5万到指定账户，后联系真侄子发现被骗。"},
        {"title": "冒充朋友急事诈骗案", "victim": "丁建平", "amount": 67800, "type": "冒充熟人", "desc": "收到冒充好友的微博私信，称在国外手机丢失无法使用银行卡，请求帮忙购买机票。转账67800元到提供的账户后，联系好友本人发现账号被盗。"},
        {"title": "冒充同学借钱诈骗案", "victim": "程小燕", "amount": 34500, "type": "冒充熟人", "desc": "收到冒充初中同学的微信好友申请，通过后对方称家人生病急需用钱。视频通话仅3秒后挂断称信号不好，要求转账到银行卡，转账后对方失联。"},
        {"title": "冒充老师收费诈骗案", "victim": "顾志强", "amount": 29800, "type": "冒充熟人", "desc": "收到冒充孩子班主任的QQ消息，称学校需缴纳补习费和资料费。对方发来支付宝收款码，扫码支付后联系班主任核实发现被骗。"},
        {"title": "冒充领导送礼诈骗案", "victim": "毛桂英", "amount": 185000, "type": "冒充熟人", "desc": "接到冒充单位领导的电话，称需要给上级送礼但自己不方便出面，要求代转账。先后分两次转账18.5万到指定账户，后与领导本人核实发现被骗。"},
        {"title": "冒充同事借款诈骗案", "victim": "邱晓峰", "amount": 45600, "type": "冒充熟人", "desc": "收到冒充公司同事的钉钉消息，称急需借钱周转。对方头像和姓名与同事一致，未电话核实直接转账45600元，后发现同事账号被盗。"},

        # --- 网络贷款 (4条) ---
        {"title": "网贷保证金诈骗案", "victim": "沈玉兰", "amount": 25600, "type": "网络贷款", "desc": "在网上搜索贷款信息后接到自称某贷款平台客服电话，称可提供10万无抵押贷款。要求先缴纳5%的保证金验证还款能力，转账后对方称流水不足需继续缴费。"},
        {"title": "网贷解冻费诈骗案", "victim": "黎志强", "amount": 48900, "type": "网络贷款", "desc": "下载'速易贷'APP申请贷款5万元，平台显示放款成功但银行卡号填写错误导致冻结。客服要求缴纳解冻费和解绑费，多次转账后平台无法打开。"},
        {"title": "网贷刷流水诈骗案", "victim": "冯晓燕", "amount": 72300, "type": "网络贷款", "desc": "接到贷款推销电话称可办理30万大额贷款，要求提供银行卡刷流水提高贷款额度。按对方指示向多个账户转账共计7.23万后，对方电话关机。"},
        {"title": "网贷提额诈骗案", "victim": "韦建华", "amount": 34500, "type": "网络贷款", "desc": "收到冒充某正规贷款平台的短信称可提升额度至50万，点击链接进入仿冒平台。填写资料后被告知需缴纳手续费和提额服务费，转账后平台无法访问。"},
    ]

    from database.models import Person, Account, Phone
    import random

    case_objects = []
    keyword_mapping = {
        '冒充客服': '冒充客服', '刷单返利': '刷单返利', '冒充公检法': '冒充公检法',
        '投资理财': '投资理财', '冒充熟人': '冒充熟人', '网络贷款': '网络贷款'
    }

    for i, cd in enumerate(demo_cases):
        case_id = f"FC{datetime.now().strftime('%Y%m%d')}{i+1:03d}"
        risk_scores = [75, 82, 68, 90, 78, 85, 72, 88, 76, 80,
                       70, 86, 74, 79, 83, 71, 87, 73, 81, 69,
                       84, 77, 89, 67, 91,
                       76, 83, 69, 91, 79, 86, 73, 89, 77, 81,
                       71, 87, 75, 80, 84, 72, 88, 70, 82, 78,
                       85, 68, 90, 74, 79, 83, 71, 87, 73, 81,
                       69, 84, 77, 89, 67, 92, 76, 82, 68, 90,
                       78, 85, 72, 88, 76, 80, 70, 86, 74, 79]
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
            keywords=[cd['type'], '诈骗', keyword_mapping.get(cd['type'], '诈骗'), '转账'],
            created_at=datetime.now() - timedelta(days=random.randint(1, 60), hours=random.randint(0, 23))
        )
        db.session.add(case)
        case_objects.append(case)
    db.session.flush()

    # ---- 3. 注入11个团伙 ----
    gang_data = [
        {'name': '京东客服诈骗团伙', 'level': 'S', 'score': 92, 'tech': '高', 'script': '冒充京东金融客服话术', 'member': '10-15人', 'amount': 1042600},
        {'name': '公检法冒充团伙', 'level': 'A', 'score': 85, 'tech': '高', 'script': '冒充公检法恐吓话术', 'member': '8-12人', 'amount': 1408800},
        {'name': '刷单返利团伙', 'level': 'B', 'score': 72, 'tech': '中', 'script': '刷单返利话术', 'member': '6-10人', 'amount': 544400},
        {'name': '虚假投资理财团伙', 'level': 'A', 'score': 88, 'tech': '高', 'script': '投资理财虚假平台', 'member': '15-20人', 'amount': 2136000},
        {'name': '冒充熟人诈骗团伙', 'level': 'B', 'score': 70, 'tech': '中', 'script': '冒充领导熟人话术', 'member': '5-8人', 'amount': 975600},
        {'name': '冒充客服独立团伙', 'level': 'A', 'score': 84, 'tech': '高', 'script': '冒充各类平台客服话术', 'member': '12-18人', 'amount': 1198700},
        {'name': '刷单返利独立团伙', 'level': 'B', 'score': 76, 'tech': '中', 'script': '刷单返利诱导话术', 'member': '8-14人', 'amount': 1322500},
        {'name': '冒充公检法独立团伙', 'level': 'A', 'score': 87, 'tech': '高', 'script': '冒充公检法恐吓话术', 'member': '15-25人', 'amount': 3502900},
        {'name': '投资理财独立团伙', 'level': 'A', 'score': 86, 'tech': '高', 'script': '虚假投资平台话术', 'member': '18-30人', 'amount': 4807000},
        {'name': '冒充熟人独立团伙', 'level': 'B', 'score': 73, 'tech': '中', 'script': '冒充熟人急事话术', 'member': '6-12人', 'amount': 487700},
        {'name': '网络贷款独立团伙', 'level': 'C', 'score': 65, 'tech': '低', 'script': '网贷手续费话术', 'member': '4-8人', 'amount': 181300},
    ]

    gang_objects = []
    gang_case_mapping = [
        list(range(0, 7)),      # Gang 1: 京东客服诈骗团伙 (7案, 冒充客服, 索引0-6)
        list(range(7, 13)),     # Gang 2: 公检法冒充团伙 (6案, 冒充公检法, 索引7-12)
        list(range(13, 18)),    # Gang 3: 刷单返利团伙 (5案, 刷单返利, 索引13-17)
        list(range(18, 22)),    # Gang 4: 虚假投资理财团伙 (4案, 投资理财, 索引18-21)
        list(range(22, 25)),    # Gang 5: 冒充熟人诈骗团伙 (3案, 冒充熟人, 索引22-24)
        list(range(25, 37)),    # Gang 6: 冒充客服独立团伙 (12案, 冒充客服, 索引25-36)
        list(range(37, 47)),    # Gang 7: 刷单返利独立团伙 (10案, 刷单返利, 索引37-46)
        list(range(47, 57)),    # Gang 8: 冒充公检法独立团伙 (10案, 冒充公检法, 索引47-56)
        list(range(57, 65)),    # Gang 9: 投资理财独立团伙 (8案, 投资理财, 索引57-64)
        list(range(65, 71)),    # Gang 10: 冒充熟人独立团伙 (6案, 冒充熟人, 索引65-70)
        list(range(71, 75)),    # Gang 11: 网络贷款独立团伙 (4案, 网络贷款, 索引71-74)
    ]

    for gi, gd in enumerate(gang_data):
        gang_id = f"GANG{datetime.now().strftime('%Y%m%d')}{gi+1:03d}"
        gang = Gang(
            gang_id=gang_id, session_id=session_id,
            gang_name=gd['name'],
            risk_level=gd['level'], risk_label={'S':'极危','A':'高危','B':'中危','C':'低危'}[gd['level']],
            risk_type='danger' if gd['level'] in ['S','A'] else ('warning' if gd['level'] == 'B' else 'info'),
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

    # ---- 5. 注入资金流向数据 (每案3-5条, 共~300条) ----
    from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson

    bank_accounts_pool = [
        ("621700288011234567", "中国建设银行", "622202100345678901", "中国工商银行"),
        ("621226400567890123", "中国工商银行", "621700322901234567", "中国建设银行"),
        ("622848001234567890", "中国农业银行", "621700188765432109", "中国建设银行"),
        ("621790600112233445", "中国银行", "622262011098765432", "交通银行"),
        ("622575800123456789", "招商银行", "621226123489012345", "中国工商银行"),
        ("621485020987654321", "中信银行", "622848567812345678", "中国农业银行"),
        ("622662030123789456", "中国光大银行", "621700234598765432", "中国建设银行"),
        ("621691550456123789", "中国邮政储蓄银行", "622202345678901234", "中国工商银行"),
        ("622630780789456123", "华夏银行", "621700456789012345", "中国建设银行"),
        ("621691330321654987", "中国民生银行", "622848901234567890", "中国农业银行"),
        ("622568800654987321", "广发银行", "621790789012345678", "中国银行"),
        ("622262011234567890", "交通银行", "622202567890123456", "中国工商银行"),
        ("621700567890123456", "中国建设银行", "621226789012345678", "中国工商银行"),
        ("622848345678901234", "中国农业银行", "621790901234567890", "中国银行"),
        ("621226901234567890", "中国工商银行", "622848789012345678", "中国农业银行"),
        ("622202789012345678", "中国工商银行", "621700123456789012", "中国建设银行"),
        ("621700901234567890", "中国建设银行", "622262034567890123", "交通银行"),
        ("621790123456789012", "中国银行", "622848456789012345", "中国农业银行"),
        ("622848567890123456", "中国农业银行", "621700789012345678", "中国建设银行"),
        ("621226345678901234", "中国工商银行", "622202901234567890", "中国工商银行"),
        ("622202123456789012", "中国工商银行", "621790345678901234", "中国银行"),
        ("621700345678901234", "中国建设银行", "621226567890123456", "中国工商银行"),
        ("622848901234567890", "中国农业银行", "622262056789012345", "交通银行"),
        ("621790567890123456", "中国银行", "622202789012345678", "中国工商银行"),
        ("621226789012345678", "中国工商银行", "621700567890123456", "中国建设银行"),
        ("622202456789012345", "中国工商银行", "621226901234567890", "中国工商银行"),
        ("621700678901234567", "中国建设银行", "622848123456789012", "中国农业银行"),
        ("621790789012345678", "中国银行", "622202345678901234", "中国工商银行"),
        ("622848234567890123", "中国农业银行", "621700890123456789", "中国建设银行"),
        ("621226123456789012", "中国工商银行", "622262078901234567", "交通银行"),
    ]

    flow_direction_annotations = [
        ("out", "受害人首次向嫌疑人账户转账"),
        ("out", "资金被转移至二级账户"),
        ("out", "资金被转移至三级账户"),
        ("out", "资金在团伙内部账户间流转"),
        ("in", "小额返利诱骗资金"),
    ]

    flow_records = []
    for ci, case_obj in enumerate(case_objects):
        num_flows = random.choice([3, 4, 5])
        for fi in range(num_flows):
            src_idx = (ci * 3 + fi) % len(bank_accounts_pool)
            tgt_idx = (src_idx + 1 + fi) % len(bank_accounts_pool)
            src, src_bank, tgt, tgt_bank = bank_accounts_pool[src_idx]
            case_amount = float(demo_cases[ci]['amount'])
            level = fi + 1
            if level == 1:
                amt = round(case_amount * random.uniform(0.8, 1.0), 2)
            elif level == 2:
                amt = round(case_amount * random.uniform(0.5, 0.9), 2)
            elif level == 3:
                amt = round(case_amount * random.uniform(0.3, 0.7), 2)
            else:
                amt = round(case_amount * random.uniform(0.1, 0.4), 2)
            dir, ann = flow_direction_annotations[fi % len(flow_direction_annotations)]
            flow = CapitalFlow(
                case_id=case_obj.case_id,
                source_account=src,
                target_account=tgt,
                bank_name=src_bank,
                amount=amt,
                transaction_time=datetime.now() - timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                ),
                direction=dir,
                level=level,
                annotation=f"{ann} (第{level}层)"
            )
            db.session.add(flow)
            flow_records.append(flow)
    print(f"   资金流向: {len(flow_records)} 条")

    # ---- 6. 注入派单数据 (每案1条, 共75条) ----
    depts = ["刑侦大队", "网安大队", "辖区派出所", "反诈中心", "经侦大队"]
    officers = ["张明", "李华", "王强", "赵刚", "刘伟", "陈志远", "周建平"]
    statuses = ["pending", "signed", "completed"]
    dispatch_records = []
    for i in range(75):
        case_obj = case_objects[i]
        days_ago = random.randint(1, 30)
        dispatch = DispatchOrder(
            alert_id=f"ALT{datetime.now().strftime('%Y%m%d')}{i+1:03d}",
            case_id=case_obj.case_id,
            assigned_dept=random.choice(depts),
            assigned_officer=random.choice(officers),
            status=random.choice(statuses),
            dispatch_time=datetime.now() - timedelta(days=days_ago),
            sign_time=datetime.now() - timedelta(days=max(0, days_ago - random.randint(1, 5))),
            feedback="已处置完毕，嫌疑人已控制" if random.random() > 0.6 else "正在跟进调查中",
            deadline=datetime.now() + timedelta(days=random.randint(1, 14)),
            created_by=1
        )
        db.session.add(dispatch)
        dispatch_records.append(dispatch)
    print(f"   派单: {len(dispatch_records)} 条")

    # ---- 7. 注入重点人员数据 (原有10条 + 新增15条 = 25条) ----
    person_types = ["前科人员", "高危人员", "涉诈重点人", "两卡人员"]

    original_persons = [
        {"name": "刘某", "id_number": "420102198803152341", "phone": "13871562341", "person_type": "前科人员",
         "risk_level": "S", "bank_account": "622202100345678901", "address": "湖北省武汉市江岸区后湖街道某某小区",
         "notes": "涉及冒充客服类诈骗，有电信诈骗前科记录，曾因诈骗罪被判刑3年"},
        {"name": "张某", "id_number": "420103199205267892", "phone": "13971565678", "person_type": "高危人员",
         "risk_level": "A", "bank_account": "621700288011234567", "address": "湖北省武汉市武昌区中南路街道某某小区",
         "notes": "涉及刷单返利类诈骗，多张银行卡被冻结，疑似团伙骨干成员"},
        {"name": "王某", "id_number": "420106198709123456", "phone": "15071569012", "person_type": "涉诈重点人",
         "risk_level": "A", "bank_account": "622848001234567890", "address": "湖北省武汉市洪山区珞南街道某某小区",
         "notes": "涉及投资理财类诈骗，名下多张银行卡涉案，资金流水异常"},
        {"name": "李某", "id_number": "420107199512347891", "phone": "18671563456", "person_type": "前科人员",
         "risk_level": "B", "bank_account": "621790600112233445", "address": "湖北省武汉市江汉区前进街道某某小区",
         "notes": "涉及冒充公检法类诈骗，曾因帮助信息网络犯罪活动罪被处理"},
        {"name": "赵某", "id_number": "420111199009012345", "phone": "13771567890", "person_type": "两卡人员",
         "risk_level": "B", "bank_account": "622575800123456789", "address": "湖北省武汉市硚口区韩家墩街道某某小区",
         "notes": "涉及冒充熟人类诈骗，名下手机卡涉案，曾出售个人银行卡获利"},
        {"name": "陈某", "id_number": "420112198612347892", "phone": "13871562342", "person_type": "高危人员",
         "risk_level": "S", "bank_account": "622262011234567890", "address": "湖北省武汉市东西湖区吴家山街道某某小区",
         "notes": "涉及网络贷款类诈骗，多次往返边境地区，有出入境异常记录"},
        {"name": "周某", "id_number": "420113199409015678", "phone": "13971565679", "person_type": "涉诈重点人",
         "risk_level": "A", "bank_account": "621700567890123456", "address": "湖北省武汉市汉南区纱帽街道某某小区",
         "notes": "涉及冒充客服类诈骗，境外电话高频呼出记录，疑似境外窝点成员"},
        {"name": "吴某", "id_number": "420114198805261234", "phone": "15071569013", "person_type": "前科人员",
         "risk_level": "B", "bank_account": "622848345678901234", "address": "湖北省武汉市蔡甸区沌口街道某某小区",
         "notes": "涉及刷单返利类诈骗，多次被公安机关打击处理，仍继续作案"},
        {"name": "郑某", "id_number": "420115199103157892", "phone": "18671563457", "person_type": "两卡人员",
         "risk_level": "C", "bank_account": "621226901234567890", "address": "湖北省武汉市江夏区纸坊街道某某小区",
         "notes": "涉及投资理财类诈骗，出售个人银行卡和手机卡，被银行列入黑名单"},
        {"name": "何某", "id_number": "420116199212347893", "phone": "13771567891", "person_type": "高危人员",
         "risk_level": "A", "bank_account": "622202789012345678", "address": "湖北省武汉市黄陂区前川街道某某小区",
         "notes": "涉及冒充公检法类诈骗，关联多个涉案账户，资金流向境外"},
    ]

    additional_persons = [
        {"name": "唐某", "id_number": "420102199608142356", "phone": "18171562350", "person_type": "前科人员",
         "risk_level": "A", "bank_account": "621700901234567890", "address": "湖北省武汉市江岸区二七街道某某小区",
         "notes": "涉及冒充客服类诈骗，曾因诈骗罪被判处有期徒刑2年，刑满释放不足半年"},
        {"name": "孙某", "id_number": "420103199705183467", "phone": "18271565680", "person_type": "高危人员",
         "risk_level": "S", "bank_account": "622848567890123456", "address": "湖北省武汉市武昌区徐家棚街道某某小区",
         "notes": "涉及刷单返利类诈骗，系多个刷单群群主，发展下线30余人，涉案金额巨大"},
        {"name": "马某", "id_number": "420106199404215678", "phone": "18371569020", "person_type": "涉诈重点人",
         "risk_level": "A", "bank_account": "621226345678901234", "address": "湖北省武汉市洪山区关山街道某某小区",
         "notes": "涉及投资理财类诈骗，冒充投资导师在微信群讲课，诱导受害人投资虚假平台"},
        {"name": "胡某", "id_number": "420107199308116789", "phone": "18471563460", "person_type": "两卡人员",
         "risk_level": "B", "bank_account": "622202123456789012", "address": "湖北省武汉市江汉区万松街道某某小区",
         "notes": "涉及冒充公检法类诈骗，名下3张银行卡被冻结，2张手机卡被关停"},
        {"name": "黄某", "id_number": "420111199612287890", "phone": "18571567895", "person_type": "高危人员",
         "risk_level": "A", "bank_account": "621700345678901234", "address": "湖北省武汉市硚口区长丰街道某某小区",
         "notes": "涉及冒充熟人类诈骗，冒充领导身份实施诈骗，掌握大量企事业单位通讯录"},
        {"name": "林某", "id_number": "420112199505091234", "phone": "18671562355", "person_type": "前科人员",
         "risk_level": "B", "bank_account": "622848901234567890", "address": "湖北省武汉市东西湖区金银湖街道某某小区",
         "notes": "涉及网络贷款类诈骗，曾因帮助信息网络犯罪活动罪被判处拘役6个月"},
        {"name": "徐某", "id_number": "420113199807154567", "phone": "18771565685", "person_type": "涉诈重点人",
         "risk_level": "S", "bank_account": "621790567890123456", "address": "湖北省武汉市汉南区东荆街道某某小区",
         "notes": "涉及冒充客服类诈骗，系境外诈骗团伙回流人员，反侦察意识强"},
        {"name": "朱某", "id_number": "420114199210187890", "phone": "18871569025", "person_type": "高危人员",
         "risk_level": "A", "bank_account": "621226789012345678", "address": "湖北省武汉市蔡甸区大集街道某某小区",
         "notes": "涉及刷单返利类诈骗，搭建虚假刷单平台，技术手段高超"},
        {"name": "曹某", "id_number": "420115199609214567", "phone": "18971563465", "person_type": "两卡人员",
         "risk_level": "B", "bank_account": "622202456789012345", "address": "湖北省武汉市江夏区藏龙岛街道某某小区",
         "notes": "涉及投资理财类诈骗，出售个人银行卡4张，为诈骗团伙提供资金账户"},
        {"name": "蒋某", "id_number": "420116199803126789", "phone": "19071567898", "person_type": "前科人员",
         "risk_level": "C", "bank_account": "621700678901234567", "address": "湖北省武汉市黄陂区横店街道某某小区",
         "notes": "涉及冒充公检法类诈骗，曾因诈骗罪被判处有期徒刑1年缓刑2年"},
        {"name": "肖某", "id_number": "420102199908236701", "phone": "19171562360", "person_type": "高危人员",
         "risk_level": "A", "bank_account": "621790789012345678", "address": "湖北省武汉市江岸区丹水池街道某某小区",
         "notes": "涉及冒充熟人类诈骗，冒充公司老板对财务人员实施诈骗，已得手多起"},
        {"name": "罗某", "id_number": "420103199604117892", "phone": "19271565690", "person_type": "涉诈重点人",
         "risk_level": "A", "bank_account": "622848234567890123", "address": "湖北省武汉市武昌区水果湖街道某某小区",
         "notes": "涉及网络贷款类诈骗，搭建虚假贷款APP，以手续费名义骗取受害人钱财"},
        {"name": "万某", "id_number": "420106199702158903", "phone": "19371569030", "person_type": "两卡人员",
         "risk_level": "B", "bank_account": "621226123456789012", "address": "湖北省武汉市洪山区和平街道某某小区",
         "notes": "涉及冒充客服类诈骗，名下多张银行卡被用于接收受害人资金"},
        {"name": "龚某", "id_number": "420107199305284567", "phone": "19471563470", "person_type": "高危人员",
         "risk_level": "S", "bank_account": "621700288011234568", "address": "湖北省武汉市江汉区唐家墩街道某某小区",
         "notes": "涉及刷单返利类诈骗，系境外诈骗团伙国内联系人，组织人员赴境外从事诈骗活动"},
        {"name": "贺某", "id_number": "420111199610317890", "phone": "19571567899", "person_type": "涉诈重点人",
         "risk_level": "A", "bank_account": "622202100345678902", "address": "湖北省武汉市硚口区古田街道某某小区",
         "notes": "涉及投资理财类诈骗，制作虚假投资平台APP，具备完整的技术开发能力"},
    ]

    risk_level_map = {"S": "极危", "A": "高危", "B": "中危", "C": "低危"}
    person_records = []

    for pd in original_persons + additional_persons:
        person = KeyPerson(
            name=pd["name"],
            id_number=pd["id_number"],
            phone=pd["phone"],
            person_type=pd["person_type"],
            risk_level=pd["risk_level"],
            risk_label=risk_level_map[pd["risk_level"]],
            bank_account=pd["bank_account"],
            address=pd["address"],
            case_ids=[random.choice(case_objects).case_id],
            notes=pd["notes"],
            gender='男' if random.random() > 0.5 else '女',
            age=str(random.randint(22, 55)),
            tags=[pd["person_type"], pd["risk_level"] + "级风险", "需重点监控"],
            source="公安大数据平台",
            is_active=True
        )
        db.session.add(person)
        person_records.append(person)
    print(f"   重点人员: {len(person_records)} 条")

    db.session.commit()
    total_gang_relations = sum(len(x) for x in gang_case_mapping)
    print(f"✅ 演示数据注入完成!")
    print(f"   会话: {session_id}")
    print(f"   案件: {len(case_objects)} 条")
    print(f"   团伙: {len(gang_objects)} 个")
    print(f"   关联: {total_gang_relations} 条")
    print(f"   资金流向: {len(flow_records)} 条")
    print(f"   派单: {len(dispatch_records)} 条")
    print(f"   重点人员: {len(person_records)} 条")
    print("=" * 50)