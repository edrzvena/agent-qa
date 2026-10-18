# agent-qa

A QA agent for web apps. You give it a URL. It opens the site in a real browser, clicks around, fills in forms, and writes up the bugs it finds, with steps to reproduce, a screenshot, and the relevant logs.

It uses Claude (Anthropic API, tool use) for the thinking and Playwright for the browser. Python only.

> **Status: in development.** Only the settings loader is done so far. Everything below describes what the project is being built to do. Sections marked *(planned)* do not work yet. The eval results table stays empty until the benchmark has actually been run.

## Why I built this

I'm a web developer, and most small projects get no real QA. Scripted end-to-end tests only check what you already thought to check. I wanted to see how far an LLM agent can get when it just uses the app like a person would, and I wanted to measure that honestly instead of showing one cherry-picked demo.

That second part drives the design. The repo includes a small shop app with 12 bugs planted on purpose, and an eval that counts how many of them the agent finds and how many false alarms it raises.

## How it works

Bugs get found two different ways, because they are two different problems.

**1. Technical errors: a passive detector, no LLM.**
While the browser runs, a listener records every console error, every failed request (status 400 and up), every page crash, and every JavaScript `alert`/`confirm` dialog. This costs nothing in tokens and it can't forget to look. If the app throws a 500, it gets logged whether or not the agent notices.

**2. Functional bugs: the agent decides.**
Some bugs produce no error at all. A cart total that ignores quantity returns a perfectly healthy 200. Only something that understands what the page is supposed to do can notice. That's the LLM's job.

The agent runs a loop:

```
get page state -> Claude picks a tool -> run it in the browser -> new page state -> repeat
```

It stops when it calls `finish`, hits the step limit, hits the cost limit, or gets stuck repeating itself.

### Tools the agent can call

| Tool | What it does |
|---|---|
| `goto(url)` | Open a page |
| `click(selector)` | Click an element |
| `fill(selector, text)` | Type into an input |
| `get_page_state()` | Return the URL, title, visible text, and a numbered list of clickable/typeable elements |
| `report_bug(title, steps, actual, expected)` | Record a bug. All four fields are required |
| `finish()` | End the run |

The agent never sees raw HTML. `get_page_state` returns trimmed text and a list of interactive elements, which keeps each step cheap and keeps the model from getting lost in markup.

### Guarding against false alarms

An agent that cries wolf is useless, so reporting is strict:

- `report_bug` needs concrete steps, what actually happened, and what should have happened. The prompt tells the model not to report guesses.
- Screenshots and detector logs are attached by the code, not written by the model, so the evidence can't be made up.
- Duplicate reports get merged.

### Guarding against runaway runs

- Step limit (default 30).
- Cost limit per run in USD (default 1.00), computed from token usage.
- If the same action happens three times in a row, the agent is told to change approach. A fourth repeat ends the run.
- API errors (rate limit, overload) are retried with backoff. If they keep failing, you get a partial report marked `truncated`, not a crash.

## The benchmark app

`dummy_app/` is a small Flask shop with login, a product list (search and price filter), a cart, and checkout. Each of the 12 bugs can be switched on or off. The ground truth lives in `dummy_app/bugs.json`.

| ID | Type | Bug |
|---|---|---|
| B01 | technical | Clicking "Add to cart" on product 3 throws a JavaScript error |
| B02 | technical | `/api/products?page=2` returns 500 |
| B03 | technical | Product 5's image returns 404 |
| B04 | functional | Login accepts a wrong password |
| B05 | functional | Cart total ignores quantity when it is above 1 |
| B06 | functional | The max-price filter does nothing |
| B07 | functional | Checkout accepts an invalid email |
| B08 | functional | "Remove" doesn't remove the item |
| B09 | functional | Empty name at checkout shows no validation message |
| B10 | functional | Negative quantity is accepted in the cart |
| B11 | functional | Search is case-sensitive |
| B12 | functional | Logout leaves the session logged in |

### How the eval scores a run

The eval runs the agent against the app twice: once with all bugs on, once with all bugs off.

- **Recall:** with all bugs on, how many of the 12 did the agent report?
- **False positives:** with all bugs off, how many bugs did it report anyway? Every one is wrong by definition.

A report counts as finding a bug if it contains one of that bug's keywords (`match_any` in `bugs.json`). This is crude and deterministic on purpose: no second LLM grading the first one. The downside is that keyword matching can miss a correct report worded unusually, so recall may be slightly understated. The keywords are fixed before the first real run and are not tuned afterwards to improve the score.

Each configuration runs several times, because LLM runs vary. Results report the mean and the range, plus average cost and steps.

### Results

*Not run yet.* This table gets filled in from real runs.

| Setting | Runs | Recall (mean, range) | False positives per clean run | Avg cost per run | Avg steps |
|---|---|---|---|---|---|
| default model | - | - | - | - | - |

## Setup

Requires Python 3.11 or newer and an Anthropic API key.

```bash
git clone <repo-url>
cd agent-qa

python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -e ".[dev]"
playwright install chromium
```

Put your key in `.env` in the project root:

```
ANTHROPIC_API_KEY=your-key-here
```

`.env` is in `.gitignore`. `.env.example` is the empty template. Never commit a real key.

Optional settings, also read from `.env` or the environment:

| Variable | Default | Meaning |
|---|---|---|
| `AGENT_QA_MODEL` | `claude-sonnet-5-5` | Claude model used by the agent |

## Usage *(planned)*

Test any site:

```bash
agent-qa run https://example.com --max-steps 30 --max-cost 1.00
```

Options: `--model`, `--max-steps`, `--max-cost`, `--out DIR` (default `runs/<timestamp>/`), `--headed` to watch the browser.

Each run writes `report.html` and `report.json` to the output folder. If the key is missing or the URL can't be reached, the command exits with a short error message and no stack trace.

Run the benchmark:

```bash
agent-qa eval --runs 3
```

This calls the real API and costs money. It is not part of the normal test suite.

## Tests

```bash
pytest
```

The unit tests cover the settings loader, the dummy app, the detectors, the browser tools, the reporter, the agent loop, and the eval scoring. They never call the real API. The agent loop is tested with a scripted fake client that returns prepared tool-use responses, so the guards (step limit, cost cap, repeat detection, retries) are checked without spending anything.

Currently passing: the settings tests (4).

## Project layout

```
agent-qa/
  PRD.md                  what the project is and what counts as done
  docs/superpowers/plans/ implementation plan, task by task
  src/agent_qa/
    config.py             settings and .env loading            (done)
    models.py             BugReport, DetectorEvent             (planned)
    detectors.py          console/network/crash/dialog listeners (planned)
    browser.py            Playwright wrapper, the agent's tools  (planned)
    agent.py              Claude tool-use loop and guards      (planned)
    report.py             HTML and JSON reports                (planned)
    cli.py                the agent-qa command                 (planned)
  dummy_app/              Flask benchmark app + bugs.json      (planned)
  evals/                  benchmark harness and results        (planned)
  tests/
```

## Limitations

- **Only two kinds of bugs.** Technical errors and functional bugs. It does not check visual layout, mobile rendering, or accessibility.
- **It can't know your intent.** Without a spec, it judges "wrong" from common sense. A rule specific to your business, like "orders over 500 get free shipping", is invisible to it unless the page shows it.
- **Non-deterministic.** Two runs on the same app can find different bugs. That's why the eval repeats runs and reports a range.
- **It costs money.** Every run calls the API. The cost cap exists for this reason, but a run is not free.
- **Single browser, single user.** Chromium only, one session, no parallel runs.
- **Logins on external sites are not handled in v1.** The agent can fill a login form it finds, but there is no credential management.
- **Keyword-based scoring** can undercount correct reports, as described above.

## Roadmap

- Visual and layout checks, including mobile viewports
- Accessibility checks (missing alt text, labels, contrast)
- Turn a found bug into a replayable Playwright regression test
- Credential support for testing logged-in areas of external sites

## License

Not decided yet.
