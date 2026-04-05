# -*- coding: utf-8 -*-
"""
生成演示用简历 PDF
输出到 data/demo_resume.pdf
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ── 中文字体注册 ──────────────────────────────────────────────
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",    # 黑体
    r"C:\Windows\Fonts\simsun.ttc",    # 宋体
    r"C:\Windows\Fonts\simkai.ttf",    # 楷体
]
FONT_NAME = "ChineseFont"
for fp in FONT_CANDIDATES:
    if os.path.exists(fp):
        pdfmetrics.registerFont(TTFont(FONT_NAME, fp))
        break
else:
    raise RuntimeError("未找到中文字体，请确认 Windows 系统字体目录")

# ── 样式定义 ──────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, fontName=FONT_NAME, **kw)

ST = {
    "name":     S("name",    fontSize=22, leading=28, textColor=colors.HexColor("#1a1a2e"), spaceAfter=2),
    "contact":  S("contact", fontSize=9,  leading=14, textColor=colors.HexColor("#555555")),
    "section":  S("section", fontSize=11, leading=16, textColor=colors.HexColor("#2563eb"),
                  spaceBefore=10, spaceAfter=4),
    "body":     S("body",    fontSize=9,  leading=14, textColor=colors.HexColor("#333333")),
    "bold":     S("bold",    fontSize=9,  leading=14, textColor=colors.HexColor("#111111")),
    "tag":      S("tag",     fontSize=8,  leading=12, textColor=colors.HexColor("#1d4ed8")),
    "sub":      S("sub",     fontSize=8,  leading=12, textColor=colors.HexColor("#666666")),
}

def section_title(text):
    return [
        Paragraph(text, ST["section"]),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#2563eb"), spaceAfter=4),
    ]

def bullet(text, indent=0.3):
    return Paragraph(f"• {text}", ParagraphStyle(
        "bullet", fontName=FONT_NAME, fontSize=9, leading=14,
        leftIndent=indent * cm, textColor=colors.HexColor("#333333")
    ))

def skill_row(skills: list):
    """横排技能标签"""
    text = "  ".join(f"[{s}]" for s in skills)
    return Paragraph(text, ST["tag"])

# ── 简历内容 ──────────────────────────────────────────────────
def build_story():
    story = []

    # 姓名 + 联系方式
    story.append(Paragraph("陈 浩", ST["name"]))
    story.append(Paragraph(
        "应届毕业生  ·  计算机科学与技术  ·  本科  ·  " +
        "chenhao_dev@email.com  ·  138-xxxx-xxxx  ·  GitHub: github.com/chenhao-dev",
        ST["contact"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ── 教育经历 ──
    story.extend(section_title("教育经历"))
    data = [
        [Paragraph("<b>计算机科学与技术，本科</b>", ST["bold"]),
         Paragraph("2021.09 — 2025.06", ST["sub"])],
        [Paragraph("某重点高校  信息工程学院", ST["body"]),
         Paragraph("GPA 3.7 / 4.0  &nbsp; 专业排名 Top 15%", ST["sub"])],
    ]
    story.append(Table(data, colWidths=[12 * cm, 5 * cm],
                       style=TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"),
                                         ("LEFTPADDING", (0,0), (-1,-1), 0),
                                         ("RIGHTPADDING", (0,0), (-1,-1), 0)])))
    story.append(Spacer(1, 0.2 * cm))

    # ── 专业技能 ──
    story.extend(section_title("专业技能"))
    skill_groups = [
        ("后端开发",  ["Java", "Python", "Spring Boot", "FastAPI", "RESTful API"]),
        ("前端开发",  ["Vue 3", "TypeScript", "HTML/CSS", "Axios"]),
        ("数据库",    ["MySQL", "Redis", "PostgreSQL", "SQL优化"]),
        ("工程工具",  ["Git", "Docker", "Linux", "Maven", "Jenkins"]),
        ("算法与基础", ["数据结构", "操作系统", "计算机网络", "设计模式"]),
    ]
    for label, skills in skill_groups:
        row_data = [[Paragraph(label, ST["bold"]), skill_row(skills)]]
        story.append(Table(row_data, colWidths=[3 * cm, 14 * cm],
                           style=TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                                             ("LEFTPADDING", (0,0), (-1,-1), 0),
                                             ("BOTTOMPADDING", (0,0), (-1,-1), 3)])))
    story.append(Spacer(1, 0.1 * cm))

    # ── 实习经历 ──
    story.extend(section_title("实习经历"))

    # 实习 1
    data1 = [
        [Paragraph("<b>后端开发实习生</b>  某互联网科技有限公司", ST["bold"]),
         Paragraph("2024.07 — 2024.12（6个月）", ST["sub"])],
    ]
    story.append(Table(data1, colWidths=[12 * cm, 5 * cm],
                       style=TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"),
                                         ("LEFTPADDING", (0,0), (-1,-1), 0),
                                         ("RIGHTPADDING", (0,0), (-1,-1), 0)])))
    for t in [
        "负责用户中心模块的后端开发，使用 Spring Boot + MySQL 实现用户注册/登录/权限管理接口",
        "引入 Redis 缓存热点数据，接口平均响应时间从 320ms 降低至 85ms，降幅约 73%",
        "参与 CI/CD 流程搭建，使用 Jenkins + Docker 实现自动化部署，发布效率提升 40%",
        "编写单元测试覆盖核心业务逻辑，模块测试覆盖率达到 82%",
    ]:
        story.append(bullet(t))
    story.append(Spacer(1, 0.2 * cm))

    # 实习 2
    data2 = [
        [Paragraph("<b>全栈开发实习生</b>  某数字科技公司", ST["bold"]),
         Paragraph("2023.07 — 2023.09（3个月）", ST["sub"])],
    ]
    story.append(Table(data2, colWidths=[12 * cm, 5 * cm],
                       style=TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"),
                                         ("LEFTPADDING", (0,0), (-1,-1), 0),
                                         ("RIGHTPADDING", (0,0), (-1,-1), 0)])))
    for t in [
        "使用 Vue 3 + TypeScript 开发数据看板前端，对接后端 RESTful API，实现图表实时刷新",
        "协助后端同事重构 Python FastAPI 服务，消除重复代码约 300 行",
    ]:
        story.append(bullet(t))
    story.append(Spacer(1, 0.2 * cm))

    # ── 项目经历 ──
    story.extend(section_title("项目经历"))

    projects = [
        {
            "title": "校园二手交易平台（个人项目）",
            "date": "2024.03 — 2024.06",
            "stack": "Spring Boot · Vue 3 · MySQL · Redis · Docker",
            "points": [
                "独立完成前后端全栈开发，实现商品发布/搜索/即时通讯/订单管理等核心功能",
                "设计并实现基于 Redis 的分布式 Session 方案，支持多端登录管理",
                "使用 Docker Compose 一键部署，GitHub Stars 80+",
            ],
        },
        {
            "title": "智能日程助手（团队项目·负责人）",
            "date": "2023.09 — 2024.01",
            "stack": "FastAPI · PostgreSQL · Vue 3 · Git",
            "points": [
                "带领4人小组完成从需求分析、架构设计到上线部署的全流程",
                "设计 RESTful API 共 28 个接口，编写接口文档并完成前后端联调",
                "荣获校级创新创业项目三等奖",
            ],
        },
    ]
    for proj in projects:
        row = [[Paragraph(f"<b>{proj['title']}</b>", ST["bold"]),
                Paragraph(proj["date"], ST["sub"])]]
        story.append(Table(row, colWidths=[12 * cm, 5 * cm],
                           style=TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"),
                                             ("LEFTPADDING", (0,0), (-1,-1), 0),
                                             ("RIGHTPADDING", (0,0), (-1,-1), 0)])))
        story.append(Paragraph(f"技术栈：{proj['stack']}", ST["sub"]))
        for p in proj["points"]:
            story.append(bullet(p))
        story.append(Spacer(1, 0.15 * cm))

    # ── 获奖荣誉 ──
    story.extend(section_title("获奖荣誉"))
    awards = [
        "2024年  全国大学生计算机设计大赛  省级三等奖",
        "2023年  校级优秀学生干部",
        "2022—2024年  连续三年获校级奖学金（综合排名前10%）",
        "英语六级 CET-6（562分）",
    ]
    for a in awards:
        story.append(bullet(a))

    # ── 自我评价 ──
    story.extend(section_title("自我评价"))
    story.append(Paragraph(
        "具备扎实的计算机基础与全栈开发能力，有两段互联网实习经历，能够独立承担后端模块开发。"
        "学习能力强，适应新技术快；有团队项目管理经验，沟通协调能力良好。"
        "对分布式系统、微服务架构有浓厚兴趣，期望加入技术驱动的团队持续成长。",
        ST["body"]
    ))

    return story


def main():
    out_path = Path(__file__).parent.parent / "data" / "demo_resume.pdf"
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    doc.build(build_story())
    print(f"✅ 简历已生成：{out_path}")
    print(f"   文件大小：{out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
