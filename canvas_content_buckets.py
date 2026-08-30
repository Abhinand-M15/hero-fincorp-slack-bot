BUCKET2_CANVAS_MARKDOWN = """# 🟡 Bucket 2 Dashboard (31–60 DPD)

## Summary

| Metric | Value |
|---|---|
| Accounts pending | 5 |
| Total pending amount | ₹45,800 |
| Average DPD | 42 days |
| Assigned partner agent | Partner Agent — Pune Cluster |
| Stage | Field visits begin — phone alone has stopped working |

## Accounts

| Loan ID | Borrower | Product | DPD | Pending Amount |
|---|---|---|---|---|
| HFCL/TW/2026/00891 | Ramesh Kumar | Two-Wheeler | 42 | ₹4,500 |
| HFCL/TW/2026/00902 | Kiran Patil | Two-Wheeler | 38 | ₹3,600 |
| HFCL/PL/2026/01301 | Ashwini More | Personal Loan | 45 | ₹13,500 |
| HFCL/UC/2026/00611 | Ganesh Pawar | Used Car | 33 | ₹15,800 |
| HFCL/CD/2026/00220 | Snehal Joshi | Consumer Durable | 50 | ₹8,400 |

## What happens here

Field visits, PTP capture, and refusal tracking. A Refused outcome routes to the manager for a Proceed/Intensify decision in ![](#{legal_channel}) — this bucket is not yet legally eligible (SARFAESI applies at 90+ DPD).
"""

BUCKET3_CANVAS_MARKDOWN = """# 🟠 Bucket 3 Dashboard (61–90 DPD)

## Summary

| Metric | Value |
|---|---|
| Accounts pending | 5 |
| Total pending amount | ₹2,28,800 |
| Average DPD | 75 days |
| Assigned partner agent | Partner Agent — Lucknow Cluster |
| Stage | Intensified visits — approaching legal-eligibility |

## Accounts

| Loan ID | Borrower | Product | DPD | Pending Amount |
|---|---|---|---|---|
| HFCL/PL/2026/01204 | Sunita Devi | Personal Loan | 68 | ₹27,000 |
| HFCL/TW/2026/00877 | Rajesh Yadav | Two-Wheeler | 74 | ₹6,800 |
| HFCL/BL/2026/00344 | Verma Traders | Business Loan | 81 | ₹1,24,000 |
| HFCL/UC/2026/00588 | Anita Singh | Used Car | 65 | ₹35,000 |
| HFCL/PL/2026/01277 | Mohd. Irfan | Personal Loan | 89 | ₹36,000 |

## What happens here

Highest single exposure: Verma Traders at ₹1,24,000. Mohd. Irfan (89 DPD) is one visit away from crossing into NPA. A Refused outcome routes to the manager for a Proceed/Intensify decision in ![](#{legal_channel}).
"""

NPA_CANVAS_MARKDOWN = """# 🔴 NPA Dashboard (90+ DPD — Legal-Eligible)

## Summary

| Metric | Value |
|---|---|
| Accounts pending | 5 |
| Total pending amount | ₹4,02,200 |
| Average DPD | 106 days |
| Assigned partner agent | Partner Agent — Ahmedabad Cluster |
| Legal eligibility | SARFAESI-eligible where secured & ≥₹20L (NBFC assets ≥₹100Cr — Hero FinCorp qualifies) |

## Accounts

| Loan ID | Borrower | Product | DPD | Pending Amount |
|---|---|---|---|---|
| HFCL/LAP/2026/00077 | Anil Traders (Prop.) | Loan Against Property | 96 | ₹1,65,000 |
| HFCL/PL/2026/00699 | Suresh Mehta | Personal Loan | 103 | ₹39,000 |
| HFCL/BL/2026/00456 | Kavya Enterprises | Business Loan | 112 | ₹1,36,000 |
| HFCL/TW/2026/01033 | Ramavath Naik | Two-Wheeler | 98 | ₹7,600 |
| HFCL/UC/2026/00721 | Preeti Malhotra | Used Car | 121 | ₹54,600 |

## What happens here

A **Refused** outcome on any of these accounts auto-escalates to ![](#{legal_channel}) — no manual click needed. The manager then decides: **Proceed with Legal Action** (Section 13(2) notice, 60-day window, for secured loans ≥₹20L) or **Hold** for more information.
"""
