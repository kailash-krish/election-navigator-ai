"""
services/flow_service.py — Scripted decision-tree flows.
Handles first-time voter wizard, eligibility checker, and document checklist
without needing API calls, for instant and reliable responses.
"""

from __future__ import annotations
import re


class FlowService:
    """Maps trigger patterns to structured response payloads."""

    def handle(self, user_input: str, context: list) -> dict | None:
        text = user_input.lower().strip()

        # ── Entry triggers ───────────────────────────────────────────────────
        if re.search(r"first.?time voter|new voter|first vote|beginner", text):
            return self._ftv_entry()

        if re.search(r"eligib|qualify|can i vote|am i eligible", text):
            return self._eligibility_question()

        if re.search(r"document|id proof|what.*need|papers required", text):
            return self._documents_checklist()

        if re.search(r"election timeline|key dates|schedule|phases", text):
            return self._election_timeline()

        if re.search(r"(what|how).*evm|evm.*work|electronic.*voting", text):
            return self._evm_explainer()

        if re.search(r"(what|how).*vvpat|paper.*trail", text):
            return self._vvpat_explainer()

        if re.search(r"register|form 6|nvsp|voter id|epic", text):
            return self._registration_steps()

        # ── Flow continuation ─────────────────────────────────────────────────
        if text in ("age_yes",):
            return self._ftv_has_age()
        if text in ("age_no",):
            return self._ftv_no_age()
        if text in ("have_id",):
            return self._ftv_ready()
        if text in ("no_id",):
            return self._registration_steps()

        return None  # Fall through to AI

    # ── First-time voter wizard ───────────────────────────────────────────────

    def _ftv_entry(self) -> dict:
        return {
            "type": "question",
            "title": "🌟 First-Time Voter Guide",
            "summary": "Let's get you vote-ready in 3 minutes. First question:",
            "items": [
                {"option": "I'm 18 or above", "description": "Eligible by age", "action": "age_yes"},
                {"option": "I'm below 18",    "description": "Not yet eligible", "action": "age_no"},
            ],
            "follow_ups": ["Check eligibility", "Documents needed", "Registration steps"],
        }

    def _ftv_has_age(self) -> dict:
        return {
            "type": "question",
            "title": "Great! Do you have a Voter ID (EPIC)?",
            "summary": "This tells me your exact next step.",
            "items": [
                {"option": "Yes, I have my Voter ID", "description": "Ready to vote!",   "action": "have_id"},
                {"option": "No, I don't have one",     "description": "Let's register",  "action": "no_id"},
            ],
            "follow_ups": ["How to register", "Required documents", "Voting day steps"],
        }

    def _ftv_no_age(self) -> dict:
        return {
            "type": "info",
            "title": "You'll be eligible soon 🎓",
            "summary": "Voting age in India is 18. Start preparing your documents now.",
            "items": [
                {"label": "Qualifying date", "value": "January 1st cutoff — register after your 18th birthday"},
                {"label": "Prepare now",     "value": "Gather Aadhaar, birth certificate, and address proof"},
                {"label": "Portal",          "value": "voters.eci.gov.in — bookmark it"},
            ],
            "follow_ups": ["Documents needed", "How to register", "Election basics"],
        }

    def _ftv_ready(self) -> dict:
        return {
            "type": "steps",
            "title": "🗳️ You're Ready to Vote!",
            "summary": "Here's exactly what to do on election day.",
            "items": [
                {"step": 1, "title": "Verify your name",   "description": "Check electoral roll at voters.eci.gov.in", "icon": "🔍"},
                {"step": 2, "title": "Find your booth",    "description": "Your booth number is on your Voter ID slip",  "icon": "📍"},
                {"step": 3, "title": "Carry valid ID",     "description": "Voter ID, Aadhaar, or any 12 approved IDs",  "icon": "🪪"},
                {"step": 4, "title": "Queue and vote",     "description": "Give biometrics, get ballot, press EVM button", "icon": "✅"},
                {"step": 5, "title": "Check VVPAT slip",  "description": "Verify your choice on the paper trail",      "icon": "🧾"},
            ],
            "follow_ups": ["What to carry", "Find polling booth", "EVM explained"],
            "tip": "Polls open 7 AM–6 PM. Morning is least crowded.",
        }

    # ── Standalone flows ──────────────────────────────────────────────────────

    def _eligibility_question(self) -> dict:
        return {
            "type": "checklist",
            "title": "✅ Voter Eligibility Criteria",
            "summary": "You must meet ALL of these to vote in Indian elections.",
            "items": [
                {"task": "Age 18 or above",           "detail": "As on January 1 of the election year",         "required": True},
                {"task": "Indian citizen",             "detail": "Persons of Indian Origin (PIO) are excluded",  "required": True},
                {"task": "Registered in electoral roll","detail": "Your name must be on the constituency list",  "required": True},
                {"task": "Not disqualified",           "detail": "No criminal disenfranchisement",               "required": True},
                {"task": "Sound mind",                 "detail": "Not declared unsound by a court",              "required": True},
            ],
            "follow_ups": ["Register to vote", "Documents needed", "How to vote"],
        }

    def _documents_checklist(self) -> dict:
        return {
            "type": "checklist",
            "title": "📄 Documents Needed for Voter ID",
            "summary": "Collect these before visiting voters.eci.gov.in to file Form 6.",
            "items": [
                {"task": "Age proof",          "detail": "Birth certificate, school certificate, or Aadhaar", "required": True},
                {"task": "Address proof",      "detail": "Aadhaar, passport, utility bill, or bank statement", "required": True},
                {"task": "Passport photo",     "detail": "Recent clear photograph, white background",          "required": True},
                {"task": "Mobile number",      "detail": "For OTP verification on NVSP portal",                "required": True},
                {"task": "Email ID",           "detail": "Optional but recommended for updates",               "required": False},
            ],
            "follow_ups": ["Registration steps", "Check eligibility", "Find booth"],
            "tip": "Aadhaar alone can serve as both age and address proof.",
        }

    def _registration_steps(self) -> dict:
        return {
            "type": "steps",
            "title": "🪪 Register for Voter ID (Form 6)",
            "summary": "Complete registration online in under 10 minutes.",
            "items": [
                {"step": 1, "title": "Visit NVSP portal",     "description": "Go to voters.eci.gov.in",                    "icon": "🌐"},
                {"step": 2, "title": "Click 'New Registration'","description": "Select Form 6 for fresh enrollment",         "icon": "📝"},
                {"step": 3, "title": "Fill personal details", "description": "Name, DOB, address, constituency",            "icon": "✏️"},
                {"step": 4, "title": "Upload documents",      "description": "Age proof, address proof, passport photo",    "icon": "📎"},
                {"step": 5, "title": "Submit & track",        "description": "Note reference ID; EPIC mailed in 4–6 weeks", "icon": "📬"},
            ],
            "follow_ups": ["Documents needed", "Check eligibility", "Voting day steps"],
            "tip": "You can also register via the Voter Helpline App on Android/iOS.",
        }

    def _election_timeline(self) -> dict:
        return {
            "type": "timeline",
            "title": "🗓️ Indian General Election Timeline",
            "summary": "Key phases and milestones in a typical Lok Sabha election cycle.",
            "items": [
                {"date": "6 months before", "event": "Electoral roll revision",    "description": "Voter list updated; new registrations open",   "status": "past"},
                {"date": "3 months before", "event": "Model Code of Conduct",      "description": "MCC kicks in when ECI announces election date",  "status": "past"},
                {"date": "2 months before", "event": "Nomination filing",          "description": "Candidates file nomination with Returning Officer","status": "current"},
                {"date": "1 month before",  "event": "Campaigning period",         "description": "Rallies, advertising, and voter outreach",        "status": "current"},
                {"date": "Election day",    "event": "Voting 7 AM – 6 PM",        "description": "EVMs and VVPATs used at polling booths",          "status": "upcoming"},
                {"date": "Count day",       "event": "Result declaration",         "description": "ECI announces winners, government formed",        "status": "upcoming"},
            ],
            "follow_ups": ["How to vote", "Register to vote", "What is EVM?"],
        }

    def _evm_explainer(self) -> dict:
        return {
            "type": "cards",
            "title": "🖥️ How Electronic Voting Machines (EVMs) Work",
            "summary": "EVMs replaced paper ballots in India. Here's everything you need to know.",
            "items": [
                {"title": "Ballot Unit",         "description": "Blue unit shows candidate list; voter presses button to vote", "icon": "🔵", "tag": "Voter side"},
                {"title": "Control Unit",        "description": "Operated by presiding officer; enables one vote at a time",   "icon": "🟢", "tag": "Officer side"},
                {"title": "VVPAT",               "description": "Prints paper slip showing your choice; visible 7 seconds",    "icon": "🧾", "tag": "Verification"},
                {"title": "Tamper-proof",        "description": "No internet; standalone device; ECI-sealed before use",       "icon": "🔒", "tag": "Security"},
                {"title": "One vote guarantee",  "description": "Machine locks after each vote; prevents double voting",       "icon": "✅", "tag": "Integrity"},
            ],
            "follow_ups": ["What is VVPAT?", "How to vote", "Election timeline"],
        }

    def _vvpat_explainer(self) -> dict:
        return {
            "type": "cards",
            "title": "🧾 VVPAT — Voter Verified Paper Audit Trail",
            "summary": "VVPAT provides a physical paper record of every vote cast on an EVM.",
            "items": [
                {"title": "What it does",       "description": "Prints paper slip with candidate name and symbol after voting",   "icon": "🖨️"},
                {"title": "Visible for 7 sec",  "description": "Slip is displayed in a glass case before falling into sealed box","icon": "⏱️"},
                {"title": "Cannot be removed",  "description": "Slip auto-drops into tamper-proof VVPAT box, not voter's hands", "icon": "🔒"},
                {"title": "Audit purpose",      "description": "ECI can order VVPAT count to verify EVM results",                "icon": "🔍"},
                {"title": "Mandatory since 2019","description": "All Lok Sabha constituencies use VVPAT-linked EVMs",            "icon": "📋"},
            ],
            "follow_ups": ["How to vote", "What is EVM?", "Election timeline"],
        }
