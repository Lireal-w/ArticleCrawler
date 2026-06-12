import os
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from db import DB
from scheduler import run_spider,clean_empty_json_files,submit_active_to_site

# 配置日志，方便观察定时任务输出
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def scheduled_task():
    """定时任务：每10秒执行一次"""
    logger.info("hello world")


# 创建后台调度器
scheduler = BackgroundScheduler()
db = DB()

def init_scheduler():
    """初始化调度器"""
    # 保留原有的间隔任务测试
    # scheduler.add_job(scheduled_task, 'interval', seconds=10)
    
    scheduler.add_job(run_spider, 'cron', hour=8, minute=0, id='run_spider')
    scheduler.add_job(clean_empty_json_files, 'cron', hour=9, minute=0, id='clean_empty_json_files')
    scheduler.add_job(submit_active_to_site, 'cron', hour=9, minute=0, id='submit_active_to_site')
    scheduler.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理：启动/关闭调度器"""
    init_scheduler()
    db.connect()
    yield
    scheduler.shutdown()
    db.close()
    logger.info("APScheduler shut down.")


# 创建 FastAPI 应用，使用 lifespan 管理生命周期
app = FastAPI(
    title="FastAPI + APScheduler Demo",
    description="一个带有后台定时任务的 FastAPI 示例",
    version="1.0.0",
    lifespan=lifespan,
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/hello")
async def hello():
    """简单的 Hello 接口"""
    return {"message": "hello"}

# app.py 新增辅助函数
def get_cron_value(field):
    """安全提取 Cron 字段的数值（假设是简单单值）"""
    if not field.expressions:
        return None
    expr = field.expressions[0]
    # 对于具体值（如 '8'），value 就是 8
    if hasattr(expr, 'value') and expr.value is not None:
        return expr.value
    # 对于范围或步进，可以返回 step 或最小值
    if hasattr(expr, 'step') and expr.step is not None:
        return expr.step
    return None

class ScheduleTime(BaseModel):
    hour: int
    minute: int

@app.put("/schedule/{job_name}")
async def update_schedule(job_name: str, time: ScheduleTime):
    # 限定只允许修改这两个任务
    valid_jobs = ["run_spider", "submit_active_to_site"]
    if job_name not in valid_jobs:
        return {"error": f"Invalid job name. Must be one of {valid_jobs}"}

    try:
        # 使用 reschedule_job 动态修改任务的 cron 触发器
        scheduler.reschedule_job(
            job_name, 
            trigger='cron', 
            hour=time.hour, 
            minute=time.minute
        )
        return {"message": f"Job '{job_name}' rescheduled to {time.hour:02d}:{time.minute:02d}"}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/schedule/{job_name}")
async def get_schedule(job_name: str):
    valid_jobs = ["run_spider", "submit_active_to_site"]
    if job_name not in valid_jobs:
        return {"error": f"Invalid job name. Must be one of {valid_jobs}"}

    job = scheduler.get_job(job_name)
    if not job:
        return {"error": "Job not found"}

    next_run_time  = job.next_run_time
    if next_run_time:
        hour = next_run_time.hour
        minute = next_run_time.minute
    else:
        hour = None
        minute = None
    return {"job_name": job_name, "hour": hour, "minute": minute}

class SiteInfo(BaseModel):
    url: str
    username: str
    app_password: str
    
@app.get("/sites")
async def get_sites():
    """获取所有站点配置"""
    try:
        sites = db.get_all_sites()
        return {"sites": sites}
    except Exception as e:
        return {"error": str(e)}

@app.post("/sites")
async def add_site(site: SiteInfo):
    """新增或更新站点配置"""
    try:
        db.insert_site(site.url, site.username, site.app_password)
        return {"message": "Site added/updated successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/sites/{site_url:path}")
async def delete_site(site_url: str):
    """删除指定站点配置"""
    try:
        # 需在 DB 类中确保有 delete_site 方法
        db.delete_site(site_url)
        return {"message": "Site deleted successfully"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)