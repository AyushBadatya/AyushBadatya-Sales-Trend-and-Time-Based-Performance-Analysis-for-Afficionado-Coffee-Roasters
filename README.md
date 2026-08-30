# ☕ Afficionado Coffee Roasters — Streamlit Dashboard

A live, interactive Streamlit web app covering:

- **Overall sales trend dashboard** — daily/monthly revenue & quantity trends with a 7-day moving average
- **Day-of-week performance charts** — average revenue/transactions by day, weekday vs weekend, basket size
- **Hourly demand heatmaps** — day-of-week × hour and product-category × hour heatmaps
- **Location comparison panels** — revenue by store, smoothed trends per store, peak-hour and traffic heatmaps

**Filters:** store location, day-of-week, hour-range slider, revenue-vs-quantity toggle, and an optional product-category filter.

> Note: the source CSV only contains a bare `year` column (no month/day). The app reconstructs real calendar
> dates by detecting where each store's transaction clock "resets" (a new business day starting), which
> recovers 181 real days (Jan 1 – Jun 30) and genuine day-of-week patterns — rather than collapsing every
> row onto one date, which is what a naive date fallback would do.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the printed `http://localhost:8501` link in Chrome.

## Get a free, public HTTPS link (Streamlit Community Cloud)

This is the fastest way to get a shareable `https://...streamlit.app` link that anyone can open in any browser — no server management needed.

1. **Create a GitHub repo** and push these files to it (`app.py`, `requirements.txt`, `.streamlit/config.toml`, and the `data/` folder with the CSV).
   ```bash
   git init
   git add .
   git commit -m "Coffee dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with your GitHub account.
3. Click **"New app"**, select your repository, branch `main`, and set the main file path to `app.py`.
4. Click **Deploy**. In 1–2 minutes you'll get a public link like:
   `https://<your-app-name>.streamlit.app`
5. Share that link — anyone can open it in Chrome (or any browser) with no login required.

Whenever you push new commits to the repo, the live app auto-updates.

## Alternative hosting

- **Hugging Face Spaces** (free): create a Space with the Streamlit SDK, upload these same files.
- **Render / Railway**: deploy as a web service using `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
