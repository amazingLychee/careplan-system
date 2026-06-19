# models.py
from django.db import models
from django.utils import timezone

class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(max_length=6, unique=True)   # MRN 唯一 → 数据库兜底防重复
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (MRN: {self.mrn})"


class Provider(models.Model):
    name = models.CharField(max_length=200)
    npi = models.CharField(max_length=10, unique=True)  # NPI 全国唯一 → unique
    phone = models.CharField(max_length=20, blank=True)
    fax = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"


class Order(models.Model):
    # 外键放在"多"的一边。on_delete=CASCADE: 病人没了,他的订单也跟着删
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="orders")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="orders")
    medication_name = models.CharField(max_length=200)
    primary_diagnosis_code = models.CharField(max_length=20)        # ICD-10
    additional_diagnoses = models.TextField(blank=True)            # 先用逗号分隔的字符串存
    medication_history = models.TextField(blank=True)
    patient_record = models.TextField(blank=True)
    order_date = models.DateField(default=timezone.now)                               # 重复检测要用"同一天"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.medication_name}"


class CarePlan(models.Model):
    # 1 对 1:一个订单对应一个 care plan。OneToOneField 而不是 ForeignKey
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="care_plan")
    content = models.TextField(blank=True)                         # 生成前为空,完成后填入
    status = models.CharField(
        max_length=20,
        default="pending",
        # 限制 status 只能是这几个值,防止乱写
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CarePlan for Order #{self.order_id} [{self.status}]"