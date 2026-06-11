"""
所有业务逻辑都堆在这一个文件里。

⚠️ 这是【故意】这样写的 —— 不分 service/serializer 层。
等到 Day 7，这个文件会变得又长又乱，那时你才会真正理解"为什么要拆分"。
现在先享受"全在一起、好找"的简单。
"""
import json
import os
import time

from django.http import JsonResponse
from django.shortcuts import render


# ============================================================
# 1. "数据库" —— 其实就是一个内存里的字典
# ============================================================
# key 是订单号(int)，value 是订单内容(dict)。
# ⚠️ 缺陷：服务器一重启，所有数据就没了。这正是 Day 3 引入真数据库的理由。
ORDERS = {}

# 订单号计数器。每来一个新订单就 +1。
# ⚠️ 缺陷：这种自增方式在多进程/多实例下会冲突，但 MVP 阶段无所谓。
_next_id = 1


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
    time.sleep(2)  # 模拟一点点延迟，让你体验"等待"的感觉（真 LLM 是 10-20 秒）
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
    收到病人信息 → sync 调 LLM 生成 care plan → 存内存 → 返回结果。

    ⚠️ 因为是 sync，这个函数会卡住 2~20 秒才返回（取决于 mock 还是真 LLM）。
       用户的浏览器在这期间一直转圈。这个痛点 Day 4 才解决。
    """
    global _next_id

    # 只接受 POST。其他方法直接打回。
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    # 从请求体里读 JSON 数据（前端发来的表单内容）
    patient_info = json.loads(request.body)

    # 调 LLM 生成 care plan —— 这一步会等待
    care_plan_text = generate_care_plan(patient_info)

    # 分配订单号，把整个订单存进内存"数据库"
    order_id = _next_id
    _next_id += 1
    ORDERS[order_id] = {
        "id": order_id,
        "patient_info": patient_info,
        "care_plan": care_plan_text,
        "status": "completed",  # MVP 阶段一步到位，直接 completed
    }

    # 返回订单号和生成好的 care plan
    return JsonResponse(ORDERS[order_id])


def get_order(request, order_id):
    """
    GET /api/orders/<id>/
    按订单号查结果。
    """
    order = ORDERS.get(order_id)
    if order is None:
        return JsonResponse({"error": "Order not found"}, status=404)
    return JsonResponse(order)
