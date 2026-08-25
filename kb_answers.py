"""
Keyword-matched answers for the knowledge base bot, sourced from the same
data as the pinned Canvas (data/products.md, data/dpd-buckets.md) so the
bot's replies stay consistent with what's written there.
"""

KB_ANSWERS = [
    (("two-wheeler", "two wheeler", " tw ", "bike loan"),
     "*Two-Wheeler Loan:* ₹10,000–₹3.5L, 14%–36% p.a., 6–60 months. Age 18+, min ₹10,000/month income, 1+ year work experience. No guarantor required."),

    (("loyalty",),
     "*Loyalty Personal Loan:* Existing two-wheeler customers only, 9+ EMIs paid with zero defaults. ₹50,000–₹5L, from 18% p.a. Minimal documentation — PAN + Aadhaar KYC refresh only."),

    (("personal loan",),
     "*Personal Loan:* ₹50,000–₹7L, 18%–30% p.a., 12–36 months. CIBIL 725+ preferred (650+ reviewed case-by-case). Age 21–58, min ₹15,000/month income."),

    (("business loan",),
     "*Business Loan:* ₹5L–₹50L, 14%–30% p.a., 12–48 months. Business operational 2+ years. Unsecured — no collateral required."),

    (("loan against property", "lap", "property loan"),
     "*Loan Against Property:* ₹20L–₹7.5Cr, 11%–17% p.a., up to 15 years. LTV up to 75% depending on property type. Business operational 3+ years, age 25–75."),

    (("used car", "car loan"),
     "*Used Car Loan:* ₹50,000–₹50L, 11.5%–26% p.a., 12–60 months. LTV up to 90%. Min income ₹15,000/month."),

    (("cibil", "deviation", "credit score"),
     "*Credit Deviation:* CIBIL below 650, income >10% below policy minimum, age outside standard range, or LTV above policy cap all count as deviations. Use the \"Request Deviation Approval\" workflow in #credit-deviation-approvals — don't email or call directly, it won't be tracked."),

    (("dpd", "bucket", "overdue", "collections"),
     "*Collections buckets:* Bucket 2 (31–60 DPD) — field visits begin. Bucket 3 (61–90 DPD) — intensified visits. NPA (90+ DPD) — legal-eligible under SARFAESI. See the bucket-specific Canvas in each collections channel."),

    (("document", "kyc", "paperwork"),
     "*Documents:* vary by product — check the pinned Canvas's per-product section for the exact list (identity, address, income proof, and product-specific documents like property papers for LAP)."),
]


def find_answer(text):
    text_lower = f" {text.lower()} "
    for keywords, answer in KB_ANSWERS:
        if any(kw in text_lower for kw in keywords):
            return answer
    return None
