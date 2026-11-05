# Art in LA: Owner's Guide (no coding needed)

This explains, in plain language, what runs on its own, the one setup step
left, what it costs, and how to undo anything.

## 1. Your Anthropic API key (already set up)

**Update (Nov 5):** your repository already has an `ANTHROPIC_API_KEY`
secret, so the AI tier is live. On its first day it read 54 pages for $0.03.
The one recommended step left is a spend limit in the Anthropic Console
(step 2 below) as a second safety net. The steps below are kept for reference,
in case you ever need to replace the key.

About 40 venues have no machine-readable calendar. An AI reader (Claude Haiku)
reads their web pages instead. The same reader fills in exhibitions for 17
museums (LACMA, Hammer, Huntington, Autry, JANM…) and repairs listings when a
venue redesigns its site. It is switched off until you add the key.

1. Get a key at https://console.anthropic.com → **API Keys** → **Create Key**.
   Copy it (it starts with `sk-ant-`).
2. Optional but recommended: in the Console, go to **Billing → Spend limits**
   and set a monthly limit of **$10**. That is a second safety net on top of
   the site's own $3 cap.
3. Open https://github.com/birdofnofeather/art-in-la/settings/secrets/actions
4. Click **New repository secret**. Name: `ANTHROPIC_API_KEY`. Value: paste the
   key. Click **Add secret**.

That's it. The next nightly run (midnight LA time) uses it automatically. To
see it work right away: open the **Actions** tab → **Daily scrape** → **Run
workflow**.

## 2. What it costs

| Part | When it runs | Expected | Hard cap |
|---|---|---|---|
| AI page reader (Claude Haiku 5.5) | nightly, only for pages whose content changed | under $1/month | **$3/month**, after which it pauses until the 1st |
| AI scraper repair (Claude Sonnet 5.5) | only when a venue stays broken 4+ days despite the reader | $0 most months | **2 runs/month** (about $1–2 each) |

Spending is logged in `scrapers/state/llm_ledger.json`. To change the $3 cap,
edit `LLM_MONTHLY_BUDGET_USD` in `.github/workflows/daily-scrape.yml`. To turn
the AI off completely, delete the secret; everything else keeps working.

## 3. What runs without you

- **Nightly scrape** (about 07:00 UTC): reads every venue, applies the
  curation rules, and publishes. A safety gate refuses to publish if the
  results look broken, so yesterday's data stays live instead.
- **Self-healing, in two tiers:**
  1. If a venue's normal reader breaks, the AI reader takes over that same
     night.
  2. If it stays broken, a repair agent rewrites that one scraper. The fix is
     kept only if all automatic tests pass.
- **Alerts:** GitHub opens an issue titled "Scraper health alert" (you get an
  email) only when something is actually broken on our side, or when the run
  refused to publish. A venue whose own website is down is not counted as
  broken.
- **Freshness check** (a separate daily job): opens an issue if the site's data
  goes stale for more than 36 hours.

## 4. How to undo anything

Every change is a separate "commit" on GitHub, so anything can be reversed.

- **Undo one change:** open https://github.com/birdofnofeather/art-in-la/commits/main,
  find the change, and copy its 7-character code (for example `d21af2f`). Then
  ask Claude: *"Revert commit d21af2f in art-in-la and push to main."*
- **Go back to before this whole overhaul (Round 11):** the last commit before
  it is **`e8d514b`** (Nov 4, 2026). Ask Claude: *"Restore art-in-la to the
  state of commit e8d514b, keeping the newest scraped data, and push to main."*
- Round 11 commits, oldest first:
  - `4174edc` map tiles
  - `db20547` map framing
  - `7620dd2` venues and scrapers
  - `d21af2f` new filters and Art/Performing switch
  - later: docs and review fixes

## 5. Adding or removing a venue later

Ask Claude something like: *"Add [venue name] to art-in-la."* The checklist it
follows is in `CLAUDE.md`. In short:

1. Add the venue to `public/data/venues.json`, including whether it is art or
   performing arts.
2. Add one line to `scrapers/generic_venues.yaml`. Most venues need no code.
