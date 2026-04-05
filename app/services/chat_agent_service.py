# -*- coding: utf-8 -*-
"""
对话智能体服务 - 8状态FSM + 情绪感知(I2)
遵循v5规范：状态机驱动对话，情绪检测阈值0.35
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from pydantic import BaseModel, Field

from app.ai.llm_client import llm_client, render_prompt

logger = logging.getLogger(__name__)


class ChatState(str, Enum):
    """对话状态枚举 - 9状态FSM（含 C-3 报告调优状态）"""
    GREETING = "GREETING"
    PORTRAIT_FILLING = "PORTRAIT_FILLING"
    INTENT_CONFIRM = "INTENT_CONFIRM"
    MATCH_ANALYSIS = "MATCH_ANALYSIS"
    REPORT_REVIEW = "REPORT_REVIEW"
    REPORT_REFINE = "REPORT_REFINE"   # C-3: 多轮报告调优
    EMOTION_SUPPORT = "EMOTION_SUPPORT"
    CAREER_GUIDANCE = "CAREER_GUIDANCE"
    END = "END"


class EmotionType(str, Enum):
    """情绪类型"""
    CALM = "calm"
    ANXIOUS = "anxious"
    CONFUSED = "confused"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"


class ChatMessage(BaseModel):
    """对话消息"""
    role: str = Field(description="user或assistant")
    content: str
    state: Optional[ChatState] = None
    emotion: Optional[EmotionType] = None
    timestamp: Optional[str] = None


class ChatSession(BaseModel):
    """对话会话"""
    session_id: str
    state: ChatState = ChatState.GREETING
    messages: List[ChatMessage] = Field(default_factory=list)
    student_portrait: Dict = Field(default_factory=dict)
    emotion_history: List[Dict] = Field(default_factory=list)
    current_emotion: Optional[EmotionType] = None
    emotion_score: float = 1.0
    turn_count: int = 0
    missing_dims: List[str] = Field(default_factory=list)
    student_id: Optional[str] = None
    # P1-FSM: 记录进入当前状态时的 turn_count，用于状态内轮次计数
    state_since_turn: int = 0


STATE_TRANSITIONS = {
    ChatState.GREETING: {
        "next": [ChatState.PORTRAIT_FILLING, ChatState.EMOTION_SUPPORT],
        "triggers": {
            "basic_info_collected": ChatState.PORTRAIT_FILLING,
            "emotion_negative": ChatState.EMOTION_SUPPORT,
        }
    },
    ChatState.PORTRAIT_FILLING: {
        "next": [ChatState.INTENT_CONFIRM, ChatState.EMOTION_SUPPORT],
        "triggers": {
            "portrait_complete": ChatState.INTENT_CONFIRM,
            "emotion_negative": ChatState.EMOTION_SUPPORT,
        }
    },
    ChatState.INTENT_CONFIRM: {
        "next": [ChatState.MATCH_ANALYSIS, ChatState.CAREER_GUIDANCE],
        "triggers": {
            "intent_confirmed": ChatState.MATCH_ANALYSIS,
            "need_guidance": ChatState.CAREER_GUIDANCE,
        }
    },
    ChatState.MATCH_ANALYSIS: {
        "next": [ChatState.REPORT_REVIEW, ChatState.CAREER_GUIDANCE, ChatState.PORTRAIT_FILLING],
        "triggers": {
            "analysis_done": ChatState.REPORT_REVIEW,
            "need_guidance": ChatState.CAREER_GUIDANCE,
            "portrait_update": ChatState.PORTRAIT_FILLING,   # 用户要求修改技能/信息
        }
    },
    ChatState.REPORT_REVIEW: {
        "next": [ChatState.END, ChatState.CAREER_GUIDANCE, ChatState.REPORT_REFINE, ChatState.PORTRAIT_FILLING],
        "triggers": {
            "user_satisfied": ChatState.END,
            "need_guidance": ChatState.CAREER_GUIDANCE,
            "request_refine": ChatState.REPORT_REFINE,
            "portrait_update": ChatState.PORTRAIT_FILLING,   # 用户要求修改信息后重新匹配
        }
    },
    ChatState.REPORT_REFINE: {
        "next": [ChatState.REPORT_REVIEW, ChatState.END],
        "triggers": {
            "refine_done": ChatState.REPORT_REVIEW,
            "end_session": ChatState.END,
        }
    },
    ChatState.EMOTION_SUPPORT: {
        "next": [ChatState.PORTRAIT_FILLING, ChatState.INTENT_CONFIRM, ChatState.END],
        "triggers": {
            "emotion_recovered": ChatState.PORTRAIT_FILLING,
            "continue_later": ChatState.END,
        }
    },
    ChatState.CAREER_GUIDANCE: {
        "next": [ChatState.MATCH_ANALYSIS, ChatState.REPORT_REVIEW, ChatState.END, ChatState.PORTRAIT_FILLING],
        "triggers": {
            "guidance_done": ChatState.MATCH_ANALYSIS,
            "back_to_report": ChatState.REPORT_REVIEW,
            "end_session": ChatState.END,
            "portrait_update": ChatState.PORTRAIT_FILLING,   # 用户要求修改技能/信息
        }
    },
    ChatState.END: {
        "next": [ChatState.GREETING],
        "triggers": {
            "restart": ChatState.GREETING,
        }
    },
}

EMOTION_KEYWORDS = {
    EmotionType.ANXIOUS: ["焦虑", "紧张", "害怕", "担心", "压力大", "不知道怎么办", "迷茫", "慌", "怕"],
    EmotionType.CONFUSED: ["不懂", "不明白", "不清楚", "搞不懂", "什么意思", "怎么选"],
    EmotionType.FRUSTRATED: ["烦", "没意思", "不想", "算了", "放弃", "没用", "没希望"],
    EmotionType.EXCITED: ["太好了", "谢谢", "有帮助", "很有用", "明白了", "清晰了"],
}

# 否定前缀：出现在关键词前3字符内则不计入情绪
_NEGATION_PREFIXES = ["没有", "不会", "不是", "并不", "没啥", "不太", "不那么", "不感到", "不觉得"]

ANXIETY_THRESHOLD = 0.35


def _count_keywords_with_negation(text: str, keywords: List[str]) -> int:
    """统计关键词出现次数，跳过被否定词修饰的关键词"""
    count = 0
    for kw in keywords:
        start = 0
        while True:
            pos = text.find(kw, start)
            if pos == -1:
                break
            prefix = text[max(0, pos - 4):pos]
            if not any(neg in prefix for neg in _NEGATION_PREFIXES):
                count += 1
            start = pos + 1
    return count


# ------------------------------------------------------------------
# A-1: 工具定义与路由（Function Calling）
# ------------------------------------------------------------------
TOOL_REGISTRY = {
    "get_portrait": {
        "description": "获取学生画像（技能、教育背景、实习经历等）",
        "args": ["student_id"],
    },
    "compute_match": {
        "description": "计算学生与指定岗位的五维匹配度",
        "args": ["student_id", "job_name"],
    },
    "get_market_trend": {
        "description": "查询岗位的市场薪资趋势和需求热度",
        "args": ["job_name"],
    },
    "get_graph_path": {
        "description": "查询从当前岗位到目标岗位的职业发展路径，以及岗位知识库详情（技能要求/薪资/入门建议）",
        "args": ["job_name"],
    },
    "search_knowledge": {
        "description": "检索本地岗位知识库，获取岗位描述、核心技能、薪资行情、市场前景、晋升路径和转岗建议",
        "args": ["query"],
    },
    "generate_report": {
        "description": "生成学生职业规划完整报告（含6章节 + 行动计划）",
        "args": ["student_id", "job_name"],
    },
    # A-3: 新增领域深度工具
    "get_assessment_result": {
        "description": "查询学生三维度能力测评分数（逻辑/职业倾向/技术自评），在对话中引用具体测评结论",
        "args": ["student_id"],
    },
    "get_learning_path": {
        "description": "根据技能差距返回结构化学习路径（课程/项目/时间线），来自知识库和技能库",
        "args": ["skill", "level"],
    },
    "get_industry_insight": {
        "description": "查询行业趋势数据（增长率/热门技能/招聘旺季/薪资水平），来自行业洞察数据",
        "args": ["industry_or_job"],
    },
    "none": {
        "description": "无需工具调用，直接回复用户",
        "args": [],
    },
}

# 需要注入 match_detail 的状态集合（不仅限于 MATCH_ANALYSIS）
_MATCH_DETAIL_STATES: frozenset = frozenset([
    "MATCH_ANALYSIS", "CAREER_GUIDANCE", "REPORT_REVIEW", "REPORT_REFINE"
])

# 触发画像回退的关键词（用户要求修改技能/信息时允许从深层状态回退）
_PORTRAIT_UPDATE_KWS: frozenset = frozenset([
    "修改技能", "我的技能有变", "技能有更新", "我学会了", "我新学了",
    "重新填写", "更新信息", "修改一下我的", "我想改", "重新录入",
    "技能加上", "补充一下我的技能",
])

# P1: 只有命中这些关键词的消息才走 tool_router，纯对话消息直接跳过
_TOOL_TRIGGER_KEYWORDS: frozenset = frozenset([
    # 匹配/评分
    "匹配", "匹配度", "分数", "多少分", "评分", "得分", "合不合适", "合适吗", "适合吗",
    # 市场/薪资
    "市场", "薪资", "工资", "薪水", "行情", "趋势", "热度", "需求", "招聘", "待遇",
    # 岗位/技能
    "岗位", "职位", "技能要求", "职业路径", "发展路径", "转岗", "转行", "晋升",
    "要求什么", "需要什么", "需要哪些", "要学什么", "要哪些",
    # 报告
    "报告", "生成报告", "帮我生成",
    # 画像/查询
    "画像", "我的情况", "我适合", "适不适合", "我的技能", "我的背景",
    # 推荐
    "推荐岗位", "推荐职位", "帮我推荐", "推荐一下", "有什么推荐",
    # 知识/介绍
    "知识库", "详情", "介绍", "了解", "什么是", "入门", "前景",
    # E-4: 高频真实问句补充
    "学习路线", "路线", "怎么学", "如何学", "该学什么", "学什么好",
    "应该怎么", "我现在", "下一步", "接下来", "现在该",
    "差距", "缺什么", "需要补", "欠缺",
    "规划", "方向", "怎么做", "如何做", "建议", "有什么建议",
    "好找工作吗", "好就业吗", "竞争", "找工作",
])

# 报告调优触发词（非流式和流式路径共用）
_REFINE_KWS: frozenset = frozenset(["修改报告", "重新生成", "润色", "改一下报告", "优化报告", "调整报告"])

# 允许从深层状态回退到画像收集的状态集合
_BACK_STATES: frozenset = frozenset(["MATCH_ANALYSIS", "CAREER_GUIDANCE", "REPORT_REVIEW"])

_TOOL_ROUTER_PROMPT_TMPL = """你是职业规划助手的工具路由器。根据用户消息决定需要调用哪个工具。

可用工具：
{tools_desc}

用户消息：{user_message}
当前状态：{state}
student_id：{student_id}
career_intent：{career_intent}

请输出JSON（不要包含markdown代码块）：
{{"tool": "工具名", "args": {{"参数名": "参数值"}}, "reason": "调用原因"}}

如果不需要工具直接回复，tool填"none"，args填{{}}。

## 示例（请严格参照）：
用户："我的匹配度怎么样？" state=MATCH_ANALYSIS career_intent=前端开发工程师
→ {{"tool": "compute_match", "args": {{"student_id": "xxx", "job_name": "前端开发工程师"}}, "reason": "用户询问匹配度"}}

用户："前端开发工资怎么样？" state=CAREER_GUIDANCE
→ {{"tool": "get_market_trend", "args": {{"job_name": "前端开发工程师"}}, "reason": "用户询问薪资行情"}}

用户："我应该怎么学Python？" state=PORTRAIT_FILLING
→ {{"tool": "get_learning_path", "args": {{"skill": "Python", "level": "入门"}}, "reason": "用户询问学习路径"}}

用户："互联网行业现在好不好进？" state=CAREER_GUIDANCE
→ {{"tool": "get_industry_insight", "args": {{"industry_or_job": "互联网"}}, "reason": "用户询问行业前景"}}

用户："好的，明白了" state=PORTRAIT_FILLING
→ {{"tool": "none", "args": {{}}, "reason": "纯对话回复，无需工具"}}

用户："我有点迷茫" state=GREETING
→ {{"tool": "none", "args": {{}}, "reason": "情绪类表达，无需工具"}}"""


class ChatAgentService:
    """对话智能体服务"""

    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self, session_id: str) -> ChatSession:
        """创建新会话"""
        session = ChatSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.info("创建对话会话: session_id=%s", session_id)
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话（仅查内存）"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除内存中的会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def restore_session(self, session_id: str, state: str, messages: list, turn_count: int = 0) -> ChatSession:
        """从DB数据重建内存会话（服务重启后恢复）"""
        session = ChatSession(session_id=session_id)
        try:
            session.state = ChatState(state)
        except ValueError:
            session.state = ChatState.GREETING
        # 仅还原最近20条消息，避免上下文过长
        for m in messages[-20:]:
            if isinstance(m, dict) and "role" in m and "content" in m:
                try:
                    session.messages.append(ChatMessage(**{k: v for k, v in m.items() if k in ChatMessage.model_fields}))
                except Exception:
                    pass
        session.turn_count = turn_count
        self.sessions[session_id] = session
        return session
    
    def detect_emotion(self, text: str) -> Tuple[EmotionType, float]:
        """
        情绪检测 (I2核心功能)
        返回: (情绪类型, 情绪得分)
        情绪得分: 0=极度焦虑, 1=非常平静
        """
        text_lower = text.lower()

        anxious_count = _count_keywords_with_negation(text_lower, EMOTION_KEYWORDS[EmotionType.ANXIOUS])
        confused_count = _count_keywords_with_negation(text_lower, EMOTION_KEYWORDS[EmotionType.CONFUSED])
        frustrated_count = _count_keywords_with_negation(text_lower, EMOTION_KEYWORDS[EmotionType.FRUSTRATED])
        excited_count = _count_keywords_with_negation(text_lower, EMOTION_KEYWORDS[EmotionType.EXCITED])
        
        total_negative = anxious_count + confused_count + frustrated_count
        
        if excited_count > 0 and total_negative == 0:
            return EmotionType.EXCITED, 0.9
        
        if total_negative == 0:
            return EmotionType.CALM, 1.0
        
        emotion_score = max(0.0, 1.0 - total_negative * 0.15)
        
        if anxious_count >= confused_count and anxious_count >= frustrated_count:
            return EmotionType.ANXIOUS, emotion_score
        elif confused_count >= frustrated_count:
            return EmotionType.CONFUSED, emotion_score
        else:
            return EmotionType.FRUSTRATED, emotion_score
    
    def should_enter_emotion_support(self, session: ChatSession) -> bool:
        """判断是否需要进入情绪支持模式"""
        if session.emotion_score < ANXIETY_THRESHOLD:
            return True
        
        if len(session.emotion_history) >= 2:
            recent_scores = [e["score"] for e in session.emotion_history[-2:]]
            if any(s < 0.5 for s in recent_scores):
                return True
        
        return False
    
    def transition_state(
        self,
        session: ChatSession,
        trigger: str
    ) -> ChatState:
        """状态转换"""
        current = session.state
        transitions = STATE_TRANSITIONS.get(current, {})
        triggers = transitions.get("triggers", {})

        new_state = triggers.get(trigger, current)
        if new_state != current:
            logger.info("状态转换 [%s]: %s --(%s)--> %s", session.session_id, current.value, trigger, new_state.value)
        session.state = new_state
        return new_state
    
    @staticmethod
    def _needs_tool_routing(message: str) -> bool:
        """P1: 预筛 — 只有查询类消息才触发 tool_router LLM 调用，纯对话消息直接跳过"""
        return any(kw in message for kw in _TOOL_TRIGGER_KEYWORDS)

    def _auto_advance_state(self, session: ChatSession) -> None:
        """P1: FSM 自动状态推进。在每轮响应生成后调用，根据画像完整度和语义进度自动触发状态迁移。"""
        state = session.state
        turns_in_state = session.turn_count - session.state_since_turn
        portrait = session.student_portrait

        if state == ChatState.GREETING:
            # 语义判断：画像中已有实质信息才推进（避免"你好"就触发状态迁移）
            has_info = bool(
                (portrait.get("basic_info") or {}).get("name")
                or portrait.get("education")
                or portrait.get("skills")
            )
            # 超过3轮仍无信息则也推进（兜底，避免卡死在GREETING）
            if has_info or turns_in_state >= 3:
                self.transition_state(session, "basic_info_collected")
                session.state_since_turn = session.turn_count

        elif state == ChatState.PORTRAIT_FILLING:
            missing = self.get_missing_dimensions(portrait)
            progress = self.compute_progress(portrait)
            # 完整度 ≥60%，或缺失维度 ≤1，或已在本状态 ≥10 轮（原7轮容易截断用户）
            if progress >= 60 or len(missing) <= 1 or turns_in_state >= 10:
                self.transition_state(session, "portrait_complete")
                session.state_since_turn = session.turn_count

        elif state == ChatState.INTENT_CONFIRM:
            career_intent = (portrait.get("career_intent") or "").strip()
            # 有明确意向才推进；无意向时容忍更多轮次（原3轮太短，改为6轮）
            if career_intent or turns_in_state >= 6:
                self.transition_state(session, "intent_confirmed")
                session.state_since_turn = session.turn_count

        elif state == ChatState.EMOTION_SUPPORT:
            # 情绪恢复（score > 0.6）后自动返回画像收集
            if session.emotion_score > 0.6 and turns_in_state >= 1:
                self.transition_state(session, "emotion_recovered")
                session.state_since_turn = session.turn_count

    def get_missing_dimensions(self, portrait: Dict) -> List[str]:
        """获取缺失的画像维度"""
        missing = []
        
        if not portrait.get("basic_info", {}).get("name"):
            missing.append("姓名")
        if not portrait.get("education"):
            missing.append("教育经历")
        if not portrait.get("skills"):
            missing.append("技能特长")
        if not portrait.get("internships") and not portrait.get("projects"):
            missing.append("实践经历")
        if not portrait.get("career_intent"):
            missing.append("求职意向")
        
        return missing
    
    def compute_progress(self, portrait: Dict) -> int:
        """计算信息完整度"""
        dims = [
            portrait.get("basic_info", {}).get("name"),
            portrait.get("education"),
            portrait.get("skills"),
            portrait.get("internships") or portrait.get("projects"),
            portrait.get("career_intent"),
            portrait.get("inferred_soft_skills"),
        ]
        filled = sum(1 for d in dims if d)
        return int(filled / len(dims) * 100)
    
    def _preprocess_message(self, session: "ChatSession", user_message: str) -> None:
        """提取情绪、追加用户消息、执行FSM状态转换 — 非流式和流式路径共用"""
        emotion, score = self.detect_emotion(user_message)
        session.current_emotion = emotion
        session.emotion_score = score
        session.emotion_history.append({"emotion": emotion.value, "score": score, "turn": session.turn_count})

        session.messages.append(ChatMessage(role="user", content=user_message, state=session.state, emotion=emotion))
        session.turn_count += 1

        if self.should_enter_emotion_support(session) and session.state != ChatState.EMOTION_SUPPORT:
            logger.info("情绪分数=%.2f 低于阈值%.2f，进入情绪支持: session=%s", score, ANXIETY_THRESHOLD, session.session_id)
            session.state = ChatState.EMOTION_SUPPORT

        if session.state == ChatState.REPORT_REVIEW and any(kw in user_message for kw in _REFINE_KWS):
            self.transition_state(session, "request_refine")

        if session.state.value in _BACK_STATES and any(kw in user_message for kw in _PORTRAIT_UPDATE_KWS):
            logger.info("[FSM/回退] 检测到画像修改请求，回退 PORTRAIT_FILLING: session=%s", session.session_id)
            self.transition_state(session, "portrait_update")
            session.state_since_turn = session.turn_count

    async def generate_response(
        self,
        session: ChatSession,
        user_message: str,
    ) -> str:
        """生成对话响应"""
        t0 = time.monotonic()
        logger.debug("generate_response: session=%s state=%s turn=%d msg_len=%d",
                     session.session_id, session.state.value, session.turn_count, len(user_message))

        self._preprocess_message(session, user_message)

        _analysis_states = {ChatState.MATCH_ANALYSIS, ChatState.CAREER_GUIDANCE}
        if session.state == ChatState.EMOTION_SUPPORT:
            response = await self._generate_emotion_response(session, user_message)
        elif session.state in _analysis_states or self._needs_tool_routing(user_message):
            logger.info("[ReAct] 触发工具路由: session=%s state=%s msg='%s'",
                        session.session_id, session.state.value, user_message[:40])
            response = await self.react_loop(session, user_message)
        else:
            response = await self._generate_normal_response(session, user_message)

        # C-1: 主动追问缺失信息
        proactive = self.should_proactively_ask(session, user_message)
        if proactive and proactive not in response:
            response = response + "\n\n" + proactive

        session.messages.append(ChatMessage(
            role="assistant",
            content=response,
            state=session.state,
        ))

        # P1-FSM: 每轮响应后自动推进状态
        self._auto_advance_state(session)
        # C-3: 持久化跨会话记忆
        await self._save_memory_if_needed(session)

        logger.info("generate_response完成 [%.2fs]: session=%s state=%s emotion=%s",
                    time.monotonic() - t0, session.session_id, session.state.value, emotion.value)
        return response
    
    async def generate_response_stream(
        self,
        session: ChatSession,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """真实流式响应生成器。分析/工具触发场景先走 ReAct 链，结果再流式输出"""
        logger.debug("generate_response_stream: session=%s state=%s turn=%d",
                     session.session_id, session.state.value, session.turn_count)

        self._preprocess_message(session, user_message)

        _analysis_states = {ChatState.MATCH_ANALYSIS, ChatState.CAREER_GUIDANCE}
        if session.state != ChatState.EMOTION_SUPPORT and (
            session.state in _analysis_states or self._needs_tool_routing(user_message)
        ):
            logger.info("[ReAct/stream] 触发工具路由: session=%s state=%s msg='%s'",
                        session.session_id, session.state.value, user_message[:40])
            # D-3: 立即发送思考占位，消除工具调用期间的等待感
            yield "⚙️ 正在查询相关信息..."
            try:
                # A-2: 流式工具调用通知（在 react_loop 执行前后插入 SSE tool_call 事件）
                react_response = await self._react_loop_with_sse(session, user_message)
            except Exception as e:
                logger.warning("[ReAct/stream] ReAct失败，降级正常响应: %s", e)
                react_response = await self._generate_normal_response(session, user_message)
            session.messages.append(ChatMessage(
                role="assistant",
                content=react_response,
                state=session.state,
            ))
            self._auto_advance_state(session)
            await self._save_memory_if_needed(session)
            yield "\n\n" + react_response
            return

        # 构建 system_prompt（统一通过 _build_system_prompt，避免重复代码）
        if session.state == ChatState.EMOTION_SUPPORT:
            recent_messages = [
                msg.content for msg in session.messages[-3:]
                if msg.role == "user"
            ]
            system_prompt = render_prompt(
                "emotion_support_v1.jinja2",
                emotion_score=session.emotion_score,
                emotion_label=session.current_emotion.value if session.current_emotion else "unknown",
                recent_messages=recent_messages,
            )
            temperature = 0.8
            fallback_fn = self._fallback_emotion_response
        else:
            session.missing_dims = self.get_missing_dimensions(session.student_portrait)
            system_prompt = await self._build_system_prompt(session)
            system_prompt = self._adapt_tone(system_prompt, session.current_emotion, session.turn_count)
            temperature = 0.7
            fallback_fn = lambda: self._fallback_response(session, session.missing_dims)

        history = []
        for msg in session.messages[-12:]:
            role = "user" if msg.role == "user" else "assistant"
            history.append({"role": role, "content": msg.content})

        full_parts: list[str] = []
        stream_t0 = time.monotonic()
        try:
            logger.debug("开始流式LLM调用: session=%s state=%s", session.session_id, session.state.value)
            async for chunk in llm_client.chat_stream_with_history(
                messages=history,
                system_prompt=system_prompt,
                temperature=temperature,
            ):
                full_parts.append(chunk)
                yield chunk
            logger.info("流式LLM完成 [%.2fs]: session=%s tokens≈%d",
                        time.monotonic() - stream_t0, session.session_id, sum(len(c) for c in full_parts))
        except Exception as e:
            logger.warning("流式LLM失败，使用兜底响应: session=%s error=%s", session.session_id, e)
            fallback = fallback_fn()
            full_parts = [fallback]
            yield fallback

        full_response = "".join(full_parts)
        session.messages.append(ChatMessage(
            role="assistant",
            content=full_response,
            state=session.state,
        ))
        # P1-FSM: 流式响应结束后自动推进状态
        self._auto_advance_state(session)
        # C-3: 持久化跨会话记忆
        await self._save_memory_if_needed(session)

    async def _generate_normal_response(
        self,
        session: ChatSession,
        user_message: str,
        tool_context: Optional[str] = None,
    ) -> str:
        """生成正常对话响应（统一调用 _build_system_prompt，无重复提取逻辑）"""
        session.missing_dims = self.get_missing_dimensions(session.student_portrait)
        prompt = await self._build_system_prompt(session)
        if tool_context:
            prompt += f"\n\n[工具查询结果] {tool_context}"
        prompt = self._adapt_tone(prompt, session.current_emotion, session.turn_count)

        history = [
            {"role": "user" if m.role == "user" else "assistant", "content": m.content}
            for m in session.messages[-12:]
        ]
        try:
            return await llm_client.chat_with_history(
                messages=history,
                system_prompt=prompt,
                temperature=0.7,
            )
        except Exception as e:
            logger.warning("正常对话LLM失败，使用兜底: session=%s error=%s", session.session_id, e)
            return self._fallback_response(session, session.missing_dims)
    
    async def _generate_emotion_response(
        self,
        session: ChatSession,
        user_message: str,
    ) -> str:
        """生成情绪支持响应"""
        recent_messages = [
            msg.content for msg in session.messages[-3:]
            if msg.role == "user"
        ]
        
        prompt = render_prompt(
            "emotion_support_v1.jinja2",
            emotion_score=session.emotion_score,
            emotion_label=session.current_emotion.value if session.current_emotion else "unknown",
            recent_messages=recent_messages,
        )
        
        try:
            response = await llm_client.chat_with_history(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=prompt,
                temperature=0.8,
            )
            return response
        except Exception as e:
            logger.warning("情绪支持LLM失败，使用兜底: session=%s error=%s", session.session_id, e)
            return self._fallback_emotion_response()
    
    def _fallback_response(
        self,
        session: ChatSession,
        missing_dims: List[str],
    ) -> str:
        """兜底响应（LLM不可用时）"""
        state = session.state
        
        if state == ChatState.GREETING:
            return "你好！我是职路，你的职业规划助手。请问怎么称呼你？目前是哪个学校、什么专业的呢？"
        
        elif state == ChatState.PORTRAIT_FILLING:
            if missing_dims:
                dim = missing_dims[0]
                if dim == "姓名":
                    return "请问怎么称呼你？"
                elif dim == "教育经历":
                    return "能介绍一下你的教育背景吗？比如学校、专业、年级？"
                elif dim == "技能特长":
                    return "你有哪些技能特长呢？可以是编程、设计、沟通等任何方面。"
                elif dim == "实践经历":
                    return "有过实习或项目经历吗？简单介绍一下？"
                elif dim == "求职意向":
                    return "你希望从事什么类型的工作？有目标岗位吗？"
            return "还有什么想补充的信息吗？"
        
        elif state == ChatState.INTENT_CONFIRM:
            return "你确认要投递这些岗位吗？还是需要我帮你分析一下？"
        
        elif state == ChatState.MATCH_ANALYSIS:
            return "正在为你分析岗位匹配度，请稍等..."
        
        elif state == ChatState.REPORT_REVIEW:
            return "报告已生成，你对结果有什么疑问吗？"
        
        else:
            return "还有什么我可以帮助你的吗？"
    
    def _fallback_emotion_response(self) -> str:
        """情绪支持兜底响应"""
        return (
            "我理解你现在可能有些压力。职业规划确实是一个需要时间思考的过程，"
            "不用太着急。我们可以慢慢来，一步一步梳理。你觉得怎么样？"
        )
    
    # ------------------------------------------------------------------
    # E-3: 构建统一 system prompt（E-1/E-5 参数统一提取）
    # ------------------------------------------------------------------
    async def _build_system_prompt(self, session: "ChatSession") -> str:
        """构建包含学生背景快照的 system prompt（所有对话路径统一调用此方法）"""
        portrait = session.student_portrait
        missing_dims = self.get_missing_dimensions(portrait)
        progress = self.compute_progress(portrait)
        long_term_memory: List[str] = portrait.get("long_term_memory") or []
        current_match = portrait.get("current_match")
        student_skills = (portrait.get("skills") or [])[:12]

        # 教育背景简述
        edu_list = portrait.get("education") or []
        edu_brief = ""
        if edu_list:
            e = edu_list[0]
            edu_brief = f"{e.get('degree','')} {e.get('school','')} {e.get('major','')}".strip()
        elif portrait.get("basic_info"):
            bi = portrait["basic_info"]
            edu_brief = f"{bi.get('grade','')} {bi.get('school','')} {bi.get('major','')}".strip()

        # 实习/项目简述
        intern_parts = []
        for i in (portrait.get("internships") or [])[:3]:
            co = i.get("company", ""); ro = i.get("role", ""); mo = i.get("duration_months") or 0
            intern_parts.append(f"{co}·{ro}({mo}个月)" if mo else f"{co}·{ro}")
        proj_parts = [p.get("name", "") for p in (portrait.get("projects") or [])[:2]]
        internship_brief = "、".join(intern_parts + [f"项目:{n}" for n in proj_parts if n]) or ""

        # 匹配详情：在所有涉及匹配结果的状态中均注入（不仅限于 MATCH_ANALYSIS）
        match_detail = ""
        if current_match and session.state.value in _MATCH_DETAIL_STATES:
            dims = current_match.get("dimensions") or {}

            def _dim_score(d: dict, k: str) -> int:
                v = d.get(k) or {}
                return round(v.get("score", 0)) if isinstance(v, dict) else 0

            br = _dim_score(dims, "basic_requirements")
            ps = _dim_score(dims, "professional_skills")
            pq = _dim_score(dims, "professional_qualities")
            dp = _dim_score(dims, "development_potential")
            matched = (dims.get("professional_skills") or {}).get("matched_skills") or []
            gaps = (dims.get("professional_skills") or {}).get("gap_skills") or []
            must_gaps = [
                g.get("skill", "") if isinstance(g, dict) else str(g)
                for g in gaps
                if (g.get("importance", "") if isinstance(g, dict) else "") == "must_have"
            ][:3]
            md = dims.get("market_demand") or {}
            avg_k = md.get("avg_salary_k") if isinstance(md, dict) else 0
            jd_cnt = md.get("jd_count") if isinstance(md, dict) else 0
            match_detail = (
                f"- 各维度：基础要求{br}分 | 职业技能{ps}分 | 职业素养{pq}分 | 发展潜力{dp}分\n"
                f"- 已匹配技能：{', '.join(matched[:5]) or '无'}\n"
                f"- must_have差距：{', '.join(must_gaps) or '无'}\n"
                + (f"- 市场：平均薪资{avg_k}K/月，JD数量{jd_cnt}条\n" if avg_k else "")
            )

        return render_prompt(
            "chat_agent_v1.jinja2",
            current_state=session.state.value,
            missing_dimensions=missing_dims,
            student_name=portrait.get("basic_info", {}).get("name") or "同学",
            progress_pct=progress,
            today_date=datetime.now().strftime("%Y-%m-%d"),
            long_term_memory=long_term_memory,
            current_match=current_match,
            student_skills=student_skills,
            student_education=edu_brief,
            student_internships=internship_brief,
            match_detail=match_detail,
        )

    # ------------------------------------------------------------------
    # A-5: ReAct 推理链（Reasoning + Acting）
    # ------------------------------------------------------------------
    async def react_loop(
        self,
        session: "ChatSession",
        user_message: str,
        max_steps: int = 3,
    ) -> str:
        """
        三步 ReAct 循环：Thought → Action → Observation → 最终回复。
        用于需要调用工具才能准确回答的复杂问题（如"我的匹配度是多少"）。
        """
        react_prompt_tmpl = (
            "你是职业规划助手。请基于以下信息回复用户。\n\n"
            "用户问题：{user_message}\n"
            "推理历史：\n{history}\n\n"
            "请给出最终简洁友好的中文回复（不要重复推理步骤）："
        )

        history_parts: list[str] = []
        current_message = user_message

        for step in range(max_steps):
            # Thought: 决定是否需要工具
            decision = await self.tool_router(session, current_message)
            if not decision or decision.get("tool") in (None, "none"):
                break  # 无需工具，直接回复

            tool_name = decision["tool"]
            args = decision.get("args", {})
            reason = decision.get("reason", "")

            # Action: 执行工具
            observation = await self.execute_tool(tool_name, args)
            if not observation:
                break

            # 记录推理步骤
            history_parts.append(
                f"Step {step+1}: 调用工具[{tool_name}]（{reason}）→ 观察：{observation}"
            )
            # 将观察注入下一步上下文
            current_message = f"{user_message}\n[已知信息] {observation}"

        if not history_parts:
            # 没有工具调用，走正常流程
            return await self._generate_normal_response(session, user_message)

        # E-3: 最终回复带入 system prompt（保留角色/状态上下文）
        history_str = "\n".join(history_parts)
        final_user_msg = react_prompt_tmpl.format(
            user_message=user_message, history=history_str
        )
        try:
            system_prompt = await self._build_system_prompt(session)
            reply = await llm_client.chat_with_history(
                messages=[{"role": "user", "content": final_user_msg}],
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=600,
            )
            return reply
        except Exception as e:
            logger.warning("[ReAct] 最终回复失败: %s", e)
            return await self._generate_normal_response(session, user_message)

    # ------------------------------------------------------------------
    # C-1: 主动提问策略（Proactive Questioning）
    # ------------------------------------------------------------------
    def should_proactively_ask(self, session: "ChatSession", user_message: str) -> Optional[str]:
        """
        判断是否需要主动追问缺失信息。
        返回追问文案，或 None（不需要追问）。
        触发条件：PORTRAIT_FILLING 状态 + 有缺失维度 + 用户消息较短（未提供信息）
        """
        if session.state != ChatState.PORTRAIT_FILLING:
            return None
        missing = self.get_missing_dimensions(session.student_portrait)
        if not missing:
            return None
        # 用户消息较短（< 20字），说明没有提供实质信息
        if len(user_message.strip()) > 20:
            return None
        dim = missing[0]
        proactive_map = {
            "姓名": "你好，请问怎么称呼你呢？",
            "教育经历": "能告诉我你目前的学历和就读院校吗？",
            "技能特长": "你掌握哪些技术技能呢？比如编程语言、工具、框架？",
            "实践经历": "有过实习或者参与过项目吗？简单聊聊？",
            "求职意向": "你有明确的目标岗位方向吗？比如前端开发、数据分析？",
        }
        return proactive_map.get(dim)

    # ------------------------------------------------------------------
    # A-1: 工具路由（Function Calling）
    # ------------------------------------------------------------------
    async def tool_router(
        self,
        session: "ChatSession",
        user_message: str,
    ) -> Optional[Dict[str, Any]]:
        """
        根据用户消息决策是否需要调用工具。
        返回 {"tool": str, "args": dict, "reason": str} 或 None（解析失败/无需工具）。
        """
        tools_desc = "\n".join(
            f"- {name}: {info['description']} (参数: {info['args']})"
            for name, info in TOOL_REGISTRY.items()
        )
        # 将本会话已缓存的工具结果提示给 LLM，避免重复调用相同工具
        tool_cache = session.student_portrait.get("tool_cache") or {}
        cache_hint = ""
        if tool_cache:
            cached_keys = list(tool_cache.keys())[:5]
            cache_hint = f"\n已缓存工具结果（无需重复调用）：{', '.join(cached_keys)}"

        prompt = _TOOL_ROUTER_PROMPT_TMPL.format(
            tools_desc=tools_desc,
            user_message=user_message[:300],
            state=session.state.value,
            student_id=session.student_id or "未知",
            career_intent=session.student_portrait.get("career_intent") or "未知",
        ) + cache_hint
        try:
            raw = await llm_client.chat(prompt, temperature=0.1, max_tokens=300)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:]).rstrip("`").strip()
            decision = json.loads(raw)
            tool = decision.get("tool", "none")
            if tool not in TOOL_REGISTRY:
                return None
            # P1: 检查工具缓存，如果已有相同参数的结果则直接复用
            if tool != "none":
                cache_key = f"{tool}:{json.dumps(decision.get('args', {}), sort_keys=True, ensure_ascii=False)}"
                if cache_key in tool_cache:
                    logger.info("[ToolCache] 命中缓存: session=%s key=%s", session.session_id, cache_key)
                    decision["_cached_result"] = tool_cache[cache_key]
            logger.info("[ToolRouter] session=%s tool=%s reason=%s",
                        session.session_id, tool, decision.get("reason", ""))
            return decision
        except Exception as e:
            logger.debug("[ToolRouter] 解析失败（正常降级）: %s", e)
            return None

    # ── 工具处理器（每个工具对应一个私有 async 方法）────────────────────────────

    async def _tool_get_portrait(self, args: Dict[str, Any]) -> Optional[str]:
        from app.db.database import get_db_session
        from app.db.crud.student_crud import StudentCRUD
        async with get_db_session() as db:
            student_row = await StudentCRUD().get_by_student_id(db, args.get("student_id", ""))
        if not student_row:
            return None
        skills = (student_row.skills or [])[:10]
        edu_list = student_row.education or []
        edu_str = ""
        if edu_list:
            e = edu_list[0]
            edu_str = f"{e.get('degree','')} {e.get('school','')} {e.get('major','')}".strip()
        intern_months = sum((i.get("duration_months") or 0) for i in (student_row.internships or []))
        return (
            f"[画像] 学历：{edu_str or '未知'}；"
            f"技能（{len(skills)}项）：{', '.join(skills)}；"
            f"实习{intern_months}个月，{len(student_row.projects or [])}个项目；"
            f"意向：{student_row.career_intent or '未知'}；"
            f"竞争力：{student_row.competitiveness_level or '未知'}"
        )

    async def _tool_compute_match(self, args: Dict[str, Any]) -> Optional[str]:
        from app.services.match_service import match_service
        from app.db.database import get_db_session
        from app.db.crud.student_crud import StudentCRUD
        student_id = args.get("student_id", "")
        job_name = args.get("job_name", "")
        async with get_db_session() as db:
            student_row = await StudentCRUD().get_by_student_id(db, student_id)
        if not student_row:
            return None
        portrait = {
            "skills": student_row.skills or [],
            "basic_info": student_row.basic_info or {},
            "education": student_row.education or [],
            "internships": student_row.internships or [],
            "projects": student_row.projects or [],
            "inferred_soft_skills": student_row.inferred_soft_skills or {},
            "career_intent": student_row.career_intent or "",
            "completeness": student_row.completeness or 0.5,
        }
        result = await match_service.compute_match(portrait, job_name)
        dims = result.dimensions
        matched = (dims.professional_skills.matched_skills or [])[:5]
        gaps = dims.professional_skills.gap_skills or []
        must_gaps = [g.skill for g in gaps if g.importance == "must_have"][:3]
        nice_gaps = [g.skill for g in gaps if g.importance != "must_have"][:2]
        return (
            f"[匹配] {job_name} 综合匹配度 {result.overall_score:.0f}分（置信度{result.confidence:.0%}）\n"
            f"各维度：基础要求{dims.basic_requirements.score:.0f} | "
            f"职业技能{dims.professional_skills.score:.0f} | "
            f"职业素养{dims.professional_qualities.score:.0f} | "
            f"发展潜力{dims.development_potential.score:.0f}\n"
            f"已匹配技能：{', '.join(matched) or '无'}\n"
            f"must_have差距：{', '.join(must_gaps) or '无'}；"
            f"nice_to_have差距：{', '.join(nice_gaps) or '无'}\n"
            f"竞争定位：{result.competitive_context or '未生成'}"
        )

    async def _tool_get_market_trend(self, args: Dict[str, Any]) -> Optional[str]:
        from app.services.market_service import market_service
        job_name = args.get("job_name", "")
        trend = await market_service.get_job_market_details(job_name)
        if not isinstance(trend, dict):
            return f"[市场] {job_name} 暂无市场数据"
        avg = trend.get("avg_salary_k") or 0
        jd_cnt = trend.get("jd_count") or 0
        top_co = trend.get("top_companies") or []
        hot_skills = trend.get("hot_skills") or []
        return (
            f"[市场] {job_name}：平均薪资{avg}K/月，在招JD {jd_cnt}条\n"
            + (f"热门公司：{', '.join(top_co[:4])}\n" if top_co else "")
            + (f"高频技能要求：{', '.join(hot_skills[:6])}" if hot_skills else "")
        )

    async def _tool_get_graph_path(self, args: Dict[str, Any]) -> Optional[str]:
        from app.graph.job_graph_repo import job_graph
        from app.services.rag_service import search_knowledge_base
        job_name = args.get("job_name", "")
        parts = []
        info = job_graph.get_job_info(job_name)
        if info:
            skills_str = ", ".join((info.get("skills") or [])[:6])
            parts.append(f"[图谱] {job_name} 技能要求：{skills_str}")
            if info.get("promotion_path"):
                parts.append(f"晋升路径：{info['promotion_path']}")
        kb_hits = search_knowledge_base(job_name, top_k=1)
        if kb_hits:
            kb = kb_hits[0]
            for key, label in [("salary_range", "薪资行情"), ("market_outlook", "市场前景"),
                                ("entry_advice", "入门建议")]:
                if kb.get(key):
                    parts.append(f"{label}：{kb[key]}")
            if kb.get("transfer_options"):
                parts.append(f"可转岗位：{', '.join(kb['transfer_options'][:3])}")
        return "\n".join(parts) if parts else None

    async def _tool_search_knowledge(self, args: Dict[str, Any]) -> Optional[str]:
        from app.services.rag_service import search_knowledge_base
        query = args.get("query", "")
        hits = search_knowledge_base(query, top_k=2)
        if not hits:
            return f"未找到与\"{query}\"相关的知识库条目"
        result_parts = []
        for h in hits:
            p = [f"【{h['job']}】{h.get('description', '')}"]
            for key, label in [("core_skills", None), ("salary_range", "薪资"),
                                ("market_outlook", "前景"), ("entry_advice", "建议")]:
                if h.get(key):
                    val = ", ".join(h[key][:6]) if isinstance(h[key], list) else h[key]
                    p.append(f"{label or '核心技能'}：{val}")
            result_parts.append(" | ".join(p))
        return "\n".join(result_parts)

    async def _tool_get_assessment_result(self, args: Dict[str, Any]) -> Optional[str]:
        from app.db.database import get_db_session
        from app.db.crud.student_crud import StudentCRUD
        async with get_db_session() as db:
            student_row = await StudentCRUD().get_by_student_id(db, args.get("student_id", ""))
        if not student_row:
            return None
        ability = student_row.ability_profile or {}
        if not ability:
            return "[测评] 该学生尚未完成能力测评"
        parts = []
        if ability.get("logic_score") is not None:
            parts.append(f"逻辑推理：{ability['logic_score']}分")
        if ability.get("career_tendency_score") is not None:
            parts.append(f"职业倾向：{ability['career_tendency_score']}分（{ability.get('career_tendency_type','未知')}型）")
        if ability.get("tech_score") is not None:
            parts.append(f"技术自评：{ability['tech_score']}分")
        if ability.get("recommended_jobs"):
            parts.append(f"测评推荐岗位：{', '.join(ability['recommended_jobs'][:3])}")
        return ("[测评结果] " + "；".join(parts)) if parts else "[测评] 暂无详细测评数据"

    async def _tool_get_learning_path(self, args: Dict[str, Any]) -> Optional[str]:
        from app.constants import SKILL_SUGGESTIONS
        from app.services.rag_service import search_knowledge_base
        skill = args.get("skill", "")
        suggestion = SKILL_SUGGESTIONS.get(skill)
        if suggestion:
            return f"[学习路径] {skill}：{suggestion}"
        hits = search_knowledge_base(skill, top_k=1)
        if hits and hits[0].get("entry_advice"):
            return f"[学习路径] {skill}入门建议：{hits[0]['entry_advice']}"
        return f"[学习路径] {skill}：建议搜索官方文档 + 完成1个实战项目，通常需要2-4周"

    async def _tool_get_industry_insight(self, args: Dict[str, Any]) -> Optional[str]:
        from app.data.industry_insights import INDUSTRY_INSIGHTS, get_industry_for_job
        query = args.get("industry_or_job", "")
        insight = next(
            (data for key, data in INDUSTRY_INSIGHTS.items() if query in key or key in query),
            None,
        )
        if not insight:
            ind = get_industry_for_job(query)
            insight = INDUSTRY_INSIGHTS.get(ind, {}) if ind else {}
        if not insight:
            return f"[行业洞察] 暂无 '{query}' 相关行业数据"
        hot_skills = (insight.get("hot_skills") or [])[:5]
        seasons = insight.get("hiring_seasons") or []
        return (
            f"[行业洞察] 增长率：{insight.get('growth_rate','未知')}；"
            f"平均薪资：{insight.get('avg_salary_k','未知')}K/月；"
            f"竞争比：{insight.get('competitive_ratio','未知')}\n"
            f"热门技能：{', '.join(hot_skills)}\n"
            + (f"招聘旺季：{', '.join(seasons)}" if seasons else "")
        )

    # ── 工具调度表 ────────────────────────────────────────────────────────────

    _TOOL_HANDLERS: Dict[str, str] = {
        "get_portrait": "_tool_get_portrait",
        "compute_match": "_tool_compute_match",
        "get_market_trend": "_tool_get_market_trend",
        "get_graph_path": "_tool_get_graph_path",
        "search_knowledge": "_tool_search_knowledge",
        "generate_report": None,  # 无 DB/LLM 调用，直接返回
        "get_assessment_result": "_tool_get_assessment_result",
        "get_learning_path": "_tool_get_learning_path",
        "get_industry_insight": "_tool_get_industry_insight",
    }

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """执行工具并返回摘要字符串（注入到下一轮 LLM 上下文）"""
        if tool_name == "generate_report":
            return "[报告] 正在生成，请稍候（通常需要10-30秒）"
        handler_name = self._TOOL_HANDLERS.get(tool_name)
        if not handler_name:
            logger.warning("[ToolExecutor] 未知工具: %s", tool_name)
            return None
        try:
            return await getattr(self, handler_name)(args)
        except Exception as e:
            logger.warning("[ToolExecutor] tool=%s 执行失败: %s", tool_name, e)
            return None

    async def _react_loop_with_sse(
        self,
        session: "ChatSession",
        user_message: str,
        max_steps: int = 3,
    ) -> str:
        """A-2: 带工具调用记录的 ReAct 循环，工具结果存入 session 供前端面板读取"""
        import json as _json
        tool_calls_log: List[Dict] = []

        react_prompt_tmpl = (
            "你是职业规划助手。请基于以下信息回复用户。\n\n"
            "用户问题：{user_message}\n"
            "推理历史：\n{history}\n\n"
            "请给出最终简洁友好的中文回复（不要重复推理步骤）："
        )

        history_parts: list[str] = []
        current_message = user_message

        for step in range(max_steps):
            decision = await self.tool_router(session, current_message)
            if not decision or decision.get("tool") in (None, "none"):
                break

            tool_name = decision["tool"]
            args = decision.get("args", {})
            reason = decision.get("reason", "")

            # P1: 优先使用工具缓存结果（避免重复 LLM/DB 调用）
            cached_result = decision.get("_cached_result")
            if cached_result:
                observation = cached_result
                logger.debug("[ToolCache/ReAct] 使用缓存结果: tool=%s", tool_name)
            else:
                observation = await self.execute_tool(tool_name, args)
                # 写入工具缓存（本会话有效）
                if observation:
                    cache_key = f"{tool_name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"
                    session.student_portrait.setdefault("tool_cache", {})[cache_key] = observation

            if not observation:
                break

            # A-2: 记录工具调用（存入 session，前端可从消息附属字段读取）
            tool_calls_log.append({
                "tool": tool_name,
                "reason": reason,
                "result_summary": observation[:120],
            })

            history_parts.append(
                f"Step {step+1}: 调用工具[{tool_name}]（{reason}）→ 观察：{observation}"
            )
            current_message = f"{user_message}\n[已知信息] {observation}"

        # 将工具调用记录追加到最近一条 assistant 消息的 session 状态中
        if tool_calls_log:
            session.student_portrait.setdefault("last_tool_calls", [])
            session.student_portrait["last_tool_calls"] = tool_calls_log

        if not history_parts:
            return await self._generate_normal_response(session, user_message)

        history_str = "\n".join(history_parts)
        final_user_msg = react_prompt_tmpl.format(
            user_message=user_message, history=history_str
        )
        try:
            system_prompt = await self._build_system_prompt(session)
            reply = await llm_client.chat_with_history(
                messages=[{"role": "user", "content": final_user_msg}],
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=600,
            )
            return reply
        except Exception as e:
            logger.warning("[ReAct/SSE] 最终回复失败: %s", e)
            return await self._generate_normal_response(session, user_message)

    # ------------------------------------------------------------------
    # C-2: 语气适配器
    # ------------------------------------------------------------------
    def _adapt_tone(self, prompt: str, emotion: Optional[EmotionType], turn_count: int) -> str:
        """根据情绪和对话轮次在系统提示末尾追加语气指引"""
        tone_hints: List[str] = []
        if emotion == EmotionType.ANXIOUS:
            tone_hints.append("用户情绪较焦虑，请用温柔、鼓励的语气回复，避免使用评判性语言。")
        elif emotion == EmotionType.FRUSTRATED:
            tone_hints.append("用户有些沮丧，请先共情再给出建议，语气要轻松不施压。")
        elif emotion == EmotionType.EXCITED:
            tone_hints.append("用户情绪积极，可以略微活泼、充满热情地回复。")
        if turn_count <= 2:
            tone_hints.append("这是对话初期，语气要亲切、引导性强。")
        elif turn_count >= 10:
            tone_hints.append("对话已进入深度阶段，可以更专业直接地给出建议。")
        if tone_hints:
            return prompt + "\n\n[语气要求] " + " ".join(tone_hints)
        return prompt

    # ------------------------------------------------------------------
    # A-4: 跨会话记忆注入
    # ------------------------------------------------------------------
    async def load_user_memory(self, session: ChatSession) -> None:
        """从 DB 加载长期记忆并注入到 student_portrait。
        冲突解决策略：session portrait 中已有值的字段不被 DB 旧记忆覆盖（session > DB 优先）。
        """
        if not session.student_id:
            return
        try:
            from app.db.database import get_db_session
            from app.db.crud.user_memory_crud import UserMemoryCRUD
            async with get_db_session() as db:
                memories = await UserMemoryCRUD.get_all(db, session.student_id)
            if memories:
                portrait = session.student_portrait
                ltm = portrait.setdefault("long_term_memory", {})
                injected = 0
                for key, value in memories.items():
                    # 只填充 session portrait 中尚未有值的字段，避免覆盖本次会话的新数据
                    portrait_key = key  # DB key 与 portrait key 同名
                    if portrait_key in portrait and portrait[portrait_key]:
                        continue  # session 已有值，跳过
                    # 长期记忆注入到 long_term_memory 列表（供 system prompt 展示）
                    if key not in ("last_state", "skills_snapshot"):  # 状态/快照不注入展示列表
                        ltm[key] = value
                        injected += 1
                logger.info("[Memory] 加载长期记忆 %d 条（跳过 %d 条已有值）: student=%s",
                            injected, len(memories) - injected, session.student_id)
        except Exception as e:
            logger.warning("[Memory] 加载记忆失败: %s", e)

    async def save_user_memory(
        self,
        student_id: str,
        session_id: str,
        key: str,
        value: str,
        confidence: float = 0.9,
    ) -> None:
        """持久化单条跨会话记忆"""
        try:
            from app.db.database import get_db_session
            from app.db.crud.user_memory_crud import UserMemoryCRUD
            async with get_db_session() as db:
                await UserMemoryCRUD.upsert(db, student_id, key, value, session_id, confidence)
            logger.debug("[Memory] 保存记忆: student=%s key=%s", student_id, key)
        except Exception as e:
            logger.warning("[Memory] 保存记忆失败: %s", e)

    # ------------------------------------------------------------------
    # O2-e: 结构化意图提取器（城市/薪资/行业偏好）
    # ------------------------------------------------------------------
    def _extract_intent_from_message(self, message: str, portrait: Dict) -> None:
        """从用户消息规则提取结构化意图并更新 student_portrait（城市/薪资/行业偏好）"""
        import re as _re

        # 城市偏好：提及 "去XX" / "在XX工作" / "XX城市" / "XX找工作"
        city_patterns = [
            _re.compile(r'(?:去|在|到|想去|希望在|打算去|留在)(北京|上海|深圳|广州|杭州|成都|武汉|南京|西安|重庆|苏州|厦门|长沙|济南|合肥|天津|郑州|宁波|青岛|大连)'),
            _re.compile(r'(北京|上海|深圳|广州|杭州|成都|武汉|南京|西安|重庆|苏州|厦门|长沙)(?:工作|就业|发展|找工作)'),
        ]
        for p in city_patterns:
            m = p.search(message)
            if m:
                city = m.group(1)
                portrait.setdefault("preferences", {})["city"] = city
                logger.debug("[IntentExtract] 城市偏好: %s", city)
                break

        # 薪资期望：XX k / XX千 / XX万
        salary_pattern = _re.compile(r'(?:薪资|工资|月薪|期望|想要|希望)[^\d]*(\d+)\s*[kK千]?')
        m = salary_pattern.search(message)
        if m:
            val = int(m.group(1))
            portrait.setdefault("preferences", {})["expected_salary_k"] = val
            logger.debug("[IntentExtract] 薪资期望: %dK", val)

        # 行业偏好
        industry_kws = {
            "互联网": ["互联网", "IT公司", "科技公司", "大厂"],
            "金融": ["金融", "银行", "证券", "基金", "保险"],
            "教育": ["教育", "培训", "学校"],
            "游戏": ["游戏", "网游", "电竞"],
            "医疗": ["医疗", "医院", "健康", "医药"],
            "制造": ["制造业", "工厂", "硬件"],
        }
        for industry, kws in industry_kws.items():
            if any(kw in message for kw in kws):
                portrait.setdefault("preferences", {})["industry"] = industry
                logger.debug("[IntentExtract] 行业偏好: %s", industry)
                break

        # 排斥偏好检测：识别用户明确不想从事的岗位/行业/城市
        _REJECT_PREFIXES = ["不想", "不做", "不考虑", "不去", "不要", "不愿意", "拒绝", "排除",
                            "没兴趣", "不感兴趣", "不喜欢做", "不打算"]
        _REJECT_TARGETS = {
            # 岗位类型
            "前端": ["前端", "前端开发", "前端工程师"],
            "后端": ["后端", "后端开发", "后端工程师", "服务端"],
            "算法": ["算法", "机器学习", "深度学习", "AI工程师"],
            "运维": ["运维", "DevOps", "SRE"],
            "测试": ["测试", "QA", "质量保证"],
            "产品": ["产品经理", "产品", "PM"],
            "销售": ["销售", "业务", "BD"],
            # 行业
            "游戏": ["游戏", "游戏行业"],
            "金融": ["金融", "金融行业"],
            "教育": ["教育", "培训机构"],
        }
        for prefix in _REJECT_PREFIXES:
            if prefix in message:
                for category, targets in _REJECT_TARGETS.items():
                    if any(t in message for t in targets):
                        rejected = portrait.setdefault("preferences", {}).setdefault("rejected", [])
                        if category not in rejected:
                            rejected.append(category)
                            logger.debug("[IntentExtract] 排斥偏好: %s", category)
                        break

    async def _save_memory_if_needed(self, session: ChatSession) -> None:
        """C-3: 自动持久化关键画像字段为跨会话记忆（幂等：每轮检查，有变化则 upsert）"""
        if not session.student_id:
            return
        portrait = session.student_portrait

        # O2-e: 从最近一条用户消息提取结构化意图
        recent_user_msgs = [m.content for m in session.messages[-3:] if m.role == "user"]
        for msg in recent_user_msgs:
            self._extract_intent_from_message(msg, portrait)

        # 保存求职意向
        career_intent = (portrait.get("career_intent") or "").strip()
        if career_intent:
            await self.save_user_memory(
                session.student_id, session.session_id,
                "career_intent", career_intent, confidence=0.9,
            )
        # 保存学生姓名
        name = (portrait.get("basic_info") or {}).get("name", "").strip()
        if name:
            await self.save_user_memory(
                session.student_id, session.session_id,
                "name", name, confidence=0.95,
            )
        # 保存当前 FSM 状态（用于下次会话恢复进度提示）
        await self.save_user_memory(
            session.student_id, session.session_id,
            "last_state", session.state.value, confidence=1.0,
        )
        # 保存城市/薪资/行业偏好
        prefs = portrait.get("preferences") or {}
        for pref_key, pref_val in prefs.items():
            await self.save_user_memory(
                session.student_id, session.session_id,
                f"pref_{pref_key}", str(pref_val), confidence=0.85,
            )
        # 保存最近一次匹配岗位及得分（跨会话可告知用户"上次你匹配了XX，得分XX"）
        current_match = portrait.get("current_match")
        if current_match and current_match.get("job_name"):
            score = current_match.get("overall_score", 0)
            await self.save_user_memory(
                session.student_id, session.session_id,
                "last_matched_job",
                f"{current_match['job_name']}（{score:.0f}分）",
                confidence=0.95,
            )
        # 保存技能摘要（供下次会话快速恢复背景）
        skills = (portrait.get("skills") or [])[:8]
        if skills:
            await self.save_user_memory(
                session.student_id, session.session_id,
                "skills_snapshot",
                "、".join(skills),
                confidence=0.85,
            )

    def update_portrait(
        self,
        session: ChatSession,
        updates: Dict,
    ) -> None:
        """更新学生画像"""
        for key, value in updates.items():
            if key in session.student_portrait:
                if isinstance(session.student_portrait[key], dict):
                    session.student_portrait[key].update(value)
                elif isinstance(session.student_portrait[key], list):
                    if isinstance(value, list):
                        session.student_portrait[key].extend(value)
                    else:
                        session.student_portrait[key].append(value)
                else:
                    session.student_portrait[key] = value
            else:
                session.student_portrait[key] = value


chat_agent_service = ChatAgentService()
