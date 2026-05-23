"""Agent 编排引擎"""
import logging
import time
import uuid
from typing import AsyncGenerator

from agents.orchestrator import Orchestrator
from agents.schemas import AgentMessage, AgentResult, AgentType, TaskStatus

logger = logging.getLogger(__name__)


class AgentEngine:
    """Agent 编排引擎 — 路由 → Agent 执行"""

    def __init__(self, llm_fn=None, llm_fn_stream=None):
        self.llm_fn = llm_fn
        self.llm_fn_stream = llm_fn_stream
        self.orchestrator = Orchestrator(llm_fn=llm_fn, llm_fn_stream=llm_fn_stream)

    def process(
        self,
        content: str,
        history: list[dict] | None = None,
        intent: str | None = None,
    ) -> AgentResult:
        """
        处理用户请求

        Args:
            content: 用户输入内容
            history: 对话历史
            intent: 指定 intent（跳过路由）

        Returns:
            AgentResult
        """
        task_id = str(uuid.uuid4())

        # 如果指定了 intent，直接执行
        if intent:
            try:
                agent_type = AgentType(intent)
            except ValueError:
                agent_type = AgentType.AFFAIRS

            message = AgentMessage(
                task_id=task_id,
                source=AgentType.ORCHESTRATOR,
                target=agent_type,
                intent=intent,
                content=content,
                history=history or [],
            )
            agent = self.orchestrator.agents.get(agent_type)
            if agent:
                return agent.execute(message)
            return self._error_result(task_id, AgentType.AFFAIRS, "未知的 Agent 类型")

        # 路由 → 执行
        return self._process_simple(content, history, task_id)

    async def process_stream(
        self,
        content: str,
        history: list[dict] | None = None,
        intent: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式处理用户请求，逐个 token 返回"""
        if intent:
            try:
                agent_type = AgentType(intent)
            except ValueError:
                agent_type = AgentType.AFFAIRS

            message = AgentMessage(
                task_id=str(uuid.uuid4()),
                source=AgentType.ORCHESTRATOR,
                target=agent_type,
                intent=intent,
                content=content,
                history=history or [],
            )
            agent = self.orchestrator.agents.get(agent_type)
            if agent:
                async for token in agent.execute_stream(message):
                    yield token
                return

        # 简单模式：路由 → 流式执行
        _, stream = await self.orchestrator.execute_stream(content, history)
        async for token in stream:
            yield token

    def _process_simple(
        self, content: str, history: list[dict] | None, task_id: str
    ) -> AgentResult:
        """简单模式处理"""
        decision = self.orchestrator.route(content, history)
        agent_type = decision.intent if isinstance(decision.intent, AgentType) else AgentType.AFFAIRS

        agent = self.orchestrator.agents.get(agent_type)
        if not agent:
            return self._error_result(task_id, AgentType.AFFAIRS, "Agent 未初始化")

        message = AgentMessage(
            task_id=task_id,
            source=AgentType.ORCHESTRATOR,
            target=agent_type,
            intent=agent_type.value,
            content=content,
            history=history or [],
        )

        return agent.execute(message)

    @staticmethod
    def _error_result(task_id: str, agent_type: AgentType, error: str) -> AgentResult:
        return AgentResult(
            task_id=task_id,
            agent_type=agent_type,
            status=TaskStatus.FAILED,
            answer="处理出错，请稍后重试",
            error=error,
        )
