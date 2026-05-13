"""主控路由 Agent (Orchestrator) — 意图分类 + 任务分发"""
import json
import logging
import re
from typing import AsyncGenerator
from .schemas import AgentMessage, AgentType, OrchestratorDecision
from .academic_agent import AcademicAgent
from .affairs_agent import AffairsAgent
from .growth_agent import GrowthAgent
from .general_agent import GeneralAgent

logger = logging.getLogger(__name__)

# 关键词路由兜底映射
KEYWORD_ROUTING = {
    AgentType.ACADEMIC: [
        "知识点", "课件", "练习题", "复习计划", "文献综述", "实验报告",
        "错题", "论文", "课程", "考试", "学习",
    ],
    AgentType.AFFAIRS: [
        "请假", "奖学金", "助学金", "补办", "转专业", "休学",
        "成绩", "毕业", "宿舍", "流程", "申请", "模板",
        "教务", "选课", "学分",
    ],
    AgentType.GROWTH: [
        "职业规划", "简历", "面试", "校园", "社团", "考研",
        "保研", "就业", "成长", "考试提醒",
    ],
    AgentType.GENERAL: [
        "你好", "hello", "聊天", "闲聊", "随便聊聊",
        "帮我写", "帮我做一个", "介绍一下", "什么是",
    ],
}


class Orchestrator:
    """主控路由 Agent"""

    def __init__(self, llm_fn=None, llm_fn_stream=None, use_llm_routing: bool = True):
        self.llm_fn = llm_fn
        self.llm_fn_stream = llm_fn_stream
        self.use_llm_routing = use_llm_routing
        self.agents = {
            AgentType.ACADEMIC: AcademicAgent(llm_fn=llm_fn, llm_fn_stream=llm_fn_stream),
            AgentType.AFFAIRS: AffairsAgent(llm_fn=llm_fn, llm_fn_stream=llm_fn_stream),
            AgentType.GROWTH: GrowthAgent(llm_fn=llm_fn, llm_fn_stream=llm_fn_stream),
            AgentType.GENERAL: GeneralAgent(llm_fn=llm_fn, llm_fn_stream=llm_fn_stream),
        }

    def route(self, content: str, history: list[dict] | None = None) -> OrchestratorDecision:
        """路由决策：判断用户输入属于哪个领域"""
        if self.use_llm_routing and self.llm_fn:
            return self._llm_route(content)
        return self._keyword_route(content)

    def execute(self, content: str, history: list[dict] | None = None) -> tuple[AgentType, str]:
        """路由并执行：先路由，再派发到对应 Agent"""
        decision = self.route(content, history)
        agent = self.agents.get(decision.intent)

        if not agent:
            return AgentType.AFFAIRS, "抱歉，我暂时无法处理您的请求。"

        message = AgentMessage(
            task_id="",
            source=AgentType.ORCHESTRATOR,
            target=decision.intent,
            intent=decision.intent.value if isinstance(decision.intent, AgentType) else "general",
            content=content,
            history=history or [],
        )

        result = agent.execute(message)
        return result.agent_type, result.answer

    async def execute_stream(self, content: str, history: list[dict] | None = None) -> tuple[AgentType, AsyncGenerator[str, None]]:
        """路由并流式执行：先路由，再流式调用对应 Agent"""
        decision = self.route(content, history)
        agent = self.agents.get(decision.intent)

        if not agent:
            async def error_stream():
                yield "抱歉，我暂时无法处理您的请求。"
            return AgentType.AFFAIRS, error_stream()

        message = AgentMessage(
            task_id="",
            source=AgentType.ORCHESTRATOR,
            target=decision.intent,
            intent=decision.intent.value if isinstance(decision.intent, AgentType) else "general",
            content=content,
            history=history or [],
        )

        return decision.intent, agent.execute_stream(message)

    def _llm_route(self, content: str) -> OrchestratorDecision:
        """基于 LLM 的意图分类"""
        prompt = (
            "你是一个意图分类器。请判断以下用户输入属于哪个领域：\n"
            "- academic: 学术相关（课件、练习题、复习、论文、实验报告等）\n"
            "- affairs: 校园事务相关（请假、奖学金、助学金、转专业、毕业等）\n"
            "- growth: 成长相关（职业规划、简历、面试、校园生活等）\n"
            "- general: 通用对话（日常聊天、知识问答、创意写作、编程等）\n\n"
            f"用户输入：{content[:500]}\n\n"
            '只返回 JSON：{"intent": "academic|affairs|growth|general", "confidence": 0.0-1.0, "reason": "原因"}'
        )

        try:
            response = self.llm_fn([{"role": "user", "content": prompt}])
            data = json.loads(re.search(r"\{.*\}", response, re.DOTALL).group())
            intent_map = {
                "academic": AgentType.ACADEMIC,
                "affairs": AgentType.AFFAIRS,
                "growth": AgentType.GROWTH,
                "general": AgentType.GENERAL,
            }
            intent = intent_map.get(data.get("intent", "affairs"), AgentType.AFFAIRS)
            return OrchestratorDecision(
                intent=intent,
                confidence=data.get("confidence", 0.5),
                reason=data.get("reason", ""),
            )
        except Exception:
            logger.exception("LLM 路由失败，使用关键词 fallback")
            return self._keyword_route(content)

    def _keyword_route(self, content: str) -> OrchestratorDecision:
        """基于关键词的兜底路由"""
        text = content.lower()
        scores = {}
        for agent_type, keywords in KEYWORD_ROUTING.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[agent_type] = score

        best = max(scores, key=scores.get)
        max_score = scores[best]
        confidence = min(max_score / 3.0, 1.0)  # 归一化

        return OrchestratorDecision(
            intent=best,
            confidence=confidence,
            reason=f"匹配 {max_score} 个关键词",
        )
