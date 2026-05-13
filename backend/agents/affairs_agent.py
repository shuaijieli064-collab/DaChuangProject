"""政务 Agent — 校园事务问答、流程编排、申请模板生成"""
from typing import AsyncGenerator
from .base_agent import BaseAgent
from .schemas import AgentMessage, AgentType


class AffairsAgent(BaseAgent):
    agent_type = AgentType.AFFAIRS

    def _handle(self, message: AgentMessage) -> str:
        messages = self._build_messages(message)
        return self._call_llm(messages)

    async def execute_stream(self, message: AgentMessage) -> AsyncGenerator[str, None]:
        messages = self._build_messages(message)
        async for token in self._call_llm_stream(messages):
            yield token

    def _build_messages(self, message: AgentMessage) -> list[dict]:
        intent = message.intent or "query"
        kb_context = message.context.get("kb_context", "")

        if intent == "template":
            system_prompt = (
                "你是一位专业的高校学生事务助手，擅长撰写各类学生申请材料。"
                "请生成规范、正式的申请模板，格式清晰，可直接使用。"
                "用 [...] 标注需要填写的内容。"
            )
        else:
            system_prompt = (
                "你是一位专业的高校学生事务助手，熟悉各类校园事务的办理流程、"
                "所需材料和注意事项。请用清晰、结构化的方式回答问题，包括：\n"
                "1. 办理流程（分步骤）\n"
                "2. 所需材料清单\n"
                "3. 办理地点和时间\n"
                "4. 注意事项\n"
                "如涉及具体规定，请说明以学校实际规定为准。"
            )

        if kb_context:
            system_prompt += f"\n\n【知识库参考】\n{kb_context}"

        messages = [{"role": "system", "content": system_prompt}]
        if message.history:
            messages.extend(message.history[-5:])
        messages.append({"role": "user", "content": message.content})
        return messages
