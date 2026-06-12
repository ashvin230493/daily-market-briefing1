"""
Daily Market Briefing Script
Fetches headlines from CNN Business, CNBC, Motley Fool, Forbes
Summarizes via Claude API and emails via Gmail SMTP
"""

import feedparser
import anthropic
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

FEEDS = {
    "CNN Business":  "https://rss.cnn.com/rss/money_latest.rss",
    "CNBC":          "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Motley Fool":   "https://www.fool.com/feeds/index.aspx",
    "Forbes":        "https://www.forbes.com/investing/feed2/",
}

MAX_ARTICLES_PER_SOURCE = 8


def fetch_headlines():
    results = {}
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            articles = []
            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                articles.append({
                    "title":   entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "link":    entry.get("link", ""),
                })
            results[source] = articles
            print(f"✓ {source}: {len(articles)} articles")
        except Exception as e:
            print(f"✗ {source}: {e}")
            results[source] = []
    return results


def build_prompt(headlines):
    today = datetime.now().strftime("%A, %d %B %Y")
    lines = [f"Today is {today}. Below are the latest headlines from major financial news sources.\n"]
    for source, articles in headlines.items():
        lines.append(f"\n## {source}")
        for a in articles:
            lines.append(f"- {a['title']}")
            if a["summary"]:
                lines.append(f"  {a['summary'][:200]}")
    lines.append("""
Based on the above, write a concise daily market briefing for an investor focused on US equities and global macro trends. Structure it exactly like this:

**MARKET MOOD** (1-2 sentences: overall sentiment today)

**TOP 5 STORIES TO WATCH**
For each story: bold headline, then 2-3 sentences on what it means for markets/investors.

**SECTORS & STOCKS IN FOCUS**
Which sectors or individual stocks are getting attention today and why.

**RISKS & WATCH LIST**
Key risks, macro concerns, or events to monitor this week.

**BOTTOM LINE**
One sharp paragraph - what should an investor keep in mind going into today's session?

Keep the total length under 600 words. Be direct, no fluff.
""")
    return "\n".join(lines)


def get_briefing_from_claude(prompt):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def build_html_email(briefing_text):
    today = datetime.now().strftime("%A, %d %B %Y")
    import re
    html_body = briefing_text
    html_body = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_body)
    html_body = html_body.replace('\n\n', '</p><p>').replace('\n', '<br>')
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
  .container {{ max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 8px; }}
  .header {{ background: #0a2540; color: white; padding: 24px 32px; }}
  .header h1 {{ margin: 0;
