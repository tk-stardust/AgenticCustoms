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
│   ├── agents/                    # 五大智能体
│   │   ├── base.py                # Agent 基类（输入输出校验）
│   │   ├── hs_classifier/         # ① HS编码推理（RAG + LLM）
│   │   ├── tariff_calculator/     # ② 关税计算（查税率表 + LLM）
│   │   ├── compliance_checker/    # ③ 合规校验（制裁匹配 + LLM）
│   │   ├── origin_matcher/        # ④ 原产地匹配（FTA规则 + LLM）
│   │   └── doc_generator/         # ⑤ 申报文件生成 + 交叉校验
│   │
│   ├── orchestration/             # LangGraph 编排
│   │   ├── state.py               # 全流程共享状态
│   │   └── graph.py               # classify → 并行 → document 拓扑
│   │
│   ├── api/                       # API 路由
│   │   ├── deps.py                # 依赖注入（Agent 单例工厂）
│   │   └── routes/
│   │       ├── classify.py        # POST /api/classify
│   │       ├── pipeline.py        # POST /api/pipeline/full（含自动存档）
│   │       ├── history.py         # GET  /api/history
│   │       ├── report.py          # GET  /api/pipeline/report/{id}（下载申报报告）
│   │       ├── ocr.py             # POST /api/ocr（图片识别商品信息）
│   │       └── pages.py           # 前端 SPA 页面路由（刷新不 404）
│   └── tests/                     # 单元测试（23 passed）
│       ├── test_domain.py          # 领域实体校验
│       ├── test_errors.py          # 业务异常定义
│       └── test_api.py             # API 接口测试
│
├── frontend/                      # Vue3 + Vite 前端
│   └── src/
│       ├── views/
│       │   ├── HomeView.vue       # 首页——功能卡片导航 + 统计摘要
│       │   ├── ClassifyView.vue   # HS归类页（双栏：表单+OCR拍照识别+结果展示）
│       │   ├── PipelineView.vue   # 一键全流程（5Agent卡片+流程步骤条+报告下载）
│       │   ├── DashboardView.vue  # 风险看板（统计卡片+ECharts饼/柱图+风险列表）
│       │   └── HistoryView.vue    # 历史记录（搜索/筛选/表格+空状态引导）
│       ├── styles/                # UI 设计系统
│       │   ├── design-tokens.css  # 56 个 CSS 变量（配色/排版/圆角/阴影）
│       │   ├── global.css         # 全局重置 + 工具类
│       │   └── element-overrides.css  # Element Plus 主题覆写
│       ├── stores/pipeline.ts     # Pinia 流水线状态
│       ├── api/                   # Axios API 调用层（classify/pipeline/history/ocr）
│       ├── types/                 # TypeScript 类型（与后端 Pydantic 对齐）
│       └── router/                # Vue Router 4
│
├── .env.example                   # 环境变量模板
├── docker-compose.yml             # MySQL + Backend
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

## API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/classify` | HS 编码归类（~17s） |
| `POST` | `/api/pipeline/full?target_country=US` | 一键全流程（~60s） |
| `POST` | `/api/ocr` | 图片 OCR 识别商品信息 |
| `GET` | `/api/history?limit=20` | 申报历史记录 |
| `GET` | `/api/pipeline/report/{request_id}` | 下载申报报告 HTML |
| `GET` | `/docs` | Swagger API 文档 |

## 快速开始

### 环境要求

- Python >= 3.11（已实测 3.12、3.13）
- MySQL 8.0（本机或 Docker）
- DashScope API Key（通义千问 Qwen-Plus）

### 本地开发

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS agentic_customs CHARACTER SET utf8mb4;"

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 MYSQL_PASSWORD、DASHSCOPE_API_KEY、EMBEDDING_MODEL_PATH

# 3. 安装依赖
cd backend
pip install -e ".[dev]"

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

访问 `http://localhost:8000` 使用完整功能。`/docs` 查看 Swagger API 文档。

### Docker 一键启动

```bash
docker compose up -d
```

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

### Phase 3 — 多智能体协作 ✅ 已完成
- [x] 关税计算 Agent（税率表查询 + LLM 分析）
- [x] 合规校验 Agent（制裁匹配 + LLM 风险评估）
- [x] 原产地匹配 Agent（FTA 规则匹配 + 策略推荐）
- [x] 申报文件生成 Agent（汇总 + LLM 生成 + 交叉校验）
- [x] LangGraph 编排（HS → 并行三 Agent → 文件生成）
- [x] `/api/pipeline/full` 接口（全流程 40-60s）
- [x] 一键全流程前端页面（PipelineView）

### Phase 4 — 前端完善 + 测试 ✅ 已完成
- [x] ECharts 风险看板（统计卡片 + 饼图/柱图 + 风险列表）
- [x] 历史记录查询（搜索/筛选/表格 + 空状态引导）
- [x] 首页导航（4 张功能卡片 + 5 步可视化流程 + 统计卡片）
- [x] UI 设计系统（56 个 CSS 变量 + Element Plus 全局主题）
- [x] 全局布局（侧边栏 + 毛玻璃顶部栏 + 面包屑 + 路由切换动画）
- [x] SPA 托管（FastAPI 直接服务前端构建产物，一个端口）
- [x] 申报报告下载（HTML 报告，可打印为 PDF）
- [x] 图片 OCR 拍照识别（qwen-vl-plus 自动提取商品信息）
- [x] 单元测试（36 passed：领域/异常/配置/种子/Agent/API）
- [ ] Docker 生产部署（暂缓）

## 后续优化计划

### 🔴 高优先级（影响业务正确性）⚠️ 已开发，待测试
- [x] 增加货物数量和申报价值字段（Commodity 加 quantity + declared_value）
- [x] 合规校验每项单独打勾/打叉（禁运 / 制裁 / 许可证 / 环保），缺数据标注"未查到"
- [x] Agent 查不到数据时显式标注"未查到，请人工核实"，不静默输出空值
- [x] 申报报告全中文化（报告内容中文，JSON 字段名保留英文供前端解析）
- [x] Dashboard 统计卡片改为从数据库实时计算（GET /api/stats）
- [ ] **已知问题**：一键全流程完成后右侧可能显示空白页（历史记录中有数据，疑似 store 响应式未触发重渲染），需测试确认

### 🟡 中优先级（提升体验和健壮性）
- [ ] 一键全流程每步输出可审计中间结果（前端展示输入/输出/检查项）
- [ ] 风险记录列表从 mock 改为读取 `/api/history` 真实数据
- [ ] 首页统计数据从 mock 改为真实数据库查询
- [ ] 历史记录后端加分页（page + page_size + 总数），前端加分页器
- [ ] 历史记录"导出"按钮接 CSV 导出接口
- [ ] Pipeline 进度改为 SSE 推送真实后端进度（替代当前前端模拟计时）
- [ ] 长等待增加"停止分析"取消按钮
- [ ] "清空"按钮只清表单不清结果，增加独立"清除结果"按钮
- [ ] LLM 调用加重试机制（最多 2 次），失败返回友好中文错误信息
- [ ] 输入框增加长度限制（名称 200 字，描述 2000 字）
- [ ] 商品描述区域增加 OCR 拍照入口

### 🟢 低优先级（打磨细节）
- [ ] 报告改为 PDF 下载，排版参照真实中国海关报关单格式
- [ ] 完整文件包补充：税费明细表、原产地证书正式格式
- [ ] 税率数据标注生效日期（"数据更新至 YYYY-MM-DD"）
- [ ] 一票多商品同时申报
- [ ] HS 归类页步骤 1/2/3 改为时间线 + 卡片展示，关键条文高亮
- [ ] 报告视图增加折叠/展开切换
- [ ] 风险看板空状态增加示例数据切换开关
- [ ] 顶部栏用户头像改为"关于/帮助"入口
- [ ] 导入真实海关税则 + 美国 HTS + OFAC 制裁清单数据（文件已下载，待写导入脚本）

## 设计原则

1. **正确性第一**：Agent 输入输出 Pydantic 强校验，所有结论可溯源至条文
2. **可读性第二**：目录名即架构分层，文件名即职责，函数名动词开头
3. **可维护性第三**：新增贸易国只改配置不动代码，LLM 适配层可替换模型
4. **健壮性第四**：流水线不因单点失败而中断，可断点重试
5. **性能第五**：关税/合规/原产地三 Agent 并行，热点数据缓存

## License

MIT
