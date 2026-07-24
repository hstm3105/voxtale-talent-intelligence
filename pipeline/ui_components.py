import math
from typing import Optional, List, Dict, Any

def clean_html(html_str: str) -> str:
    """Strips leading whitespace from every line of HTML to prevent Streamlit markdown code block parsing."""
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())

def render_confidence_ring(score: int, decision: str = "Shortlist", size: int = 38) -> str:
    """
    Renders an inline SVG circular progress ring for scores (0-100).
    38px diameter SVG, stroke-width 3, r=16 (circumference ~= 100.53).
    Foreground ring color mapped to decision state with JetBrains Mono centered score text.
    """
    color_map = {
        "Shortlist": "#34D399",
        "Maybe": "#FBBF24",
        "Needs Manual Review": "#A78BFA",
        "Reject": "#FB7185"
    }
    color = color_map.get(decision, "#34D399")
    r = 16
    circumference = 2 * math.pi * r  # ~100.53096
    bounded_score = max(0, min(100, int(score)))
    stroke_dashoffset = circumference * (1.0 - bounded_score / 100.0)

    svg = f"""<div style="display: inline-flex; align-items: center; justify-content: center; position: relative; width: {size}px; height: {size}px; vertical-align: middle;"><svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="#26262F" stroke-width="3" /><circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{stroke_dashoffset:.2f}" stroke-linecap="round" transform="rotate(-90 {size/2} {size/2})" style="transition: stroke-dashoffset 1s ease;" /></svg><span style="position: absolute; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 600; color: #F2F1F7; line-height: 1;">{bounded_score}</span></div>"""
    return clean_html(svg)


def render_chip(label: str, kind: str = "decision") -> str:
    """
    Renders an HTML colored pill chip.
    - kind="decision": maps label to decision color scheme with dim bg & 5px colored dot.
    - kind="flag": flags="none" renders as plain muted text; non-none flags use violet ("Needs Manual Review") scheme.
    """
    if kind == "flag":
        clean_label = (label or "none").strip()
        if clean_label.lower() in ["none", "clean", "", "no flags"]:
            return """<span style="font-family: 'Inter', sans-serif; font-size: 11.5px; color: #5C5A6E;">none</span>"""
        
        # Non-none flags use violet color scheme (#A78BFA)
        violet_color = "#A78BFA"
        violet_bg = "rgba(167, 139, 250, 0.1)"
        return f"""<span style="display: inline-flex; align-items: center; gap: 6px; background: {violet_bg}; color: {violet_color}; border-radius: 20px; padding: 4px 10px; font-size: 11.5px; font-weight: 500; font-family: 'Inter', sans-serif; white-space: nowrap;"><span style="width: 5px; height: 5px; border-radius: 50%; background-color: {violet_color}; display: inline-block;"></span>{clean_label}</span>"""

    # Decision chip
    color_map = {
        "Shortlist": ("#34D399", "rgba(52, 211, 153, 0.1)"),
        "Maybe": ("#FBBF24", "rgba(251, 191, 36, 0.1)"),
        "Needs Manual Review": ("#A78BFA", "rgba(167, 139, 250, 0.1)"),
        "Reject": ("#FB7185", "rgba(251, 113, 133, 0.1)")
    }
    color, dim_bg = color_map.get(label, ("#34D399", "rgba(52, 211, 153, 0.1)"))

    return f"""<span style="display: inline-flex; align-items: center; gap: 6px; background: {dim_bg}; color: {color}; border-radius: 20px; padding: 4px 10px; font-size: 11.5px; font-weight: 500; font-family: 'Inter', sans-serif; white-space: nowrap;"><span style="width: 5px; height: 5px; border-radius: 50%; background-color: {color}; display: inline-block;"></span>{label}</span>"""


def format_text_field(val: Any) -> str:
    """Formats string or list values into clean text for table cells."""
    if not val:
        return ""
    if isinstance(val, list):
        return "; ".join(str(x) for x in val if x)
    return str(val).strip()


def build_candidate_html_table(records: List[Dict[str, Any]]) -> str:
    """
    Builds a dark, glassmorphic HTML candidate table with inline Confidence Rings, Decision/Flag Chips & Assessed Role.
    Headers: Candidate & Resume | Assessed Role | Decision | Score Ring | Flags | Key Strengths | Qualification Gaps | Recruiter Rationale
    """
    if not records:
        return "<p style='color: #8E8CA3; padding: 10px;'>No candidates found.</p>"

    rows_html = ""
    for r in records:
        cand_name = r.get("candidate_name", "Unknown Candidate")
        filename = r.get("resume_filename", r.get("filename", ""))
        target_role = format_text_field(r.get("target_role") or r.get("jd_title") or r.get("role_title") or "N/A")
        decision = r.get("decision", "Shortlist")
        score = int(r.get("score_0_100", 0))
        flags = r.get("flags", "none")
        strengths = format_text_field(r.get("key_strengths", ""))
        gaps = format_text_field(r.get("key_gaps", ""))
        rationale = format_text_field(r.get("rationale", ""))

        ring = render_confidence_ring(score, decision)
        dec_chip = render_chip(decision, kind="decision")
        flag_chip = render_chip(flags, kind="flag")

        # Cell 1: Candidate & Resume
        # Cell 2: Assessed Role
        # Cell 3: Decision
        # Cell 4: Score Ring
        # Cell 5: Flags
        # Cell 6: Key Strengths
        # Cell 7: Qualification Gaps
        # Cell 8: Recruiter Rationale
        rows_html += f"""<tr style="border-bottom: 1px solid #26262F;"><td style="padding: 12px 14px; color: #F2F1F7;"><div style="font-weight: 600; color: #F2F1F7; font-size: 0.92rem;">{cand_name}</div><div style="font-size: 0.78rem; color: #8E8CA3; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">{filename}</div></td><td style="padding: 12px 14px; color: #8E8CA3; font-size: 0.84rem; font-weight: 500; max-width: 170px;"><div style="background: rgba(255,255,255,0.04); border: 1px solid #26262F; border-radius: 6px; padding: 4px 10px; display: inline-block; color: #E2E8F0; line-height: 1.3;">{target_role}</div></td><td style="padding: 12px 14px; text-align: center; vertical-align: middle;">{dec_chip}</td><td style="padding: 12px 14px; text-align: center; vertical-align: middle;">{ring}</td><td style="padding: 12px 14px; text-align: center; vertical-align: middle;">{flag_chip}</td><td style="padding: 12px 14px; color: #8E8CA3; font-size: 0.84rem; max-width: 220px; line-height: 1.4;">{strengths}</td><td style="padding: 12px 14px; color: #8E8CA3; font-size: 0.84rem; max-width: 220px; line-height: 1.4;">{gaps}</td><td style="padding: 12px 14px; color: #8E8CA3; font-size: 0.84rem; max-width: 280px; line-height: 1.4;">{rationale}</td></tr>"""

    table_html = f"""<div style="overflow-x: auto; background: #14141C; border: 1px solid #26262F; border-radius: 12px; margin-bottom: 16px;"><table style="width: 100%; border-collapse: collapse; text-align: left; font-family: 'Inter', sans-serif;"><thead><tr style="border-bottom: 1px solid #26262F; background: rgba(255, 255, 255, 0.02);"><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600;">Candidate & Resume</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600;">Assessed Role</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600; text-align: center;">Decision</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600; text-align: center;">Score Ring</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600; text-align: center;">Flags</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600;">Key Strengths</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600;">Qualification Gaps</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: #8E8CA3; font-weight: 600;">Recruiter Rationale</th></tr></thead><tbody>{rows_html}</tbody></table></div>"""
    return clean_html(table_html)
