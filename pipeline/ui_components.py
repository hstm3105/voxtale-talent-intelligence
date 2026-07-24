import math
from typing import Optional, List, Dict, Any

def clean_html(html_str: str) -> str:
    """Strips leading whitespace from every line of HTML to prevent Streamlit markdown code block parsing."""
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())

def render_confidence_ring(score: int, decision: str = "Shortlist", size: int = 38) -> str:
    """
    Renders an inline SVG circular progress ring for scores (0-100).
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

    svg = f"""<div style="display: inline-flex; align-items: center; justify-content: center; position: relative; width: {size}px; height: {size}px; vertical-align: middle;"><svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="var(--border-hairline)" stroke-width="3" /><circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{stroke_dashoffset:.2f}" stroke-linecap="round" transform="rotate(-90 {size/2} {size/2})" style="transition: stroke-dashoffset 1s ease;" /></svg><span style="position: absolute; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 600; color: var(--text-primary); line-height: 1;">{bounded_score}</span></div>"""
    return clean_html(svg)


def render_chip(label: str, kind: str = "decision") -> str:
    """
    Renders an HTML colored pill chip.
    """
    if kind == "flag":
        clean_label = (label or "none").strip()
        if clean_label.lower() in ["none", "clean", "", "no flags"]:
            return """<span style="font-family: 'Inter', sans-serif; font-size: 11.5px; color: var(--text-muted);">none</span>"""
        
        violet_color = "#A78BFA"
        violet_bg = "rgba(167, 139, 250, 0.12)"
        return f"""<span style="display: inline-flex; align-items: center; gap: 6px; background: {violet_bg}; color: {violet_color}; border: 1px solid rgba(167, 139, 250, 0.25); border-radius: 20px; padding: 4px 10px; font-size: 11.5px; font-weight: 500; font-family: 'Inter', sans-serif; white-space: nowrap;"><span style="width: 5px; height: 5px; border-radius: 50%; background-color: {violet_color}; display: inline-block;"></span>{clean_label}</span>"""

    color_map = {
        "Shortlist": ("#34D399", "rgba(52, 211, 153, 0.12)"),
        "Maybe": ("#FBBF24", "rgba(251, 191, 36, 0.12)"),
        "Needs Manual Review": ("#A78BFA", "rgba(167, 139, 250, 0.12)"),
        "Reject": ("#FB7185", "rgba(251, 113, 133, 0.12)")
    }
    color, dim_bg = color_map.get(label, ("#34D399", "rgba(52, 211, 153, 0.12)"))

    return f"""<span style="display: inline-flex; align-items: center; gap: 6px; background: {dim_bg}; color: {color}; border: 1px solid rgba(255,255,255,0.05); border-radius: 20px; padding: 4px 10px; font-size: 11.5px; font-weight: 500; font-family: 'Inter', sans-serif; white-space: nowrap;"><span style="width: 5px; height: 5px; border-radius: 50%; background-color: {color}; display: inline-block;"></span>{label}</span>"""


def format_text_field(val: Any) -> str:
    """Formats string or list values into clean text for table cells."""
    if not val:
        return ""
    if isinstance(val, list):
        return "; ".join(str(x) for x in val if x)
    return str(val).strip()


def render_kpi_card(title: str, value: Any, subtitle: str = "", accent_color: str = "#6E62F5") -> str:
    """
    Renders an executive glassmorphic KPI metric tile with a top accent indicator line
    and JetBrains Mono metric readout.
    """
    sub_element = f'<div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 4px;">{subtitle}</div>' if subtitle else ''
    card_html = f"""<div style="background: var(--surface-bg); border: 1px solid var(--border-hairline); border-top: 3px solid {accent_color}; border-radius: 12px; padding: 14px 18px; font-family: 'Inter', sans-serif;"><div style="font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-secondary); margin-bottom: 6px;">{title}</div><div style="font-size: 1.45rem; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; line-height: 1.2;">{value}</div>{sub_element}</div>"""
    return clean_html(card_html)


def extract_skill_tokens(text: str) -> List[str]:
    """Extracts short tech/domain skill tokens from a candidate summary text."""
    if not text:
        return []
    
    known_techs = [
        "SQL", "Python", "Looker", "A/B Testing", "OTT Streaming", "Machine Learning",
        "Deep Learning", "Transformers", "LLMs", "Reinforcement Learning", "Predictive Modeling",
        "React", "Node", "AWS", "Docker", "Kubernetes", "PyTorch", "TensorFlow", "Tableau",
        "Data Engineering", "ETL", "System Architecture", "Product Strategy", "Growth Analytics"
    ]
    
    found_skills = []
    text_lower = text.lower()
    for tech in known_techs:
        if tech.lower() in text_lower and tech not in found_skills:
            found_skills.append(tech)
            
    raw_segments = [s.strip() for s in text.replace(";", ",").split(",") if s.strip()]
    for seg in raw_segments:
        if 2 <= len(seg) <= 22 and seg not in found_skills and not seg.lower().startswith("and ") and not seg.lower().startswith("proven "):
            found_skills.append(seg)
            
    return list(dict.fromkeys(found_skills))[:8]


def render_skill_tags(skills: Any) -> str:
    """
    Renders extracted short skill tokens as interactive styled pill badges.
    Prevents long paragraph sentence duplication.
    """
    if not skills:
        return ""
    if isinstance(skills, str):
        skill_list = extract_skill_tokens(skills)
    elif isinstance(skills, list):
        skill_list = [str(s).strip() for s in skills if str(s).strip() and len(str(s).strip()) <= 25]
    else:
        return ""

    if not skill_list:
        return ""

    tags_html = ""
    for s in skill_list[:8]:
        tags_html += f"""<span style="display: inline-block; background: rgba(110, 98, 245, 0.12); color: var(--brand-accent); border: 1px solid rgba(110, 98, 245, 0.25); border-radius: 12px; padding: 2px 8px; font-size: 0.74rem; font-family: 'JetBrains Mono', monospace; font-weight: 500; margin: 2px 3px;">{s}</span>"""

    return clean_html(f"""<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">{tags_html}</div>""")


def build_candidate_html_table(records: List[Dict[str, Any]]) -> str:
    """
    Builds a glassmorphic HTML candidate table with inline Confidence Rings, Decision/Flag Chips & Assessed Role.
    """
    if not records:
        return "<p style='color: var(--text-secondary); padding: 10px;'>No candidates found.</p>"

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

        rows_html += f"""<tr style="border-bottom: 1px solid var(--border-hairline);"><td style="padding: 12px 14px; color: var(--text-primary);"><div style="font-weight: 600; color: var(--text-primary); font-size: 0.92rem;">{cand_name}</div><div style="font-size: 0.78rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; margin-top: 2px;">{filename}</div></td><td style="padding: 12px 14px; color: var(--text-secondary); font-size: 0.84rem; font-weight: 500; max-width: 170px;"><div style="background: var(--raised-bg); border: 1px solid var(--border-hairline); border-radius: 6px; padding: 4px 10px; display: inline-block; color: var(--text-primary); line-height: 1.3;">{target_role}</div></td><td style="padding: 12px 14px; text-align: center; vertical-align: middle;">{dec_chip}</td><td style="padding: 12px 14px; text-align: center; vertical-align: middle;">{ring}</td><td style="padding: 12px 14px; text-align: center; vertical-align: middle;">{flag_chip}</td><td style="padding: 12px 14px; color: var(--text-secondary); font-size: 0.84rem; max-width: 220px; line-height: 1.4;">{strengths}</td><td style="padding: 12px 14px; color: var(--text-secondary); font-size: 0.84rem; max-width: 220px; line-height: 1.4;">{gaps}</td><td style="padding: 12px 14px; color: var(--text-secondary); font-size: 0.84rem; max-width: 280px; line-height: 1.4;">{rationale}</td></tr>"""

    table_html = f"""<div style="overflow-x: auto; background: var(--surface-bg); border: 1px solid var(--border-hairline); border-radius: 12px; margin-bottom: 16px;"><table style="width: 100%; border-collapse: collapse; text-align: left; font-family: 'Inter', sans-serif;"><thead><tr style="border-bottom: 1px solid var(--border-hairline); background: rgba(110, 98, 245, 0.04);"><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600;">Candidate & Resume</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600;">Assessed Role</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600; text-align: center;">Decision</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600; text-align: center;">Score Ring</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600; text-align: center;">Flags</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600;">Key Strengths</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600;">Qualification Gaps</th><th style="padding: 12px 14px; font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); font-weight: 600;">Recruiter Rationale</th></tr></thead><tbody>{rows_html}</tbody></table></div>"""
    return clean_html(table_html)
