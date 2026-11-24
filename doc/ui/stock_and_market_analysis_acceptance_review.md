# Stock and Market Analysis Acceptance Review

Date 2026-11-23 (UTC+08:00).

The grouping into market research and single-security research fits the two
workflows. The operator paths passed with controlled inputs, while the
workspace failed the first-screen and security-identity criteria. This review
covered the two pages and all eleven tabs in Chromium at widths of 1,500 and
390 pixels using Conda Python 3.11. Browser actions used an isolated service,
database and market fixtures. The report and graph checks used controlled
generation and inputs. The measurements apply to that environment.

| Page and tab | Design and interaction review | Observed result |
| --- | --- | --- |
| Market / Quotes and Sectors | Index and sector views belong together. Two visible refresh controls invoke the same action. Placeholder columns and blank plots need an initial state. | Refresh populated the chart. The report workflow captured the active rules and downloaded the saved HTML. |
| Market / Macroeconomics | The series picker belongs in market research. The three actions for loading data, page AI and the older model report need clearer placement and labels. | The report used scoped macro evidence and the HTML preview and download worked. |
| Market / Market News | Geography and topic are independently useful. Numeric news ID entry and internal field names interrupt reading. | Overseas finance filtering excluded unrelated articles. The keyword chart rendered eight positive bars from the same controlled corpus. |
| Market / Resource Pools | A shared collection belongs here. The flow asks the operator to copy a numeric ID into the import form. | Created a pool, previewed a two-security CSV, confirmed the import and verified both stored members. A narrow first load via the old resources link selected Quotes and Sectors. |
| Market / Screening and Validation | Recommendation, comparison and backtesting form one flow. Pool and strategy entries use numeric IDs. A pending task currently displays a zero ID. | Loaded the pool into screening, generated candidates, opened one company, returned to the existing list, ran candidate comparison and completed a backtest with a positive task identifier. |
| Stock / Fundamentals | The company identity should anchor the page. The displayed name can remain from the previous security after a fast edit and tab change. | Loaded the profile for 600519. On two checks the input changed to 600036 while the heading still showed the original company after changing tabs. |
| Stock / Technical | The chart and indicator explanations fit this tab. Trade-related auxiliary controls place the plot below the initial viewport in the measured layout. | Loaded the candlestick chart and verified RSI appeared in the indicator table. |
| Stock / Financials | One statement selector organizes the shared snapshot. Detailed financial and model report controls make the initial view longer. | Loaded a snapshot, switched to cash flow and verified the visible statement value. |
| Stock / News and Disclosures | The observed sources contain news and research reports. Issuer announcements need an explicit source or coverage marker to support the current title. | Loaded the company-specific news and research results with the common security selector. |
| Stock / Relationships | Combining rule and CLI graphs with the security selector makes sense. History, run identifiers and separate export controls take space above the graph. | Built and exported a rule graph, exercised CLI graph open, evidence, cancellation and export. Leaving a stalled financial read reached graph controls. |
| Stock / Events and Risk | Both are company-specific. Historical filing dates and calculated risk have separate actions. Display precision and the observation period could be clearer. | Loaded volatility, drawdown and turnover. Loaded historical announcement dates from the financial fixtures. |

## Release blockers

1. Both research sections can render in the same frame. The selected page
   state recorded Stock Analysis, while the document still showed Quotes and
   Sectors above it. The HTML omitted the two wrapper identifiers that the
   visibility rules target. On a desktop direct stock link, the security
   control started at about 751 pixels in the frame. At a width of 390 pixels
   it started at about 974 pixels and was below the viewport. A responsive
   pass requires the selected page alone and its header and tabs before the
   panels.
2. Editing the symbol and immediately changing tabs can retain the previous
   company name. The identity and results should reflect the same committed
   security. Acceptance should cover a quick edit and switch, a delayed read,
   returning to a cached tab and a change of market.
3. The old resource pool link selected its intended tab at 1,500 pixels and
   fell back to Quotes and Sectors at 390 pixels. The narrow tab bar moved
   entries to its overflow control before route selection. Verify all old
   links and explicit tab links at both widths with the correct content
   visible and the selected tab identifiable.

## Follow-up interaction checks

Give each tab one primary data action and an AI action where supported.
Keep read-only information, filters and actions in stable positions. Provide
explicit initial and empty states for grids and charts. Place strategy and
pool selectors next to the actions that consume them. Verify announcement
source coverage and label the evidence accordingly.

The audit recorded browser screenshots, selected-tab state and backend
confirmation for persisted pool members and the completed backtest. The
browser regression suite covered scoped report entry, cancellation, preview
and downloads. The application code was reviewed against the existing design.
