# -*- coding: utf-8 -*-
"""
统一LLM客户端 - 所有LLM调用必须经过此处
遵循v5规范C2：所有LLM调用必须通过统一入口
支持四档切换：Groq / DeepSeek / Qwen / Ollama本地
"""

import json
import asyncio
import logging
import time
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Type, AsyncGenerator
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.ai.llm_calibrator import output_calibrator, TaskType

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

PROMPT_DIR = Path(__file__).parent / "prompts"
_jinja_env = Environment(loader=FileSystemLoader(str(PROMPT_DIR)), autoescape=False)
_jinja_env.policies["json.dumps_kwargs"] = {"ensure_ascii": False, "indent": 2}


def render_prompt(template_name: str, **kwargs) -> str:
    """从 prompts/ 目录加载并渲染Jinja2模板"""
    template = _jinja_env.get_template(template_name)
    return template.render(**kwargs)


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    async def chat(self, prompt: str, temperature: float = 0.2, max_tokens: int = 2000) -> str:
        """基础对话调用"""
        pass
    
    @abstractmethod
    async def chat_stream(self, prompt: str, temperature: float = 0.5) -> AsyncGenerator[str, None]:
        """流式输出，生成器模式"""
        pass
    
    async def chat_with_history(
        self,
        messages: list,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """带历史记录的多轮对话（默认实现：拼接为单一prompt）"""
        parts = []
        if system_prompt:
            parts.append(system_prompt)
        for msg in messages:
            role_label = "用户" if msg.get("role") == "user" else "助手"
            parts.append(f"{role_label}: {msg.get('content', '')}")
        combined_prompt = "\n\n".join(parts)
        return await self.chat(combined_prompt, temperature, max_tokens)

    async def chat_stream_with_history(
        self,
        messages: list,
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """流式多轮对话（默认实现：拼接为单一prompt后流式输出）"""
        parts = []
        if system_prompt:
            parts.append(system_prompt)
        for msg in messages:
            role_label = "用户" if msg.get("role") == "user" else "助手"
            parts.append(f"{role_label}: {msg.get('content', '')}")
        combined_prompt = "\n\n".join(parts)
        async for chunk in self.chat_stream(combined_prompt, temperature):
            yield chunk

    async def chat_structured(
        self,
        prompt: str,
        output_model: Type[T],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        retries: int = 3,
    ) -> T:
        """
        结构化输出调用：LLM返回JSON → Pydantic解析
        自动重试（指数退避），解析失败触发异常
        """
        model_name = output_model.__name__
        for attempt in range(retries):
            try:
                logger.debug("chat_structured 尝试 %d/%d: model=%s", attempt + 1, retries, model_name)
                response = await self.chat(prompt, temperature, max_tokens)
                clean = response.strip()
                if clean.startswith("```"):
                    lines = clean.split("\n")
                    clean = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                clean = clean.strip()
                result = output_model.model_validate_json(clean)
                logger.debug("chat_structured 解析成功: model=%s", model_name)
                return result
            except Exception as e:
                logger.warning("chat_structured 第%d次失败: model=%s error=%s", attempt + 1, model_name, e)
                if attempt == retries - 1:
                    raise LLMCallError(f"JSON解析失败: {e}")
                await asyncio.sleep(2 ** attempt)
        raise LLMCallError("重试次数耗尽")


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI兼容API客户端（支持Groq/DeepSeek/Qwen）"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_key or settings.LLM_API_KEY,
            base_url=base_url or settings.LLM_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        self.model = model or settings.LLM_MODEL
    
    async def chat(self, prompt: str, temperature: float = 0.2, max_tokens: int = 2000) -> str:
        t0 = time.monotonic()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = time.monotonic() - t0
            content = response.choices[0].message.content
            logger.debug("LLM chat完成 [%.2fs]: model=%s tokens≈%d", latency, self.model, len(content or ""))
            return content
        except Exception as e:
            latency = time.monotonic() - t0
            logger.error("LLM chat失败 [%.2fs]: model=%s error=%s", latency, self.model, e)
            raise LLMCallError(f"API调用失败: {e}")
    
    async def chat_stream(self, prompt: str, temperature: float = 0.5) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat_with_history(
        self,
        messages: list,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(messages)
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=msgs,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMCallError(f"API调用失败: {e}")

    async def chat_stream_with_history(
        self,
        messages: list,
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(messages)
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GroqClient(OpenAICompatibleClient):
    """Groq API客户端（高速推理）"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.LLM_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            model=settings.LLM_MODEL or "llama-3.3-70b-versatile",
        )


class DeepSeekClient(OpenAICompatibleClient):
    """DeepSeek API客户端（支持腾讯云LKEAP等兼容端点）"""

    def __init__(self):
        super().__init__(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or "https://api.deepseek.com",
            model=settings.LLM_MODEL or "deepseek-chat",
        )


class QwenClient(OpenAICompatibleClient):
    """阿里云Qwen API客户端"""

    def __init__(self):
        super().__init__(
            api_key=settings.LLM_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=settings.LLM_MODEL or "qwen-turbo",
        )


class OllamaClient(BaseLLMClient):
    """Ollama本地模型客户端"""
    
    def __init__(self, model: str = "qwen2.5:7b"):
        import httpx
        self.client = httpx.AsyncClient(timeout=300)
        self.base_url = "http://localhost:11434"
        self.model = model
    
    async def chat(self, prompt: str, temperature: float = 0.2, max_tokens: int = 2000) -> str:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stream": False,
                }
            )
            return response.json().get("response", "")
        except Exception as e:
            raise LLMCallError(f"Ollama调用失败: {e}")
    
    async def chat_stream(self, prompt: str, temperature: float = 0.5) -> AsyncGenerator[str, None]:
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": True,
            }
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]


class MockLLMClient(BaseLLMClient):
    """Mock客户端 - 开发/测试环境使用，不调用真实API
    遵循v5规范C6：MOCK_LLM=true时禁止调用真实API
    """
    
    FIXTURE_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "llm_responses"
    
    async def chat(self, prompt: str, temperature: float = 0.2, max_tokens: int = 2000) -> str:
        await asyncio.sleep(0.1)
        return '{"mock": true, "message": "Mock response for development"}'
    
    async def chat_stream(self, prompt: str, temperature: float = 0.5) -> AsyncGenerator[str, None]:
        mock_response = "这是一个Mock响应，用于开发测试。"
        for char in mock_response:
            yield char
            await asyncio.sleep(0.02)
    
    async def chat_structured(
        self,
        prompt: str,
        output_model: Type[T],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        retries: int = 3,
    ) -> T:
        fixture_file = self.FIXTURE_DIR / f"{output_model.__name__}.json"
        if fixture_file.exists():
            return output_model.model_validate_json(fixture_file.read_text(encoding="utf-8"))
        return output_model.model_validate_json('{"mock": true}')


class LLMCallError(Exception):
    """LLM调用异常"""
    def __init__(self, message: str, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(message)


def _get_client_by_provider(provider: str) -> BaseLLMClient:
    if provider == "deepseek":
        return DeepSeekClient()
    elif provider == "groq":
        return GroqClient()
    elif provider == "qwen":
        return QwenClient()
    elif provider == "ollama":
        return OllamaClient()
    raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_client() -> BaseLLMClient:
    """根据配置获取LLM客户端实例（单一供应商，失败即报错）"""
    if settings.MOCK_LLM:
        logger.info("LLM客户端初始化: Mock模式（MOCK_LLM=true）")
        return MockLLMClient()

    client = _get_client_by_provider(settings.LLM_PROVIDER)
    logger.info("LLM客户端初始化: provider=%s model=%s", settings.LLM_PROVIDER, settings.LLM_MODEL)
    return client


llm_client = get_llm_client()
