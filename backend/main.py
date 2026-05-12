"""FastAPI 主应用入口 — 智链校园 2.0

保留 1.0 Flask API 路径兼容，新增 WebSocket 流式输出和 Agent 引擎。
"""
import io
import logging
import os
import sys
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    CORS_ORIGINS, DEBUG, MAX_TEXT_LENGTH, MAX_QUERY_LENGTH,
    MAX_HISTORY_MSG_LENGTH, MAX_HISTORY_TURNS, MAX_EXAM_COUNT,
    RAG_ENABLED, AI_API_KEY,
)
from services.ai_service import chat_completion
from services.kb_service import search_knowledge, get_affair_info
from services.agent_engine import AgentEngine
from agents.schemas import AgentType

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 初始化 Agent 引擎
_llm_fn = None
if AI_API_KEY:
    def _llm_fn(messages: list[dict]) -> str:
        return chat_completion(messages)

agent_engine = AgentEngine(llm_fn=_llm_fn, use_langgraph=False)

# FastAPI 应用
app = FastAPI(
    title="智链校园 API",
    description="基于 RAG 与多智能体协同的高校垂直领域全场景辅助平台",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Pydantic Models ----

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    history: list[dict] = Field(default_factory=list)

class AcademicRequest(BaseModel):
    content: str = Field(..., max_length=10000)
    count: int = Field(default=5, ge=1, le=20)
    type: str = Field(default="mixed")

class StudyPlanRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=1000)
    exam_date: str = ""
    weak_points: str = ""
    available_hours: float = Field(default=2, gt=0, le=24)

class TemplateRequest(BaseModel):
    type: str = Field(..., min_length=1, max_length=1000)
    user_info: dict = Field(default_factory=dict)

class CareerPlanRequest(BaseModel):
    major: str = Field(..., min_length=1, max_length=1000)
    grade: str = ""
    interests: str = ""
    goals: str = ""

class ResumeRequest(BaseModel):
    resume: str = Field(..., min_length=1, max_length=10000)
    position: str = ""
    industry: str = ""

class InterviewRequest(BaseModel):
    position: str = ""
    question: str = ""
    answer: str = ""
    mode: str = "feedback"  # feedback | generate

class CampusNavRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)

class ExamReminderRequest(BaseModel):
    exams: list[dict] = Field(..., min_length=1, max_length=20)
    semester_start: str = ""

class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list)
    intent: str = ""  # 可选：指定 Agent 类型


# ---- 健康检查 ----

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "name": "智链校园 API",
        "version": "2.0.0",
        "rag_enabled": RAG_ENABLED,
    }


# ---- 学术辅助 API (兼容 1.0 路径) ----

@app.post("/api/academic/extract-knowledge")
async def extract_knowledge(req: AcademicRequest):
    if not req.content.strip():
        raise HTTPException(400, "请上传文件或输入文本内容")
    text = req.content[:MAX_TEXT_LENGTH]

    messages = [
        {"role": "system", "content": (
            "你是一位专业的大学课程辅导助手。请对用户提供的课程资料进行深度分析，"
            "提炼核心知识点，生成结构化的学习笔记。"
        )},
        {"role": "user", "content": f"请提炼以下课程资料中的知识点：\n\n{text[:3000]}"},
    ]
    result = chat_completion(messages, temperature=0.5)
    return {"result": result, "chars_processed": len(text)}


@app.post("/api/academic/generate-questions")
async def generate_questions(req: AcademicRequest):
    if not req.content.strip():
        raise HTTPException(400, "请提供知识点或课程内容")

    type_desc = {"single": "单选题", "multiple": "多选题", "short": "简答题", "mixed": "混合题型"}.get(req.type, "混合题型")
    messages = [
        {"role": "system", "content": "你是一位专业的大学课程出题助手。"},
        {"role": "user", "content": f"请根据以下内容生成 {req.count} 道{type_desc}，并附上参考答案：\n\n{req.content[:2000]}"},
    ]
    result = chat_completion(messages, temperature=0.6)
    return {"result": result}


@app.post("/api/academic/study-plan")
async def study_plan(req: StudyPlanRequest):
    context = f"课程：{req.subject}"
    if req.exam_date:
        context += f"\n考试日期：{req.exam_date}"
    if req.weak_points:
        context += f"\n薄弱知识点：{req.weak_points}"
    context += f"\n每天可用学习时间：{req.available_hours:g} 小时"

    messages = [
        {"role": "system", "content": "你是一位经验丰富的学习规划师。请制定详细、可执行的复习计划。"},
        {"role": "user", "content": f"请为我制定复习计划：\n{context}"},
    ]
    result = chat_completion(messages, temperature=0.6)
    return {"result": result}


@app.post("/api/academic/literature-review")
async def literature_review(req: dict = {}):
    topic = req.get("topic", "").strip()
    field = req.get("field", "").strip()
    if not topic:
        raise HTTPException(400, "请填写研究主题")

    messages = [
        {"role": "system", "content": "你是一位专业的学术写作助手。请帮助学生构建文献综述框架。"},
        {"role": "user", "content": f"研究主题：{topic}\n研究领域：{field}\n\n请提供综述框架、写作要点和关键词建议。"},
    ]
    result = chat_completion(messages, temperature=0.6)
    return {"result": result}


@app.post("/api/academic/lab-report")
async def lab_report(req: dict = {}):
    experiment = req.get("experiment", "").strip()
    purpose = req.get("purpose", "").strip()
    method = req.get("method", "").strip()
    data = req.get("data", "").strip()
    if not experiment:
        raise HTTPException(400, "请填写实验名称")

    content = f"实验名称：{experiment}"
    if purpose: content += f"\n实验目的：{purpose}"
    if method: content += f"\n实验方法：{method}"
    if data: content += f"\n实验数据：{data}"

    messages = [
        {"role": "system", "content": "你是一位专业的理工科实验报告写作助手。"},
        {"role": "user", "content": f"请帮我撰写实验报告初稿：\n\n{content}"},
    ]
    result = chat_completion(messages, temperature=0.5)
    return {"result": result}


@app.post("/api/academic/wrong-questions")
async def wrong_questions(req: dict = {}):
    questions = req.get("questions", "").strip()
    subject = req.get("subject", "").strip()
    if not questions:
        raise HTTPException(400, "请输入错题内容")

    messages = [
        {"role": "system", "content": "你是一位专业的辅导老师。请分析错题原因并给出正确解析。"},
        {"role": "user", "content": f"{'课程：' + subject + chr(10) if subject else ''}以下是我的错题，请分析：\n\n{questions[:2000]}"},
    ]
    result = chat_completion(messages, temperature=0.5)
    return {"result": result}


# ---- 校园事务 API (兼容 1.0 路径) ----

AFFAIR_KEYWORDS = {
    "请假": ["请假", "病假", "事假", "外出"],
    "奖学金": ["奖学金", "国奖", "校奖"],
    "助学金": ["助学金", "贫困补助"],
    "证件补办": ["补办", "证件", "学生证", "校园卡"],
    "转专业": ["转专业", "换专业"],
    "休学": ["休学", "暂停学业"],
    "成绩查询": ["成绩", "绩点", "GPA", "补考", "重修"],
    "毕业手续": ["毕业", "离校"],
    "宿舍调换": ["宿舍", "换寝室"],
}


def _detect_affair_type(query: str) -> str | None:
    query_lower = query.lower()
    for affair, keywords in AFFAIR_KEYWORDS.items():
        if any(kw.lower() in query_lower for kw in keywords):
            return affair
    return None


@app.post("/api/affairs/query")
async def query_affair(req: ChatRequest):
    query = req.query[:MAX_QUERY_LENGTH]
    affair_type = _detect_affair_type(query)

    # RAG 检索
    kb_context = ""
    kb_results = search_knowledge(query)
    if kb_results:
        kb_context = "\n".join(r.get("content", "") for r in kb_results[:3])

    # 结构化知识库补充
    if affair_type:
        info = get_affair_info(affair_type)
        if info:
            if isinstance(info, dict):
                info_str = "\n".join(f"**{k}**：{v}" for k, v in info.items())
            else:
                info_str = str(info)
            kb_context = info_str + "\n\n" + kb_context

    system_prompt = (
        "你是智链校园的校园事务助手。请根据以下参考资料回答问题。\n"
        "回答要清晰、结构化，包含办理流程、所需材料和注意事项。\n"
        "如涉及具体规定，请说明以学校实际规定为准。\n"
    )
    if kb_context:
        system_prompt += f"\n【参考资料】\n{kb_context}"

    messages = [{"role": "system", "content": system_prompt}]
    for item in req.history[-MAX_HISTORY_TURNS:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
            messages.append({"role": item["role"], "content": str(item.get("content", ""))[:MAX_HISTORY_MSG_LENGTH]})
    messages.append({"role": "user", "content": query})

    result = chat_completion(messages, temperature=0.4)
    return {"result": result, "affair_type": affair_type}


@app.post("/api/affairs/template")
async def generate_template(req: TemplateRequest):
    info_str = ""
    if req.user_info:
        info_str = "\n".join(
            f"{str(k)[:50]}：{str(v)[:200]}"
            for k, v in list(req.user_info.items())[:20] if v
        )

    messages = [
        {"role": "system", "content": "你是专业的学生事务助手，擅长撰写各类申请材料。"},
        {"role": "user", "content": (
            f"请生成一份【{req.type}】的标准申请模板。\n"
            f"{'学生信息：\n' + info_str if info_str else ''}\n"
            "要求：格式规范，用 [...] 标注需要填写的内容。"
        )},
    ]
    result = chat_completion(messages, temperature=0.3)
    return {"result": result}


@app.get("/api/affairs/types")
async def get_affair_types():
    return {"types": list(AFFAIR_KEYWORDS.keys())}


@app.post("/api/affairs/chat")
async def affairs_chat(req: AgentChatRequest):
    # 使用 Agent 引擎
    result = agent_engine.process(
        content=req.message[:MAX_QUERY_LENGTH],
        history=req.history,
        intent="affairs",
    )
    return {"result": result.answer, "latency_ms": result.latency_ms}


# ---- 成长助手 API (兼容 1.0 路径) ----

@app.post("/api/growth/career-plan")
async def career_plan(req: CareerPlanRequest):
    context = f"专业：{req.major}"
    if req.grade: context += f"\n年级：{req.grade}"
    if req.interests: context += f"\n兴趣方向：{req.interests}"
    if req.goals: context += f"\n目标：{req.goals}"

    messages = [
        {"role": "system", "content": "你是经验丰富的大学生涯规划导师。请提供个性化的学业规划和职业发展建议。"},
        {"role": "user", "content": f"请为我提供学业规划建议：\n{context}"},
    ]
    result = chat_completion(messages, temperature=0.6)
    return {"result": result}


@app.post("/api/growth/resume")
async def optimize_resume(req: ResumeRequest):
    context = ""
    if req.position: context += f"目标岗位：{req.position}\n"
    if req.industry: context += f"目标行业：{req.industry}\n"

    messages = [
        {"role": "system", "content": "你是专业的简历优化顾问。请对简历提供全面的优化建议。"},
        {"role": "user", "content": f"{context}\n我的简历如下：\n\n{req.resume[:2000]}"},
    ]
    result = chat_completion(messages, temperature=0.5)
    return {"result": result}


@app.post("/api/growth/interview")
async def interview_practice(req: InterviewRequest):
    if req.mode == "generate":
        if not req.position:
            raise HTTPException(400, "请填写目标岗位")
        messages = [
            {"role": "system", "content": "你是专业的面试官。请根据目标岗位生成面试题目。"},
            {"role": "user", "content": f"请为【{req.position}】岗位生成 10 道常见面试题。"},
        ]
    else:
        if not req.question or not req.answer:
            raise HTTPException(400, "请填写面试题目和您的回答")
        messages = [
            {"role": "system", "content": "你是经验丰富的面试教练。请点评学生的面试回答并提供优化建议。"},
            {"role": "user", "content": f"面试题目：{req.question}\n我的回答：{req.answer[:1000]}"},
        ]
    result = chat_completion(messages, temperature=0.6)
    return {"result": result}


@app.post("/api/growth/campus-nav")
async def campus_nav(req: CampusNavRequest):
    messages = [
        {"role": "system", "content": "你是热心的学长/学姐，请为学弟学妹提供校园生活建议。"},
        {"role": "user", "content": req.query[:MAX_QUERY_LENGTH]},
    ]
    result = chat_completion(messages, temperature=0.7)
    return {"result": result}


@app.post("/api/growth/exam-reminder")
async def exam_reminder(req: ExamReminderRequest):
    exam_list = "\n".join(
        f"- {e.get('name', '')}：{e.get('date', '')}（{e.get('notes', '')}）"
        for e in req.exams[:MAX_EXAM_COUNT]
        if e.get("name")
    )
    if not exam_list.strip():
        raise HTTPException(400, "请提供有效的考试信息")

    messages = [
        {"role": "system", "content": "你是贴心的学习助手。请生成考前复习提醒计划。"},
        {"role": "user", "content": f"考试安排：\n{exam_list}\n\n请生成复习提醒计划。"},
    ]
    result = chat_completion(messages, temperature=0.5)
    return {"result": result}


# ---- 新增：Agent 统一入口 ----

@app.post("/api/agent/chat")
async def agent_chat(req: AgentChatRequest):
    """
    统一的 Agent 对话接口 — 自动路由到对应 Agent
    """
    result = agent_engine.process(
        content=req.message[:MAX_QUERY_LENGTH],
        history=req.history,
        intent=req.intent or None,
    )
    return {
        "result": result.answer,
        "agent_type": result.agent_type.value,
        "status": result.status.value,
        "latency_ms": result.latency_ms,
    }


# ---- WebSocket 流式输出 ----

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 流式对话"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            history = data.get("history", [])
            intent = data.get("intent", "")

            if not message:
                await websocket.send_json({"error": "消息不能为空"})
                continue

            # 使用流式输出
            async def stream_response():
                result = agent_engine.process(
                    content=message[:MAX_QUERY_LENGTH],
                    history=history,
                    intent=intent or None,
                )
                # 逐字发送
                answer = result.answer
                chunk_size = 5
                for i in range(0, len(answer), chunk_size):
                    await websocket.send_json({
                        "type": "chunk",
                        "content": answer[i : i + chunk_size],
                        "done": False,
                    })
                    await asyncio_sleep(0.02)  # 打字机效果
                await websocket.send_json({
                    "type": "done",
                    "content": answer,
                    "done": True,
                    "agent_type": result.agent_type.value,
                    "latency_ms": result.latency_ms,
                })

            await stream_response()

    except WebSocketDisconnect:
        logger.info("WebSocket 断开连接")
    except Exception as e:
        logger.exception("WebSocket 异常")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


# 异步 sleep helper
async def asyncio_sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


# ---- 静态文件和 SPA ----

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            with open(index_path, encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>智链校园 2.0</h1><p>前端文件未找到</p>")


# ---- 错误处理 ----

@app.exception_handler(404)
async def not_found_handler(request, exc):
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "接口不存在"}, status_code=404)
    return await serve_frontend()
