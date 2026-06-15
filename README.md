# AgenticCustoms

> 基于 **Agentic RAG** 与 **多智能体协作** 的跨境合规贸易与关税智能申报平台

AI 外贸合规助手，通过多智能体分工协作，帮助中小外贸企业完成 **HS 编码归类 → 关税计算 → 禁限品校验 → 原产地匹配 → 申报文件生成** 的全流程闭环。

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                      前端展示层                           │
│            Vue3 + Element Plus + Pinia + ECharts         │
│  AI助手 │ HS归类 │ 关税计算 │ 合规校验 │ 全流程 │ 历史 │ 看板  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    多智能体业务层                          │
│                    LangGraph 编排                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                 │
│  │HS编码推理│→│关税计算  │→│合规校验  │                 │
│  └──────────┘ └──────────┘ └──────────┘                 │
│  ┌──────────┐ ┌──────────┐             并行+顺序协作     │
│  │原产地匹配│→│申报文件  │                               │
│  └──────────┘ └──────────┘                               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Agentic RAG 引擎                        │
│      意图识别 → 参数收集 → 实体提取 → 多轮检索 → 溯源校验 │
│                LangChain + Chroma                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                      数据层                               │
│     MySQL(结构化税则/税率/制裁) + Chroma(向量知识库)       │
│   HS编码 │ 税率表 │ 制裁清单 │ FTA规则 │ 对话历史          │
└──────────────────────────────────────────────────────────┘
```

---

## 项目结构

```
AgenticCustoms/
├── backend/
│   ├── main.py                      # FastAPI 应用入口
│   ├── requirements.txt             # Python 依赖清单
│   │
│   ├── domain/                      # 领域层 — Pydantic 业务实体
│   │   ├── enums.py                 # RiskLevel 枚举
│   │   ├── commodity.py             # 商品实体
│   │   ├── hs_code.py               # HS编码推理结果
│   │   ├── tariff_result.py         # 关税计算结果
│   │   ├── compliance_result.py     # 合规校验结果
│   │   ├── origin_result.py         # 原产地匹配结果
│   │   └── declaration_doc.py       # 申报文件实体
│   │
│   ├── shared/                      # 共享基础设施
│   │   ├── config.py                # 环境配置 (pydantic-settings)
│   │   ├── constants.py             # 共享常量 (COUNTRY_NAMES)
│   │   ├── logger.py                # 结构化日志 (structlog)
│   │   └── llm.py                   # LLM 调用适配器 + parse_llm_json
│   │
│   ├── data/                        # 数据层
│   │   ├── db/
│   │   │   ├── models.py            # ORM 模型 (6 张表)
│   │   │   └── database.py          # 异步引擎 + 自动建表
│   │   ├── seed/
│   │   │   ├── data.py              # 种子数据 (28条HS + 14条税率 + 3条制裁)
│   │   │   └── runner.py            # 幂等入库脚本
│   │   ├── import_usa.py            # 美国 HTS 导入脚本
│   │   ├── import_china.py          # 中国税则导入脚本
│   │   └── import_sanctions.py      # OFAC 制裁导入脚本
│   │
│   ├── rag/                         # RAG 引擎
│   │   ├── embedding.py             # bge-base-zh-v1.5 嵌入模型
│   │   ├── vector_store.py          # Chroma 向量库 CRUD
│   │   ├── retriever.py             # 特征拆解 + 多轮检索
│   │   └── seed.py                  # MySQL → Chroma 同步脚本
│   │
│   ├── agents/                      # 五大智能体
│   │   ├── base.py                  # Agent 基类
│   │   ├── chat/                    # AI 对话 Agent (ReAct + 4工具)
│   │   ├── hs_classifier/           # ① HS编码推理 (Agentic RAG)
│   │   ├── tariff_calculator/       # ② 关税计算 (查表 + LLM)
│   │   ├── compliance_checker/      # ③ 合规校验 (制裁匹配 + LLM)
│   │   ├── origin_matcher/          # ④ 原产地匹配 (FTA规则 + LLM)
│   │   └── doc_generator/           # ⑤ 申报文件生成 + 交叉校验
│   │
│   ├── orchestration/               # LangGraph 管道编排
│   │   ├── state.py                 # 全流程共享状态
│   │   └── graph.py                 # classify → 并行(tariff+compliance+origin) → document
│   │
│   ├── api/                         # API 路由
│   │   ├── deps.py                  # 依赖注入
│   │   └── routes/
│   │       ├── auth.py              # 登录/注册
│   │       ├── chat.py              # AI 对话 (意图分类+参数收集+Agent)
│   │       ├── classify.py          # HS 归类
│   │       ├── compliance.py        # 合规校验
│   │       ├── tariff.py            # 关税计算
│   │       ├── pipeline.py          # 一键全流程 + 文档HTML + PDF/ZIP下载
│   │       ├── history.py           # 历史记录 (分页+筛选)
│   │       ├── stats.py             # 风险看板统计
│   │       ├── report.py            # 三份文档 HTML 预览
│   │       ├── ocr.py               # 图片 OCR 识别
│   │       └── pages.py             # 前端 SPA 路由
│   │
│   └── tests/                       # 单元测试
│
├── frontend/                        # Vue3 + Vite 前端
│   └── src/
│       ├── main.ts                  # 入口
│       ├── App.vue                  # 根组件 (侧边栏+浮动聊天)
│       ├── constants.ts             # 共享常量 (COUNTRY_NAMES)
│       ├── views/
│       │   ├── HomeView.vue         # 首页
│       │   ├── ChatView.vue         # AI 助手独立页
│       │   ├── ClassifyView.vue     # HS 归类 (双栏+OCR)
│       │   ├── TariffView.vue       # 关税计算 (双模式)
│       │   ├── ComplianceView.vue   # 合规校验
│       │   ├── PipelineView.vue     # 一键全流程 (SSE+卡片)
│       │   ├── HistoryView.vue      # 历史记录 (分页+筛选)
│       │   ├── DashboardView.vue    # 风险看板 (ECharts)
│       │   ├── LoginView.vue        # 登录
│       │   └── RegisterView.vue     # 注册
│       ├── components/
│       │   ├── ChatPanel.vue        # 聊天面板 (通用)
│       │   ├── PipelineAgentCard.vue    # Agent 卡片
│       │   ├── PipelineCustomsPreview.vue  # 报关单预览
│       │   ├── PipelineOriginPreview.vue   # 原产地证预览
│       │   └── PipelineCompliancePreview.vue # 合规声明预览
│       ├── stores/
│       │   ├── auth.ts              # 认证状态
│       │   ├── chat.ts              # 聊天状态 (Pinia, 多端同步)
│       │   └── pipeline.ts          # 管道状态
│       ├── api/                     # Axios API 层
│       ├── types/                   # TypeScript 类型
│       ├── styles/                  # CSS (design-tokens + global + a4)
│       └── router/                  # Vue Router 4
│
├── 项目需求/                         # 项目文档 + 逐字稿 + 演示脚本
├── Dockerfile                       # 多阶段构建（前端 + 后端）
├── docker-compose.yml               # 一键部署编排（MySQL + App）
├── .dockerignore
├── .env.example                     # 环境变量模板
└── README.md
```

---

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
| 前端 | Vue3 + Element Plus + Pinia + ECharts |
| 版本管理 | Git |

---

## API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/login` | 登录 |
| `POST` | `/api/auth/register` | 注册 |
| `POST` | `/api/chat` | AI 对话 |
| `GET` | `/api/chat/history?session_id=` | 对话历史 |
| `DELETE` | `/api/chat/history?session_id=` | 清空对话 |
| `POST` | `/api/classify` | HS 编码归类 |
| `POST` | `/api/tariff` | 关税计算 |
| `POST` | `/api/compliance` | 合规校验 |
| `POST` | `/api/pipeline/full` | 一键全流程 (同步) |
| `POST` | `/api/pipeline/stream` | 一键全流程 (SSE流式) |
| `GET` | `/api/pipeline/report/{id}/{type}` | 文档 HTML 预览 |
| `GET` | `/api/pipeline/pdf/{id}/{type}` | 单文档 PDF 下载 |
| `GET` | `/api/pipeline/download/{id}` | 三合一 ZIP 下载 |
| `POST` | `/api/ocr` | 图片 OCR 识别 |
| `GET` | `/api/history` | 历史记录 (分页+筛选) |
| `DELETE` | `/api/history/{id}` | 删除记录 |
| `GET` | `/api/stats` | 看板统计数据 |
| `GET` | `/docs` | Swagger API 文档 |

---

## 快速开始

### 方式一：Docker Compose（推荐，一键部署）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，必填：DASHSCOPE_API_KEY=你的通义千问API密钥

# 2. 构建并启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f app
```

访问 `http://localhost:8000`，首次启动会自动建表、灌入种子数据、构建 Chroma 向量库。

常用命令：

```bash
docker-compose down          # 停止并删除容器
docker-compose up -d --build # 重新构建并启动
docker-compose logs -f app   # 查看应用日志
docker-compose exec app bash # 进入容器调试
```

### 方式二：本地开发

**环境要求：**

| 依赖 | 版本 |
|------|------|
| Python | >= 3.11 |
| MySQL | 8.0 |
| Node.js | >= 18 |
| DashScope API Key | 通义千问 Qwen-Plus |

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS agentic_customs CHARACTER SET utf8mb4;"

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 MYSQL_PASSWORD、DASHSCOPE_API_KEY 等

# 3. 安装后端依赖
cd backend
pip install -r requirements.txt

# 4. 灌入种子数据（首次运行）
python -m data.seed.runner
python -m rag.seed

# 5. 构建前端
cd ../frontend
npm install
npm run build

# 6. 启动服务
cd ../backend
python main.py
```

访问 `http://localhost:8000`，`/docs` 查看 Swagger API 文档。

---

## License

MIT
