"""Daily tech digest: fetches RSS feeds, optionally summarizes with Claude, emails the result.

Usage:
    python news_bot.py            # build digest and email it
    python news_bot.py --dry-run  # build digest, save digest_preview.html, don't email

Environment variables:
    EMAIL_ADDRESS       Gmail address that sends the digest (required unless --dry-run)
    EMAIL_APP_PASSWORD  Gmail app password (required unless --dry-run)
    EMAIL_TO            Recipient(s), comma separated (optional, defaults to EMAIL_ADDRESS)
    ANTHROPIC_API_KEY   Optional. Adds AI summaries and a Concept of the Day.
"""

import argparse
import html
import json
import os
import re
import smtplib
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import feedparser
import requests

from feeds import CONCEPTS, SECTIONS

HERE = Path(__file__).parent
HISTORY_FILE = HERE / "sent_history.json"
PREVIEW_FILE = HERE / "digest_preview.html"
LOOKBACK_DAYS = 7        # ignore articles older than this
HISTORY_DAYS = 30        # don't resend a link sent within this many days
FEED_DEADLINE = 30       # max seconds to spend downloading one feed
IST = timezone(timedelta(hours=5, minutes=30))
USER_AGENT = "Mozilla/5.0 (compatible; DailyTechDigest/1.0; +https://github.com)"
CLAUDE_MODEL = "claude-opus-5"


# ---------- fetching ----------

def fetch_feed(source, url):
    """Return (source, url, entries, error). entries is a list of dicts."""
    try:
        # Stream the body so a slow server can't hang the run past FEED_DEADLINE seconds.
        start = time.monotonic()
        with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15, stream=True) as resp:
            resp.raise_for_status()
            chunks = []
            for chunk in resp.iter_content(65536):
                chunks.append(chunk)
                if time.monotonic() - start > FEED_DEADLINE:
                    raise TimeoutError(f"took longer than {FEED_DEADLINE}s")
        parsed = feedparser.parse(b"".join(chunks))
        if not parsed.entries:
            return source, url, [], "feed loaded but has no articles"
        entries = []
        for e in parsed.entries:
            ts = e.get("published_parsed") or e.get("updated_parsed")
            published = datetime(*ts[:6], tzinfo=timezone.utc) if ts else None
            summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
            summary = re.sub(r"\s+", " ", html.unescape(summary)).strip()
            entries.append({
                "source": source,
                "title": html.unescape(e.get("title", "(untitled)")).strip(),
                "link": e.get("link", ""),
                "summary": summary[:400],
                "published": published,
            })
        return source, url, entries, None
    except Exception as exc:  # network errors, HTTP errors, parse errors
        return source, url, [], f"{type(exc).__name__}: {exc}"[:200]


def matches_keywords(entry, keywords):
    if not keywords:
        return True
    text = f"{entry['title']} {entry['summary']}".lower()
    return any(re.search(rf"\b{re.escape(k.lower())}\b", text) for k in keywords)


def load_history():
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    return {link: d for link, d in data.items() if datetime.fromisoformat(d) > cutoff}


def save_history(history, sections):
    now = datetime.now(timezone.utc).isoformat()
    for sec in sections:
        for item in sec["items"]:
            history[item["link"]] = now
    HISTORY_FILE.write_text(json.dumps(history, indent=1, sort_keys=True), encoding="utf-8")


def collect(history):
    """Fetch all feeds in parallel and build the section list."""
    # One daemon thread per feed, with an overall deadline: a site that hangs
    # (even in DNS or TLS setup, which requests' timeout doesn't cover) is
    # reported as failed instead of stalling the whole run.
    results = {}

    def worker(src, url):
        results[url] = fetch_feed(src, url)

    threads = [threading.Thread(target=worker, args=(src, url), daemon=True)
               for sec in SECTIONS for src, url in sec["feeds"]]
    for t in threads:
        t.start()
    deadline = time.monotonic() + FEED_DEADLINE + 15
    for t in threads:
        t.join(max(0, deadline - time.monotonic()))
    for sec in SECTIONS:
        for src, url in sec["feeds"]:
            results.setdefault(url, (src, url, [], "timed out (site did not respond)"))

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    seen = set(history)
    sections, failed, report = [], [], []
    for sec in SECTIONS:
        candidates = []
        for src, url in sec["feeds"]:
            _, _, entries, err = results[url]
            if err:
                failed.append((sec["title"], src, url, err))
                report.append(f"  FAIL  {src:28} {err}")
                continue
            report.append(f"  OK    {src:28} {len(entries)} articles")
            for e in entries:
                if e["published"] and e["published"] < cutoff:
                    continue
                if not e["link"] or e["link"] in seen or not matches_keywords(e, sec["keywords"]):
                    continue
                candidates.append(e)
        candidates.sort(key=lambda e: e["published"] or cutoff, reverse=True)

        # Round-robin across sources so one busy feed doesn't fill the section.
        by_source = {}
        for e in candidates:
            by_source.setdefault(e["source"], []).append(e)
        picked = []
        while len(picked) < sec["max_items"] and any(by_source.values()):
            for src in list(by_source):
                if by_source[src] and len(picked) < sec["max_items"]:
                    picked.append(by_source[src].pop(0))
        for e in picked:
            seen.add(e["link"])
        sections.append({"title": sec["title"], "items": picked})
    return sections, failed, report


# ---------- optional Claude summaries ----------

def add_ai_summaries(sections):
    """Adds 'ai_summary' and 'learn' to each item; returns Concept of the Day HTML text or None."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        print("anthropic package not installed; skipping AI summaries")
        return None

    items = [it for sec in sections for it in sec["items"]]
    concept = CONCEPTS[datetime.now(IST).toordinal() % len(CONCEPTS)]
    articles = "\n\n".join(
        f"[{i}] {it['title']} ({it['source']})\n{it['summary']}" for i, it in enumerate(items)
    )
    prompt = (
        "You are writing a daily learning digest for a software engineer in India who wants to "
        "understand how tech companies build systems (Netflix, Uber, Google), AI, and how tech is "
        "used in manufacturing, logistics and real estate, and who is looking for ideas to build "
        "and earn from.\n\n"
        "For each article below, write a plain-English summary of at most two sentences, and one "
        "short 'what you can learn' line (a concept, technique or business idea it teaches). "
        "Base it only on the text given; if the text is thin, keep it brief rather than guessing.\n\n"
        f"Also write a 'Concept of the Day' lesson on: {concept}. Explain it in about 150 words for "
        "a beginner, with one real-world company example, then one small project idea to practice it.\n\n"
        f"Articles:\n\n{articles}"
    )
    schema = {
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "summary": {"type": "string"},
                        "learn": {"type": "string"},
                    },
                    "required": ["index", "summary", "learn"],
                    "additionalProperties": False,
                },
            },
            "concept_title": {"type": "string"},
            "concept_lesson": {"type": "string"},
            "concept_project": {"type": "string"},
        },
        "required": ["articles", "concept_title", "concept_lesson", "concept_project"],
        "additionalProperties": False,
    }

    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIConnectionError as exc:
        print(f"Could not reach Claude API, skipping AI summaries: {exc}")
        return None
    except anthropic.RateLimitError as exc:
        print(f"Claude API rate limited, skipping AI summaries: {exc}")
        return None
    except anthropic.APIStatusError as exc:
        print(f"Claude API error {exc.status_code}, skipping AI summaries: {exc.message}")
        return None

    if response.stop_reason != "end_turn":
        print(f"Claude stopped with '{response.stop_reason}', skipping AI summaries")
        return None
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("Claude returned invalid JSON, skipping AI summaries")
        return None

    for a in data["articles"]:
        if 0 <= a["index"] < len(items):
            items[a["index"]]["ai_summary"] = a["summary"]
            items[a["index"]]["learn"] = a["learn"]
    return data


# ---------- rendering ----------

def esc(s):
    return html.escape(s or "", quote=True)


def render(sections, failed, concept):
    today = datetime.now(IST).strftime("%A, %d %B %Y")
    parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Daily Tech Digest</title></head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2328;">
<div style="max-width:680px;margin:0 auto;padding:24px 16px;">
<h1 style="margin:0 0 4px;font-size:24px;">Daily Tech Digest</h1>
<div style="color:#656d76;font-size:14px;margin-bottom:24px;">{today}</div>"""]

    if concept:
        parts.append(f"""<div style="background:#eef4ff;border-left:4px solid #3b6fd8;border-radius:6px;padding:16px 18px;margin-bottom:28px;">
<div style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#3b6fd8;font-weight:600;">Concept of the Day</div>
<h2 style="margin:6px 0 10px;font-size:18px;">{esc(concept['concept_title'])}</h2>
<div style="font-size:15px;line-height:1.55;white-space:pre-line;">{esc(concept['concept_lesson'])}</div>
<div style="font-size:14px;line-height:1.5;margin-top:10px;"><b>Try building:</b> {esc(concept['concept_project'])}</div>
</div>""")

    for sec in sections:
        parts.append(f'<h2 style="font-size:18px;border-bottom:2px solid #d0d7de;padding-bottom:6px;margin:28px 0 12px;">{esc(sec["title"])}</h2>')
        if not sec["items"]:
            parts.append('<p style="color:#656d76;font-size:14px;">Nothing new today.</p>')
            continue
        for it in sec["items"]:
            date = it["published"].astimezone(IST).strftime("%d %b") if it["published"] else ""
            desc = it.get("ai_summary") or (it["summary"][:280] + ("…" if len(it["summary"]) > 280 else ""))
            learn = f'<div style="font-size:14px;color:#1a7f37;margin-top:4px;"><b>Learn:</b> {esc(it["learn"])}</div>' if it.get("learn") else ""
            parts.append(f"""<div style="background:#fff;border:1px solid #d0d7de;border-radius:6px;padding:12px 14px;margin-bottom:10px;">
<a href="{esc(it['link'])}" style="font-size:16px;font-weight:600;color:#0969da;text-decoration:none;">{esc(it['title'])}</a>
<div style="font-size:12px;color:#656d76;margin:3px 0 6px;">{esc(it['source'])}{' · ' + date if date else ''}</div>
<div style="font-size:14px;line-height:1.5;">{esc(desc)}</div>{learn}
</div>""")

    if failed:
        rows = "".join(f"<li><b>{esc(src)}</b> ({esc(sec)}): {esc(err)}<br><span style='color:#656d76'>{esc(url)}</span></li>" for sec, src, url, err in failed)
        parts.append(f"""<div style="margin-top:32px;padding:12px 14px;background:#fff8e6;border:1px solid #e3c36b;border-radius:6px;font-size:13px;">
<b>Feeds that failed today</b> (fix these in feeds.py):<ul style="margin:6px 0 0;padding-left:18px;">{rows}</ul></div>""")

    parts.append('<p style="font-size:12px;color:#8c959f;margin-top:32px;">Sent by your Daily Tech Digest bot.</p></div></body></html>')
    return "\n".join(parts)


# ---------- email ----------

def send_email(html_body, subject):
    sender = os.environ.get("EMAIL_ADDRESS")
    password = os.environ.get("EMAIL_APP_PASSWORD")
    if not sender or not password:
        sys.exit("EMAIL_ADDRESS and EMAIL_APP_PASSWORD must be set (or use --dry-run).")
    recipients = [r.strip() for r in (os.environ.get("EMAIL_TO") or sender).split(",") if r.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText("Your email client doesn't support HTML. Open digest in a browser.", "plain"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password.replace(" ", ""))
        smtp.sendmail(sender, recipients, msg.as_string())
    print(f"Email sent to {', '.join(recipients)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="save digest_preview.html instead of emailing")
    args = parser.parse_args()

    history = load_history()
    sections, failed, report = collect(history)
    print("Feed check:")
    print("\n".join(report))
    total = sum(len(s["items"]) for s in sections)
    print(f"\n{total} new articles, {len(failed)} failed feeds")

    concept = add_ai_summaries(sections)
    body = render(sections, failed, concept)
    subject = f"Daily Tech Digest · {datetime.now(IST).strftime('%d %b %Y')}"

    if args.dry_run:
        PREVIEW_FILE.write_text(body, encoding="utf-8")
        print(f"Dry run: saved {PREVIEW_FILE.name}")
        return
    send_email(body, subject)
    save_history(history, sections)


if __name__ == "__main__":
    main()
