"""学术 Agent — 知识点提炼、练习题生成、文献综述、实验报告、错题分析"""
from .base_agent import BaseAgent
from .schemas import AgentMessage, AgentType


class AcademicAgent(BaseAgent):
    agent_type = AgentType.ACADEMIC

    def _handle(self, message: AgentMessage) -> str:
        intent = message.intent or "general"
        content = message.content

        prompt_map = {
            "extract_knowledge": (
                "你是一位专业的大学课程辅导助手。请对用户提供的课程资料进行深度分析，"
                "提炼核心知识点，生成结构化的学习笔记。"
                "要求：列出 3-8 个核心知识点，标注重要程度，指出易错点。使用 Markdown 格式。"
            ),
            "generate_questions": (
                "你是一位专业的大学课程出题助手。请根据提供的知识点内容出题，"
                "题目要有针对性、难度适中、能考查核心知识。使用 Markdown 格式。"
            ),
            "study_plan": (
                "你是一位经验丰富的学习规划师。请根据学生提供的信息，"
                "制定详细、可执行的复习计划。使用 Markdown 格式。"
            ),
            "literature_review": (
                "你是一位专业的学术写作助手。请帮助学生构建文献综述框架，"
                "提供写作思路和参考结构。"
            ),
            "lab_report": (
                "你是一位专业的理工科实验报告写作助手。请根据提供的实验信息，"
                "生成规范的实验报告初稿框架和内容建议。"
            ),
            "wrong_questions": (
                "你是一位专业的辅导老师。请对学生提供的错题进行分析，"
                "找出错误原因，给出正确解析，并总结解题规律。"
            ),
        }

        system_prompt = prompt_map.get(
            intent,
            self._build_system_prompt("学术辅导"),
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if message.history:
            messages.extend(message.history[-5:])
        messages.append({"role": "user", "content": content})

        return self._call_llm(messages)
