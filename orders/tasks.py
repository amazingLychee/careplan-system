import os
from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Celery app
app = Celery('careplan', broker='redis://redis:6379/0')

@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 第一次重试等 60 秒
    autoretry_for=(Exception,),
    retry_backoff=True,  # 指数退避：60s, 120s, 240s
)
def generate_careplan_task(self, careplan_id):
    """
    Celery 异步任务：从数据库拿 careplan，调 LLM，存结果。
    失败自动重试最多 3 次，指数退避。
    """
    from orders.models import CarePlan
    from orders.views import generate_care_plan

    logger.info(f"开始处理 careplan #{careplan_id}")

    care_plan = CarePlan.objects.get(id=careplan_id)
    care_plan.status = 'processing'
    care_plan.save()

    order = care_plan.order
    patient_info = {
        "patient_first_name": order.patient.first_name,
        "patient_last_name": order.patient.last_name,
        "medication_name": order.medication_name,
        "primary_diagnosis_code": order.primary_diagnosis_code,
    }

    content = generate_care_plan(patient_info)

    care_plan.content = content
    care_plan.status = 'completed'
    care_plan.save()
    logger.info(f"careplan #{careplan_id} 完成")