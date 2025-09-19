"""Standalone analysis engine for the Web Redesign Client Scout."""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

__all__ = ["AnalysisError", "AnalysisResult", "analyze_website", "analyze_to_dict"]


class AnalysisError(RuntimeError):
    """Raised when a website cannot be analysed."""


@dataclass
class AnalysisResult:
    """Container describing the outcome of a website scan."""

    url: str
    normalized_url: str
    status_code: int
    response_time_ms: float
    page_size_kb: float
    design_score: int
    design_breakdown: Dict[str, int]
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    evidence_points: List[str] = field(default_factory=list)
    summary: str = ""
    mobile_friendly: bool = False
    last_refresh_years: Optional[float] = None
    image_count: int = 0
    missing_alt_count: int = 0
    cta_count: int = 0
    forms_count: int = 0
    tel_link_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain ``dict`` representation of the analysis."""

        return asdict(self)


DESIGN_CATEGORY_LIBRARY: Dict[str, Dict[str, str]] = {
    "Brand Cohesion": {
        "strength": "Visual identity feels consistent and premium across the journey.",
        "gap": "Brand cues shift between sections, diluting trust and recognition.",
        "action": "Audit typography, colors, and imagery to create a documented UI kit that locks the brand together.",
    },
    "Visual Hierarchy": {
        "strength": "Key sections guide the eye smoothly with clear spacing and typography.",
        "gap": "Important messages compete for attention, forcing visitors to hunt for next steps.",
        "action": "Restructure hero and pillar sections so that one primary action is obvious on every screen.",
    },
    "Content Clarity": {
        "strength": "Messaging is concise and scannable, making the value proposition easy to grasp.",
        "gap": "Copy blocks are dense, and supporting facts are buried below the fold.",
        "action": "Rewrite key pages with skimmable headings, proof points, and simplified copy.",
    },
    "Conversion Readiness": {
        "strength": "Calls-to-action feel intentional and are paired with persuasive proof.",
        "gap": "Forms and CTAs lack urgency, so visitors stall before taking action.",
        "action": "Design a focused conversion path with bold CTAs, risk reducers, and social proof in strategic locations.",
    },
    "Accessibility": {
        "strength": "Color contrast and interaction states support inclusive browsing.",
        "gap": "Contrast, keyboard focus, or alt text gaps will create friction for a growing portion of your audience.",
        "action": "Address contrast ratios, alt text, and focus states to align with WCAG AA expectations.",
    },
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _human_join(items: Iterable[str]) -> str:
    values = [value for value in items if value]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f" and {values[-1]}"


def _normalize_url(raw_url: str) -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        raise AnalysisError("Please provide a website URL to analyze.")
    parsed = urlparse(candidate)
    if not parsed.scheme:
        candidate = f"https://{candidate}"
        parsed = urlparse(candidate)
    if not parsed.netloc:
        raise AnalysisError("The website URL is missing a domain name.")
    return candidate


def _calculate_age_years(date: Optional[datetime]) -> Optional[float]:
    if date is None:
        return None
    timestamp = pd.to_datetime(date, utc=True, errors="coerce")
    if pd.isna(timestamp):
        return None
    if hasattr(timestamp, "tz_convert"):
        try:
            timestamp = timestamp.tz_convert(None)
        except TypeError:
            timestamp = timestamp.tz_localize(None)
    delta = datetime.now() - timestamp.to_pydatetime()
    return delta.days / 365.25


def _score_response_time(ms: float) -> float:
    if ms <= 1000:
        return 95
    if ms <= 2000:
        return 85
    if ms <= 3000:
        return 70
    if ms <= 4500:
        return 55
    if ms <= 6000:
        return 45
    return 35


def _score_page_weight(kb: float) -> float:
    if kb <= 700:
        return 92
    if kb <= 1500:
        return 80
    if kb <= 2500:
        return 65
    if kb <= 4000:
        return 52
    return 40


def _score_resource_count(count: int) -> float:
    if count <= 25:
        return 90
    if count <= 40:
        return 75
    if count <= 60:
        return 60
    return 45


def _clamp(value: float, lower: float = 0, upper: float = 100) -> float:
    return max(lower, min(upper, value))


def _unique_list(items: Iterable[str]) -> List[str]:
    unique: List[str] = []
    for item in items:
        text = (item or "").strip()
        if text and text not in unique:
            unique.append(text)
    return unique


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_website(url: str) -> AnalysisResult:
    """Analyze *url* and return a :class:`AnalysisResult`."""

    normalized_url = _normalize_url(url)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    def _fetch(target_url: str):
        start = time.perf_counter()
        response = session.get(target_url, timeout=12)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return response, elapsed_ms

    try:
        response, response_time_ms = _fetch(normalized_url)
    except requests.RequestException:
        if normalized_url.startswith("https://"):
            fallback = "http://" + normalized_url[len("https://") :]
            try:
                response, response_time_ms = _fetch(fallback)
                normalized_url = fallback
            except requests.RequestException as exc:
                raise AnalysisError(f"Failed to reach {url}. {exc}") from exc
        else:
            raise AnalysisError(f"Failed to reach {url}. Please verify the address and try again.")
    except Exception as exc:  # Safety net for unexpected issues
        raise AnalysisError(f"Failed to analyze {url}. {exc}") from exc

    status_code = response.status_code
    content = response.content or b""
    page_size_kb = len(content) / 1024 if content else 0.0

    if not response.text:
        response.encoding = response.apparent_encoding or "utf-8"
    page_text = response.text or content.decode("utf-8", errors="ignore")

    soup = BeautifulSoup(page_text, "html.parser")

    last_modified_header = response.headers.get("Last-Modified")
    if last_modified_header:
        parsed_last_update = pd.to_datetime(last_modified_header, utc=True, errors="coerce")
        if pd.notna(parsed_last_update):
            last_update = parsed_last_update.tz_convert(None).to_pydatetime()
        else:
            last_update = None
    else:
        last_update = None

    meta_viewport = soup.find("meta", attrs={"name": re.compile("viewport", re.I)})
    if not meta_viewport:
        meta_viewport = soup.find("meta", attrs={"property": re.compile("viewport", re.I)})
    viewport_content = meta_viewport.get("content", "").lower() if meta_viewport else ""
    mobile_friendly = "width=device-width" in viewport_content or "initial-scale" in viewport_content

    images = soup.find_all("img")
    image_count = len(images)
    images_with_alt = sum(1 for img in images if (img.get("alt") or "").strip())
    missing_alt_count = image_count - images_with_alt
    alt_ratio = images_with_alt / image_count if image_count else 1.0

    scripts = [script for script in soup.find_all("script") if script.get("src")]
    script_count = len(scripts)

    links = soup.find_all("a")
    cta_keywords = [
        "contact",
        "book",
        "schedule",
        "demo",
        "quote",
        "start",
        "consult",
        "call",
        "enquire",
        "enquiry",
        "enroll",
        "buy",
        "shop",
        "signup",
        "sign up",
        "get started",
    ]
    cta_count = 0
    for link in links:
        text = link.get_text(strip=True).lower()
        if text and any(keyword in text for keyword in cta_keywords):
            cta_count += 1
    tel_links = sum(1 for link in links if (link.get("href") or "").lower().startswith(("tel:", "mailto:")))

    forms_count = len(soup.find_all("form"))

    text_content = " ".join(segment.strip() for segment in soup.stripped_strings)
    word_count = len(text_content.split())
    paragraphs = soup.find_all("p")
    paragraph_count = len(paragraphs)
    avg_paragraph_words = word_count / paragraph_count if paragraph_count else float(word_count)

    structured_data = soup.find_all("script", attrs={"type": lambda value: value and "ld+json" in value.lower()})

    response_score = _score_response_time(response_time_ms)
    weight_score = _score_page_weight(page_size_kb)
    resource_score = _score_resource_count(image_count + script_count)
    speed_score = int(round(_clamp(0.5 * response_score + 0.3 * weight_score + 0.2 * resource_score)))

    title_tag = soup.find("title")
    title_length = len(title_tag.get_text(strip=True)) if title_tag else 0
    favicon_present = bool(soup.find("link", rel=lambda value: value and "icon" in value.lower()))
    og_site_name = bool(soup.find("meta", attrs={"property": "og:site_name"}))

    brand_score = 60
    if favicon_present:
        brand_score += 8
    if og_site_name:
        brand_score += 7
    if title_length >= 30:
        brand_score += 5
    if not title_tag:
        brand_score -= 12
    brand_score = _clamp(brand_score, 35, 92)

    visual_score = 62
    heading_counts = {tag: len(soup.find_all(tag)) for tag in ["h1", "h2", "h3"]}
    if heading_counts.get("h1", 0) == 1:
        visual_score += 10
    elif heading_counts.get("h1", 0) == 0:
        visual_score -= 12
    if heading_counts.get("h2", 0) >= 2:
        visual_score += 8
    if heading_counts.get("h3", 0) >= 3:
        visual_score += 4
    if paragraph_count and avg_paragraph_words <= 110:
        visual_score += 6
    elif avg_paragraph_words > 150:
        visual_score -= 8
    visual_score = _clamp(visual_score, 30, 90)

    content_score = 65
    if 400 <= word_count <= 1500:
        content_score += 6
    elif word_count > 2200 or word_count < 150:
        content_score -= 8
    if paragraph_count >= 8:
        content_score += 4
    if avg_paragraph_words < 80:
        content_score += 4
    elif avg_paragraph_words > 140:
        content_score -= 5
    if structured_data:
        content_score += 4
    content_score = _clamp(content_score, 35, 92)

    conversion_score = 55
    if cta_count >= 3:
        conversion_score += 15
    elif cta_count >= 1:
        conversion_score += 8
    else:
        conversion_score -= 6
    if forms_count >= 1:
        conversion_score += 10
    if tel_links >= 1:
        conversion_score += 5
    conversion_score = _clamp(conversion_score, 30, 90)

    accessibility_score = 68
    if alt_ratio >= 0.8:
        accessibility_score += 8
    elif alt_ratio < 0.5:
        accessibility_score -= 10
    if mobile_friendly:
        accessibility_score += 6
    else:
        accessibility_score -= 12
    if heading_counts.get("h1", 0) == 1:
        accessibility_score += 4
    elif heading_counts.get("h1", 0) == 0:
        accessibility_score -= 6
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        accessibility_score += 4
    accessibility_score = _clamp(accessibility_score, 30, 92)

    design_breakdown = {
        "Brand Cohesion": round(brand_score),
        "Visual Hierarchy": round(visual_score),
        "Content Clarity": round(content_score),
        "Conversion Readiness": round(conversion_score),
        "Accessibility": round(accessibility_score),
        "Speed": speed_score,
    }
    design_score = int(np.clip(np.mean(list(design_breakdown.values())), 0, 100))

    strengths: List[str] = []
    gaps: List[str] = []
    recommended_actions: List[str] = []

    for category, score in design_breakdown.items():
        if category == "Speed":
            # Speed is represented by evidence points rather than narrative text.
            continue
        details = DESIGN_CATEGORY_LIBRARY.get(category, {})
        if score >= 72:
            strengths.append(f"{category} ({score}/100) — {details.get('strength', '')}")
        elif score <= 65:
            gaps.append(f"{category} ({score}/100) — {details.get('gap', '')}")
            recommended_actions.append(
                f"Raise {category.lower()} by {details.get('action', 'designing focused improvements for this area.')}"
            )
        else:
            recommended_actions.append(
                f"Tighten {category.lower()} ({score}/100) so it matches the stronger sections. {details.get('action', '')}"
            )

    recommended_actions = _unique_list(recommended_actions)
    strengths = _unique_list(strengths)
    gaps = _unique_list(gaps)

    weakest = [name for name, value in sorted(design_breakdown.items(), key=lambda kv: kv[1])[:2]]
    strongest = [name for name, value in sorted(design_breakdown.items(), key=lambda kv: kv[1], reverse=True)[:2]]

    site_age_years = _calculate_age_years(last_update)

    summary_parts = [
        f"The design benchmark for {normalized_url} lands at {design_score}/100 based on structure, content, and accessibility checks.",
        f"The page responded in {response_time_ms/1000:.1f}s and weighs {page_size_kb:.0f} KB, two signals prospects feel immediately.",
    ]
    if site_age_years is not None:
        summary_parts.insert(
            1,
            f"Server headers suggest the last significant refresh was roughly {site_age_years:.1f} years ago, shaping how modern the experience feels.",
        )
    if weakest:
        summary_parts.append(f"Greatest friction sits within {_human_join(weakest)} where cohesion and storytelling taper off.")
    if strongest:
        summary_parts.append(f"Strengths you can amplify include {_human_join(strongest)}.")
    summary_parts.append(
        "Use this blend of hard metrics and narrative talking points to frame the redesign opportunity with clients."
    )
    summary = " ".join(summary_parts)

    if not gaps:
        gaps.append(
            "The core system is strong; focus on polishing micro-interactions to stay ahead of competitors."
        )
    if not recommended_actions:
        recommended_actions.append(
            "Document a lightweight design system playbook to protect the gains made across the experience."
        )

    evidence_points: List[str] = []
    evidence_points.append(
        f"First response landed in {response_time_ms:.0f} ms with a {status_code} status code — buyers expect <1500 ms for a premium feel."
    )
    evidence_points.append(
        f"Page weight is {page_size_kb:.0f} KB across {image_count} images and {script_count} scripts, which influences load speed and perception."
    )
    if image_count and missing_alt_count:
        evidence_points.append(
            f"{missing_alt_count} of {image_count} images are missing alt text, leaving accessibility and SEO equity on the table."
        )
    if cta_count == 0:
        evidence_points.append("No primary calls-to-action were detected, so visitors lack a clear next step.")
    elif cta_count < 2:
        evidence_points.append(
            f"Only {cta_count} clear call-to-action link{'s' if cta_count != 1 else ''} were detected, limiting conversion paths."
        )
    if forms_count == 0:
        evidence_points.append("No lead capture forms or booking widgets were present on the scanned page.")
    if site_age_years is not None:
        evidence_points.append(
            f"Server headers indicate a refresh cadence of about {site_age_years:.1f} years, signalling dated conventions."
        )
    evidence_points = _unique_list(evidence_points)

    return AnalysisResult(
        url=url,
        normalized_url=normalized_url,
        status_code=status_code,
        response_time_ms=response_time_ms,
        page_size_kb=page_size_kb,
        design_score=design_score,
        design_breakdown={key: int(value) for key, value in design_breakdown.items()},
        strengths=strengths,
        gaps=gaps,
        recommended_actions=recommended_actions,
        evidence_points=evidence_points,
        summary=summary,
        mobile_friendly=mobile_friendly,
        last_refresh_years=site_age_years,
        image_count=image_count,
        missing_alt_count=missing_alt_count,
        cta_count=cta_count,
        forms_count=forms_count,
        tel_link_count=tel_links,
    )


def analyze_to_dict(url: str) -> Dict[str, Any]:
    """Convenience wrapper that returns the analysis as a dictionary."""

    return analyze_website(url).to_dict()
