"""通用对话 Agent — 日常聊天、知识问答、创意写作"""
from typing import AsyncGenerator
from .base_agent import BaseAgent
from .schemas import AgentMessage, AgentType


class GeneralAgent(BaseAgent):
    agent_type = AgentType.GENERAL

    def _handle(self, message: AgentMessage) -> str:
        messages = self._build_messages(message)
        return self._call_llm(messages)

    async def execute_stream(self, message: AgentMessage) -> AsyncGenerator[str, None]:
        messages = self._build_messages(message)
        async for token in self._call_llm_stream(messages):
            yield token

    def _build_messages(self, message: AgentMessage) -> list[dict]:
        system_prompt = (
            "你是一位友善、专业的 AI 助手。你可以进行日常聊天、知识问答、"
            "创意写作、编程帮助、问题解答等。\n\n"
            "回答要求：\n"
            "1. 使用中文回答（除非用户明确要求其他语言）\n"
            "2. 回答简洁明了、条理清晰\n"
            "3. 使用 Markdown 格式增强可读性\n"
            "4. 涉及数学公式时，使用 $...$ 包裹行内公式，$$...$$ 包裹行间公式\n"
            "5. 代码示例使用 ```language 代码 ``` 格式\n"
            "6. 如果不确定，请坦诚说明"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend((message.history or [])[-10:])
        messages.append({"role": "user", "content": message.content})
        return messages
