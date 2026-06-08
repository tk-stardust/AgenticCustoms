import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期——启动时自动建表，关闭时记录日志"""
    logger.info("app.startup", env=settings.app_env)
    # 延迟导入避免模块级循环依赖
    try:
        from data.db.database import init_db
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

# 业务 API 路由
from api.routes.classify import router as classify_router
from api.routes.pipeline import router as pipeline_router
from api.routes.history import router as history_router
from api.routes.report import router as report_router
from api.routes.ocr import router as ocr_router
from api.routes.stats import router as stats_router
app.include_router(classify_router)
app.include_router(pipeline_router)
app.include_router(history_router)
app.include_router(report_router)
app.include_router(ocr_router)
app.include_router(stats_router)

# 前端页面路由（每个 Vue Router 路径对应一个路由，刷新不 404）
from api.routes.pages import router as pages_router
app.include_router(pages_router)


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


# 静态资源必须在所有路由之后挂载
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=True)
