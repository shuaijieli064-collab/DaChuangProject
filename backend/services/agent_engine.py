"""Agent 编排引擎 — LangGraph 编排 + 简单模式 fallback"""
import logging
import time
import uuid
from typing import AsyncGenerator

from agents.orchestrator import Orchestrator
from agents.schemas import AgentMessage, AgentResult, AgentType, TaskStatus

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Agent 编排引擎

    支持两种模式：
    1. LangGraph 模式：有向图状态管理 + 复合任务串行流水线
    2. 简单模式：路由 → 单 Agent 执行（默认）
    """

    def __init__(self, llm_fn=None, llm_fn_stream=None, use_langgraph: bool = False):
        self.llm_fn = llm_fn
        self.llm_fn_stream = llm_fn_stream
        self.use_langgraph = use_langgraph
        self.orchestrator = Orchestrator(llm_fn=llm_fn, llm_fn_stream=llm_fn_stream)
        self._langgraph_app = None

        if use_langgraph:
            self._langgraph_app = self._build_langgraph()

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

        # LangGraph 模式
        if self._langgraph_app:
            return self._process_langgraph(content, history, task_id)

        # 简单模式：路由 → 执行
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

    def _process_langgraph(
        self, content: str, history: list[dict] | None, task_id: str
    ) -> AgentResult:
        """LangGraph 模式处理"""
        if not self._langgraph_app:
            return self._process_simple(content, history, task_id)

        try:
            start = time.time()
            state = {
                "messages": [{"role": "user", "content": content}],
                "history": history or [],
                "results": {},
                "current_agent": None,
            }
            final_state = self._langgraph_app.invoke(state)

            answer = final_state.get("messages", [])[-1].get("content", "") if final_state.get("messages") else ""
            latency = (time.time() - start) * 1000

            return AgentResult(
                task_id=task_id,
                agent_type=AgentType.ORCHESTRATOR,
                status=TaskStatus.COMPLETED,
                answer=answer,
                latency_ms=latency,
            )
        except Exception as e:
            logger.exception("LangGraph 执行失败，降级为简单模式")
            return self._process_simple(content, history, task_id)

    def _build_langgraph(self):
        """构建 LangGraph 工作流"""
        try:
            from langgraph.graph import StateGraph, END
        except ImportError:
            logger.warning("LangGraph 未安装，使用简单模式")
            return None

        def create_graph_state():
            return {
                "messages": [],
                "history": [],
                "results": {},
                "current_agent": None,
            }

        try:
            from typing import TypedDict, Any

            class GraphState(TypedDict):
                messages: list[dict[str, Any]]
                history: list[dict[str, Any]]
                results: dict[str, Any]
                current_agent: str | None

            workflow = StateGraph(GraphState)
        except Exception:
            return None

        # 路由节点
        def route_node(state):
            content = state["messages"][-1]["content"] if state["messages"] else ""
            decision = self.orchestrator.route(content, state.get("history"))
            agent_type = decision.intent.value if hasattr(decision.intent, "value") else str(decision.intent)
            return {"current_agent": agent_type, "history": state.get("history", [])}

        # 执行节点
        def execute_node(state):
            agent_type_str = state.get("current_agent", "affairs")
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                agent_type = AgentType.AFFAIRS

            content = state["messages"][-1]["content"] if state["messages"] else ""
            message = AgentMessage(
                task_id="",
                source=AgentType.ORCHESTRATOR,
                target=agent_type,
                intent=agent_type_str,
                content=content,
                history=state.get("history", []),
            )
            agent = self.orchestrator.agents.get(agent_type)
            if agent:
                result = agent.execute(message)
                return {"results": {agent_type_str: result.answer}, "current_agent": agent_type_str}
            return {"results": {agent_type_str: "处理失败"}, "current_agent": agent_type_str}

        # 组装
        workflow.add_node("route", route_node)
        workflow.add_node("execute", execute_node)
        workflow.set_entry_point("route")
        workflow.add_edge("route", "execute")
        workflow.add_edge("execute", END)

        return workflow.compile()

    @staticmethod
    def _error_result(task_id: str, agent_type: AgentType, error: str) -> AgentResult:
        return AgentResult(
            task_id=task_id,
            agent_type=agent_type,
            status=TaskStatus.FAILED,
            answer="处理出错，请稍后重试",
            error=error,
        )
