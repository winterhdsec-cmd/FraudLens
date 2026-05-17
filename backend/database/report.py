import os
from datetime import datetime
from . import db
from .crud import get_case_by_id, get_gang_by_id
from .models import Case, Gang, GangCaseRelation, EvidenceItem
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')


def _ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'ChineseTitle',
        parent=styles['Title'],
        fontSize=22,
        leading=30,
        alignment=1,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        'ChineseHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=20,
        spaceBefore=12,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        'ChineseBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=16,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        'ChineseSmall',
        parent=styles['Normal'],
        fontSize=8,
        leading=12,
        textColor=colors.grey
    ))
    return styles


def generate_case_report(case_id):
    _ensure_reports_dir()
    case = get_case_by_id(case_id)
    if not case:
        raise ValueError(f'Case {case_id} not found')

    file_name = f'report_case_{case_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    file_path = os.path.join(REPORTS_DIR, file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=20*mm,
        leftMargin=15*mm,
        rightMargin=15*mm
    )
    styles = _get_styles()
    elements = []

    elements.append(Paragraph('反诈智能研判报告', styles['ChineseTitle']))
    elements.append(Spacer(1, 6*mm))

    header_data = [
        ['报告编号', f'RPT-{case_id}'],
        ['生成日期', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['案件状态', case.get('status', '')],
    ]
    header_table = Table(header_data, colWidths=[40*mm, 100*mm])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8*mm))

    elements.append(Paragraph('一、案件基本信息', styles['ChineseHeading']))
    info_data = [
        ['案件标题', case.get('title', '')],
        ['诈骗类型', case.get('scam_type', '')],
        ['风险等级', case.get('risk_label', '')],
        ['涉案金额', case.get('amount', '')],
        ['案件来源', case.get('source', '')],
        ['诈骗手段', case.get('description', '')[:200] if case.get('description') else ''],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 105*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph('二、受害人信息', styles['ChineseHeading']))
    victim_data = [
        ['姓名', case.get('victim', '')],
        ['性别', case.get('victim_gender', '')],
        ['年龄', case.get('victim_age', '')],
        ['电话', case.get('victim_phone', '')],
        ['职业', case.get('victim_job', '')],
        ['地址', case.get('victim_address', '')],
    ]
    victim_table = Table(victim_data, colWidths=[35*mm, 105*mm])
    victim_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(victim_table)
    elements.append(Spacer(1, 6*mm))

    entities = case.get('extracted_entities', {})
    if entities:
        elements.append(Paragraph('三、提取实体信息', styles['ChineseHeading']))
        entity_rows = []
        for key, values in entities.items():
            if isinstance(values, list) and values:
                entity_rows.append([key, ', '.join(str(v) for v in values[:5])])
        if entity_rows:
            entity_table = Table(entity_rows, colWidths=[35*mm, 105*mm])
            entity_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(entity_table)
            elements.append(Spacer(1, 6*mm))

    keywords = case.get('keywords', [])
    if keywords:
        elements.append(Paragraph('四、关键词分析', styles['ChineseHeading']))
        kw_text = '、'.join(keywords)
        elements.append(Paragraph(kw_text, styles['ChineseBody']))
        elements.append(Spacer(1, 4*mm))

    evidence_list = EvidenceItem.query.filter_by(case_id=case_id).all()
    if evidence_list:
        elements.append(Paragraph('五、证据材料', styles['ChineseHeading']))
        evi_data = [['编号', '类型', '内容', '状态']]
        for i, ev in enumerate(evidence_list, 1):
            evi_data.append([str(i), ev.type, (ev.content or '')[:60], ev.status])
        evi_table = Table(evi_data, colWidths=[12*mm, 30*mm, 68*mm, 25*mm])
        evi_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(evi_table)
        elements.append(Spacer(1, 6*mm))

    ai_report = case.get('ai_report', '')
    if ai_report:
        elements.append(Paragraph('六、智能分析报告', styles['ChineseHeading']))
        elements.append(Paragraph(ai_report[:2000], styles['ChineseBody']))

    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph('— 报告结束 —', styles['ChineseSmall']))

    doc.build(elements)
    return file_path


def generate_gang_report(gang_id):
    _ensure_reports_dir()
    gang = get_gang_by_id(gang_id)
    if not gang:
        raise ValueError(f'Gang {gang_id} not found')

    file_name = f'report_gang_{gang_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    file_path = os.path.join(REPORTS_DIR, file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=20*mm,
        leftMargin=15*mm,
        rightMargin=15*mm
    )
    styles = _get_styles()
    elements = []

    elements.append(Paragraph('反诈智能研判报告 - 犯罪团伙', styles['ChineseTitle']))
    elements.append(Spacer(1, 6*mm))

    header_data = [
        ['团伙编号', f'GNG-{gang_id}'],
        ['生成日期', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['威胁等级', gang.get('threat_level', '')],
    ]
    header_table = Table(header_data, colWidths=[40*mm, 100*mm])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8*mm))

    elements.append(Paragraph('一、团伙基本信息', styles['ChineseHeading']))
    info_data = [
        ['团伙名称', gang.get('gang_name', '')],
        ['风险等级', gang.get('risk_label', '')],
        ['综合评分', str(gang.get('comprehensive_score', 0))],
        ['可信度', str(gang.get('confidence', 0))],
        ['预估成员数', gang.get('member_count_estimate', '')],
        ['技术等级', gang.get('tech_level', '')],
        ['剧本类型', gang.get('script_type', '')],
        ['关联案件数', str(gang.get('total_cases', 0))],
        ['总涉案金额', gang.get('total_amount_involved', '')],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 105*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    related = gang.get('related_cases', [])
    if related:
        elements.append(Paragraph('二、关联案件', styles['ChineseHeading']))
        case_data = [['编号', '案件ID', '受害人', '涉案金额', '风险等级']]
        for i, rc in enumerate(related, 1):
            case_data.append([
                str(i),
                rc.get('case_id', ''),
                rc.get('victim', ''),
                rc.get('amount', ''),
                rc.get('risk_level', ''),
            ])
        case_table = Table(case_data, colWidths=[10*mm, 30*mm, 35*mm, 35*mm, 30*mm])
        case_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(case_table)
        elements.append(Spacer(1, 6*mm))

    description = gang.get('description', '')
    if description:
        elements.append(Paragraph('三、团伙描述', styles['ChineseHeading']))
        elements.append(Paragraph(description[:1000], styles['ChineseBody']))
        elements.append(Spacer(1, 6*mm))

    modus_operandi = gang.get('modus_operandi', '')
    if modus_operandi:
        elements.append(Paragraph('四、作案手法', styles['ChineseHeading']))
        elements.append(Paragraph(modus_operandi[:1000], styles['ChineseBody']))
        elements.append(Spacer(1, 6*mm))

    fingerprint = gang.get('fingerprint', [])
    if fingerprint:
        elements.append(Paragraph('五、团伙特征指纹', styles['ChineseHeading']))
        for fp in fingerprint:
            if isinstance(fp, str):
                elements.append(Paragraph(f'• {fp}', styles['ChineseBody']))
            elif isinstance(fp, dict):
                elements.append(Paragraph(f'• {fp.get("name", "")}: {fp.get("value", "")}', styles['ChineseBody']))

    prevention_advice = gang.get('prevention_advice', '')
    if prevention_advice:
        elements.append(Paragraph('六、防范建议', styles['ChineseHeading']))
        if isinstance(prevention_advice, list):
            for item in prevention_advice:
                elements.append(Paragraph(f'• {item}', styles['ChineseBody']))
        else:
            elements.append(Paragraph(str(prevention_advice)[:1000], styles['ChineseBody']))

    risk_assessment = gang.get('risk_assessment', {})
    if risk_assessment:
        elements.append(Paragraph('七、风险评估', styles['ChineseHeading']))
        if isinstance(risk_assessment, dict):
            for key, value in risk_assessment.items():
                elements.append(Paragraph(f'• {key}: {value}', styles['ChineseBody']))
        else:
            elements.append(Paragraph(str(risk_assessment)[:1000], styles['ChineseBody']))

    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph('— 报告结束 —', styles['ChineseSmall']))

    doc.build(elements)
    return file_path


def export_case_docx(case_id):
    _ensure_reports_dir()
    case = get_case_by_id(case_id)
    if not case:
        raise ValueError(f'Case {case_id} not found')

    file_name = f'case_{case_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx'
    file_path = os.path.join(REPORTS_DIR, file_name)

    document = Document()

    section = document.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    title = document.add_heading('反诈智能研判报告', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f'报告编号: RPT-{case_id}    生成日期: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(128, 128, 128)

    document.add_heading('一、案件基本信息', level=1)
    info_table = document.add_table(rows=6, cols=2)
    info_table.style = 'Table Grid'
    info_data = [
        ('案件标题', case.get('title', '')),
        ('诈骗类型', case.get('scam_type', '')),
        ('风险等级', case.get('risk_label', '')),
        ('涉案金额', case.get('amount', '')),
        ('案件来源', case.get('source', '')),
        ('案件状态', case.get('status', '')),
    ]
    for i, (label, value) in enumerate(info_data):
        info_table.rows[i].cells[0].text = label
        info_table.rows[i].cells[1].text = value

    document.add_heading('二、受害人信息', level=1)
    victim_table = document.add_table(rows=6, cols=2)
    victim_table.style = 'Table Grid'
    victim_data = [
        ('姓名', case.get('victim', '')),
        ('性别', case.get('victim_gender', '')),
        ('年龄', case.get('victim_age', '')),
        ('电话', case.get('victim_phone', '')),
        ('职业', case.get('victim_job', '')),
        ('地址', case.get('victim_address', '')),
    ]
    for i, (label, value) in enumerate(victim_data):
        victim_table.rows[i].cells[0].text = label
        victim_table.rows[i].cells[1].text = value

    entities = case.get('extracted_entities', {})
    if entities:
        document.add_heading('三、提取实体信息', level=1)
        valid_entities = {k: v for k, v in entities.items() if isinstance(v, list) and v}
        if valid_entities:
            entity_table = document.add_table(rows=len(valid_entities), cols=2)
            entity_table.style = 'Table Grid'
            for i, (key, values) in enumerate(valid_entities.items()):
                entity_table.rows[i].cells[0].text = key
                entity_table.rows[i].cells[1].text = ', '.join(str(v) for v in values[:5])

    keywords = case.get('keywords', [])
    if keywords:
        document.add_heading('四、关键词分析', level=1)
        document.add_paragraph('、'.join(keywords))

    ai_report = case.get('ai_report', '')
    if ai_report:
        document.add_heading('五、智能分析报告', level=1)
        document.add_paragraph(ai_report[:2000])

    document.save(file_path)
    return file_path