# Macroeconomic and Corporate Fundamentals Analysis

Approved on 2026-11-03. This document describes the implemented research boundaries and contains no implementation code. The previous model-interface work remains in the working tree.

## Purpose and existing gaps

The existing stock-detail provider exposes valuation and market-cap snapshots. Its technical and valuation score does not establish earnings quality. The existing Alpha regime workflow consumes imported point-in-time macroeconomic records; it does not provide a daily macroeconomic dashboard. Existing report headings and fundamental document roles do not create missing statement evidence.

This feature adds two views under Market Research: Macroeconomics and Fundamentals. The initial scope is Chinese macroeconomic series and A-share companies. Existing stock, market-review, Alpha and Agent workflows retain their established behavior. Unsupported markets receive an explicit capability error.

## Sources and immutable observations

Macro observations cover GDP cumulative year-on-year growth, CPI and PPI year-on-year changes, manufacturing PMI, M2 year-on-year growth, social financing increments, and one-year/five-year LPR. Each series retains its own unit, frequency and basis. GDP cumulative growth must not be presented as a single-quarter growth rate. Independent plot axes prevent comparisons across incompatible units.

The public-source adapter follows the field contracts inspected in the installed AKShare sources, while using bounded platform-controlled HTTP requests. Eastmoney supplies macro series, three financial-statement summaries and reported financial indicators. The MOFCOM economic data service supplies social financing. These are attributed to their actual upstream sources. Interface presence is not treated as proof of availability; live samples must be recorded separately.

Raw responses are content-addressed and retained with revision identifiers. Cache entries record refresh time and the earliest observation of that response revision. Derived research snapshots retain their source versions. Original publication times remain unknown where unavailable. Announcement dates retain day precision and do not imply an exact publication instant.

These current public revisions are not historically point-in-time eligible. Past announcement dates do not prove that the downloaded values are the originally announced values. Reports reject past dates that precede creation of the selected snapshot. Historical research still requires separately verified historical versions and availability evidence.

## Financial calculations and coverage

Financial records retain reporting period, currency, unit, cumulative or period-end basis and field provenance. The initial sources contain statement summaries, not a claim of complete filing coverage. Missing fields remain unknown.

Cumulative values convert to single-quarter values only when the preceding cumulative period exists in the same year. TTM requires four consecutive complete quarters. Year-on-year percentages require a positive comparable base; zero and negative bases receive explicit states and retain their original amounts. Cash-flow quality ratios use consolidated net profit where available, rather than mixing parent and consolidated scopes.

ROE and gross margin retain the provider's reported definitions. Reported weighted cumulative ROE is not annualized or replaced by a homemade equity ratio. Debt components with incomplete coverage remain a disclosed-component subtotal, never total interest-bearing debt. Financial institutions receive a specialized-method warning and do not receive generic industrial margin, ROE or interest-debt judgments.

Peer samples require the same industry and reporting period. The selected sample is recorded and does not represent the entire industry. Current PE/PB values retain their quotation timestamp and cannot establish historical valuation percentiles. Missing or simulated valuation data do not contaminate actual financial evidence.

Selecting a reporting endpoint limits the derived history and report evidence to that endpoint, including when reopening an older snapshot. Peer aliases resolve to a unique security before collection. Simulation markers survive source, comparison, snapshot and report boundaries; a mixed comparison remains explicitly simulated. Optional financial attachments to legacy stock reports require a compatible frozen snapshot or a current research date, and never attach a current revision to a historical report silently.

## Shared execution and presentation

REST, declarative CLI and Gradio use the same analysis service. Data fetches occur only after explicit user actions. The page can display observations and calculations without a model. Raw source snapshots, calculated values, scope, gaps, periods and immutable identifiers remain inspectable.

Optional macroeconomic and fundamental reports use the existing persisted report workflow. The new tasks use the ordinary shared model client, including OpenAI/LiteLLM selection and RPM controls. Structured model text is parsed through json_repair. Traditional textual ReAct is retained. Reports distinguish observed data from interpretations and do not invent policies, business segments, forecasts, target prices or orders.

Existing individual-stock reports may explicitly request financial-statement evidence. Navigation and report reopening reuse established UI components. No strategy score, portfolio weight or trading instruction changes automatically.

## Verification

Unit checks cover quarter conversion, TTM continuity, growth bases, missing values, financial institutions, currency, company identity, reporting dates, revisions, caching, network boundaries and snapshot integrity. Integration checks cover REST/CLI/UI, source attribution, report persistence and exact reuse of selected evidence. Browser acceptance checks both views and confirms that navigation performs no source fetch or model generation.

Live public-source acceptance records availability and latency separately from controlled fixtures. Model acceptance uses the user's selected free WorkBuddy Hy3 model. Windows is the local acceptance platform; portability is reviewed without claiming a Linux execution that did not occur.

Applicable Ruff, mypy, pytest, dependency and secret checks run after review. Existing security debt and unavailable scanners remain explicit. Documentation and code comments introduced by this feature use English. Test services stop after acceptance. Temporary files require explicit user approval before deletion.

## Reference contracts

- [AKShare Chinese macroeconomic interfaces](https://akshare.akfamily.xyz/data/macro/macro.html)
- [AKShare financial interfaces](https://akshare.akfamily.xyz/data/stock/stock.html)
- [Eastmoney macroeconomic data](https://data.eastmoney.com/cjsj/)
- [MOFCOM social financing increments](https://data.mofcom.gov.cn/gnmy/shrzgm.shtml)
