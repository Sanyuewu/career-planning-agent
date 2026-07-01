# -*- coding: utf-8 -*-
"""
报告导出服务 - 支持 PDF 和 Word 格式
"""

import io
import re
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent

# 候选字体路径（按优先级）
_FONT_CANDIDATES = [
    BASE_DIR / "fonts" / "SimHei.ttf",
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
]


def _strip_markdown(text: str) -> str:
    """移除常见 Markdown 标记，保留纯文本"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


class ReportExportService:

    def __init__(self):
        self._font_name = 'Helvetica'
        self._font_bold = 'Helvetica-Bold'
        self._setup_fonts()

    def _setup_fonts(self):
        if not REPORTLAB_AVAILABLE:
            return
        for path in _FONT_CANDIDATES:
            if path.exists():
                try:
                    pdfmetrics.registerFont(TTFont('SimHei', str(path)))
                    self._font_name = 'SimHei'
                    self._font_bold = 'SimHei'
                    return
                except Exception:
                    continue

    def export_to_pdf(self, report_data: Dict[str, Any]) -> bytes:
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 未安装，请运行: pip install reportlab")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        fn = self._font_name
        fb = self._font_bold

        title_style = ParagraphStyle('Title', fontName=fb, fontSize=18,
                                     spaceAfter=6, alignment=1)
        meta_style = ParagraphStyle('Meta', fontName=fn, fontSize=9,
                                    textColor=colors.grey, spaceAfter=20, alignment=1)
        h1_style = ParagraphStyle('H1', fontName=fb, fontSize=14,
                                  spaceBefore=18, spaceAfter=8,
                                  borderPad=4, backColor=colors.HexColor('#F0F4FF'),
                                  leftIndent=0)
        h2_style = ParagraphStyle('H2', fontName=fb, fontSize=12,
                                  spaceBefore=12, spaceAfter=6)
        body_style = ParagraphStyle('Body', fontName=fn, fontSize=10,
                                    leading=18, spaceAfter=4)
        bullet_style = ParagraphStyle('Bullet', fontName=fn, fontSize=10,
                                      leading=16, leftIndent=12, spaceAfter=2,
                                      bulletIndent=0)

        story = []
        job_name = report_data.get('job', {}).get('title') or report_data.get('job_name', '')
        story.append(Paragraph(f"职业发展规划报告", title_style))
        if job_name:
            story.append(Paragraph(f"目标岗位：{job_name}", meta_style))
        story.append(Paragraph(
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            meta_style
        ))
        story.append(Spacer(1, 10))

        chapters = report_data.get('chapters_json', [])
        if chapters:
            for ch in chapters:
                title = _strip_markdown(ch.get('title', ''))
                content = ch.get('content', '')
                if title:
                    story.append(Paragraph(title, h1_style))
                for line in content.splitlines():
                    line = line.rstrip()
                    if not line:
                        story.append(Spacer(1, 4))
                        continue
                    if line.startswith('### '):
                        story.append(Paragraph(_strip_markdown(line), h2_style))
                    elif line.startswith('## '):
                        story.append(Paragraph(_strip_markdown(line), h1_style))
                    elif re.match(r'^[-*]\s+', line):
                        text = _strip_markdown(re.sub(r'^[-*]\s+', '', line))
                        story.append(Paragraph(f"• {text}", bullet_style))
                    elif re.match(r'^\d+\.\s+', line):
                        text = _strip_markdown(re.sub(r'^\d+\.\s+', '', line))
                        story.append(Paragraph(f"• {text}", bullet_style))
                    else:
                        story.append(Paragraph(_strip_markdown(line), body_style))
        else:
            # 无 chapters_json 时降级为结构化摘要
            story.append(Paragraph("人岗匹配分析", h1_style))
            match_data = report_data.get('match_result', {})
            story.append(Paragraph(
                f"总体匹配度：{match_data.get('total_match', 0):.1f}%", body_style
            ))
            rows = [
                ["维度", "匹配度"],
                ["基础要求", f"{match_data.get('basic_match', 0):.1f}%"],
                ["职业技能", f"{match_data.get('skill_match', 0):.1f}%"],
                ["职业素养", f"{match_data.get('quality_match', 0):.1f}%"],
                ["发展潜力", f"{match_data.get('potential_match', 0):.1f}%"],
            ]
            tbl = Table(rows, colWidths=[6 * cm, 4 * cm])
            tbl.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), fn),
                ('FONTNAME', (0, 0), (-1, 0), fb),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90D9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#F5F5F5')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(tbl)

        story.append(Spacer(1, 30))
        story.append(Paragraph("— 报告结束 —", meta_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def export_to_docx(self, report_data: Dict[str, Any]) -> bytes:
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx 未安装，请运行: pip install python-docx")

        doc = Document()

        job_name = report_data.get('job', {}).get('title') or report_data.get('job_name', '')
        title = doc.add_heading("职业发展规划报告", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        if job_name:
            p = doc.add_paragraph(f"目标岗位：{job_name}")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        chapters = report_data.get('chapters_json', [])
        if chapters:
            for ch in chapters:
                title_text = _strip_markdown(ch.get('title', ''))
                content = ch.get('content', '')
                if title_text:
                    doc.add_heading(title_text, level=1)
                for line in content.splitlines():
                    line = line.rstrip()
                    if not line:
                        continue
                    if line.startswith('### '):
                        doc.add_heading(_strip_markdown(line), level=3)
                    elif line.startswith('## '):
                        doc.add_heading(_strip_markdown(line), level=2)
                    elif re.match(r'^[-*]\s+', line):
                        text = _strip_markdown(re.sub(r'^[-*]\s+', '', line))
                        doc.add_paragraph(text, style='List Bullet')
                    elif re.match(r'^\d+\.\s+', line):
                        text = _strip_markdown(re.sub(r'^\d+\.\s+', '', line))
                        doc.add_paragraph(text, style='List Number')
                    else:
                        doc.add_paragraph(_strip_markdown(line))
        else:
            doc.add_heading("人岗匹配分析", level=1)
            match_data = report_data.get('match_result', {})
            doc.add_paragraph(f"总体匹配度：{match_data.get('total_match', 0):.1f}%")
            tbl = doc.add_table(rows=5, cols=2)
            tbl.style = 'Table Grid'
            headers = tbl.rows[0].cells
            headers[0].text = "维度"
            headers[1].text = "匹配度"
            for i, (dim, key) in enumerate([
                ("基础要求", "basic_match"), ("职业技能", "skill_match"),
                ("职业素养", "quality_match"), ("发展潜力", "potential_match")
            ]):
                row = tbl.rows[i + 1].cells
                row[0].text = dim
                row[1].text = f"{match_data.get(key, 0):.1f}%"

        doc.add_paragraph()
        doc.add_paragraph("— 报告结束 —")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def export_report(self, report_data: Dict[str, Any], format_type: str = "pdf") -> bytes:
        if format_type.lower() == "pdf":
            return self.export_to_pdf(report_data)
        elif format_type.lower() in ["docx", "word"]:
            return self.export_to_docx(report_data)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")


report_export_service = ReportExportService()
