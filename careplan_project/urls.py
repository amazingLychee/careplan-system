"""
URL 路由：决定哪个网址交给哪个函数处理。
就像公司前台的指示牌——"找人事去 3 楼，找财务去 5 楼"。
"""
from django.urls import path
from orders import views

urlpatterns = [
    # 首页：返回填表单的 HTML 页面
    path("", views.index, name="index"),

    # POST /api/orders/  → 提交病人信息，生成 care plan
    path("api/orders/", views.create_order, name="create_order"),

    # GET /api/orders/<id>/  → 按订单号查结果
    path("api/orders/<int:order_id>/", views.get_order, name="get_order"),

    path('api/careplan/<int:careplan_id>/status/', views.careplan_status, name='careplan-status'),
]
