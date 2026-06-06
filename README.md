# AgenticCustoms

> 基于 **Agentic RAG** 与 **多智能体协作** 的跨境合规贸易与关税智能申报平台

AI 外贸合规助手，通过多智能体分工协作，帮助中小外贸企业完成 **HS 编码归类 → 关税计算 → 禁限品校验 → 原产地匹配 → 申报文件生成** 的全流程闭环。

---

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   前端展示层                          │
│         Vue3 + Element Plus + ECharts               │
│  商品输入 │ 关税试算 │ 风险看板 │ 文件下载 │ 历史记录  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                 多智能体业务层                        │
│                  LangGraph 编排                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │HS编码推理│ │关税计算  │ │合规校验  │             │
│  └──────────┘ └──────────┘ └──────────┘             │
│  ┌──────────┐ ┌──────────┐                          │
│  │原产地匹配│ │申报文件  │  并行 + 顺序协作          │
│  └──────────┘ └──────────┘                          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                Agentic RAG 引擎                      │
│    意图识别 → 问题拆解 → 多轮检索 → 溯源校验          │
│              LangChain + Chroma                      │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   数据层                              │
│   MySQL(结构化税则/税率) + Chroma(向量知识库)         │
│  HS编码 │ 关税表 │ 制裁清单 │ FTA原产地规则            │
└─────────────────────────────────────────────────────┘
```

## 项目结构

```
AgenticCustoms/
├── backend/
│   ├── main.py                    # FastAPI 应用入口
│   ├── pyproject.toml             # 项目元数据与依赖
│   ├── requirements.txt           # Docker 构建用依赖清单
│   │
│   ├── domain/                    # 领域层 — 纯业务实体
│   │   ├── enums.py               # RiskLevel / TradeRoute / IntentType
│   │   ├── commodity.py           # 商品实体
│   │   ├── hs_code.py             # HS编码推理结果
│   │   ├── tariff_result.py       # 关税计算结果
│   │   ├── compliance_result.py   # 合规校验结果
│   │   ├── origin_result.py       # 原产地匹配结果
│   │   └── declaration_doc.py     # 申报文件实体
│   │
│   ├── shared/                    # 共享基础设施
│   │   ├── config.py              # 环境配置(pydantic-settings)
│   │   ├── errors.py              # 业务异常定义
│   │   ├── logger.py              # 结构化日志(structlog)
│   │   └── llm.py                 # LLM 调用适配器(DashScope)
│   │
│   ├── data/                      # 数据层
│   │   ├── db/
│   │   │   ├── models.py          # 4张ORM表(hs_codes/tariff/sanctions/declarations)
│   │   │   └── database.py        # 异步引擎 + 会话 + 自动建表
│   │   └── seed/
│   │       ├── data.py            # 28条HS编码+14条税率+3条制裁
│   │       └── runner.py          # 幂等入库脚本
│   │
│   ├── rag/                       # RAG引擎
│   │   ├── embedding.py           # bge-base-zh-v1.5 本地嵌入模型
│   │   ├── vector_store.py        # Chroma 向量库CRUD
│   │   ├── retriever.py           # 商品特征拆解 + 多轮检索
│   │   └── seed.py               # MySQL → Chroma 同步脚本
│   │
│   ├── agents/                    # 多智能体
│   │   ├── base.py                # Agent 基类(输入输出校验)
│   │   └── hs_classifier/
│   │       └── agent.py           # HS编码推理Agent(RAG+LLM)
│   │
│   ├── orchestration/             # [待开发] LangGraph编排
│   │
│   ├── api/                       # API 路由
│   │   ├── deps.py                # 依赖注入
│   │   └── routes/
│   │       ├── classify.py        # POST /api/classify
│   │       └── pages.py           # 前端页面路由（SPA 刷新不 404）
│   └── tests/                     # [待开发] 测试
│
├── frontend/                      # Vue3 + Vite 前端
├── docker-compose.yml             # MySQL + Chroma + Backend
├── Dockerfile.backend
└── README.md
```

## 技术栈

| 组件 | 选型 |
|------|------|
| 后端框架 | FastAPI |
| 大语言模型 | Qwen-Plus (DashScope) |
| 嵌入模型 | bge-base-zh-v1.5 |
| 向量数据库 | Chroma |
| RAG 框架 | LangChain |
| 多智能体框架 | LangGraph |
| 关系数据库 | MySQL 8.0 |
| 前端 | Vue3 + Element Plus + ECharts |
| 部署 | Docker + Nginx |

## 快速开始

### 环境要求

- Python >= 3.11
- Docker & Docker Compose
- MySQL 8.0 (Docker 提供)

### 本地开发

```bash
# 1. 启动基础设施
docker compose up -d mysql

# 2. 安装 Python 依赖
cd backend
pip install -e ".[dev]"

# 3. 配置环境变量 (可选，有默认值)
cp .env.example .env

# 4. 启动开发服务器
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker 一键启动

```bash
docker compose up -d
```

访问 `http://localhost:8000/health` 验证服务状态。

## 实施路线图

### Phase 1 — 骨架搭建 ✅ 已完成
- [x] 目录结构规划
- [x] 领域实体定义（7 个 Pydantic 模型）
- [x] 数据库模型（4 张表，启动时自动建表）
- [x] 配置、异常、日志基础设施
- [x] 种子数据（28 条 HS 编码 + 14 条税率 + 3 条制裁）
- [x] Docker 环境（MySQL + Backend）
- [x] 前端骨架（Vite + Vue3 + Pinia + Axios + Element Plus + 4 页面路由）

### Phase 2 — RAG 引擎 + HS 归类（最小闭环）✅ 已完成
- [x] Chroma 向量库初始化（28条HS编码已嵌入）
- [x] 商品特征拆解 & Query 改写（LLM驱动的多轮检索）
- [x] 条文溯源校验（推理路径含WCO注释引用）
- [x] HS 编码推理 Agent（RAG检索 + LLM推理合成）
- [x] `/api/classify` 接口（17s端到端，返回编码+置信度+推理链）
- [x] 前端归类页面（表单输入 → 展示编码/置信度/推理路径/条文溯源）

### Phase 3 — 多智能体协作
- [ ] 关税计算 Agent
- [ ] 合规校验 Agent
- [ ] 原产地匹配 Agent
- [ ] 申报文件生成 Agent
- [ ] LangGraph 编排（HS推理 → 并行三 Agent → 文件生成）
- [ ] `/api/pipeline/full` 接口

### Phase 4 — 前端完善 + 部署
- [ ] 一键全流程页面（PipelineView）
- [ ] ECharts 风险看板
- [ ] 历史记录查询
- [ ] Docker 生产部署
- [ ] 单元测试 & 集成测试

## 设计原则

1. **正确性第一**：Agent 输入输出 Pydantic 强校验，所有结论可溯源至条文
2. **可读性第二**：目录名即架构分层，文件名即职责，函数名动词开头
3. **可维护性第三**：新增贸易国只改配置不动代码，LLM 适配层可替换模型
4. **健壮性第四**：流水线不因单点失败而中断，可断点重试
5. **性能第五**：关税/合规/原产地三 Agent 并行，热点数据缓存

## License

MIT
