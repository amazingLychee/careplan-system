# Care Plan Generation System — Design Doc

> Status: Draft (v0.1)
> Owner: [你的名字]
> Last updated: 2026-06-03

---

## 1. Overview / 背景

CVS 旗下一家 specialty pharmacy 的药剂师目前需要**手动**为每个病人撰写 care plan,每份耗时 20–40 分钟。这些 care plan 是 Medicare 报销和 pharma 合规所**必需**的。由于人手严重不足,这项工作长期积压。

本系统的目标是:让医疗工作者通过一个 web 表单录入病人信息,系统自动调用 LLM 生成专业的 care plan,药剂师审核后打印交给病人。

**谁用这个系统:** CVS 的医疗工作者(药剂师 / 医疗助理)。病人**不直接接触**本系统。

---

## 2. Goals / Non-Goals

### Goals(本期要做)
- 医疗工作者通过 web 表单录入患者信息、药物、诊断
- 对所有输入做格式验证
- 自动检测重复(患者、订单、provider)
- 调用 LLM 生成 care plan(一个订单 = 一种药物 = 一份 care plan)
- 生成的 care plan 可下载
- 支持导出数据用于 pharma 报告

### Non-Goals(本期明确不做)
- 病人自助使用(本系统只给医疗工作者用)
- 多机构 / 多数据源接入(后续迭代)
- 病人医疗记录的长期归档管理

---

## 3. Requirements

### 3.1 输入字段(来自客户需求)

| 字段 | 类型 / 格式规则 |
|---|---|
| Patient First Name | string |
| Patient Last Name | string |
| Referring Provider | string |
| Referring Provider NPI | 10 位数字 |
| Patient MRN(唯一 ID) | 唯一的 6 位数字 |
| Patient Primary Diagnosis | ICD-10 code |
| Medication Name | string |
| Additional Diagnosis | ICD-10 code 列表 |
| Medication history | string 列表 |
| Patient Records | string 或 pdf 文档 |

### 3.2 功能需求

| 功能 | 是否必须 | 说明 |
|---|---|---|
| 患者 / 订单重复检测 | 必须 | 不能打乱现有工作流 |
| Care Plan 生成 | 必须 | 核心价值 |
| Provider 重复检测 | 必须 | 影响 pharma 报告 |
| 导出报告 | 必须 | pharma 报告需要 |
| Care Plan 下载 | 必须 | 用户需上传到自己的系统 |

### 3.3 Care Plan 输出格式(必含内容)
- Problem list / Drug therapy problems
- Goals(SMART)
- Pharmacist interventions / plan
- Monitoring plan & lab schedule

### 3.4 非功能性 / Production-Ready 要求
- 每个输入都要验证
- 完整性规则始终保证数据一致
- 错误处理安全、清晰、可控(不暴露 stack trace 或 PHI)
- 代码模块化、可导航
- 关键逻辑有自动化测试覆盖
- 项目 clone 下来开箱即可端到端运行

---

## 4. Design Decisions(关键设计决策 + 理由)

> 这些决策来自需求澄清后与客户确认的结果。需求文档原文只写了"warning if duplicates",
> 这些规则是把模糊需求落地为明确规则的产物。

### 4.1 Care Plan 的粒度
**决策:** 一个 care plan 对应一个订单(一种药物)。
**理由:** 药剂师是按药开 care plan 的,一个病人取多种药就是多个订单、多份 care plan。

### 4.2 重复检测规则

| 场景 | 处理方式 | 理由 |
|---|---|---|
| 同患者 + 同药 + **同一天** | **ERROR**(阻止) | 几乎肯定是重复提交 |
| 同患者 + 同药 + **不同天** | **WARNING**(确认后可继续) | 可能是续方 |
| MRN 相同 + 名字或 DOB 不同 | **WARNING**(确认后可继续) | 可能是录入错误 |
| 名字 + DOB 相同 + MRN 不同 | **WARNING**(确认后可继续) | 可能是同一人 |
| NPI 相同 + Provider 名字不同 | **ERROR**(必须修正) | NPI 全国唯一,不可能对应两个名字 |

### 4.3 ERROR vs WARNING 的区别
- **ERROR**:阻止操作,用户必须修正后才能继续。
- **WARNING**:提示风险,但用户确认(confirm)后可以继续提交。

---

## 5. Open Questions(待确认 / 后续决定)

> 真实 design doc 一定有这一块——开发初期不可能什么都想清楚。

- Patient Records 的 "string OR pdf" 如何统一处理?pdf 要不要解析成文本喂给 LLM?
- LLM 调用失败时的重试策略具体怎么定(重试几次?间隔多久?)
- 导出报告的具体格式(CSV?字段有哪些?)
- 系统的并发量预期(几十个药剂师同时用?)——影响后续架构选型

---

## 6. 后续迭代方向(超出本期范围)
- 异步处理 LLM 调用(避免用户长时间等待)
- 多数据源接入(JSON / XML 等不同格式)
- 监控与告警
- 云部署
