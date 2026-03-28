# Polymarket Arbitrage Scanner — Copilot Instructions

Use the existing project as the source of truth.

## Project context
- This project scans Polymarket market data for potential mispricing opportunities.
- Python handles data fetching, parsing, and persistence.
- C++ handles the numerically sensitive pricing check.
- The README section "Why I Added a C++ Backend" is the tone anchor for the repository.

## Scope
- Rewrite comments, docstrings, Doxygen blocks, and README text when asked.
- Keep code behavior, logic, signatures, and control flow unchanged unless explicitly requested.
- Preserve Doxygen tags and documentation structure where present.

## Writing style
- Write like the builder of the project, not like an outside reviewer.
- Use plain technical English.
- Keep the voice thoughtful, direct, specific, believable, and human.
- Prefer causal explanations over polished summaries.
- State what was learned or why something mattered instead of using vague transitions like "based on that" or "as it evolved."
- Keep wording interview-defensible.

## Avoid
- AI-sounding phrasing
- inflated or overclaimed language
- abstract jargon when simpler wording is better
- textbook-style overexplanations
- claims about benchmarks, complexity, guarantees, or measured improvements unless they are explicitly supported by the code or README

## Comment guidance
- Comments should explain what a component does, why it exists, and any important assumptions.
- Keep comments close to the code they describe.
- Do not turn comments into blog posts.
- Prefer natural wording like "potential mispricing" over more abstract terms like "pricing anomaly" unless the code specifically uses that term.

## Workflow
- Prefer minimal churn.
- Work one file at a time.
- If I explicitly ask for automatic review, continue through the remaining files one by one without waiting for approval.
- Skip generated files, build artifacts, virtual environments, and cache folders.
- End automatic passes with a final summary of changed files and any risky wording.