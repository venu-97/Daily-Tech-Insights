# Daily Tech Digest

Emails you a daily digest at **7:00 AM India time** with six sections:

1. **AI & Research**: Google Research, OpenAI, Hugging Face, Berkeley AI, MIT
2. **How Big Tech Builds Things**: Netflix, Meta, Airbnb, Grab, Lyft, Cloudflare, Spotify, Pinterest, Dropbox, ByteByteGo
3. **Top Tech News**: Hacker News, TechCrunch, The Verge, Ars Technica
4. **Manufacturing**: Manufacturing Dive, IoT Analytics, The Robot Report
5. **Fleets & Logistics**: FreightWaves, Supply Chain Dive, Logistics Viewpoints
6. **Real Estate & PropTech**: HousingWire, Propmodo, Inman

It runs free on GitHub Actions, so your computer doesn't need to be on. Articles are never repeated within 30 days.
If a feed breaks, the email lists it at the bottom so you know what to fix in `feeds.py`.

**Optional AI summaries:** add a Claude API key and every article gets a two-sentence summary plus a
"Learn:" line, and the email opens with a **Concept of the Day** lesson (caching, route optimization,
RAG, digital twins…) with a small project idea. This costs a few cents a day in API usage.

## Setup (about 15 minutes)

### 1. Create a Gmail app password
1. Turn on 2-Step Verification: <https://myaccount.google.com/security>
2. Create an app password: <https://myaccount.google.com/apppasswords> (name it "Tech Digest").
3. Copy the 16-character password. You'll paste it into GitHub in step 3, and nowhere else.

### 2. Put the code on GitHub
Create a **private** repository at <https://github.com/new>, then push this folder to it:

```bash
git remote add origin https://github.com/YOUR-USERNAME/daily-tech-digest.git
git push -u origin main
```

### 3. Add secrets
In the repository: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `EMAIL_ADDRESS` | your Gmail address |
| `EMAIL_APP_PASSWORD` | the 16-character app password |
| `EMAIL_TO` | *(optional)* where to send it; defaults to `EMAIL_ADDRESS`. Comma-separate multiple addresses. |
| `ANTHROPIC_API_KEY` | *(optional)* from <https://console.anthropic.com> for AI summaries |

### 4. Test it
**Actions** tab → **Daily Tech Digest** → **Run workflow**. You should get the email within a minute or two.
After that it runs by itself every morning.

## Run it on your computer

```bash
pip install -r requirements.txt
python news_bot.py --dry-run
```

`--dry-run` checks every feed, prints which ones work, and saves `digest_preview.html` without sending email.

## Customize
- **Add or remove sources:** edit `feeds.py`. Any RSS/Atom feed URL works.
- **Filter a section:** the `keywords` list keeps only matching articles (empty = keep all).
- **More or fewer articles:** change `max_items` per section.
- **Change the time:** edit the `cron` line in `.github/workflows/daily_digest.yml` (it's in UTC; India is UTC+5:30).
- **Concept topics:** edit `CONCEPTS` in `feeds.py`.

Note: GitHub's scheduled runs can start 5–20 minutes late when its servers are busy. That's normal.
