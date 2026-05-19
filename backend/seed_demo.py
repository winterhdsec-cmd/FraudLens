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
        total_cases=75,
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
    identities = ["430****1234", "420****5678", "410****9012", "440****3456", "450****7890",
                 "460****2345", "470****6789", "480****0123", "490****4567", "500****8901"]
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