from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.startup", env=settings.app_env)
    try:
        from data.database import init_db
        await init_db()
        logger.info("db.tables_created")
    except Exception as e:
        logger.warning("db.init_failed", error=str(e))
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title="AgenticCustoms API",
    description="跨境合规贸易与关税智能申报平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgenticCustoms - 跨境合规贸易智能申报平台</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #303133; }
  .container { max-width: 800px; margin: 80px auto; text-align: center; }
  h1 { font-size: 28px; margin-bottom: 8px; }
  .subtitle { color: #909399; margin-bottom: 40px; font-size: 14px; }
  .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
  .card { background: #fff; border-radius: 8px; padding: 24px; text-decoration: none;
          color: #303133; border: 1px solid #ebeef5; transition: box-shadow .2s; }
  .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
  .card h3 { font-size: 16px; margin-bottom: 6px; }
  .card p { font-size: 13px; color: #909399; }
  .footer { margin-top: 48px; font-size: 12px; color: #c0c4cc; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px;
           margin-left: 6px; vertical-align: middle; }
  .badge-ok { background: #e1f3d8; color: #67c23a; }
  .badge-wip { background: #fdf6ec; color: #e6a23c; }
</style>
</head>
<body>
<div class="container">
  <h1>AgenticCustoms <span class="badge badge-ok">v0.1</span></h1>
  <p class="subtitle">基于 Agentic RAG 与多智能体协作的跨境合规贸易关税智能申报平台</p>
  <div class="grid">
    <a href="/api/classify" class="card">
      <h3>HS 编码归类 <span class="badge badge-wip">开发中</span></h3>
      <p>根据商品描述自动推理 HS 编码</p>
    </a>
    <a href="/api/pipeline/full" class="card">
      <h3>一键全流程 <span class="badge badge-wip">开发中</span></h3>
      <p>归类 → 关税 → 合规 → 原产地 → 申报文件</p>
    </a>
    <a href="/health" class="card">
      <h3>健康检查 <span class="badge badge-ok">可用</span></h3>
      <p>服务状态与版本信息</p>
    </a>
    <a href="/docs" class="card">
      <h3>API 文档 <span class="badge badge-ok">可用</span></h3>
      <p>Swagger UI 交互式接口文档</p>
    </a>
  </div>
  <p class="footer">FastAPI + LangChain + LangGraph + Qwen-Plus &nbsp;|&nbsp; Vue3 + Element Plus</p>
</div>
</body>
</html>"""


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=True)
