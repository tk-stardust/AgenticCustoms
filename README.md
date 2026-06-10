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

> ⚠️ **以下改动已完成但未完整端到端测试。** 涉及 SSE 流式推送、DocGenerator 代码层计算、真实数据导入等核心链路，上线前需逐项验证。

### ✅ 已完成（前四轮迭代）
- [x] 增加货物数量和申报价值字段
- [x] 合规校验每项单独打勾/打叉，缺数据标注"未查到"
- [x] Agent 查不到数据时显式标注"未查到，请人工核实"
- [x] 申报报告全中文化
- [x] Dashboard 统计卡片改为数据库实时计算（`GET /api/stats`）
- [x] 一键全流程切页回不来 / 空白页（恢复 `<keep-alive>` + `onActivated`/`onDeactivated`）
- [x] axios 超时 30s → classify 120s / pipeline 300s
- [x] 按钮缺 `type="button"` 导致页面刷新、localStorage 脏数据残留、定时器未清理
- [x] Pipeline 结果区改造 5 项：税费明细表 / 合规清单 / 交叉校验 / Agent 颜色 / 模态框文档预览
- [x] 后端 graph.py + pipeline.py 透传中间结果到前端
- [x] LLM 重试（chat + chat_vision，最多 2 次，指数退避）
- [x] 输入框长度限制（名称/描述/功能/用途/材质/max）
- [x] "清空表单" / "清除结果" 按钮分离
- [x] ZIP 下载申报文件（后端 `GET /api/pipeline/download/{id}`，`zipfile` 打包三份 HTML）
- [x] 美国 HTS 导入补全（FTA 优惠税率 / 反倾销字段，6 位编码覆盖）
- [x] 关税税率 LIKE 前缀匹配修复 + `data_missing` 警告
- [x] 税费明细 / 合规校验折叠展开
- [x] 税费显示具体金额（`declared_value × rate`）
- [x] 全局页面 max-width 1100 → 1400px
- [x] 侧边栏折叠动画修复 + 图标居中 + 悬浮 tooltip
- [x] 历史记录分页器全面重做（吸底 / 页码 / 每页条数 / 跳转）
- [x] Dashboard 图表数据与表格数据分离（饼图用全量聚合，表格取最近 5 条）
- [x] 国家名称本地化（US→美国，EU→欧盟 等）
- [x] 清除结果同步重置顶部步骤条
- [x] 历史记录默认每页 10 条
- [x] 风险看板 → 历史记录筛选修复（sessionStorage 方案）

---

### 🔴 高优先级（影响业务正确性）

- [x] **DocGenerator 代码层计算，不让 LLM 自述**：`customs_declaration` 数值字段由代码从 `tariff_result` 直接填入，LLM 只负责生成 `compliance_statement` 文案。交叉校验也改为代码层比对，彻底消灭"LLM 填错税率 → 自己校验出不一致 → 标记失败"的虚假错误。
- [x] **HomeView 首页卡片数字改为动态**：四张功能卡片的统计数据从 `/api/stats` 实时读取（已收录 HS 编码数 / 合规通过率 / 风险预警数 / 申报总条数）。

### 🟡 中优先级

- [x] PipelineView 增加 OCR 拍照入口（名称框旁，与 ClassifyView 一致）
- [x] 历史记录后端加分页（page + page_size + total），前端 `el-pagination` 分页器
- [x] 税率数据标注生效日期（税费表下方注明"数据更新至 2024-06"）
- [x] 长等待增加"停止分析"取消按钮（AbortController + 运行中点击按钮取消）
- [x] Pipeline 进度改为 SSE 推送真实后端进度（新增 `/api/pipeline/stream` 端点，每个 Agent 开始时推送 `agent: N, message: ...`，完成时推送 `done: true`，前端 `fetch` + `ReadableStream` 解析 SSE，替代 `setInterval` 假动画）

### 🟢 低优先级

- [x] PDF 下载：不做 weasyprint（依赖重），模态框底部加"打印 / PDF"按钮，`window.print()` + `@media print` CSS 隐藏 UI 只留 A4 文档，浏览器"另存为 PDF"即可
- [x] 同票多商品项：表单支持添加多个商品行（名称/HS编码/数量/价值），表格形式管理
- [x] 导入真实数据：三阶段全部完成 — ① 美国 HTS（`hts_2026_revision_9_csv.csv`，500条）② 中国税则（`hscode2026.xlsx`，500条）③ OFAC 制裁（`sdn_enhanced.xml`，200条），导入脚本均幂等可重复执行
- [x] HS 归类页关键条文高亮（引用卡中 WCO / HS公约 / 章号 / 品目 / 注释 等关键词黄色高亮）
- [x] 风险看板空状态增加示例数据切换开关（"加载示例数据"按钮，点击填充 4 条模拟记录 + 统计数字，可退出恢复真实数据）

### ❌ 已删除（不合理或已被覆盖）

- ~~完整文件包补充：税费明细表、原产地证书正式格式~~ → Pipeline 结果区改造已覆盖
- ~~风险记录列表从 mock 改真实数据~~ → DashboardView 已读 `/api/history` + `/api/stats`
- ~~历史记录导出 CSV~~ → 用户更需要的是下载申报文件（已有），CSV 导出历史记录无明确场景
- ~~HS 归类页步骤 1/2/3 改为时间线 + 卡片展示~~ → 当前箭头流程条已足够直观
- ~~报告视图增加折叠/展开切换~~ → 模态框已解决空间问题
- ~~顶部栏用户头像改为"关于/帮助"入口~~ → 太细碎，不值得单列

---
	
### Phase 5 — AI 对话 + 关税独立（待开始）

- [ ] **关税计算独立页面**：将关税计算从 Pipeline 拆分，用户已知 HS 编码时无需跑全流程（60s）。页面仿 ClassifyView（左表单 + 右结果），后端新增 `POST /api/tariff`，复用已有 TariffCalculatorAgent
- [ ] **AI 对话 ChatPanel 组件**：聊天气泡 + 输入框 + loading 动画，参考 Agent_Task 项目实现
- [ ] **AI 对话悬浮抽屉**：右下角全局固定按钮，点击侧边滑出抽屉面板，在任何页面随时唤起不中断工作流
- [ ] **AI 对话独立页面**：侧边栏新增"AI 助手"导航入口，全屏沉浸式使用
- [ ] **AI 对话后端 `/api/chat` 端点**：复用 RAG + LLM 基础设施，意图路由分发
- [ ] **AI 对话意图路由**：知识问答 → 直接回答；HS 归类/关税/合规 → 直接回答 + 可选跳转对应页面；申报文件 → 不直接回答，强引导跳转 Pipeline，用户拒绝则提示"该功能需在专用流程中完成，聊天暂不支持"；跳转携带上下文参数
- [ ] **登录注册**（低优先级）：用户表 + JWT 认证 + 注册/登录/找回密码 + 历史记录按用户隔离 + 路由鉴权守卫

### Phase 6 — 功能完善（待开始）

- [ ] **历史归类案例复用**：HS 归类成功后自动写入 Chroma，后续检索命中历史案例提高准确率
- [ ] **独立合规校验页面**：仿 ClassifyView 双栏布局（左表单 + 右结果）。左侧：商品名称/描述/材质/功能/目标国家 + "开始校验"按钮。右侧：综合风险等级色块（绿/黄/红）+ 违规项逐条列出（类别/描述/严重程度/法规来源，逐项打勾打叉）+ 许可证要求 + 制裁命中 + 合规结论文字总结。复用已有 ComplianceCheckerAgent，新增 `POST /api/compliance` 端点
- [ ] **端到端集成测试**：覆盖 Pipeline 全链路（归类 → 计税 → 合规 → 原产地 → 申报），验证五个 Agent 输出

### 暂缓（数据积累）

- [ ] WCO HS 注释文本（归类总规则、类章注释）入库
- [ ] 欧盟 TARIC 关税数据导入
- [ ] 合规法规库（RoHS / REACH / FDA / CE / FCC / FPLA / Lacey Act / CPSIA）结构化
- [ ] 50 国贸易数据覆盖
- [ ] Docker 生产部署（Nginx 反向代理 + SSL + 健康检查）

## 设计原则

1. **正确性第一**：Agent 输入输出 Pydantic 强校验，所有结论可溯源至条文
2. **可读性第二**：目录名即架构分层，文件名即职责，函数名动词开头
3. **可维护性第三**：新增贸易国只改配置不动代码，LLM 适配层可替换模型
4. **健壮性第四**：流水线不因单点失败而中断，可断点重试
5. **性能第五**：关税/合规/原产地三 Agent 并行，热点数据缓存

## License

MIT
