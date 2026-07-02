"""
所有业务逻辑都堆在这一个文件里。

⚠️ 这是【故意】这样写的 —— 不分 service/serializer 层。
等到 Day 7，这个文件会变得又长又乱，那时你才会真正理解"为什么要拆分"。
现在先享受"全在一起、好找"的简单。
"""
import json
import os
import logging
import time
import redis

from django.http import JsonResponse
from django.shortcuts import render
from orders.models import Patient, Provider, Order, CarePlan

logging.basicConfig(
    level=logging.INFO,                              # 记录 INFO 级别及以上的日志
    format="%(asctime)s [%(levelname)s] %(message)s",  # 日志格式:时间 [级别] 内容
)
logger = logging.getLogger(__name__)                 # 拿到这个文件专属的 logger
r = redis.Redis(host="redis", port=6379, db=0)

# ============================================================



# ============================================================
# 2. 调用 LLM 生成 care plan
# ============================================================
def generate_care_plan(patient_info: dict) -> str:
    """
    输入病人信息，返回一段 care plan 文本。

    通过环境变量 USE_MOCK_LLM 切换：
      - "1"（默认）：用假的 mock，立即返回固定文本，不花钱不等待
      - "0"：调用真正的 Claude API
    """
    use_mock = os.environ.get("USE_MOCK_LLM", "1") == "1"

    if use_mock:
        return _mock_llm(patient_info)
    else:
        return _real_llm(patient_info)


def _mock_llm(patient_info: dict) -> str:
    """假的 LLM：睡 2 秒假装在'思考'，然后返回一段写死的 care plan。"""
    time.sleep(10)  # 模拟一点点延迟，让你体验"等待"的感觉（真 LLM 是 10-20 秒）
    name = patient_info.get("patient_first_name", "") + " " + patient_info.get("patient_last_name", "")
    med = patient_info.get("medication_name", "the medication")
    return f"""SPECIALTY PHARMACY CARE PLAN (MOCK)
Patient: {name}
Medication: {med}

PROBLEM LIST / DRUG THERAPY PROBLEMS (DTPs)
- Need for specialty medication therapy
- Risk of injection/infusion-related reactions
- Potential drug-drug interactions

GOALS (SMART)
- Achieve clinical improvement within 12 weeks
- No severe adverse drug reactions

PHARMACIST INTERVENTIONS / PLAN
- Verify dosing and administration
- Patient education on self-administration
- Coordinate with referring provider

MONITORING PLAN & FOLLOW-UP SCHEDULE
- Week 1: phone call after first dose
- Week 4: lab draw + provider update
- Week 12: comprehensive assessment
"""


def _real_llm(patient_info: dict) -> str:
    """真正调用 Claude API。需要设置环境变量 ANTHROPIC_API_KEY。"""
    from anthropic import Anthropic

    client = Anthropic()  # 自动从环境变量 ANTHROPIC_API_KEY 读 key

    # 把病人信息拼成一段给 LLM 看的文字
    prompt = f"""You are a clinical pharmacist. Generate a specialty pharmacy care plan
for the following patient. The care plan MUST include these four sections:
Problem list, Goals, Pharmacist interventions, Monitoring plan.

Patient information:
{json.dumps(patient_info, indent=2, ensure_ascii=False)}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    # 取出返回文本
    return message.content[0].text


# ============================================================
# 3. 三个 view 函数（对应 urls.py 里的三条路由）
# ============================================================

def index(request):
    """首页：返回填表单的 HTML 页面。"""
    return render(request, "index.html")


def create_order(request):
    """
    POST /api/orders/
    收到病人信息 → 拆进数据库(病人/医生/订单) → sync 调 LLM → 存 care plan → 返回。

    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    form_data = json.loads(request.body)
    logger.info("[1] 收到请求,病人: %s %s",
                form_data.get("patient_first_name"),
                form_data.get("patient_last_name"))

    # ---- 拆数据进库：和你导入脚本里做的事一模一样 ----
    # 病人：用 mrn 去重，见过就复用
    patient, _ = Patient.objects.get_or_create(
        mrn=str(form_data.get("patient_mrn")),
        defaults={
            "first_name": form_data.get("patient_first_name", ""),
            "last_name": form_data.get("patient_last_name", ""),
            "date_of_birth": form_data.get("patient_dob") or None,
        },
    )
    # 医生：用 npi 去重
    provider, _ = Provider.objects.get_or_create(
        npi=str(form_data.get("provider_npi")),
        defaults={
            "name": form_data.get("provider_name", ""),
            "phone": form_data.get("provider_phone", ""),
            "fax": form_data.get("provider_fax", ""),
        },
    )
    # 订单：每次都新建
    order = Order.objects.create(
        patient=patient,
        provider=provider,
        medication_name=form_data.get("medication_name", ""),
        primary_diagnosis_code=form_data.get("primary_diagnosis_code", ""),
        additional_diagnoses=form_data.get("additional_diagnoses", ""),
        medication_history=form_data.get("medication_history", ""),
        patient_record=form_data.get("patient_record", ""),
    )

    logger.info("[2] 订单 #%d 已存库,开始调用 LLM...", order.id)


    # ---- 存 care plan，但状态是 pending，内容先空着 ----
    # 注意:不调 LLM 了! generate_care_plan 这一步整个删掉
    care_plan = CarePlan.objects.create(
        order=order,
        content="",                # ← 还没生成,空着
        status="pending",          # ← 关键:待处理
    )

    # ---- 把 careplan_id 扔进 Redis 队列(我们的"篮子")----
    from orders.tasks import generate_careplan_task
    generate_careplan_task.delay(care_plan.id)
    logger.info("[3] careplan #%d 已入队,立刻返回", care_plan.id)

    # ---- 立刻返回"收到了",不等 LLM ----
    return JsonResponse({
        "id": order.id,
        "careplan_id": care_plan.id,
        "status": "pending",       # ← 告诉前端:收到了,正在处理
    }, status=201)


def get_order(request, order_id):
    """
    GET /api/orders/<id>/
    按订单号从数据库查结果。
    """
    logger.info("[GET-1] 查询订单 #%d", order_id)

    # 从数据库查这个订单，查不到返回 None
    order = Order.objects.filter(id=order_id).first()
    if order is None:
        logger.info("[GET-2] 订单 #%d 不存在,404", order_id)
        return JsonResponse({"error": "Order not found"}, status=404)

    # order.care_plan 能直接拿到关联的 CarePlan（OneToOne 的反向访问）
    care_plan = order.care_plan
    logger.info("[GET-3] 找到订单 #%d", order_id)

    return JsonResponse({
        "id": order.id,
        "status": care_plan.status,
        "care_plan": care_plan.content,
    })

def careplan_status(request, careplan_id):
    """
    GET /api/careplan/<id>/status/
    前端轮询这个接口,问"care plan 好了没"。
    这个接口是【被动】的:前端问一次,它答一次。它自己不知道"3秒"这回事。
    """
    logger.info("[STATUS-1] 查询 careplan #%d", careplan_id)

    care_plan = CarePlan.objects.filter(id=careplan_id).first()
    if care_plan is None:
        logger.info("[STATUS-2] careplan #%d 不存在,404", careplan_id)
        return JsonResponse({"error": "CarePlan not found"}, status=404)

    response_data = {
        "id": care_plan.id,
        "status": care_plan.status,
    }

    # 只有 completed 才带内容;pending/processing 时 content 本来就空,没必要传
    if care_plan.status == "completed":
        response_data["content"] = care_plan.content

    # failed 只给通用提示,不暴露 LLM 报错堆栈或 PHI(brief 硬性要求)
    if care_plan.status == "failed":
        response_data["error_message"] = "生成失败，请重试"

    logger.info("[STATUS-3] careplan #%d 状态: %s", careplan_id, care_plan.status)
    return JsonResponse(response_data)