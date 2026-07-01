# -*- coding: utf-8 -*-
"""
LLM 服务层 - 支持多种大模型提供商
"""

import asyncio
import logging
import time
import httpx
from typing import Dict, List, Any, Optional
import json
from app.config import settings
from app.core.observability import metrics

logger = logging.getLogger(__name__)


RESUME_PARSE_PROMPT = """你是一位专业的简历分析师，请根据以下七维度评估标准解析简历：

【七维度评估标准】

1. 专业技能（skills）
   - 从项目经历、技能列表、工作描述中提取
   - 区分掌握程度：精通（有深度项目经验）、熟练（能独立使用）、了解（有基础认知）
   - 提取技术栈、工具、编程语言等

2. 证书要求（certificates）
   - 提取专业证书、资格证书、认证证书
   - 包括：学历证书、职业资格证书、技能认证等

3. 创新能力（innovation）
   - 优秀：有专利、论文、竞赛获奖、技术攻关、产品创新经历
   - 良好：有创新项目、技术改进、独立设计经历
   - 一般：缺乏相关证据

4. 学习能力（learning）
   - 优秀：自学多种技能、跨领域项目、持续学习记录、快速适应新技术
   - 良好：有学习新技能经历、参加培训、获得证书
   - 一般：缺乏相关证据

5. 抗压能力（stress_resistance）
   - 优秀：有高难度项目、紧急项目、高强度工作经历
   - 良好：有挑战性任务、多任务并行经历
   - 一般：缺乏相关证据

6. 沟通能力（communication）
   - 优秀：有团队领导、演讲、客户对接、跨部门协作经历
   - 良好：有团队协作、项目汇报、文档编写经历
   - 一般：缺乏相关证据

7. 实习能力（internship）
   - 优秀：有2段以上实习经历或高质量实习
   - 良好：有1段实习经历
   - 一般：无实习但有项目经历

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何额外说明：

```json
{
    "name": "姓名",
    "student_id": "学号（如有）",
    "skills": [
        {"name": "技能名称", "level": "精通/熟练/了解"}
    ],
    "certificates": ["证书1", "证书2"],
    "education": [
        {"school": "学校名称", "major": "专业", "degree": "学历", "period": "时间段"}
    ],
    "internships": [
        {"company": "公司名称", "position": "职位", "duration": "时长", "description": "主要工作内容"}
    ],
    "projects": [
        {"name": "项目名称", "role": "角色", "description": "项目描述和技术栈", "highlights": ["亮点1", "亮点2"]}
    ],
    "awards": ["奖项1", "奖项2"],
    "career_intent": "求职意向（如：后端开发工程师）",
    "interests": ["从简历/项目推断的兴趣方向，如 算法、数据分析"],
    "job_preferences": {
        "industries": ["期望行业，如 互联网、金融科技"],
        "cities": ["期望城市"],
        "salary_expectation": "期望薪资区间（如有）",
        "work_style": "工作方式偏好：稳定 / 挑战（如能推断）",
        "values": ["职业价值取向：成长 / 薪资 / 稳定 / 兴趣（如能推断）"]
    },
    "innovation": {
        "level": "优秀/良好/一般",
        "evidence": "具体证据描述"
    },
    "learning": {
        "level": "优秀/良好/一般",
        "evidence": "具体证据描述"
    },
    "stress_resistance": {
        "level": "优秀/良好/一般",
        "evidence": "具体证据描述"
    },
    "communication": {
        "level": "优秀/良好/一般",
        "evidence": "具体证据描述"
    },
    "internship_ability": {
        "level": "优秀/良好/一般",
        "evidence": "具体证据描述"
    }
}
```

【简历内容】
{resume_text}

请开始解析："""


class LLMService:
    """
    LLM 服务
    支持 DeepSeek/Qwen/Groq/Ollama
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL
        self.timeout = settings.LLM_TIMEOUT
        # 降级 Provider（主调用持续失败时切换）
        self.fallback_api_key = settings.LLM_FALLBACK_API_KEY
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.fallback_base_url = settings.LLM_FALLBACK_BASE_URL
        self.max_retries = settings.LLM_MAX_RETRIES
        self._async_client: Optional[httpx.AsyncClient] = None

    # ── 优雅降级：MOCK_LLM 或无 key 时不硬崩，给结构化兜底 + 降级提示 ──
    DEGRADED_NOTE = "（AI 服务暂时不可用，以下为系统降级内容，仅供参考）"
    _COMMON_SKILLS = [
        "Python", "Java", "JavaScript", "TypeScript", "Vue", "React", "Angular",
        "HTML", "CSS", "Node.js", "Express", "Spring Boot", "Spring", "MySQL",
        "Redis", "MongoDB", "SQL", "Linux", "Docker", "Kubernetes", "Git", "Go",
        "C++", "C#", "PHP", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Selenium",
        "JMeter", "Excel", "机器学习", "深度学习", "数据分析", "计算机视觉", "自动化测试",
    ]

    def _degraded(self) -> bool:
        return bool(settings.MOCK_LLM) or not self.api_key

    def _rule_extract(self, resume_text: str) -> Dict[str, Any]:
        """无 LLM 时的规则兜底简历解析：关键词扫技能 + 正则取意向/姓名。基础但真实。"""
        import re
        low = (resume_text or "").lower()
        skills = [s for s in self._COMMON_SKILLS if s.lower() in low]
        m = re.search(r"(?:求职意向|目标岗位|意向)[：: ]*([^\n，。,；;]+)", resume_text or "")
        intent = m.group(1).strip() if m else ""
        first = (resume_text or "").strip().splitlines()[0] if (resume_text or "").strip() else ""
        name = first.split()[0][:8] if first else ""
        result = self._get_default_result()
        result["name"] = name
        result["skills"] = [{"name": s, "level": "熟练"} for s in skills]
        result["career_intent"] = intent
        result["_degraded"] = True
        return self._validate_and_fix_result(result)

    async def _chat_completion(self, payload_base: Dict) -> Dict:
        """
        统一的 chat completion 调用：每个 Provider 内重试 + 指数退避，
        主 Provider 耗尽后切换到降级 Provider。采集延迟/token/失败指标。
        返回原始 OpenAI 响应 JSON。
        """
        providers = [("primary", self.api_key, self.base_url, self.model)]
        if self.fallback_api_key and self.fallback_base_url and self.fallback_model:
            providers.append(("fallback", self.fallback_api_key,
                              self.fallback_base_url, self.fallback_model))

        client = await self._get_async_client()
        last_err: Optional[Exception] = None

        for name, key, url, model in providers:
            if not key:
                continue
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {**payload_base, "model": model}
            for attempt in range(self.max_retries + 1):
                t0 = time.perf_counter()
                try:
                    resp = await client.post(
                        f"{url}/chat/completions", json=payload, headers=headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    metrics.observe("llm.latency_ms", (time.perf_counter() - t0) * 1000)
                    usage = data.get("usage") or {}
                    if usage.get("total_tokens"):
                        metrics.incr("llm.tokens", usage["total_tokens"])
                    if name == "fallback":
                        metrics.incr("llm.fallback_used")
                    return data
                except Exception as e:
                    last_err = e
                    metrics.incr("llm.error")
                    logger.warning("[llm:%s] 调用失败 (try %d/%d): %s",
                                   name, attempt + 1, self.max_retries + 1, e)
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * (2 ** attempt))

        raise last_err if last_err else RuntimeError("LLM 无可用 Provider")

    async def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,  # 不使用系统代理，直连LLM API
            )
        return self._async_client

    async def close(self):
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()

    async def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        temperature: float = 0.3,
        tool_choice: str = "auto",
    ) -> Dict:
        """
        Function Calling 接口 — LLM 自主决定调用哪些工具。
        返回完整的 message 对象（含 tool_calls 列表或纯文本 content）。
        降级：无 key/MOCK 或调用失败 → 返回无工具的降级消息，不抛（Agent 不崩）。
        """
        if self._degraded():
            return {"role": "assistant", "content": self.DEGRADED_NOTE}
        try:
            result = await self._chat_completion({
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "temperature": temperature,
            })
            return result["choices"][0]["message"]   # {"role","content","tool_calls"?}
        except Exception as e:
            logger.warning("[llm] chat_with_tools 降级: %s", e)
            return {"role": "assistant", "content": self.DEGRADED_NOTE}

    async def chat_stream(self, messages: List[Dict], temperature: float = 0.7):
        """
        流式生成（无工具）。异步逐段 yield 文本 delta（token 级）。
        用于开放问答与最终总结，首字延迟接近首个 SSE chunk 到达时间。
        降级：无 key/MOCK 或流异常 → yield 一段降级提示，不抛。
        """
        if self._degraded():
            yield self.DEGRADED_NOTE
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        client = await self._get_async_client()
        try:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
        except Exception as e:
            logger.warning("[llm] chat_stream 降级: %s", e)
            yield self.DEGRADED_NOTE

    async def chat_with_tools_stream(
        self,
        messages: List[Dict],
        tools: List[Dict],
        temperature: float = 0.3,
        tool_choice: str = "auto",
    ):
        """
        流式 Function Calling。逐步 yield 事件：
          {"type":"content","delta": "..."}          # 思考文本增量（token 级）
          {"type":"final","content": str, "tool_calls": [...]}  # 收尾：完整文本 + 累积的工具调用
        工具调用在 OpenAI 兼容流中以分片 delta 返回，这里按 index 累积成完整调用。
        降级：无 key/MOCK 或流异常 → 收尾给无工具的降级 final，不抛（Agent 不崩）。
        """
        if self._degraded():
            yield {"type": "final", "content": self.DEGRADED_NOTE, "tool_calls": []}
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": temperature,
            "stream": True,
        }
        client = await self._get_async_client()
        content_buf = []
        tool_slots: Dict[int, Dict] = {}

        try:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})

                    content = delta.get("content")
                    if content:
                        content_buf.append(content)
                        yield {"type": "content", "delta": content}

                    for tc in (delta.get("tool_calls") or []):
                        idx = tc.get("index", 0)
                        slot = tool_slots.setdefault(
                            idx, {"id": "", "type": "function",
                                  "function": {"name": "", "arguments": ""}}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["function"]["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["function"]["arguments"] += fn["arguments"]
        except Exception as e:
            logger.warning("[llm] chat_with_tools_stream 降级: %s", e)
            if not content_buf:
                content_buf.append(self.DEGRADED_NOTE)

        final_tool_calls = [tool_slots[i] for i in sorted(tool_slots)]
        yield {
            "type": "final",
            "content": "".join(content_buf),
            "tool_calls": final_tool_calls,
        }

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        调用 LLM 生成回复

        Args:
            messages: 消息列表
            temperature: 温度参数

        Returns:
            生成的文本（降级：无 key/MOCK 或调用失败 → 返回降级提示，不抛）
        """
        if self._degraded():
            return self.DEGRADED_NOTE
        try:
            result = await self._chat_completion({
                "messages": messages,
                "temperature": temperature,
            })
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result.get("content", "")
        except Exception as e:
            logger.warning("[llm] chat 降级: %s", e)
            return self.DEGRADED_NOTE

    async def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        使用 LLM 解析简历文本，提取七维度画像信息

        Args:
            resume_text: 简历文本内容

        Returns:
            解析后的结构化数据
        """
        if self._degraded():
            return self._rule_extract(resume_text)

        prompt = RESUME_PARSE_PROMPT.replace("{resume_text}", resume_text)

        for attempt in range(3):
            try:
                response = await self.chat([
                    {"role": "system", "content": "你是一位专业的简历分析师，擅长从简历中提取结构化信息并评估候选人能力。请严格按照JSON格式输出。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.2)

                content = response.strip()

                if not content:
                    print(f"LLM returned empty response (attempt {attempt + 1})")
                    continue

                if content.startswith("```json"):
                    content = content[content.find("```json") + 7:]
                if content.startswith("```"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:content.rfind("```")]

                content = content.strip()

                json_start = content.find("{")
                json_end = content.rfind("}")
                if json_start != -1 and json_end != -1:
                    content = content[json_start:json_end + 1]

                result = json.loads(content)

                result = self._validate_and_fix_result(result)

                return result

            except json.JSONDecodeError as je:
                print(f"JSON decode error (attempt {attempt + 1}): {je}")
                if attempt == 2:
                    return self._get_default_result()
            except Exception as e:
                print(f"LLM parse resume error (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    return self._get_default_result()

        return self._get_default_result()

    def _validate_and_fix_result(self, result: Dict) -> Dict:
        """验证并修复解析结果"""
        default = self._get_default_result()

        if not result.get("name"):
            result["name"] = default["name"]

        if not isinstance(result.get("skills"), list):
            result["skills"] = []
        else:
            normalized_skills = []
            for skill in result["skills"]:
                if isinstance(skill, str):
                    normalized_skills.append({"name": skill, "level": "熟练"})
                elif isinstance(skill, dict) and skill.get("name"):
                    if skill.get("level") not in ["精通", "熟练", "了解"]:
                        skill["level"] = "熟练"
                    normalized_skills.append(skill)
            result["skills"] = normalized_skills

        for dim in ["innovation", "learning", "stress_resistance", "communication", "internship_ability"]:
            if not isinstance(result.get(dim), dict):
                result[dim] = default[dim]
            else:
                if result[dim].get("level") not in ["优秀", "良好", "一般"]:
                    result[dim]["level"] = "一般"
                if not result[dim].get("evidence"):
                    result[dim]["evidence"] = "暂无相关证据"

        for field in ["certificates", "education", "internships", "projects", "awards"]:
            if not isinstance(result.get(field), list):
                result[field] = []

        return result

    def _get_default_result(self) -> Dict:
        """返回默认的解析结果结构"""
        return {
            "name": "",
            "student_id": "",
            "skills": [],
            "certificates": [],
            "education": [],
            "internships": [],
            "projects": [],
            "awards": [],
            "career_intent": "",
            "innovation": {"level": "一般", "evidence": "暂无相关证据"},
            "learning": {"level": "一般", "evidence": "暂无相关证据"},
            "stress_resistance": {"level": "一般", "evidence": "暂无相关证据"},
            "communication": {"level": "一般", "evidence": "暂无相关证据"},
            "internship_ability": {"level": "一般", "evidence": "暂无相关证据"}
        }

    async def generate_match_analysis(self, student_info: Dict, job_info: Dict, match_score: float) -> str:
        """
        使用 LLM 生成匹配分析说明

        Args:
            student_info: 学生信息
            job_info: 岗位信息
            match_score: 匹配分数

        Returns:
            匹配分析说明
        """
        prompt = f"""
请根据以下信息生成人岗匹配分析说明:

学生信息:
{json.dumps(student_info, ensure_ascii=False, indent=2)}

岗位信息:
{json.dumps(job_info, ensure_ascii=False, indent=2)}

匹配分数: {match_score}

请生成一段200字左右的匹配分析说明,包括:
1. 整体匹配评价
2. 各维度分析
3. 改进建议
"""

        try:
            response = await self.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.5)
            return response
        except Exception as e:
            print(f"LLM generate match analysis error: {e}")
            return ""

    async def polish_report(self, report_content: str) -> str:
        """
        使用 LLM 润色报告内容

        Args:
            report_content: 报告内容

        Returns:
            润色后的内容
        """
        prompt = """
请润色以下职业规划报告内容,使其更加专业、流畅:

""" + report_content + """

要求:
1. 保持原意
2. 语言更加专业
3. 结构更加清晰
"""

        try:
            response = await self.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            return response
        except Exception as e:
            print(f"LLM polish report error: {e}")
            return report_content

    async def enhance_student_portrait(self, basic_info: Dict) -> Dict:
        """
        使用 LLM 增强学生画像

        Args:
            basic_info: 基础信息

        Returns:
            增强后的画像
        """
        prompt = f"""
请根据以下学生基础信息，生成更完整的能力画像：

基础信息：
{json.dumps(basic_info, ensure_ascii=False, indent=2)}

请分析并补充以下内容：
1. 根据项目经历推断可能掌握的技能
2. 根据经历评估软技能水平
3. 给出职业发展建议

请以JSON格式返回，包含以下字段：
{{
    "inferred_skills": ["推断的技能"],
    "skill_gaps": ["可能需要提升的技能"],
    "career_suggestions": ["职业发展建议"],
    "strengths": ["优势分析"],
    "weaknesses": ["待提升方面"]
}}
"""

        try:
            response = await self.chat([
                {"role": "system", "content": "你是一位专业的职业规划顾问。"},
                {"role": "user", "content": prompt}
            ], temperature=0.3)

            content = response.strip()

            if content.startswith("```json"):
                content = content[content.find("```json") + 7:]
            if content.startswith("```"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:content.rfind("```")]

            content = content.strip()

            json_start = content.find("{")
            json_end = content.rfind("}")
            if json_start != -1 and json_end != -1:
                content = content[json_start:json_end + 1]

            return json.loads(content)
        except Exception as e:
            print(f"LLM enhance student portrait error: {e}")
            return {
                "inferred_skills": [],
                "skill_gaps": [],
                "career_suggestions": [],
                "strengths": [],
                "weaknesses": []
            }


llm_service = LLMService()
