"""成长 Agent — 学业规划、简历优化、面试训练、校园导航"""
from typing import AsyncGenerator
from .base_agent import BaseAgent
from .schemas import AgentMessage, AgentType


class GrowthAgent(BaseAgent):
    agent_type = AgentType.GROWTH

    def _handle(self, message: AgentMessage) -> str:
        messages = self._build_messages(message)
        return self._call_llm(messages)

    async def execute_stream(self, message: AgentMessage) -> AsyncGenerator[str, None]:
        messages = self._build_messages(message)
        async for token in self._call_llm_stream(messages):
            yield token

    def _build_messages(self, message: AgentMessage) -> list[dict]:
        intent = message.intent or "general"

        prompt_map = {
            "career_plan": (
                "你是一位经验丰富的大学生涯规划导师。请根据学生的专业、年级和兴趣，"
                "提供个性化的学业规划和职业发展建议。"
                "包括：学业重点安排、核心技能培养路径、实习/竞赛建议、毕业去向分析、近期行动计划。"
                "使用 Markdown 格式。"
            ),
            "resume": (
                "你是一位专业的简历优化顾问。请对简历提供全面的优化建议，包括：\n"
                "1. 整体结构和排版建议\n"
                "2. 内容优化（量化成果、动词使用）\n"
                "3. 关键词优化\n"
                "4. 针对目标岗位的个性化建议\n"
                "请直接给出优化后的建议版本。"
            ),
            "interview": (
                "你是一位经验丰富的面试教练。请对学生的面试回答进行点评，"
                "从内容完整性、表达逻辑、亮点挖掘等方面给出改进建议，"
                "并提供一个优化后的示范回答。"
            ),
            "campus_nav": (
                "你是一位热心的学长/学姐，熟悉大学生活的方方面面。"
                "请用轻松友好的语气提供建议，包括学习资源、社团活动、生活服务、心理健康等。"
            ),
            "exam_reminder": (
                "你是一位贴心的学习助手。请根据学生的考试日历，"
                "生成考前复习提醒计划，包括考前 1 个月、2 周、1 周、3 天的复习建议。"
            ),
        }

        system_prompt = prompt_map.get(
            intent,
            self._build_system_prompt("个性化成长"),
        )

        messages = [{"role": "system", "content": system_prompt}]
        if message.history:
            messages.extend(message.history[-5:])
        messages.append({"role": "user", "content": message.content})
        return messages
