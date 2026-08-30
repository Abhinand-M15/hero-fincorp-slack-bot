"""
The 'assigned work' each role sees before they do anything — this is what
answers "how does the assigned partner agent know where to go / what to log."
Static demo data, matching data/loan-account-schema.md.
"""

BUCKET_QUEUES = {
    "collections-bucket2": [
        {"loan_id": "HFCL/TW/2026/00891", "borrower": "Ramesh Kumar", "dpd": 42,
         "assigned_officer": "Partner Agent — Pune Cluster"},
        {"loan_id": "HFCL/TW/2026/00902", "borrower": "Kiran Patil", "dpd": 38,
         "assigned_officer": "Partner Agent — Pune Cluster"},
        {"loan_id": "HFCL/PL/2026/01301", "borrower": "Ashwini More", "dpd": 45,
         "assigned_officer": "Partner Agent — Pune Cluster"},
        {"loan_id": "HFCL/UC/2026/00611", "borrower": "Ganesh Pawar", "dpd": 33,
         "assigned_officer": "Partner Agent — Pune Cluster"},
        {"loan_id": "HFCL/CD/2026/00220", "borrower": "Snehal Joshi", "dpd": 50,
         "assigned_officer": "Partner Agent — Pune Cluster"},
    ],
    "collections-bucket3": [
        {"loan_id": "HFCL/PL/2026/01204", "borrower": "Sunita Devi", "dpd": 68,
         "assigned_officer": "Partner Agent — Lucknow Cluster"},
        {"loan_id": "HFCL/TW/2026/00877", "borrower": "Rajesh Yadav", "dpd": 74,
         "assigned_officer": "Partner Agent — Lucknow Cluster"},
        {"loan_id": "HFCL/BL/2026/00344", "borrower": "Verma Traders", "dpd": 81,
         "assigned_officer": "Partner Agent — Lucknow Cluster"},
        {"loan_id": "HFCL/UC/2026/00588", "borrower": "Anita Singh", "dpd": 65,
         "assigned_officer": "Partner Agent — Lucknow Cluster"},
        {"loan_id": "HFCL/PL/2026/01277", "borrower": "Mohd. Irfan", "dpd": 89,
         "assigned_officer": "Partner Agent — Lucknow Cluster"},
    ],
    "collections-npa": [
        {"loan_id": "HFCL/LAP/2026/00077", "borrower": "Anil Traders (Prop.)", "dpd": 96,
         "assigned_officer": "Partner Agent — Ahmedabad Cluster"},
        {"loan_id": "HFCL/PL/2026/00699", "borrower": "Suresh Mehta", "dpd": 103,
         "assigned_officer": "Partner Agent — Ahmedabad Cluster"},
        {"loan_id": "HFCL/BL/2026/00456", "borrower": "Kavya Enterprises", "dpd": 112,
         "assigned_officer": "Partner Agent — Ahmedabad Cluster"},
        {"loan_id": "HFCL/TW/2026/01033", "borrower": "Ramavath Naik", "dpd": 98,
         "assigned_officer": "Partner Agent — Ahmedabad Cluster"},
        {"loan_id": "HFCL/UC/2026/00721", "borrower": "Preeti Malhotra", "dpd": 121,
         "assigned_officer": "Partner Agent — Ahmedabad Cluster"},
    ],
}

BUCKET_LABELS = {
    "collections-bucket2": "Bucket 2 (31–60 DPD)",
    "collections-bucket3": "Bucket 3 (61–90 DPD)",
    "collections-npa": "NPA (90+ DPD — legal-eligible)",
}

DEVIATION_QUEUE = [
    {"loan_id": "HFCL/PL/2026/01590", "product": "Personal Loan", "amount": "4,50,000",
     "requesting_officer": "Branch Credit Officer, Pune Cluster",
     "suggested_type": "CIBIL Score", "suggested_detail": "640 vs 700 preferred"},
]

# Deviation requests already filed, waiting on the Credit Head's decision.
# Officer submissions (via the form above) get appended here too, instead of
# each one posting its own separate approval card.
PENDING_APPROVALS = [
    {"loan_id": "HFCL/PL/2026/01590", "product": "Personal Loan", "amount": "4,50,000",
     "deviation_type": "CIBIL Score", "deviation_detail": "640 vs 700 preferred",
     "justification": "Existing loyalty customer, 14 months of on-time 2W EMI history, requesting personal loan top-up.",
     "requesting_officer": "Branch Credit Officer, Pune Cluster"},
    {"loan_id": "HFCL/TW/2026/00915", "product": "Two-Wheeler Loan", "amount": "1,20,000",
     "deviation_type": "Income Shortfall", "deviation_detail": "₹8,500/month vs ₹10,000 minimum",
     "justification": "Seasonal income, applicant provided 6-month averaged bank statement showing consistent inflow.",
     "requesting_officer": "Branch Credit Officer, Nashik Cluster"},
    {"loan_id": "HFCL/UC/2026/00512", "product": "Used Car Loan", "amount": "8,75,000",
     "deviation_type": "Age Outside Range", "deviation_detail": "Applicant aged 63, standard max is 60 at maturity",
     "justification": "Co-applicant (son, age 34) has stable income and will service the loan; applicant is a guarantor.",
     "requesting_officer": "Branch Credit Officer, Jaipur Cluster"},
    {"loan_id": "HFCL/LAP/2026/00203", "product": "Loan Against Property", "amount": "62,00,000",
     "deviation_type": "LTV Breach", "deviation_detail": "78% requested vs 75% policy cap for residential",
     "justification": "Property in prime location with strong resale value; applicant has 5-year clean repayment history on an existing LAP.",
     "requesting_officer": "Branch Credit Officer, Ahmedabad Cluster"},
    {"loan_id": "HFCL/BL/2026/00389", "product": "Business Loan", "amount": "22,00,000",
     "deviation_type": "Income Shortfall", "deviation_detail": "Latest ITR shows 15% lower turnover than policy minimum",
     "justification": "Turnover dip tied to one-time GST filing correction; current-year provisional figures show recovery.",
     "requesting_officer": "Branch Credit Officer, Lucknow Cluster"},
]

LEAD_QUEUE = [
    {"lead_id": "LEAD/2026/08341", "contact_name": "Deepak Yadav",
     "source": "Dealership Walk-in (Kothrud showroom)", "product_interest": "Two-Wheeler Loan"},
    {"lead_id": "LEAD/2026/08342", "contact_name": "Priya Nair",
     "source": "Digital Ad — Personal Loan campaign", "product_interest": "Personal Loan"},
    {"lead_id": "LEAD/2026/08343", "contact_name": "Suresh Bhandari",
     "source": "Referral — existing customer", "product_interest": "Loyalty Personal Loan"},
    {"lead_id": "LEAD/2026/08344", "contact_name": "Meena Iyer",
     "source": "Branch Walk-in — Ahmedabad", "product_interest": "Loan Against Property"},
    {"lead_id": "LEAD/2026/08345", "contact_name": "Arjun Deshmukh",
     "source": "Dealership Walk-in (Nashik showroom)", "product_interest": "Two-Wheeler Loan"},
    {"lead_id": "LEAD/2026/08346", "contact_name": "Kavita Rao",
     "source": "Digital Ad — Business Loan campaign", "product_interest": "Business Loan"},
    {"lead_id": "LEAD/2026/08347", "contact_name": "Farhan Sheikh",
     "source": "Branch Walk-in — Lucknow", "product_interest": "Used Car Loan"},
    {"lead_id": "LEAD/2026/08348", "contact_name": "Neha Kulkarni",
     "source": "Referral — existing customer", "product_interest": "Consumer Durable Loan"},
    {"lead_id": "LEAD/2026/08349", "contact_name": "Vikram Chauhan",
     "source": "Digital Ad — Two-Wheeler campaign", "product_interest": "Two-Wheeler Loan"},
]
