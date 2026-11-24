# Market Research Workspace Optimization Plan

Date 2026-11-24 (UTC+08:00). Approved and implemented.

The workspace has two research pages and eleven tabs. The browser review of
the workspace changes recorded in commit `3b0c7ac` verified the main data, graph, screening and reporting
workflows with controlled inputs. It identified three regressions that affect
which page or security the user sees. Address those first, then simplify the
individual workflows. [Browser acceptance review](stock_and_market_analysis_acceptance_review.md)

## 1. Page visibility and route selection

The DOM captured in Conda Chromium lacked the two group identifiers used by the
visibility rules. Both research sections could appear even when the route
correctly identified Stock Analysis. The security input began at approximately
751 pixels on the desktop view and 974 pixels in the narrow view.

Use an explicit page container with a rendered identity in both supported
Gradio environments. Apply the resolved route before showing the page.
Keep the shared header immediately followed by the selected page's tab bar
and content. Preserve completed results and form values when a user returns
to the same scope. Dispatch remote reads only for the selected page and tab
under the existing worker and cancellation policy.

Use one stable tab mapping for sidebar selection, keyboard navigation, deep
links, legacy aliases, and browser Back and Forward. Keep all research tabs
reachable in a horizontally scrollable strip at narrow widths. Bring the active
tab into view. Use the same mapping in the embedded and standalone views.

**Acceptance.** At 1,500 by 1,000 pixels and 390 by 844 pixels, only the
selected research page contributes visible content or keyboard focus. On a
direct stock link, the security field and selected tab appear within the first
screen without scrolling. Test all eleven canonical destinations and existing
market links, including Resources on narrow screens, in both interface
languages. Reload and use Back and Forward with a non-default tab. Confirm the
network trace contains no background request from an unopened tab.

## 2. Security identity and asynchronous results

The browser reproduced a previous company name after editing the code and
switching tabs immediately. Use one committed security identity for the
market, normalized code and resolved name. As soon as the user applies a new
selection, replace the old heading with the new code and its resolving state.
Use the selected market and a new request revision for the heading, tab data,
graph runs, AI report evidence and floating assistant context.

Discard responses from previous selections and use page-owned cancellation
for transient requests. Attach every reusable result to the same market,
security, tab and relevant filters. Errors and unsupported markets get a
scoped, readable status. Completed report and accepted task records retain
their original research scope.

**Acceptance.** Load 600519, delay a read, switch to 600036 and immediately
visit another tab. Check the heading, visible data, export and AI evidence,
then return and replay the late 600519 response. Repeat with keyboard input,
paste, two browser windows, browser history and an A-share to Hong Kong market
change. The new scope remains consistent even if the previous worker finishes
later.

## 3. Tab workflows and layout

Use one primary data action in each eligible tab. Group it with **Analyze with
AI** where supported. Keep the selected market or security, data timestamp,
source availability and progress near the results. Render named loading,
empty and retry states. Use existing report generation, governed inputs and
HTML export through the current page scope.

| Page and tab | Proposed adjustment | Acceptance |
| --- | --- | --- |
| Market / Quotes and Sectors | Keep one refresh action, preserve timestamped rows during a refresh and replace placeholder grids and charts with named states. | Indices, sectors and charts update as their own results arrive. A failed sector source leaves already loaded indices readable. |
| Market / Macroeconomics | Put rule data and AI at the top. Put alternate report settings and report history in the report panel. | Rule data and AI generation can be exercised independently. A report records the displayed series and dates. |
| Market / Market News | Open details by selecting a story. Use readable columns for title, source and publication time. | Selecting a row opens its details and source link. Geographic and topic filters continue to update both the list and keyword chart. |
| Market / Resource Pools | Use a named pool selector. Select a new pool immediately after creation and group file validation with import. | Create a pool, preview a CSV, confirm import and view its members without copying an identifier. |
| Market / Screening and Validation | Place named pool and strategy selectors beside the workflow. Display submission stages and show the assigned backtest identifier when available. | Load a pool, select a candidate, return with filters restored, compare candidates and finish a backtest. While waiting, the visible state describes the task stage. |
| Stock / Fundamentals | Show the resolved company, sector, market and valuation summary near the header. | A change of security updates the source, timestamp and displayed identity together. |
| Stock / Technical | Put the price chart and concise indicator interpretation before auxiliary actions. | The chart and its controls are visible before watchlist management. Indicator values use the chart's selected period. |
| Stock / Financials | Keep one statement selector and consistent data and report actions. Put source details and historical comparisons below the main statement. | Cash flow and other statements use the same snapshot. Changing the security clears the previous statement context promptly. |
| Stock / News and Disclosures | Label company news, research and issuer filings individually, with coverage and source labels. | An issuer filing has traceable source evidence. A market without a filing feed shows the coverage gap while other company news remains usable. |
| Stock / Relationships | Prioritize current status and graph preview. Group run history, evidence and exports near the result. | Rules and CLI mode both use the selected security. Progress, cancellation and the graph export work from the visible result. |
| Stock / Events and Risk | Give historical disclosures and risk metrics separate visual groups. Show observation period, units and readable precision. | Dates retain their source. Volatility and drawdown use a verifiable series and state the measured interval. |

## Delivery and verification

Implement and verify phases 1 and 2 together before changing the tab-level
layout. Then review each of the eleven tabs against the table above. Add
targeted browser regressions for the reproduced failures and reuse the
existing graph, report, chart and screening scenarios. Capture the first
usable control, first displayed result, duplicate request count and time to
cancel a deliberately stalled read. Measure with the same fixtures as the
previous review in each environment. Record browser and source time
separately.

Run the Windows project and Conda browser suites, the applicable Linux
regressions, Ruff, mypy, both strict documentation builds and the publication
secret scan. Update the usage guide, design and weekly changelog with the
observed results. Stop the test services and keep local test artifacts on E.

## Implementation and acceptance notes

The browser renders each research page inside a stable container and uses an
accessible scrollable tab strip. The Conda and project browser checks covered
the narrow legacy resource-pool link, first-screen security field and rapid
symbol change. The previous result is hidden while the reset is applied and
the report and assistant context follow the active page revision.

Controlled browser checks exercised financial statements, macro reports,
resource-pool import, candidate selection, screening comparison and a
completed backtest. News rows open the article and original link directly.
Issuer filing coverage is described in the disclosure view. Financial
announcement dates remain available through Events and Risk where the
existing source supplies them.

Windows was tested in both the project and Conda environments. Local Linux
browser validation was blocked by unavailable WSL virtualization.
Dependency audits reported advisories in the repository's existing pins.

In one serial Conda Chromium comparison using the seeded quote fixture, the
previous commit exposed the controls at 7.86 seconds and the first sector
chart at 38.91 seconds. The updated page exposed them at 11.08 and 42.51
seconds. These measurements identify a remaining cold-entry cost under the
test conditions.

## Cold-entry follow-up

The initial browser layout mounted the contents of all eleven research tabs.
The accessible tab strip now selects the corresponding Gradio panel. Gradio
mounts the contents on first selection and keeps the visited panel's state
available for return navigation. Stable route identifiers still select the
destination at narrow widths and from legacy links.

The quote worker now loads a dedicated index and sector adapter. The adapter
shares the existing table scales and chart styling. It retains the completed
tables for the final response after publishing each one independently. The
worker keeps the same source deadlines, cache scope and page cancellation.

| Conda Chromium seeded quote probe | Prior workspace | Optimized workspace |
| --- | ---: | ---: |
| Refresh controls available | 9.01 s | 8.52 s |
| First sector chart from navigation | 34.77 s | 17.27 s |
| Worker execution recorded in logs | 21.4 s | 4.8 s |
| Mounted research panels with controls | 11 | 2 |
| DOM elements at the first controls | 3,286 | 1,060 |

These are single cold runs using the same seeded workload. Browser navigation
and server startup varied between runs. Regression checks exercise route
restoration, symbol changes, candidate return, rule-data partial delivery,
sector errors, graph cancellation and AI report export.
