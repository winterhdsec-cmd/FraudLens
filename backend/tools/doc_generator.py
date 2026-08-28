"""
法律文书生成器（Phase E1-1）

支持生成符合公安文书规范的：
  - 止付通知书（紧急止付）
  - 冻结决定书（协助冻结财产决定书）
  - 研判报告（案件分析报告）

设计原则：
  - 优先使用 reportlab（PDF 质量高、字体可控）
  - 无 reportlab 时降级为 HTML（浏览器打印为 PDF）
  - 字体兼容中文（Windows SimSun / Linux NotoSansCJK）
  - 文书内容 100% 来自结构化数据，避免 LLM 生成导致法律风险
"""
import os
import io
from datetime import datetime
from typing import Dict, Any, Optional, List

from tools.response import logger


# ── 字体路径探测 ──
def _find_cjk_font() -> Optional[str]:
    """探测系统中可用的中文字体路径。"""
    candidates = [
        # Windows
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        # Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# ════════════════════════════════════════════════════════════════════
# 一、文书内容构造（与 PDF 引擎解耦）
# ════════════════════════════════════════════════════════════════════

def build_freeze_order_context(order: Any, case: Any = None,
                               applicant: Dict[str, Any] = None) -> Dict[str, Any]:
    """构造冻结/止付文书的渲染上下文。

    Args:
        order: FreezeOrder 对象（含 order_id/case_id/action_type/target_accounts/
               legal_basis/freeze_amount/applicant_name 等）
        case: Case 对象（可选，用于填充案件信息）
        applicant: 申请人信息（可选，含 department/phone）

    Returns:
        dict: 可直接用于 PDF/HTML 渲染的上下文
    """
    now = datetime.now()
    targets = order.target_accounts or []
    target_lines = []
    for i, t in enumerate(targets, 1):
        if isinstance(t, dict):
            target_lines.append(
                f"{i}. 账户户名：{t.get('account_name', '—')}    "
                f"账号：{t.get('account_number', t.get('account', '—'))}    "
                f"开户行：{t.get('bank_name', '—')}"
            )
        else:
            target_lines.append(f"{i}. 账户/账号：{t}")

    action_verb = "冻结" if (order.action_type or "").startswith("冻") else "止付"
    doc_title = "协助冻结财产决定书" if action_verb == "冻结" else "紧急止付通知书"

    return {
        "doc_title": doc_title,
        "doc_number": order.order_id,
        "case_id": order.case_id,
        "case_title": (case.title if case else "") or f"案件 {order.case_id}",
        "scam_type": (case.scam_type if case else "") or "—",
        "amount_text": f"人民币 {order.freeze_amount:,.2f} 元" if order.freeze_amount else "—",
        "action_verb": action_verb,
        "target_lines": target_lines,
        "target_count": len(targets),
        "legal_basis": order.legal_basis or "《中华人民共和国反电信网络诈骗法》第十一条、第十二条",
        "applicant_name": order.applicant_name or (applicant or {}).get("username", ""),
        "applicant_department": (applicant or {}).get("department", "") or (order.department or ""),
        "applicant_phone": (applicant or {}).get("phone", ""),
        "reason": order.reason or "涉案资金需要紧急止付/冻结，防止资金转移",
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "issue_date": now.strftime("%Y年%m月%d日"),
    }


def build_investigation_report_context(task: Any, case: Any = None,
                                       gang: Any = None) -> Dict[str, Any]:
    """构造研判报告的渲染上下文。"""
    now = datetime.now()
    output = task.output_result or {} if hasattr(task, "output_result") else {}
    statistics = output.get("statistics", {}) if isinstance(output, dict) else {}
    gangs = output.get("gangs", []) if isinstance(output, dict) else []

    return {
        "doc_title": "案件研判分析报告",
        "doc_number": task.task_id if hasattr(task, "task_id") else "",
        "case_id": task.case_id if hasattr(task, "case_id") else "",
        "case_title": (case.title if case else "") or f"案件 {task.case_id}",
        "scam_type": (case.scam_type if case else "") or "—",
        "risk_level": (case.risk_label if case else "") or "—",
        "operator_name": task.operator_name if hasattr(task, "operator_name") else "",
        "department": task.department if hasattr(task, "department") else "",
        "confidence": task.confidence if hasattr(task, "confidence") else 0,
        "gate_decision": task.gate_decision if hasattr(task, "gate_decision") else "",
        "quality_score": statistics.get("quality_score", 0) if isinstance(statistics, dict) else 0,
        "n_gangs": len(gangs),
        "gang_summary": [
            {
                "gang_id": g.get("gang_id", ""),
                "gang_name": g.get("gang_name", "未命名团伙"),
                "member_count": g.get("member_count_estimate", ""),
                "threat_level": g.get("threat_level", ""),
                "total_amount": g.get("total_amount", ""),
            }
            for g in gangs if isinstance(g, dict)
        ],
        "issue_date": now.strftime("%Y年%m月%d日"),
    }


# ════════════════════════════════════════════════════════════════════
# 二、PDF 渲染（reportlab）
# ════════════════════════════════════════════════════════════════════

def _render_freeze_pdf(ctx: Dict[str, Any]) -> bytes:
    """用 reportlab 渲染冻结/止付文书 PDF。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors

    # 注册中文字体
    font_path = _find_cjk_font()
    font_name = "SimSun"
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception as e:
            logger.warning(f"注册中文字体失败: {e}")
            font_name = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=25*mm, rightMargin=25*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ChineseTitle", parent=styles["Title"],
        fontName=font_name, fontSize=22, leading=30,
        alignment=TA_CENTER, spaceAfter=20,
    )
    body_style = ParagraphStyle(
        "ChineseBody", parent=styles["Normal"],
        fontName=font_name, fontSize=12, leading=22,
        alignment=TA_LEFT, firstLineIndent=24, spaceAfter=10,
    )
    label_style = ParagraphStyle(
        "ChineseLabel", parent=styles["Normal"],
        fontName=font_name, fontSize=12, leading=22,
        alignment=TA_LEFT, spaceAfter=6,
    )

    elements = []
    # 标题
    elements.append(Paragraph(ctx["doc_title"], title_style))
    elements.append(Spacer(1, 10*mm))

    # 文号
    elements.append(Paragraph(f"文号：{ctx['doc_number']}", label_style))
    elements.append(Spacer(1, 5*mm))

    # 案件信息
    elements.append(Paragraph(
        f"<b>案件编号：</b>{ctx['case_id']}", body_style
    ))
    elements.append(Paragraph(
        f"<b>案件名称：</b>{ctx['case_title']}", body_style
    ))
    elements.append(Paragraph(
        f"<b>案件类型：</b>{ctx['scam_type']}", body_style
    ))
    elements.append(Paragraph(
        f"<b>涉案金额：</b>{ctx['amount_text']}", body_style
    ))
    elements.append(Spacer(1, 5*mm))

    # 法律依据
    elements.append(Paragraph(
        f"<b>法律依据：</b>{ctx['legal_basis']}", body_style
    ))
    elements.append(Spacer(1, 5*mm))

    # 事由
    elements.append(Paragraph("<b>事由：</b>", label_style))
    elements.append(Paragraph(ctx["reason"], body_style))
    elements.append(Spacer(1, 5*mm))

    # {action_verb}对象列表
    elements.append(Paragraph(
        f"<b>拟{ctx['action_verb']}账户/财产（共 {ctx['target_count']} 项）：</b>",
        label_style
    ))
    for line in ctx["target_lines"]:
        elements.append(Paragraph(line, body_style))
    elements.append(Spacer(1, 8*mm))

    # 落款
    elements.append(Paragraph(
        f"申请单位：{ctx['applicant_department']}", body_style
    ))
    elements.append(Paragraph(
        f"申请人：{ctx['applicant_name']}", body_style
    ))
    if ctx.get("applicant_phone"):
        elements.append(Paragraph(
            f"联系电话：{ctx['applicant_phone']}", body_style
        ))
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(
        f"{ctx['issue_date']}",
        ParagraphStyle("Date", parent=body_style, alignment=TA_CENTER)
    ))

    doc.build(elements)
    return buf.getvalue()


def _render_investigation_pdf(ctx: Dict[str, Any]) -> bytes:
    """用 reportlab 渲染研判报告 PDF。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors

    font_path = _find_cjk_font()
    font_name = "SimSun"
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception:
            font_name = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=25*mm, rightMargin=25*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ChineseTitle", parent=styles["Title"],
        fontName=font_name, fontSize=20, leading=28,
        alignment=TA_CENTER, spaceAfter=20,
    )
    h2_style = ParagraphStyle(
        "ChineseH2", parent=styles["Heading2"],
        fontName=font_name, fontSize=14, leading=22,
        spaceBefore=10, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ChineseBody", parent=styles["Normal"],
        fontName=font_name, fontSize=12, leading=22,
        firstLineIndent=24, spaceAfter=6,
    )

    elements = []
    elements.append(Paragraph(ctx["doc_title"], title_style))
    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph(f"报告编号：{ctx['doc_number']}", body_style))
    elements.append(Paragraph(f"生成日期：{ctx['issue_date']}", body_style))
    elements.append(Spacer(1, 5*mm))

    elements.append(Paragraph("一、案件基本信息", h2_style))
    elements.append(Paragraph(f"案件编号：{ctx['case_id']}", body_style))
    elements.append(Paragraph(f"案件名称：{ctx['case_title']}", body_style))
    elements.append(Paragraph(f"诈骗类型：{ctx['scam_type']}", body_style))
    elements.append(Paragraph(f"风险等级：{ctx['risk_level']}", body_style))

    elements.append(Paragraph("二、研判结论", h2_style))
    elements.append(Paragraph(f"研判人：{ctx['operator_name']}（{ctx['department']}）", body_style))
    elements.append(Paragraph(f"置信度：{ctx['confidence']:.2%}", body_style))
    elements.append(Paragraph(f"门控决策：{ctx['gate_decision']}", body_style))
    elements.append(Paragraph(f"质量评分：{ctx['quality_score']:.2%}", body_style))
    elements.append(Paragraph(f"检出团伙数：{ctx['n_gangs']}", body_style))

    if ctx["gang_summary"]:
        elements.append(Paragraph("三、团伙清单", h2_style))
        table_data = [["团伙编号", "团伙名称", "成员数", "威胁等级", "涉案金额"]]
        for g in ctx["gang_summary"]:
            table_data.append([
                g["gang_id"], g["gang_name"],
                str(g["member_count"]), g["threat_level"], str(g["total_amount"]),
            ])
        tbl = Table(table_data, colWidths=[40*mm, 40*mm, 20*mm, 25*mm, 35*mm])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f1525")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(tbl)

    elements.append(Spacer(1, 15*mm))
    elements.append(Paragraph("（本报告由 FraudLens 智能研判系统自动生成，仅供办案参考）",
                              ParagraphStyle("Foot", parent=body_style,
                                             alignment=TA_CENTER, fontSize=10)))

    doc.build(elements)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════
# 三、HTML 降级渲染（无 reportlab 时）
# ════════════════════════════════════════════════════════════════════

def _render_freeze_html(ctx: Dict[str, Any]) -> str:
    """HTML 降级版冻结/止付文书（浏览器打印为 PDF）。"""
    target_html = "".join(f"<li>{line}</li>" for line in ctx["target_lines"])
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>{ctx['doc_title']}</title>
<style>
  body {{ font-family: "SimSun", "宋体", serif; max-width: 210mm; margin: 20mm auto; padding: 25mm; line-height: 1.8; color: #000; }}
  h1 {{ text-align: center; font-size: 26pt; margin-bottom: 30pt; }}
  .doc-number {{ text-align: right; margin-bottom: 20pt; }}
  .section {{ margin: 12pt 0; text-indent: 24pt; }}
  .label {{ font-weight: bold; }}
  ol {{ padding-left: 36pt; }}
  .footer {{ margin-top: 40pt; text-align: center; }}
  @media print {{ body {{ margin: 0; }} }}
</style></head>
<body>
  <h1>{ctx['doc_title']}</h1>
  <div class="doc-number">文号：{ctx['doc_number']}</div>
  <div class="section"><span class="label">案件编号：</span>{ctx['case_id']}</div>
  <div class="section"><span class="label">案件名称：</span>{ctx['case_title']}</div>
  <div class="section"><span class="label">案件类型：</span>{ctx['scam_type']}</div>
  <div class="section"><span class="label">涉案金额：</span>{ctx['amount_text']}</div>
  <div class="section"><span class="label">法律依据：</span>{ctx['legal_basis']}</div>
  <div class="section"><span class="label">事由：</span>{ctx['reason']}</div>
  <div class="section"><span class="label">拟{ctx['action_verb']}账户/财产（共 {ctx['target_count']} 项）：</span></div>
  <ol>{target_html}</ol>
  <div class="section">申请单位：{ctx['applicant_department']}</div>
  <div class="section">申请人：{ctx['applicant_name']}</div>
  <div class="footer">{ctx['issue_date']}</div>
</body></html>"""


def _render_investigation_html(ctx: Dict[str, Any]) -> str:
    """HTML 降级版研判报告。"""
    gang_rows = "".join(
        f"<tr><td>{g['gang_id']}</td><td>{g['gang_name']}</td>"
        f"<td>{g['member_count']}</td><td>{g['threat_level']}</td>"
        f"<td>{g['total_amount']}</td></tr>"
        for g in ctx["gang_summary"]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>{ctx['doc_title']}</title>
<style>
  body {{ font-family: "SimSun", "宋体", serif; max-width: 210mm; margin: 20mm auto; padding: 25mm; line-height: 1.8; }}
  h1 {{ text-align: center; font-size: 22pt; margin-bottom: 20pt; }}
  h2 {{ font-size: 14pt; margin: 15pt 0 8pt; }}
  .section {{ text-indent: 24pt; margin: 6pt 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10pt 0; }}
  th, td {{ border: 1px solid #666; padding: 6pt; text-align: center; font-size: 11pt; }}
  th {{ background: #0f1525; color: #fff; }}
  .footer {{ margin-top: 30pt; text-align: center; font-size: 10pt; color: #666; }}
  @media print {{ body {{ margin: 0; }} }}
</style></head>
<body>
  <h1>{ctx['doc_title']}</h1>
  <div class="section">报告编号：{ctx['doc_number']}</div>
  <div class="section">生成日期：{ctx['issue_date']}</div>
  <h2>一、案件基本信息</h2>
  <div class="section">案件编号：{ctx['case_id']}</div>
  <div class="section">案件名称：{ctx['case_title']}</div>
  <div class="section">诈骗类型：{ctx['scam_type']}</div>
  <div class="section">风险等级：{ctx['risk_level']}</div>
  <h2>二、研判结论</h2>
  <div class="section">研判人：{ctx['operator_name']}（{ctx['department']}）</div>
  <div class="section">置信度：{ctx['confidence']:.2%}</div>
  <div class="section">门控决策：{ctx['gate_decision']}</div>
  <div class="section">质量评分：{ctx['quality_score']:.2%}</div>
  <div class="section">检出团伙数：{ctx['n_gangs']}</div>
  <h2>三、团伙清单</h2>
  <table><thead><tr><th>团伙编号</th><th>团伙名称</th><th>成员数</th><th>威胁等级</th><th>涉案金额</th></tr></thead>
  <tbody>{gang_rows}</tbody></table>
  <div class="footer">（本报告由 FraudLens 智能研判系统自动生成，仅供办案参考）</div>
</body></html>"""


# ════════════════════════════════════════════════════════════════════
# 四、对外统一接口
# ════════════════════════════════════════════════════════════════════

def generate_freeze_order_doc(order: Any, case: Any = None,
                              applicant: Dict[str, Any] = None,
                              fmt: str = "pdf") -> Dict[str, Any]:
    """生成冻结/止付文书。

    Args:
        order: FreezeOrder 对象
        case: Case 对象（可选）
        applicant: 申请人信息（可选）
        fmt: "pdf" 或 "html"

    Returns:
        {"content": bytes/str, "content_type": "application/pdf"/"text/html",
         "filename": "..."}
    """
    ctx = build_freeze_order_context(order, case, applicant)
    filename = f"{ctx['doc_title']}_{ctx['doc_number']}.pdf"

    if fmt == "pdf":
        try:
            content = _render_freeze_pdf(ctx)
            return {
                "content": content,
                "content_type": "application/pdf",
                "filename": filename,
            }
        except ImportError:
            logger.warning("reportlab 未安装，降级为 HTML 文书")
            return {
                "content": _render_freeze_html(ctx),
                "content_type": "text/html",
                "filename": f"{ctx['doc_title']}_{ctx['doc_number']}.html",
            }
    else:
        return {
            "content": _render_freeze_html(ctx),
            "content_type": "text/html",
            "filename": f"{ctx['doc_title']}_{ctx['doc_number']}.html",
        }


def generate_investigation_report(task: Any, case: Any = None,
                                  gang: Any = None,
                                  fmt: str = "pdf") -> Dict[str, Any]:
    """生成研判报告。"""
    ctx = build_investigation_report_context(task, case, gang)
    filename = f"研判报告_{ctx['doc_number']}.pdf"

    if fmt == "pdf":
        try:
            content = _render_investigation_pdf(ctx)
            return {
                "content": content,
                "content_type": "application/pdf",
                "filename": filename,
            }
        except ImportError:
            logger.warning("reportlab 未安装，降级为 HTML 报告")
            return {
                "content": _render_investigation_html(ctx),
                "content_type": "text/html",
                "filename": f"研判报告_{ctx['doc_number']}.html",
            }
    else:
        return {
            "content": _render_investigation_html(ctx),
            "content_type": "text/html",
            "filename": f"研判报告_{ctx['doc_number']}.html",
        }
