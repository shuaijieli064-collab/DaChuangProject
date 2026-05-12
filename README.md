# 智链校园 — 基于 RAG 与多智能体协同的高校垂直领域全场景辅助平台

河南省大学生创新训练重点项目 · 郑州轻工业大学

## 项目简介

**智链校园 2.0** 是一个面向高校场景的 AI 全场景辅助平台，基于 RAG（检索增强生成）架构与 Multi-Agent（多智能体）协同机制，构建集学术深度辅助、校园政务自动化、个性化成长规划于一体的智能平台。

### 核心特性

| 模块 | 功能 |
|------|------|
| 📚 学术辅助 | 课件知识点提炼、练习题生成、复习计划、文献综述框架、实验报告、错题分析 |
| 🏫 校园事务 | 请假/奖助学金/证件补办等流程查询、多轮对话、申请模板生成 |
| 🎯 成长助手 | 学业规划建议、简历优化、面试训练、校园生活导航 |

### 技术架构

- **数据层**: ETL 数据清洗 → 语义切片 → BGE-m3 Embedding → Milvus 向量存储
- **检索层**: 混合搜索（向量召回 + BM25）+ BGE-reranker 重排序
- **模型层**: LLM + 思维链 (CoT) + 检索增强生成 (RAG)
- **Agent 层**: Orchestrator 路由 + 学术/政务/成长子 Agent + LangGraph 编排
- **应用层**: FastAPI (async) + WebSocket 流式输出 + Vue3 前端

## 快速启动

### 方式一：本地开发（保留 Flask 兼容）

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置 AI_API_KEY
python app.py          # Flask 模式
# 或
uvicorn main:app --reload  # FastAPI 模式
```

### 方式二：Docker 部署

```bash
docker compose up -d
```

浏览器访问 `http://localhost:5000`（Flask/FastAPI）或 `http://localhost:80`（Docker）。

## 项目结构

```
study-main/
├── backend/                    # Python 后端
│   ├── main.py                 # FastAPI 入口（2.0 新增）
│   ├── app.py                  # Flask 入口（1.0 兼容）
│   ├── config.py               # 配置（含 RAG 配置）
│   ├── Dockerfile              # 后端容器化
│   ├── requirements.txt        # 依赖列表
│   ├── .env.example            # 环境变量模板
│   ├── etl/                    # ETL 数据管道（2.0 新增）
│   │   ├── loader.py           # 文档加载器
│   │   ├── splitter.py         # 语义切片
│   │   └── ingest.py           # 入库脚本
│   ├── agents/                 # Multi-Agent（2.0 新增）
│   │   ├── orchestrator.py     # 路由 Agent
│   │   ├── academic_agent.py   # 学术 Agent
│   │   ├── affairs_agent.py    # 政务 Agent
│   │   ├── growth_agent.py     # 成长 Agent
│   │   ├── base_agent.py       # Agent 基类
│   │   └── schemas.py          # 通信协议
│   ├── services/               # 服务层
│   │   ├── vector_store.py     # Milvus 向量存储
│   │   ├── bm25.py             # BM25 关键词检索
│   │   ├── rag_chain.py        # RAG 链路
│   │   ├── agent_engine.py     # Agent 编排引擎
│   │   ├── kb_service.py       # 知识库服务
│   │   └── ai_service.py       # LLM API 调用
│   └── routes/                 # Flask 路由（1.0 兼容）
├── frontend/                   # 1.0 前端（原生 HTML/JS）
├── frontend-vue/               # 2.0 前端（Vue3 + Element Plus）
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── components/ChatView.vue
│   │   ├── composables/chatStore.ts
│   │   └── styles/main.css
│   ├── Dockerfile
│   └── nginx.conf
├── data/                       # 知识库数据
│   └── campus_knowledge.json
├── docker-compose.yml          # Docker 编排
├── README.md
└── 项目书.md                   # 大创项目申报书
```

## API 接口

### 统一 Agent 接口（2.0 新增）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/chat` | 统一对话（自动路由到对应 Agent） |
| WS | `/ws/chat` | WebSocket 流式对话 |
| GET | `/api/health` | 健康检查 |

### 原有接口（1.0 兼容）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/academic/extract-knowledge` | 知识点提炼 |
| POST | `/api/academic/generate-questions` | 练习题生成 |
| POST | `/api/academic/study-plan` | 复习计划生成 |
| POST | `/api/academic/literature-review` | 文献综述框架 |
| POST | `/api/academic/lab-report` | 实验报告辅助 |
| POST | `/api/academic/wrong-questions` | 错题分析 |
| POST | `/api/affairs/query` | 事务查询 |
| POST | `/api/affairs/chat` | 事务多轮对话 |
| POST | `/api/affairs/template` | 申请模板生成 |
| POST | `/api/growth/career-plan` | 学业规划 |
| POST | `/api/growth/resume` | 简历优化 |
| POST | `/api/growth/interview` | 面试训练 |
| POST | `/api/growth/campus-nav` | 校园导航 |
| POST | `/api/growth/exam-reminder` | 考试提醒 |

## 数据入库

```bash
# 将 PDF/Word/TXT 文档导入向量知识库
cd backend
python -m etl.ingest data/pdfs/*.pdf data/docs/*.docx
```

## 技术栈

- **后端**: Python 3.12, FastAPI + Flask, LangChain/LangGraph
- **向量检索**: Milvus, BGE-m3 Embedding, BM25 + Rerank
- **前端**: Vue3 + TypeScript, Element Plus, Markdown 渲染
- **部署**: Docker Compose, Nginx, Redis
