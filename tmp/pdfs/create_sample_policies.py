from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)

GREEN = colors.HexColor("#23674E")
DARK = colors.HexColor("#24312C")
MUTED = colors.HexColor("#6F7D76")
PALE = colors.HexColor("#EEF4F0")
LINE = colors.HexColor("#DDE6E1")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=GREEN, spaceAfter=8, alignment=TA_CENTER, tracking=1.6))
styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=28, leading=34, textColor=DARK, spaceAfter=14, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=17, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=23, textColor=DARK, spaceBefore=4, spaceAfter=10))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=GREEN, spaceBefore=11, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=DARK, spaceAfter=7))
styles.add(ParagraphStyle(name="Bulletx", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, leftIndent=12, firstLineIndent=-8, bulletIndent=0, textColor=DARK, spaceAfter=5))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=15, textColor=GREEN))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(22*mm, 16*mm, 188*mm, 16*mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(22*mm, 10.5*mm, "ACME COMPANY  |  FICTIONAL PORTFOLIO SAMPLE")
    canvas.drawRightString(188*mm, 10.5*mm, f"Page {doc.page}")
    canvas.restoreState()

def cover(title, owner, effective, version):
    return [
        Spacer(1, 32*mm),
        Paragraph("ACME COMPANY", styles["CoverLabel"]),
        Paragraph(title, styles["DocTitle"]),
        Paragraph("A fictional internal policy created for the Atlas knowledge assistant portfolio demonstration.", styles["Subtitle"]),
        Spacer(1, 18*mm),
        Table([
            [Paragraph("DOCUMENT OWNER", styles["Smallx"]), Paragraph(owner, styles["Bodyx"])],
            [Paragraph("EFFECTIVE DATE", styles["Smallx"]), Paragraph(effective, styles["Bodyx"])],
            [Paragraph("VERSION", styles["Smallx"]), Paragraph(version, styles["Bodyx"])],
            [Paragraph("CLASSIFICATION", styles["Smallx"]), Paragraph("Internal", styles["Bodyx"])],
        ], colWidths=[42*mm, 75*mm], style=TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), PALE), ("BOX", (0,0), (-1,-1), .6, LINE),
            ("INNERGRID", (0,0), (-1,-1), .4, LINE), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 10), ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 9), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ])),
        Spacer(1, 20*mm),
        Paragraph("For demonstration only. This document does not describe a real company and should not be treated as legal, employment, security, or operational advice.", styles["Subtitle"]),
        PageBreak(),
    ]

def section(title, paragraphs=(), bullets=()):
    items = [Paragraph(title, styles["H1x"])]
    items += [Paragraph(p, styles["Bodyx"]) for p in paragraphs]
    items += [Paragraph(f"• {b}", styles["Bulletx"]) for b in bullets]
    return items

def subsection(title, paragraphs=(), bullets=()):
    items = [Paragraph(title, styles["H2x"])]
    items += [Paragraph(p, styles["Bodyx"]) for p in paragraphs]
    items += [Paragraph(f"• {b}", styles["Bulletx"]) for b in bullets]
    return items

def make(filename, title, owner, body):
    doc = SimpleDocTemplate(str(OUT / filename), pagesize=A4, rightMargin=22*mm, leftMargin=22*mm, topMargin=20*mm, bottomMargin=23*mm, title=title, author="Acme Company - Fictional Sample")
    story = cover(title, owner, "1 September 2026", "1.0") + body
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

leave = []
leave += section("1. Purpose", ["This policy explains annual leave, requests, approval, carryover, and unplanned absence for full-time employees of the fictional Acme Company."])
leave += section("2. Annual leave entitlement", ["Full-time employees receive <b>25 working days of paid annual leave</b> in each calendar year. Leave accrues monthly from the employee's start date. Part-time employees receive a pro-rated entitlement."])
leave += subsection("Public holidays", ["Company-recognized public holidays do not reduce annual leave. The applicable holiday calendar is based on the employee's country of employment."])
leave += section("3. Request and approval", bullets=["Submit requests in the People portal.", "Request planned leave at least two weeks in advance whenever possible.", "The employee's direct manager approves or declines the request.", "Do not book non-refundable travel until approval is recorded.", "Managers should respond within five working days and consider team coverage fairly."])
leave += section("4. Carryover", ["Employees may carry over up to <b>5 unused days</b> into the next calendar year. Carried days must be used by <b>31 March</b>; unused carried days expire after that date unless local law requires otherwise."])
leave += section("5. Unplanned absence", ["If illness or an emergency prevents attendance, notify your manager as soon as reasonably possible. Sick leave is recorded separately and does not normally reduce annual leave."])
leave += section("6. Questions and exceptions", ["People Operations handles policy questions and legally required exceptions. Managers cannot independently change leave entitlement or carryover limits."])
leave += subsection("Quick reference", bullets=["Annual entitlement: 25 working days", "Advance notice: two weeks when possible", "Approver: direct manager", "Carryover: up to 5 days", "Carryover deadline: 31 March"])

remote = []
remote += section("1. Purpose", ["This policy sets expectations for hybrid work, workplace safety, information security, and temporary work from another country."])
remote += section("2. Standard hybrid arrangement", ["Employees may work remotely for up to <b>three days per week</b>. Teams should agree on shared office days so collaboration, customer commitments, and operational coverage remain effective."])
remote += subsection("Availability", bullets=["Be reachable during the team's agreed core hours.", "Keep your calendar and working location current.", "Attend required in-person meetings with reasonable notice.", "Use approved collaboration and storage tools."])
remote += section("3. Home office equipment", ["Each employee may claim up to <b>$500 per calendar year</b> for approved home office equipment. Eligible items include a monitor, keyboard, mouse, headset, desk, or ergonomic chair. Submit an itemized receipt through the expense system within 30 days."])
remote += section("4. Working from another country", ["Working outside the employee's country of employment requires <b>prior written approval from People Operations</b>. Submit the request at least 30 days before travel. Approval may be declined because of tax, immigration, employment, customer, or information-security obligations."])
remote += section("5. Security and privacy", bullets=["Use company-managed devices and multi-factor authentication.", "Use the approved VPN when required.", "Prevent household members and visitors from viewing confidential information.", "Do not print customer data at home unless Security has approved it.", "Report lost devices or suspected incidents immediately."])
remote += section("6. Health, safety, and review", ["Employees are responsible for maintaining a safe working space and reporting concerns. Managers may review a remote arrangement when performance, security, customer service, or team coverage is affected."])
remote += subsection("Quick reference", bullets=["Remote limit: up to 3 days each week", "Equipment allowance: $500 each calendar year", "International work: written People Operations approval required", "International request lead time: 30 days"])

onboarding = []
onboarding += section("Welcome to Acme", ["This guide gives new engineering employees a clear path through their first week. Your manager and onboarding buddy will help you complete each step."])
onboarding += section("Before day one", bullets=["Confirm delivery or collection of your company laptop.", "Read the acceptable-use and information-security policies.", "Check the calendar invitations for orientation and team introductions."])
onboarding += section("Day one: identity and access", bullets=["Activate your company account through the invitation sent by IT.", "Enroll in <b>multi-factor authentication</b> immediately.", "Set up the approved password manager.", "Sign in to email, chat, the People portal, and the service desk.", "Meet your manager and onboarding buddy."])
onboarding += section("Days two and three: engineering setup", bullets=["Request GitHub organization access through the IT service desk.", "Install the approved development tools listed in the engineering portal.", "Clone the starter repository and run its automated checks.", "Review the team's architecture overview and coding standards.", "Never copy credentials into source code or commit secrets to Git."])
onboarding += section("Days four and five: first contribution", bullets=["Pair with your buddy on a small, low-risk task.", "Open a pull request and respond to review feedback.", "Observe the deployment process in a non-production environment.", "Schedule a first-week check-in with your manager."])
onboarding += section("Production access", ["Production access is not granted automatically. It requires completed security training, a documented business need, and approval from the engineering manager. Access must use the employee's individual account and the least privilege required for the task."])
onboarding += section("Getting help", ["Use the IT service desk for accounts and devices, the Security channel for security questions or incidents, and your onboarding buddy for development-environment help. Report suspected security incidents immediately."])
onboarding += subsection("First-week checklist", bullets=["SSO and MFA active", "Password manager configured", "GitHub request approved", "Development environment working", "Security training complete", "First pull request opened", "Manager check-in completed"])

make("leave-policy.pdf", "Annual Leave Policy", "People Operations", leave)
make("remote-work-policy.pdf", "Remote Work Policy", "People Operations and Security", remote)
make("onboarding-guide.pdf", "Engineering Onboarding Guide", "Engineering Enablement", onboarding)
print("\n".join(str(p) for p in sorted(OUT.glob("*.pdf"))))
