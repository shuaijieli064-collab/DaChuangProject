"""Agent 通信 JSON Schema 协议"""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    ACADEMIC = "academic"
    AFFAIRS = "affairs"
    GROWTH = "growth"
    GENERAL = "general"
    ORCHESTRATOR = "orchestrator"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentMessage(BaseModel):
    """Agent 间通信消息"""
    task_id: str = Field(description="任务唯一标识")
    source: AgentType = Field(description="来源 Agent")
    target: AgentType = Field(description="目标 Agent")
    intent: str = Field(description="意图分类标签")
    content: str = Field(description="用户输入内容")
    context: dict[str, Any] = Field(default_factory=dict, description="附加上下文")
    history: list[dict] = Field(default_factory=list, description="对话历史")


class AgentResult(BaseModel):
    """Agent 执行结果"""
    task_id: str
    agent_type: AgentType
    status: TaskStatus
    answer: str = ""
    sources: list[dict] = Field(default_factory=list, description="引用来源")
    error: str = ""
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestratorDecision(BaseModel):
    """路由 Agent 决策"""
    intent: AgentType
    confidence: float = Field(ge=0.0, le=1.0, description="意图置信度")
    reason: str = ""
    needs_multi_agent: bool = Field(default=False, description="是否需要多 Agent 协作")
    execution_order: list[AgentType] = Field(
        default_factory=list,
        description="串行执行顺序（复合任务）",
    )
