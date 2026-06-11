import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from .scheduler import run_spider,clean_empty_json_files

# 配置日志，方便观察定时任务输出
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def scheduled_task():
    """定时任务：每10秒执行一次"""
    logger.info("hello world")


# 创建后台调度器
scheduler = BackgroundScheduler()

def init_scheduler():
    """初始化调度器"""
    # 保留原有的间隔任务测试
    scheduler.add_job(scheduled_task, 'interval', seconds=10)
    
    # 每天早上 8:00 执行爬虫任务
    scheduler.add_job(run_spider, 'cron', hour=8, minute=0)
    
    # 每天早上 9:00 执行清理空 JSON 文件任务
    scheduler.add_job(clean_empty_json_files, 'cron', hour=9, minute=0)
    
    scheduler.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理：启动/关闭调度器"""
    init_scheduler()
    logger.info("APScheduler started, will print 'hello world' every 10 seconds.")
    yield
    scheduler.shutdown()
    logger.info("APScheduler shut down.")


# 创建 FastAPI 应用，使用 lifespan 管理生命周期
app = FastAPI(
    title="FastAPI + APScheduler Demo",
    description="一个带有后台定时任务的 FastAPI 示例",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/hello")
async def hello():
    """简单的 Hello 接口"""
    return {"message": "hello"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)