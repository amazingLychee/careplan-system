"""
把 pharmacy_single_table_data.xlsx（单表）拆进 4 张表。

核心难点：单表里同一个病人/医生会重复出现很多行，
但 Patient.mrn 和 Provider.npi 都是 unique，不能重复插入。
解法：get_or_create —— 见过就复用，没见过才新建。
"""
from datetime import datetime
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand
from django.db import transaction

from orders.models import Patient, Provider, Order, CarePlan


# Django management command 固定写法：继承 BaseCommand，逻辑写在 handle 里
class Command(BaseCommand):
    help = "Import single-table xlsx into Patient/Provider/Order/CarePlan"

    def handle(self, *args, **options):
        # 找到 xlsx。BASE_DIR 是项目根目录，文件就放那
        xlsx_path = Path("pharmacy_single_table_data.xlsx")
        if not xlsx_path.exists():
            self.stderr.write(f"找不到文件: {xlsx_path.resolve()}")
            return

        wb = openpyxl.load_workbook(xlsx_path, read_only=True)
        ws = wb["All_Data_Single_Table"]   # 用那个有数据的 sheet

        rows = list(ws.iter_rows(values_only=True))
        header = rows[0]                    # 第一行是列名
        data_rows = rows[1:]               # 剩下的才是数据

        # 把列名映射成"列名 -> 索引"，这样下面可以用名字取值，不用记第几列
        col = {name: i for i, name in enumerate(header)}

        # 计数器，最后打印出来让你直观看到"去重"的效果
        created_patients = 0
        created_providers = 0
        created_orders = 0

        # transaction.atomic: 整批要么全成功，要么全失败回滚。
        # 防止导到一半报错，留下一堆残缺数据。
        with transaction.atomic():
            for row_num, row in enumerate(data_rows, start=2):
                if row is None or len(row) < len(header):
                    self.stdout.write(f"跳过第 {row_num} 行（空行或列数不足）")
                    continue

                # ---- 1. 病人：同一个 MRN 只建一次 ----
                patient, p_created = Patient.objects.get_or_create(
                    mrn=str(row[col["patient_mrn"]]),   # 用 mrn 判断是不是同一个人
                    defaults={                          # 只有"新建"时才用这些值
                        "first_name": row[col["patient_first_name"]],
                        "last_name": row[col["patient_last_name"]],
                        "date_of_birth": self._parse_date(row[col["patient_dob"]]),
                    },
                )
                if p_created:
                    created_patients += 1

                # ---- 2. 医生：同一个 NPI 只建一次 ----
                provider, pr_created = Provider.objects.get_or_create(
                    npi=str(row[col["provider_npi"]]),
                    defaults={
                        "name": row[col["provider_name"]],
                        "phone": row[col["provider_phone"]] or "",
                        "fax": row[col["provider_fax"]] or "",
                    },
                )
                if pr_created:
                    created_providers += 1

                # ---- 3. 订单：每一行都是一个新订单（订单不去重）----
                order = Order.objects.create(
                    patient=patient,                    # 外键：指向上面那个病人
                    provider=provider,                  # 外键：指向上面那个医生
                    medication_name=row[col["medication_name"]],
                    primary_diagnosis_code=row[col["primary_diagnosis_code"]] or "",
                    additional_diagnoses=row[col["additional_diagnoses"]] or "",
                    medication_history=row[col["medication_history"]] or "",
                    patient_record=row[col["patient_record"]] or "",
                    order_date=self._parse_date(row[col["order_date"]]),
                )
                created_orders += 1

                # ---- 4. CarePlan：单表里已经有现成内容，直接当 completed 存 ----
                CarePlan.objects.create(
                    order=order,                        # 1对1：指向上面那个订单
                    content=row[col["care_plan_content"]] or "",
                    status="completed",                 # 历史数据，视为已生成
                )

        # 打印结果。重点看：病人/医生远少于订单数，这就是去重的意义
        self.stdout.write(self.style.SUCCESS(
            f"\n导入完成！\n"
            f"  订单 Order:     {created_orders}\n"
            f"  病人 Patient:   {created_patients}（去重后）\n"
            f"  医生 Provider:  {created_providers}（去重后）\n"
        ))

    @staticmethod
    def _parse_date(value):
        """xlsx 里日期可能是字符串 '2025-03-05'，转成 date 对象"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()