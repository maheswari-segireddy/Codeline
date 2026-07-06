# Codeline — B.Tech CS Learning Agent

An agentic study companion covering **Python, Java, DBMS, Data Structures & Algorithms,
and Operating Systems** — built for Kaggle's AI Agents competition (Agents for Good,
education). Pure Python, one file, no Docker.

For every topic, the agent can:
- **Teach** — generate concise study notes on demand (overview, key concepts, a code
  example, common mistakes), so it's not just a quiz bank.
- **Practice adaptively** — run a visible **diagnose → plan → generate → adapt** loop:
  diagnose gaps with a quick quiz, plan what to focus on, generate a fresh question
  targeting the weakest subskill, then grade the answer and adjust difficulty and
  mastery in real time.

The sidebar shows the agent's reasoning at each step, plus live mastery bars.

## Run it locally

```bash
pip install -r requirements.txt

mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and paste your free key from
# https://aistudio.google.com/apikey

streamlit run app.py
```

Opens at **http://localhost:8501**.

## Deploy it (free, no Docker)

**Streamlit Community Cloud:**

1. Push this folder to a GitHub repo (`.streamlit/secrets.toml` is gitignored, so your
   key stays local and never gets committed).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. Click **New app**, pick your repo, set the main file to `app.py`.
4. Under **Advanced settings → Secrets**, paste:
   ```
   GEMINI_API_KEY = "your-google-ai-studio-key-here"
   ```
5. Click **Deploy**. You'll get a public `yourapp.streamlit.app` URL in about a minute.

## Adding more subjects or topics

Everything is data-driven from the `SUBJECTS` dictionary at the top of `app.py`. To add
a new subject or topic, add an entry in the same shape:

```python
"c_programming": {
    "name": "C programming",
    "icon": "\u2699\ufe0f",
    "topics": {
        "pointers": {
            "name": "Pointers",
            "subskills": ["Pointer basics", "Pointer arithmetic", "Pointers & arrays", "Function pointers"],
        },
    },
},
```

The agent generates notes and questions for whatever subskills you list — no manual
content-writing required.

## Notes for your Kaggle submission

- The sidebar's "agent trail" is the clearest evidence of agentic decision-making —
  point judges to it.
- `MODEL_ID` defaults to `gemini-2.5-flash`. Override via env var or Streamlit secret
  if you want a different Gemini model (check https://aistudio.google.com for current
  options and free-tier limits).
- Progress saves to local JSON files under `progress/`, one per subject+topic. On
  Streamlit Community Cloud's free tier the filesystem can reset on redeploys/sleep —
  fine for a judged demo, not meant for production multi-user persistence.
