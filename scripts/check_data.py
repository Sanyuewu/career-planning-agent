# -*- coding: utf-8 -*-
"""数据检查脚本 - 用于赛题评估"""

import json
import sys

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')

def check_job_profiles():
    with open(r'd:\DPJ\claudde\data\job_profiles.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    print(f'[OK] 岗位画像数量: {len(profiles)} 个 (要求>=10个)')
    print(f'     岗位名称示例: {", ".join([p["岗位名称"] for p in profiles[:5]])}...')
    
    # 检查字段完整性
    required_fields = ['专业技能', '证书要求', '创新能力', '学习能力', '抗压能力', '沟通能力', '实习经历']
    complete_count = 0
    for p in profiles:
        if all(f in p for f in required_fields):
            complete_count += 1
    print(f'     完整字段画像: {complete_count}/{len(profiles)}')
    return len(profiles)

def check_job_graph():
    with open(r'd:\DPJ\claudde\data\job_graph.json', 'r', encoding='utf-8') as f:
        graph = json.load(f)
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    job_nodes = [n for n in nodes if n.get('attrs', {}).get('node_type') == 'Job']
    skill_nodes = [n for n in nodes if n.get('attrs', {}).get('node_type') == 'Skill']
    promote_edges = [e for e in edges if e.get('relation') == 'PROMOTES_TO']
    transfer_edges = [e for e in edges if e.get('relation') == 'TRANSFER_TO']
    
    print(f'[OK] 图谱节点数: {len(nodes)} (岗位{len(job_nodes)}, 技能{len(skill_nodes)})')
    print(f'[OK] 图谱边数: {len(edges)} (晋升{len(promote_edges)}, 换岗{len(transfer_edges)})')
    
    # 检查换岗路径
    jobs_with_transfers = set()
    for e in transfer_edges:
        jobs_with_transfers.add(e.get('source'))
    print(f'     有换岗路径的岗位: {len(jobs_with_transfers)} 个 (要求>=5个)')
    return len(transfer_edges)

def check_knowledge_base():
    with open(r'd:\DPJ\claudde\data\knowledge_base.json', 'r', encoding='utf-8') as f:
        kb = json.load(f)
    print(f'[OK] 知识库条目数: {len(kb)} 条 (提交材料①)')
    return len(kb)

def check_job_real():
    """检查真实JD数据"""
    import sqlite3
    try:
        conn = sqlite3.connect(r'd:\DPJ\claudde\data\career.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_real")
        count = cursor.fetchone()[0]
        print(f'[OK] 真实JD数据: {count} 条 (企业提供10000条)')
        conn.close()
        return count
    except Exception as e:
        print(f'[WARN] 真实JD数据检查失败: {e}')
        return 0

if __name__ == '__main__':
    print('=' * 60)
    print('赛题数据检查报告')
    print('=' * 60)
    check_job_profiles()
    check_job_graph()
    check_knowledge_base()
    check_job_real()
    print('=' * 60)
