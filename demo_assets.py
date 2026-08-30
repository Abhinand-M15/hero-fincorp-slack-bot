"""
Generates the sample supporting documents used by the CPA approval demo —
a CIBIL summary, a bank statement extract, a property valuation and so on.

They are written as real one-page PDFs (no third-party library) so the demo can
show a genuine file attached to an approval request, living in a private
channel that no external partner agent is a member of.

    python3 demo_assets.py        # writes ./demo_files/*.pdf
"""
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "demo_files")

DOCUMENTS = {
    "cibil_summary.pdf": ("CIBIL Summary Extract", [
        "Applicant: Deepak Yadav", "PAN: ABCPYXXXXF", "Bureau: TransUnion CIBIL",
        "", "Score: 640", "Score band: Sub-prime (policy preference 700+)",
        "Enquiries last 6 months: 2", "Accounts: 1 active (Hero FinCorp two-wheeler)",
        "Days past due, last 24 months: 0", "Write-offs / settlements: None",
        "", "SUPPORTING NOTE", "Score is depressed by thin file, not by delinquency.",
        "", "-- Sample document generated for the Hero FinCorp Slack demo --",
    ]),
    "repayment_history.pdf": ("Repayment History", [
        "Loan: HFCL/TW/2024/44120  (Two-Wheeler)", "Customer: Deepak Yadav",
        "", "EMIs due: 14      EMIs paid: 14      Bounces: 0",
        "Average days early: 3", "Foreclosure requests: None",
        "", "Assessment: consistent on-time repayment across 14 months.",
        "", "-- Sample document generated for the Hero FinCorp Slack demo --",
    ]),
    "property_valuation.pdf": ("Property Valuation Report", [
        "Borrower: Kavya Enterprises", "Property: Commercial-residential, Satellite, Ahmedabad",
        "", "Assessed market value: Rs. 79,50,000", "Loan requested: Rs. 62,00,000",
        "Requested LTV: 78 percent", "Policy cap (residential): 75 percent",
        "", "Valuer: Empanelled, Registration IBBI/RV/XXXX/2231",
        "Comparable sales within 1 km support the assessed value.",
        "", "-- Sample document generated for the Hero FinCorp Slack demo --",
    ]),
    "itr_extract.pdf": ("Income Tax Return Extract", [
        "Assessee: Kavya Enterprises", "Assessment Year: 2025-26",
        "", "Gross turnover: Rs. 2,41,00,000", "Declared profit: Rs. 18,60,000",
        "Prior year turnover: Rs. 2,74,00,000",
        "", "Note: the year-on-year dip corresponds to a one-time GST filing",
        "correction; provisional current-year figures show recovery.",
        "", "-- Sample document generated for the Hero FinCorp Slack demo --",
    ]),
    "bank_statement.pdf": ("Bank Statement Extract (6 months)", [
        "Account holder: Arjun Deshmukh", "Bank: XXXX  Account ending 4417",
        "", "Month        Credits        Closing balance",
        "March        Rs. 11,400     Rs. 18,220", "April        Rs.  9,900     Rs. 21,050",
        "May          Rs. 12,700     Rs. 26,480", "June         Rs.  8,200     Rs. 22,110",
        "July         Rs. 10,850     Rs. 25,900", "August       Rs. 11,300     Rs. 29,640",
        "", "Six-month average credit: Rs. 10,725 against a Rs. 10,000 minimum.",
        "", "-- Sample document generated for the Hero FinCorp Slack demo --",
    ]),
    "payment_receipt.pdf": ("Collection Receipt", [
        "Receipt No: HFCL/RCPT/2026/88214", "Loan: HFCL/TW/2026/00891",
        "Customer: Ramesh Kumar", "", "Amount collected: Rs. 4,500",
        "Mode: UPI", "Collected by: Rakesh Sharma (External Partner, Pune)",
        "", "This receipt is generated from the Salesforce visit record.",
        "", "-- Sample document generated for the Hero FinCorp Slack demo --",
    ]),
}


def _escape(text):
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(title, lines):
    parts = ["BT", "/F1 16 Tf", "50 790 Td", f"({_escape(title)}) Tj", "/F1 11 Tf", "0 -30 Td"]
    for line in lines:
        parts.append(f"({_escape(line)}) Tj" if line else "() Tj")
        parts.append("0 -16 Td")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", "replace")


def build_pdf(title, lines):
    content = _content_stream(title, lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


def ensure_documents():
    """Create every sample document that is missing. Returns {name: path}."""
    os.makedirs(OUT_DIR, exist_ok=True)
    paths = {}
    for name, (title, lines) in DOCUMENTS.items():
        path = os.path.join(OUT_DIR, name)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(build_pdf(title, lines))
        paths[name] = path
    return paths


def path_for(name):
    return os.path.join(OUT_DIR, name)


if __name__ == "__main__":
    for name, path in ensure_documents().items():
        print(f"{name:28} {os.path.getsize(path):>6} bytes  ->  {path}")
