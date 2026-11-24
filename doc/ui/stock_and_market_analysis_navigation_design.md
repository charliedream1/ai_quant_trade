# Stock and Market Analysis Navigation

Date 2026-11-23 (UTC+08:00). Approved and implemented.

## Navigation

The **Market Research** sidebar has two entries. **Market Analysis** opens by
default on **Quotes and Sectors**. **Stock Analysis** opens on **Fundamentals**
with a shared market and security selector above the tabs. Dedicated links
open their specified tab. When users switch between the two entries within the
same browser tab, each page restores its last active tab.

Both pages use the same layout. The page header shows the current market, the
relevant filters and the actions for the selected tab. A single row of tabs
below the header switches the research view. On narrow screens, the row scrolls
horizontally and keeps the selected tab in view. Tabs can be operated with the
keyboard, and their selection is indicated by text and state as well as color.

### Stock Analysis

All six tabs share the selected market and security. The page header displays
the security code and name when resolved. Tabs can keep their own settings,
such as chart period and financial reporting period.

| Tab | Existing content and actions |
| --- | --- |
| Fundamentals | Company profile, industry and available valuation fields, with source and quote time. |
| Technical | Price and volume, indicator explanations and available benchmark comparisons. |
| Financials | Statements, profitability, cash flow, history and peer comparisons where available. |
| News and Disclosures | Company-specific news, research reports and available issuer disclosures. |
| Relationships | Saved relationships, rule-based and CLI-assisted construction, progress, evidence and export for the selected security. |
| Events and Risk | Historical announcement dates from sourced statements, volatility, drawdown and liquidity measures where available. |

The **Relationships** tab includes the full existing graph workflow. The
selected security populates both graph modes, saved runs are filtered by
market and security, and graph history shows its as-of date. The page opens
on the rule-based graph view unless a saved navigation preference or deep link
selects the other mode. The user starts graph construction explicitly.

### Market Analysis

Market Analysis shares the market selection between its five tabs. Each tab
keeps its own data scope and filters.

| Tab | Existing content and actions |
| --- | --- |
| Quotes and Sectors | Major indices, industry and concept rankings, gainers and decliners, sector charts and watchlist quotes. |
| Macroeconomics | Economic releases, historical series, color scales and dated source information. |
| Market News | Market-relevant domestic and overseas news, finance and policy filters, and keyword strength using the same filtered corpus. |
| Screening and Validation | The existing stock recommendation, candidate comparison and backtest workflow. Use compact in-content controls for these three steps. |
| Resource Pools | Create and import universes, inspect membership, and screen a selected pool with the existing strategy workflow. |

Screening can open a selected candidate in Stock Analysis with its market and
security carried over. Returning to Screening restores the user's filters and
candidate selection. Resource pools can feed the screening universe. Factor
research and monitoring retain their destination under **Strategy Construction**.

## Loading and report context

- Mount the page header and the selected tab first. Fetch data for the active
  tab; run independent reads in parallel where provider limits and existing
  cache policy allow. Render each section when it is ready, with its source,
  observation time and loading state. The Quotes and Sectors tab can show the
  existing timestamped snapshot while the current data refreshes.
- Scope transient work to the browser window, active tab, market and security
  or filters. Cancel in-flight tab work when its scope changes. Completed
  results can be reused when the scope matches. Explicit durable tasks follow
  their existing lifecycle. The display checks the current scope before
  applying a result.
- Place the tab's rule-data action and **Analyze with AI** together in the
  page header where that tab supports them. Regular data loading can begin on
  entry. A model run begins when the user submits the analysis. The report and
  floating assistant identify the active page, tab and security or filters and
  use matching server-side evidence. Use existing report history, cancellation
  and HTML preview and download. The Relationships tab uses its dedicated
  rule and model graph workflow.

## Route migration

Use stable page and tab identifiers independent of the display language.
Navigation, direct links and browser Back and Forward use the same route
mapping. Links carry the relevant existing market and security context when
available. Preserve report and saved result identifiers where linked, and
resolve valid saved results in their appropriate tab. Optional market and
security state added to links should use the existing validation boundaries.

| Existing market view | Destination |
| --- | --- |
| Quotes | Market Analysis / Quotes and Sectors |
| Macro | Market Analysis / Macroeconomics |
| News | Market Analysis / Market News |
| Recommendations | Market Analysis / Screening and Validation |
| Resources | Market Analysis / Resource Pools |
| Stock | Stock Analysis / Fundamentals, or the requested valid stock tab |
| Fundamentals | Stock Analysis / Financials |
| Relations | Stock Analysis / Relationships |
| Factors | Strategy Construction / Factor Research and Monitoring |

## Implementation and acceptance

1. Update the market navigation registry, route aliases and labels. Move the
   existing panels into the two pages, using their current data and action
   contracts. Use separate rendering entry points for sections where lazy
   activation requires them.
2. Bind tab switches, symbol changes, report evidence and floating assistant
   context to the same active page state. Route the recommendation and
   relationship shortcuts through this state.
3. Test direct and legacy URLs, browser history, desktop and mobile, keyboard
   navigation and Chinese and English labels. Walk through every current
   function, including rule and CLI graph progress, cancellation and export,
   screening through backtest, and report preview and download.
4. In a browser trace, compare first usable controls and first results with
   the current workspace. With one source stalled, confirm that switching tabs
   keeps controls usable, stops the abandoned request and prevents old results
   from appearing in the active tab. Verify request counts for unopened tabs
   and restore a completed tab under its matching market and security.
5. Synchronize the market research and navigation guides and record the
   validation in the weekly changelog.

## Validation results

The controlled Conda Chromium probe used the same quotes link and seeded
data before and after the route change. The quote controls became usable
after 11.50 seconds on the previous revision and 6.19 seconds on the updated
workspace. The first rendered sector chart appeared after 38.63 and 25.06
seconds, respectively. These are single runs with local test observations.

Browser acceptance exercised legacy financial and relationship links, keyboard
tab selection, history restoration, independent page cancellation, candidate
selection and return, rule graph export, CLI graph progress, and report preview
and download. The financial view uses a statement selector and renders one
detail table from the loaded snapshot. This resolved the Conda browser stall
when selecting the cash flow view inside the grouped workspace.
