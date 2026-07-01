# -*- coding: utf-8 -*-
"""
YOUTU-GraphRAG 检索服务适配器
集成 YOUTU-GraphRAG 的核心检索功能
支持使用现有图谱文件进行检索
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
YOUTU_DIR = BASE_DIR / "youtu-graphrag"
LOCAL_MODEL_PATH = str(BASE_DIR / "models" / "all-MiniLM-L6-v2")

sys.path.insert(0, str(YOUTU_DIR))

YOUTU_AVAILABLE = False
KTRetriever = None
GraphQ = None
get_config = None
SentenceTransformer = None

try:
    from models.retriever.enhanced_kt_retriever import KTRetriever
    from models.retriever.agentic_decomposer import GraphQ
    from config import get_config
    from sentence_transformers import SentenceTransformer
    YOUTU_AVAILABLE = True
except ImportError as e:
    print(f"YOUTU-GraphRAG modules not available: {e}")


class YOUTURetrieverService:
    """YOUTU-GraphRAG 检索服务"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if YOUTURetrieverService._initialized:
            return

        self.retriever: Optional[KTRetriever] = None
        self.decomposer: Optional[GraphQ] = None
        self.config = None
        self.schema_path = str(YOUTU_DIR / "schemas" / "career.json")
        self.graph_path = str(YOUTU_DIR / "output" / "graphs" / "career_new.json")
        self.cache_dir = str(YOUTU_DIR / "retriever" / "faiss_cache_new" / "career")

        self.graph_data = None
        self.nodes_index = {}
        self.skills_index = {}
        self.jobs_index = {}
        # 职业路径索引：name -> {"PROMOTES_TO": [...], "TRANSFERS_TO": [...]}
        self.career_paths: Dict[str, Dict] = {}

        self._load_graph()
        self._init_youtu()
        YOUTURetrieverService._initialized = True

    def _load_graph(self):
        """加载图谱数据 - 支持 career_new.json 列表格式"""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    self.graph_data = json.load(f)

                if isinstance(self.graph_data, list):
                    # career_new.json 格式: 关系列表
                    relations = self.graph_data
                    job_attrs: dict = {}  # name -> attrs dict
                    for rel in relations:
                        sp = rel.get("start_node", {}).get("properties", {})
                        ep = rel.get("end_node", {}).get("properties", {})
                        rel_type = rel.get("relation", "")
                        rel_attrs = rel.get("attributes", {})

                        stype = sp.get("schema_type", "")
                        name = sp.get("name", "")

                        if stype == "Job" and name:
                            if name not in job_attrs:
                                # 首次遇到该岗位节点：一并收录数值属性
                                # dim_*_text 由 optimize_graph.py 写入，优先使用
                                job_attrs[name] = {
                                    "name": name, "skills": [], "certificates": [],
                                    "salary_range": "",
                                    "innovation": sp.get("dim_innovation_text", "一般"),
                                    "learning": sp.get("dim_learning_text", "一般"),
                                    "stress_resistance": sp.get("dim_stress_text", "一般"),
                                    "communication": sp.get("dim_communication_text", "一般"),
                                    "internship": sp.get("dim_internship_text", "一般"),
                                    "top_regions": [], "top_industries": [],
                                    # 数值字段（来自 Job 节点 properties，由 optimize_graph.py 写入）
                                    "dim_innovation": sp.get("dim_innovation", 3),
                                    "dim_learning": sp.get("dim_learning", 3),
                                    "dim_stress": sp.get("dim_stress", 3),
                                    "dim_communication": sp.get("dim_communication", 3),
                                    "dim_internship": sp.get("dim_internship", 3),
                                    "salary_avg_k": sp.get("salary_avg_k", 0.0),
                                    "salary_min_k": sp.get("salary_min_k", 0.0),
                                    "salary_max_k": sp.get("salary_max_k", 0.0),
                                    "market_demand": sp.get("market_demand", 0),
                                    "entry_pct": sp.get("entry_pct", 0.0),
                                    "entry_friendly": bool(sp.get("entry_friendly", 0)),
                                }
                            else:
                                # 后续遇到同一岗位：补全可能在首次之前未出现的数值字段
                                entry = job_attrs[name]
                                for num_key in ("dim_innovation","dim_learning","dim_stress",
                                                "dim_communication","dim_internship",
                                                "salary_avg_k","salary_min_k","salary_max_k",
                                                "market_demand","entry_pct"):
                                    if not entry.get(num_key) and sp.get(num_key):
                                        entry[num_key] = sp[num_key]
                                if not entry.get("entry_friendly") and sp.get("entry_friendly"):
                                    entry["entry_friendly"] = bool(sp["entry_friendly"])

                            entry = job_attrs[name]

                            if rel_type == "REQUIRES_SKILL":
                                skill_name = ep.get("name", "")
                                if skill_name and skill_name not in entry["skills"]:
                                    entry["skills"].append(skill_name)
                            elif rel_type == "REQUIRES_CERTIFICATE":
                                cert_name = ep.get("name", "")
                                if cert_name and cert_name not in entry["certificates"]:
                                    entry["certificates"].append(cert_name)
                            elif rel_type == "LOCATED_IN":
                                region = ep.get("name", "")
                                if region and region not in entry["top_regions"]:
                                    entry["top_regions"].append(region)
                            elif rel_type == "BELONGS_TO_INDUSTRY":
                                industry = ep.get("name", "")
                                if industry and industry not in entry["top_industries"]:
                                    entry["top_industries"].append(industry)
                            elif rel_type == "has_attribute":
                                attr_name = ep.get("name", "")
                                raw = ep.get("raw", "")
                                raw_val = raw.split(": ", 1)[1].strip() if ": " in raw else ep.get("value", "")
                                if attr_name == "薪资":
                                    entry["salary_range"] = raw_val
                                # dim_*_text（optimize_graph 写入）已在首次建节点时读取，
                                # has_attribute 的 raw_val 来自 LLM 原始抽取，可能不准，跳过覆盖
                            elif rel_type == "PROMOTES_TO":
                                ename = ep.get("name", "")
                                if ename:
                                    self.career_paths.setdefault(name, {"PROMOTES_TO": [], "TRANSFERS_TO": []})
                                    self.career_paths[name]["PROMOTES_TO"].append({
                                        "target": ename,
                                        "confidence": rel_attrs.get("confidence", 0.5),
                                        "salary_increase": rel_attrs.get("salary_increase", ""),
                                        "skill_overlap": rel_attrs.get("skill_overlap", 0.0),
                                        "description": rel_attrs.get("description", ""),
                                        "shared_skills": rel_attrs.get("shared_skills", []),
                                    })
                            elif rel_type == "TRANSFERS_TO":
                                ename = ep.get("name", "")
                                if ename:
                                    self.career_paths.setdefault(name, {"PROMOTES_TO": [], "TRANSFERS_TO": []})
                                    self.career_paths[name]["TRANSFERS_TO"].append({
                                        "target": ename,
                                        "confidence": rel_attrs.get("confidence", 0.5),
                                        "skill_overlap": rel_attrs.get("skill_overlap", 0.0),
                                        "shared_skills": rel_attrs.get("shared_skills", []),
                                        "description": rel_attrs.get("description", ""),
                                    })

                    for name, attrs in job_attrs.items():
                        node = {"id": f"Job_{name}", "type": "Job", "attributes": attrs}
                        self.nodes_index[node["id"]] = node
                        self.jobs_index[name] = node

                    # 技能索引
                    skill_names: set = set()
                    for rel in relations:
                        ep = rel.get("end_node", {}).get("properties", {})
                        if ep.get("schema_type") == "Skill":
                            sn = ep.get("name", "")
                            if sn and sn not in skill_names:
                                skill_names.add(sn)
                                node = {"id": f"Skill_{sn}", "type": "Skill", "attributes": {"name": sn, "title": sn}}
                                self.nodes_index[node["id"]] = node
                                self.skills_index[sn] = node
                else:
                    # 旧格式: {"nodes": [...], "edges": [...]}
                    nodes = self.graph_data.get("nodes", [])
                    for node in nodes:
                        node_id = node.get("id", "")
                        node_type = node.get("type", "")
                        self.nodes_index[node_id] = node

                        if node_type == "Job":
                            title = node.get("attributes", {}).get("title", "")
                            if title:
                                self.jobs_index[title] = node
                        elif node_type == "Skill":
                            title = node.get("attributes", {}).get("title", "")
                            if title:
                                self.skills_index[title] = node

                print(f"图谱加载成功: {len(self.nodes_index)} 节点")
                print(f"岗位数: {len(self.jobs_index)}, 技能数: {len(self.skills_index)}")

            except Exception as e:
                print(f"加载图谱失败: {e}")

    def _load_chunks_absolute(self):
        """用绝对路径补充加载 chunk 文本到 retriever.chunk2id"""
        if not self.retriever:
            return
        chunk_file = str(YOUTU_DIR / "output" / "chunks" / "career.txt")
        if not os.path.exists(chunk_file):
            print(f"Chunk 文件不存在: {chunk_file}")
            return
        try:
            count = 0
            with open(chunk_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t", 1)
                    if len(parts) == 2 and parts[0].startswith("id:"):
                        chunk_id = parts[0][4:].strip()
                        chunk_text = parts[1].replace("Chunk: ", "", 1) if parts[1].startswith("Chunk: ") else parts[1]
                        if chunk_id and chunk_text:
                            self.retriever.chunk2id[chunk_id] = chunk_text
                            count += 1
            print(f"Chunk 文本加载成功: {count} 条")
        except Exception as e:
            print(f"加载 chunk 文本失败: {e}")

    def _init_youtu(self):
        """初始化 YOUTU-GraphRAG 组件"""
        if not YOUTU_AVAILABLE:
            print("YOUTU-GraphRAG not available, using built-in retrieval")
            return

        print("初始化 YOUTU-GraphRAG 组件...")

        try:
            if get_config:
                try:
                    self.config = get_config()
                except Exception as e:
                    print(f"加载配置失败: {e}")
                    self.config = None

            os.makedirs(self.cache_dir, exist_ok=True)

            if SentenceTransformer is None:
                print("SentenceTransformer 未导入，使用内置检索")
                return

            print(f"加载本地模型: {LOCAL_MODEL_PATH}")
            if os.path.exists(LOCAL_MODEL_PATH):
                qa_encoder = SentenceTransformer(LOCAL_MODEL_PATH)
                print("本地模型加载成功")
            else:
                print(f"本地模型路径不存在: {LOCAL_MODEL_PATH}")
                print("尝试使用模型名称加载...")
                qa_encoder = SentenceTransformer('all-MiniLM-L6-v2')

            if os.path.exists(self.graph_path):
                try:
                    print("初始化 KTRetriever...")
                    # top_k: 优先读 config（base_config.yaml retrieval.top_k=30），
                    # 传入 5 时 KTRetriever 会自动从 config 读取，避免硬编码覆盖
                    self.retriever = KTRetriever(
                        dataset="career",
                        json_path=self.graph_path,
                        device="cpu",
                        cache_dir=self.cache_dir,
                        top_k=5,
                        recall_paths=2,
                        schema_path=self.schema_path,
                        mode="agent",
                        config=self.config,
                        qa_encoder=qa_encoder
                    )
                    # 构建 FAISS 索引（含节点/关系向量索引，第一次耗时，之后走缓存）
                    print("构建 FAISS 向量索引...")
                    self.retriever.build_indices()
                    # 补充加载 chunk 文本（使用绝对路径，避免工作目录问题）
                    self._load_chunks_absolute()
                    print("KTRetriever 初始化成功，FAISS 索引就绪")
                except Exception as e:
                    print(f"KTRetriever 初始化失败: {e}")
                    import traceback
                    traceback.print_exc()

            try:
                print("初始化 GraphQ...")
                self.decomposer = GraphQ(
                    dataset_name="career",
                    config=self.config
                )
                print("GraphQ 初始化成功")
            except Exception as e:
                print(f"GraphQ 初始化失败: {e}")

        except Exception as e:
            print(f"YOUTU-GraphRAG 初始化错误: {e}")
            import traceback
            traceback.print_exc()

    async def query(self, question: str, top_k: int = 10) -> Dict[str, Any]:
        """
        智能问答接口

        Args:
            question: 用户问题
            top_k: 返回结果数量

        Returns:
            包含答案和相关信息的字典
        """
        result = {
            "question": question,
            "answer": "",
            "triples": [],
            "chunk_ids": [],
            "context": "",
            "related_jobs": [],
            "related_skills": []
        }

        # ── 优先委托独立检索微服务（配置 RETRIEVAL_SERVICE_URL 时）──
        # 结构化索引/匹配 encoder 仍在进程内；此处仅把重型 NL 检索外置，可独立扩容。
        try:
            from app.services.retrieval_client import retrieval_client
            if retrieval_client.enabled:
                remote = await retrieval_client.query(question, top_k=top_k)
                if remote is not None:
                    # 远程结果合并本地结构化检索（jobs/skills 来自进程内索引）
                    remote.setdefault("related_jobs", self._search_jobs(question)[:5])
                    remote.setdefault("related_skills", self._search_skills(question)[:10])
                    return remote
                # remote 不可用 → 落到进程内逻辑（降级）
        except Exception as e:
            print(f"[retrieval] 委托远程失败，降级进程内: {e}")

        if self.retriever:
            try:
                # ── Step 1: intent-based involved_types routing（关键词路由）
                involved_types = self._intent_involved_types(question)

                # ── Step 2: 查询分解
                #    优先用官方 GraphQ decomposer（YOUTU 模块可用时）；
                #    否则用 Gap 2 LLM 分解器（论文 3.3 节）
                sub_questions: List[str] = []
                decomposed = None

                if self.decomposer:
                    try:
                        decomposed = self.decomposer.decompose(question, self.schema_path)
                        decomposer_types = decomposed.get("involved_types", {})
                        if decomposer_types and not involved_types:
                            involved_types = decomposer_types
                        sub_questions = decomposed.get("sub_questions", [])
                    except Exception as e:
                        print(f"[GraphQ分解] 失败: {e}")

                if not sub_questions:
                    # Gap 2：LLM Schema 增强分解作为 fallback
                    llm_subs = await self._llm_decompose_query(question)
                    if llm_subs:
                        sub_questions = llm_subs
                        result["decomposed"] = llm_subs
                        print(f"[Gap2-LLM分解] {len(llm_subs)} 个子查询: {llm_subs}")

                # ── Step 3: 检索（含 Gap 3 迭代反思，最多 2 轮）
                MAX_REFLECT = 2
                current_top_k = top_k

                for reflect_round in range(MAX_REFLECT + 1):
                    # 优先并行子问题检索；该 KTRetriever 版本若无此方法，
                    # 退回单问检索（process_retrieval_results 可用且有效），
                    # 避免直接异常跌入 LLM-only 兜底，保留真实图谱检索质量。
                    if sub_questions and hasattr(self.retriever, "process_subquestions_parallel"):
                        raw, _ = self.retriever.process_subquestions_parallel(
                            sub_questions,
                            top_k=current_top_k,
                            involved_types=involved_types,
                        )
                    else:
                        raw, _ = self.retriever.process_retrieval_results(
                            question,
                            top_k=current_top_k,
                            involved_types=involved_types,
                        )

                    all_triples    = raw.get("triples", [])
                    chunk_ids      = raw.get("chunk_ids", [])
                    chunk_contents = raw.get("chunk_contents", {})

                    triples_list   = all_triples[:current_top_k] if isinstance(all_triples, list) else list(all_triples)[:current_top_k]
                    chunk_ids_list = list(chunk_ids)[:current_top_k] if not isinstance(chunk_ids, list) else chunk_ids[:current_top_k]
                    ctx            = self._build_context(all_triples, chunk_contents, chunk_ids_list)[:4000]

                    # Gap 3：反思判断（最后一轮不再反思）
                    if reflect_round < MAX_REFLECT:
                        sufficient = await self._reflect(question, ctx)
                        if sufficient:
                            print(f"[Gap3-反思] 第{reflect_round+1}轮上下文充足，跳出")
                            break
                        else:
                            current_top_k = min(current_top_k * 2, 40)
                            print(f"[Gap3-反思] 第{reflect_round+1}轮不足，扩大top_k→{current_top_k}重检索")
                    # 最后一轮直接使用结果

                result["triples"]   = triples_list
                result["chunk_ids"] = chunk_ids_list
                result["context"]   = ctx
                if decomposed:
                    result["decomposed"] = decomposed.get("sub_questions", [])

                answer = self.retriever.generate_answer(
                    self.retriever.generate_prompt(question, result["context"])
                )
                result["answer"] = answer

            except Exception as e:
                print(f"YOUTU 查询错误: {e}")
                result = await self._fallback_query(question, result)
        else:
            result = await self._fallback_query(question, result)

        related_jobs = self._search_jobs(question)
        related_skills = self._search_skills(question)
        result["related_jobs"] = related_jobs[:5]
        result["related_skills"] = related_skills[:10]

        return result

    async def _fallback_query(self, question: str, result: Dict) -> Dict:
        """降级查询方法 - 使用内置检索"""
        related_jobs = self._search_jobs(question)
        related_skills = self._search_skills(question)

        context_parts = []

        if related_jobs:
            context_parts.append("相关岗位:")
            for job in related_jobs[:3]:
                attrs = job.get("attributes", {})
                context_parts.append(f"- {attrs.get('title', 'N/A')}: 薪资 {attrs.get('salary_range', 'N/A')}")
                skills = attrs.get("skills", [])[:5]
                if skills:
                    context_parts.append(f"  技能要求: {', '.join(skills)}")

        if related_skills:
            context_parts.append("\n相关技能:")
            for skill in related_skills[:5]:
                attrs = skill.get("attributes", {})
                context_parts.append(f"- {attrs.get('title', 'N/A')}")

        result["context"] = "\n".join(context_parts)
        result["related_jobs"] = related_jobs[:5]
        result["related_skills"] = related_skills[:10]

        try:
            from app.core.llm_service import llm_service
            prompt = f"""根据以下职业信息回答问题：

{result["context"]}

问题：{question}

请提供详细、准确的回答："""

            answer = await llm_service.chat([{"role": "user", "content": prompt}])
            result["answer"] = answer
        except Exception as e:
            result["answer"] = f"无法获取答案: {str(e)}"

        return result

    def _search_jobs(self, query: str) -> List[Dict]:
        """搜索相关岗位"""
        results = []
        query_lower = query.lower()

        for title, node in self.jobs_index.items():
            if query_lower in title.lower():
                results.append(node)

        if not results:
            for title, node in self.jobs_index.items():
                attrs = node.get("attributes", {})
                skills = attrs.get("skills", [])
                if any(query_lower in str(s).lower() for s in skills):
                    results.append(node)

        return results[:10]

    def _search_skills(self, query: str) -> List[Dict]:
        """搜索相关技能"""
        results = []
        query_lower = query.lower()

        for title, node in self.skills_index.items():
            if query_lower in title.lower():
                results.append(node)

        return results[:10]

    # ──────────────────────────────────────────────────────────────
    # Gap 2：Schema 增强查询分解（论文 3.3 节）
    # ──────────────────────────────────────────────────────────────

    _SCHEMA_DESC = (
        "节点类型：Job（岗位）| Skill（技能）| Certificate（证书）\n"
        "关系类型：REQUIRES_SKILL | PROMOTES_TO（晋升路径）| "
        "TRANSFERS_TO（换岗路径）| REQUIRES_CERTIFICATE | has_attribute\n"
        "属性类型：salary_avg_k | dim_innovation | dim_learning | "
        "dim_stress | dim_communication | entry_pct | skill_overlap | shared_skills"
    )

    async def _llm_decompose_query(self, question: str) -> List[str]:
        """
        论文 3.3 节 Schema-Enhanced Query Decomposer：
        用 LLM 将复杂查询分解为 2-3 个 Schema 对齐的原子子查询，
        每个子查询对应图谱中的一种关系类型或节点类型。
        失败时返回空列表（调用方降级到关键词路由）。
        """
        from app.core.llm_service import llm_service
        import re

        prompt = (
            f"你是职业规划知识图谱的查询分解器。\n"
            f"图谱 Schema：\n{self._SCHEMA_DESC}\n\n"
            f"将以下查询分解为 2-3 个原子子查询，"
            f"每个子查询聚焦 Schema 中的一种关系或节点类型。\n"
            f"若查询已足够简单（单一意图），只返回 1 个子查询。\n\n"
            f"查询：{question}\n\n"
            f'只返回 JSON，格式：{{"sub_queries": ["子查询1", "子查询2"]}}'
        )
        try:
            resp = await llm_service.chat([{"role": "user", "content": prompt}], temperature=0.1)
            m = re.search(r'\{.*\}', resp, re.DOTALL)
            if m:
                data = json.loads(m.group())
                subs = data.get("sub_queries", [])
                if isinstance(subs, list) and subs:
                    return [s for s in subs if isinstance(s, str) and s.strip()]
        except Exception as e:
            print(f"[LLM分解] 失败: {e}")
        return []

    # ──────────────────────────────────────────────────────────────
    # Gap 3：迭代推理反思（论文 3.3 节 公式9）
    # ──────────────────────────────────────────────────────────────

    async def _reflect(self, question: str, context: str) -> bool:
        """
        论文 3.3 节 Iterative Reasoning & Reflection：
        A(t) = fLLM(qt | Reasoning, H(t-1) | Reflection)
        判断当前检索上下文是否足以回答问题。
        返回 True = 足够；False = 需要扩大检索范围。
        出错时默认返回 True，不触发重检索。
        """
        from app.core.llm_service import llm_service

        prompt = (
            f"判断以下检索结果是否足以回答职业规划问题。\n"
            f"只回答 yes（足够）或 no（不足够），不要其他内容。\n\n"
            f"问题：{question}\n"
            f"检索结果摘要：{context[:600]}"
        )
        try:
            resp = await llm_service.chat([{"role": "user", "content": prompt}], temperature=0)
            return "yes" in resp.strip().lower()
        except Exception as e:
            print(f"[反思] 失败: {e}")
            return True  # 默认足够，避免无限重检索

    def _intent_involved_types(self, question: str) -> Dict[str, Any]:
        """
        P2.2: 根据查询意图返回对应的 involved_types，
        引导检索层优先召回最相关的边类型。

        意图分类（关键词匹配）：
          - promote  : 晋升、升职、职业发展路径、往上走
          - transfer : 转岗、跨行、换工作、转型、换岗
          - portrait : 岗位要求、技能要求、需要什么证书、什么能力
          - match    : 匹配、适合我、推荐岗位、我能做什么
        """
        q = question
        PROMOTE_KW  = ["晋升", "升职", "晋级", "往上", "向上发展", "升迁", "提升职级", "职业发展路径", "PROMOTES_TO"]
        TRANSFER_KW = ["转岗", "转型", "换岗", "跨行", "换工作", "换职业", "平行转", "TRANSFERS_TO", "相关岗位"]
        PORTRAIT_KW = ["岗位要求", "技能要求", "需要什么", "证书", "能力要求", "画像", "职位描述", "岗位特点", "岗位详情"]
        MATCH_KW    = ["匹配", "适合", "推荐", "我能做", "我适合", "找工作", "求职", "人岗"]

        if any(kw in q for kw in PROMOTE_KW):
            return {
                "nodes": ["Job"],
                "relations": ["PROMOTES_TO"],
                "attributes": ["salary_increase", "skill_overlap", "level_diff"]
            }
        if any(kw in q for kw in TRANSFER_KW):
            return {
                "nodes": ["Job"],
                "relations": ["TRANSFERS_TO"],
                "attributes": ["shared_skills"]
            }
        if any(kw in q for kw in PORTRAIT_KW):
            return {
                "nodes": ["Job", "Skill", "Certificate"],
                "relations": ["REQUIRES_SKILL", "REQUIRES_CERTIFICATE", "has_attribute"],
                "attributes": []
            }
        if any(kw in q for kw in MATCH_KW):
            return {
                "nodes": ["Job", "Skill", "Certificate"],
                "relations": ["REQUIRES_SKILL", "REQUIRES_CERTIFICATE", "has_attribute", "PROMOTES_TO", "TRANSFERS_TO"],
                "attributes": ["salary_increase", "shared_skills"]
            }
        # 默认：不限制，让 FAISS 自由召回
        return {}

    def _build_context(self, triples: List[str], chunk_contents,
                        chunk_ids: List[str] = None) -> str:
        """构建上下文（优先从 KTRetriever.chunk2id 取原文）

        chunk_contents 可能是：
          - Dict[str, str]：chunk_id -> chunk_text（旧格式/子问题路径）
          - List[str]：chunk_text 列表（process_retrieval_results 返回格式）
        两种情况均兼容处理。
        """
        context_parts = []

        if triples:
            context_parts.append("相关知识三元组:")
            for i, triple in enumerate(triples[:20]):
                if isinstance(triple, str):
                    context_parts.append(f"{i+1}. {triple}")

        # 将 chunk_contents 统一规范为 Dict[str, str]
        if isinstance(chunk_contents, list):
            # process_retrieval_results 返回 List[str]（纯文本），无 ID 可用
            # 用 chunk_ids 作为键（若有），否则用序号
            if chunk_ids:
                chunk_contents_dict = {cid: chunk_contents[i] for i, cid in enumerate(chunk_ids) if i < len(chunk_contents)}
            else:
                chunk_contents_dict = {str(i): text for i, text in enumerate(chunk_contents)}
        elif isinstance(chunk_contents, dict):
            chunk_contents_dict = chunk_contents
        else:
            chunk_contents_dict = {}

        # 优先用 KTRetriever 内置的 chunk2id 字典取原文（通过 chunk_ids 查询）
        resolved: Dict[str, str] = {}
        if self.retriever and hasattr(self.retriever, "chunk2id") and self.retriever.chunk2id:
            ids_to_lookup = list(chunk_contents_dict.keys()) if chunk_contents_dict else []
            if chunk_ids:
                ids_to_lookup = list(set(ids_to_lookup) | set(chunk_ids))
            for cid in ids_to_lookup[:8]:
                text = self.retriever.chunk2id.get(cid, "")
                if text:
                    resolved[cid] = text
                elif cid in chunk_contents_dict:
                    resolved[cid] = chunk_contents_dict[cid]
        else:
            resolved = dict(list(chunk_contents_dict.items())[:8]) if chunk_contents_dict else {}

        if resolved:
            context_parts.append("\n相关文档片段:")
            for i, (chunk_id, content) in enumerate(list(resolved.items())[:5]):
                content_str = content[:400] if isinstance(content, str) else str(content)[:400]
                context_parts.append(f"[{chunk_id}] {content_str}")

        return "\n".join(context_parts)

    # ──────────────────────────────────────────────────────────────
    # 四层检索接口（核心：深度利用 Youtu-GraphRAG）
    # ──────────────────────────────────────────────────────────────

    def retrieve_by_entity(self, query: str, top_k: int = 8) -> Dict[str, Any]:
        """
        L2 实体+关系层检索（FAISS 向量相似度）
        返回与 query 语义最近的实体节点和关系三元组
        """
        if not self.retriever:
            return {"nodes": [], "triples": [], "context": ""}
        try:
            q_embed, result = self.retriever.retrieve(query)
            path1 = result.get("path1_results", {})
            top_nodes = path1.get("top_nodes", [])[:top_k]
            triples = path1.get("triples", [])[:top_k]

            node_texts = []
            for nid in top_nodes:
                text = self.retriever._get_node_text(nid)
                if text and len(text) > 2:
                    node_texts.append(f"[{nid}] {text}")

            triple_texts = []
            for t in triples:
                if isinstance(t, (list, tuple)) and len(t) >= 3:
                    triple_texts.append(f"{t[0]} → {t[1]} → {t[2]}")
                elif isinstance(t, str):
                    triple_texts.append(t)

            context = ""
            if node_texts:
                context += "实体层检索结果：\n" + "\n".join(node_texts[:6]) + "\n"
            if triple_texts:
                context += "\n关系三元组：\n" + "\n".join(triple_texts[:6])

            return {"nodes": top_nodes, "triples": triple_texts, "context": context}
        except Exception as e:
            print(f"L2实体检索失败: {e}")
            return {"nodes": [], "triples": [], "context": ""}

    def retrieve_by_keyword(self, query: str, top_k: int = 8) -> Dict[str, Any]:
        """
        L3 关键词层检索（词法匹配 + 向量扩展）
        返回与 query 关键词匹配的概念节点
        """
        if not self.retriever:
            return {"nodes": [], "context": ""}
        try:
            q_embed = self.retriever._get_query_embedding(query)
            kw_result = self.retriever._keyword_strategy(query, q_embed)
            kw_nodes = kw_result.get("top_nodes", [])[:top_k]

            node_texts = []
            for nid in kw_nodes:
                text = self.retriever._get_node_text(nid)
                if text and len(text) > 2:
                    node_texts.append(f"[关键词] {text}")

            context = ""
            if node_texts:
                context = "关键词层检索结果：\n" + "\n".join(node_texts[:6])

            return {"nodes": kw_nodes, "context": context}
        except Exception as e:
            print(f"L3关键词检索失败: {e}")
            return {"nodes": [], "context": ""}

    def retrieve_by_community(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        L4 社区层检索（行业/岗位群宏观视角）
        返回 query 相关的岗位社区摘要
        """
        if not self.retriever or not hasattr(self.retriever, "faiss_retriever"):
            return {"communities": [], "context": ""}
        try:
            q_embed = self.retriever._get_query_embedding(query)
            # transform to FAISS-compatible format
            import torch
            if isinstance(q_embed, torch.Tensor):
                q_np = q_embed.cpu().numpy().reshape(1, -1)
            else:
                import numpy as np
                q_np = np.array(q_embed, dtype="float32").reshape(1, -1)

            faiss_r = self.retriever.faiss_retriever
            comm_nodes = []
            if hasattr(faiss_r, "retrieve_via_communities"):
                comm_nodes = faiss_r.retrieve_via_communities(q_embed, top_k=top_k)

            node_texts = []
            for nid in comm_nodes:
                text = self.retriever._get_node_text(nid)
                if text and len(text) > 2:
                    node_texts.append(f"[社区] {text}")

            context = ""
            if node_texts:
                context = "社区层检索结果（行业宏观）：\n" + "\n".join(node_texts[:top_k])

            return {"communities": comm_nodes, "context": context}
        except Exception as e:
            print(f"L4社区检索失败: {e}")
            return {"communities": [], "context": ""}

    def retrieve_by_attribute(self, job_name: str, attr_type: str = "all") -> Dict[str, Any]:
        """
        L1 属性层检索（直接从图谱节点提取结构化属性）
        attr_type: 'skills' / 'salary' / 'ability' / 'all'
        """
        # 先从 jobs_index（内置）快速查
        result: Dict[str, Any] = {
            "job": job_name, "skills": [], "salary": "",
            "innovation": "", "learning": "", "stress": "",
            "communication": "", "internship": "", "context": ""
        }
        if job_name in self.jobs_index:
            attrs = self.jobs_index[job_name].get("attributes", {})
            result.update({
                "skills": attrs.get("skills", []),
                "salary": attrs.get("salary_range", ""),
                "innovation": attrs.get("innovation", ""),
                "learning": attrs.get("learning", ""),
                "stress": attrs.get("stress_resistance", ""),
                "communication": attrs.get("communication", ""),
                "internship": attrs.get("internship", ""),
            })

        # 再用 KTRetriever 的节点属性接口补充
        if self.retriever:
            try:
                # 查找图中该岗位的节点 ID
                for nid in self.retriever.graph.nodes():
                    node_data = self.retriever.graph.nodes[nid]
                    props = node_data.get("properties", node_data)
                    if props.get("schema_type") == "Job" and props.get("name") == job_name:
                        raw_props = self.retriever._get_node_properties(nid)
                        if raw_props:
                            result["context"] = f"[属性层-{job_name}]\n{raw_props[:500]}"
                        break
            except Exception as e:
                print(f"L1属性检索失败: {e}")

        # 生成上下文摘要
        if not result["context"]:
            lines = [f"[属性层-{job_name}]"]
            if result["skills"]:
                lines.append(f"核心技能: {', '.join(result['skills'][:8])}")
            if result["salary"]:
                lines.append(f"薪资范围: {result['salary']}")
            for dim in ["innovation", "learning", "stress", "communication", "internship"]:
                val = result.get(dim, "")
                if val:
                    label = {"innovation":"创新","learning":"学习","stress":"抗压",
                             "communication":"沟通","internship":"实习能力"}.get(dim, dim)
                    lines.append(f"{label}: {val}")
            result["context"] = "\n".join(lines)

        return result

    def retrieve_multilayer(
        self, query: str, job_name: str = "", top_k: int = 6
    ) -> Dict[str, Any]:
        """
        多层融合检索（L1+L2+L3+L4）
        为 IRCoT 工具调用提供完整的多粒度上下文
        """
        layers: Dict[str, Any] = {
            "entity": {}, "keyword": {}, "community": {}, "attribute": {},
            "combined_context": ""
        }
        context_parts = []

        # L2 实体层
        entity_res = self.retrieve_by_entity(query, top_k=top_k)
        layers["entity"] = entity_res
        if entity_res.get("context"):
            context_parts.append(entity_res["context"])

        # L3 关键词层
        kw_res = self.retrieve_by_keyword(query, top_k=top_k)
        layers["keyword"] = kw_res
        if kw_res.get("context"):
            context_parts.append(kw_res["context"])

        # L1 属性层（需要指定岗位）
        if job_name:
            attr_res = self.retrieve_by_attribute(job_name)
            layers["attribute"] = attr_res
            if attr_res.get("context"):
                context_parts.append(attr_res["context"])

        # L4 社区层
        comm_res = self.retrieve_by_community(query, top_k=3)
        layers["community"] = comm_res
        if comm_res.get("context"):
            context_parts.append(comm_res["context"])

        layers["combined_context"] = "\n\n".join(context_parts)
        return layers

    def retrieve_job_info(self, job_name: str) -> Dict[str, Any]:
        """
        检索岗位信息

        Args:
            job_name: 岗位名称

        Returns:
            岗位信息字典
        """
        if job_name in self.jobs_index:
            node = self.jobs_index[job_name]
            attrs = node.get("attributes", {})

            return {
                "title": attrs.get("title", job_name),
                "job_count": attrs.get("job_count", 0),
                "salary_range": attrs.get("salary_range", ""),
                "salary_min": attrs.get("salary_min", 0),
                "salary_max": attrs.get("salary_max", 0),
                "salary_avg": attrs.get("salary_avg", 0),
                "skills": attrs.get("skills", []),
                "skill_frequencies": attrs.get("skill_frequencies", {}),
                "innovation": attrs.get("innovation", ""),
                "learning": attrs.get("learning", ""),
                "stress_resistance": attrs.get("stress_resistance", ""),
                "communication": attrs.get("communication", ""),
                "internship": attrs.get("internship", ""),
                "certificates": attrs.get("certificates", []),
                "job_description": attrs.get("job_description", ""),
                "requirements": attrs.get("requirements", ""),
                "top_regions": attrs.get("top_regions", []),
                "top_industries": attrs.get("top_industries", []),
                "top_companies": attrs.get("top_companies", [])
            }

        return {"error": f"未找到岗位: {job_name}"}

    def find_similar_jobs(self, job_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        查找相似岗位

        Args:
            job_name: 岗位名称
            top_k: 返回数量

        Returns:
            相似岗位列表
        """
        if job_name not in self.jobs_index:
            return []

        source_job = self.jobs_index[job_name]
        source_skills = set(source_job.get("attributes", {}).get("skills", []))

        similar_jobs = []

        for title, node in self.jobs_index.items():
            if title == job_name:
                continue

            target_skills = set(node.get("attributes", {}).get("skills", []))
            shared_skills = source_skills & target_skills

            if shared_skills:
                similarity = len(shared_skills) / max(len(source_skills), 1)
                similar_jobs.append({
                    "title": title,
                    "similarity": round(similarity, 2),
                    "shared_skills": list(shared_skills)[:5],
                    "salary_range": node.get("attributes", {}).get("salary_range", "")
                })

        similar_jobs.sort(key=lambda x: x["similarity"], reverse=True)

        return similar_jobs[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "retriever_initialized": self.retriever is not None,
            "decomposer_initialized": self.decomposer is not None,
            "graph_path": self.graph_path,
            "graph_exists": os.path.exists(self.graph_path),
            "graph_loaded": self.graph_data is not None,
            "nodes_count": len(self.nodes_index),
            "jobs_count": len(self.jobs_index),
            "skills_count": len(self.skills_index),
            "cache_dir": self.cache_dir,
            "config_loaded": self.config is not None
        }


youtu_retriever_service = YOUTURetrieverService()
