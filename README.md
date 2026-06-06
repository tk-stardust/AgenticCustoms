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
│   │   └── logger.py              # 结构化日志(structlog)
│   │
│   ├── data/                      # 数据层
│   │   └── models.py              # SQLAlchemy ORM 模型
│   │
│   ├── rag/                       # [待开发] RAG引擎
│   ├── agents/                    # [待开发] 5个智能体
│   ├── orchestration/             # [待开发] LangGraph编排
│   ├── api/                       # [待开发] FastAPI路由
│   └── tests/                     # [待开发] 测试
│
├── frontend/                      # Vue3 前端
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

### Phase 1 — 骨架搭建 ✅ 进行中
- [x] 目录结构规划
- [x] 领域实体定义 (Pydantic)
- [x] 数据库模型 (SQLAlchemy)
- [x] Docker 环境
- [ ] 数据初始化脚本

### Phase 2 — RAG 引擎 (计划中)
- [ ] 向量检索器 (Chroma)
- [ ] Query 改写与拆解
- [ ] 条文溯源标注

### Phase 3 — 多智能体 (计划中)
- [ ] HS 编码推理 Agent
- [ ] 关税计算 Agent
- [ ] 合规校验 Agent
- [ ] 原产地匹配 Agent
- [ ] 申报文件生成 Agent
- [ ] LangGraph 编排

### Phase 4 — API + 前端 (计划中)
- [ ] FastAPI 接口层
- [ ] Vue3 前端页面
- [ ] 风险看板与文件下载

### Phase 5 — 测试 + 部署 (计划中)
- [ ] 单元测试与集成测试
- [ ] Docker 生产部署
- [ ] 项目文档

## 设计原则

1. **正确性第一**：Agent 输入输出 Pydantic 强校验，所有结论可溯源至条文
2. **可读性第二**：目录名即架构分层，文件名即职责，函数名动词开头
3. **可维护性第三**：新增贸易国只改配置不动代码，LLM 适配层可替换模型
4. **健壮性第四**：流水线不因单点失败而中断，可断点重试
5. **性能第五**：关税/合规/原产地三 Agent 并行，热点数据缓存

## License

MIT
