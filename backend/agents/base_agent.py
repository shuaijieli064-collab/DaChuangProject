"""Agent 基类 — 统一的状态管理和执行接口"""
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from .schemas import AgentMessage, AgentResult, AgentType, TaskStatus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent 抽象基类"""

    agent_type: AgentType

    def __init__(self, llm_fn=None, llm_fn_stream=None, timeout: float = 30.0):
        self.llm_fn = llm_fn  # (messages) -> str
        self.llm_fn_stream = llm_fn_stream  # (messages) -> AsyncGenerator[str, None]
        self.timeout = timeout

    def execute(self, message: AgentMessage) -> AgentResult:
        """执行任务（带超时控制）"""
        task_id = message.task_id or str(uuid.uuid4())
        start = time.time()

        try:
            answer = self._handle(message)
            latency = (time.time() - start) * 1000

            return AgentResult(
                task_id=task_id,
                agent_type=self.agent_type,
                status=TaskStatus.COMPLETED,
                answer=answer,
                latency_ms=latency,
            )
        except TimeoutError:
            latency = (time.time() - start) * 1000
            logger.warning("Agent %s 任务超时: %s", self.agent_type.value, task_id)
            return AgentResult(
                task_id=task_id,
                agent_type=self.agent_type,
                status=TaskStatus.TIMEOUT,
                answer="处理超时，请稍后重试",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.exception("Agent %s 执行失败: %s", self.agent_type.value, task_id)
            return AgentResult(
                task_id=task_id,
                agent_type=self.agent_type,
                status=TaskStatus.FAILED,
                answer="处理出错，请稍后重试",
                error=str(e),
                latency_ms=latency,
            )

    @abstractmethod
    def _handle(self, message: AgentMessage) -> str:
        """子类实现具体业务逻辑"""
        ...

    def _build_system_prompt(self, role: str) -> str:
        return (
            f"你是智链校园的{role}助手。请根据知识库内容回答用户问题。\n"
            "要求：\n"
            "1. 回答基于事实，不可编造\n"
            "2. 使用 Markdown 格式\n"
            "3. 结构化输出，条理清晰\n"
        )

    def _call_llm(self, messages: list[dict]) -> str:
        if self.llm_fn:
            return self.llm_fn(messages)
        return "[LLM 未配置]"

    async def _call_llm_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """流式调用 LLM，返回 async generator of tokens"""
        if self.llm_fn_stream:
            async for token in self.llm_fn_stream(messages):
                yield token
        else:
            # Fallback: 非流式一次性返回
            yield self._call_llm(messages)

    async def execute_stream(self, message: AgentMessage) -> AsyncGenerator[str, None]:
        """流式执行任务，逐个 token yield（子类可覆写）"""
        try:
            messages = self._build_messages_for_stream(message)
            async for token in self._call_llm_stream(messages):
                yield token
        except Exception as e:
            logger.exception("Agent %s 流式执行失败: %s", self.agent_type.value, message.task_id)
            yield "处理出错，请稍后重试"

    def _build_messages_for_stream(self, message: AgentMessage) -> list[dict]:
        """默认消息构建（子类覆写以使用自定义 system prompt）"""
        system_prompt = self._build_system_prompt("AI")
        messages = [{"role": "system", "content": system_prompt}]
        if message.history:
            messages.extend(message.history[-10:])
        messages.append({"role": "user", "content": message.content})
        return messages
