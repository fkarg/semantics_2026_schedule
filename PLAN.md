# Local SEMANTiCS programme

Build a static, offline-readable programme in this folder. Native anchors link to
individual session and talk HTML pages; separate native details elements reveal
abstracts inline. Use a dense time-by-room table, with day, room and text filters.
Default to the first day, retaining an all-days link. Pin room headers, the time
column, and the current interval label inside long rows when scrolling.
Use the official workbook for times and rooms. Import descriptions from the
same public documents used by the conference website, keeping provenance and
explicitly noting outdated document times. Viewing needs no dependencies/server.

Implementation sequence:
- [x] Cache the public workbook, linked DOCX documents, and workshop descriptions.
- [x] Test that extraction preserves sessions, talks, merged cells and abstracts.
- [x] Implement import/build in Python; generate index, session and talk pages.
- [x] Add responsive CSS and optional client-side filters without link interception.
- [x] Verify generated links, offline viewing, new tabs, expansions and filtering
      in Chromium; review and document opening/refreshing the copy.

No worktree, deployment, backend, or git repository is required. Implementation
stays with the main agent; research and review can use independent agents.

Review record: the external peer attempt failed on sandbox network access; the
host retry was denied by automatic approval review because it could export local
source to an unverified model destination. A fresh internal GPT-6 reviewer was
used instead; this is not cross-model independence. Its first pass found a unique
defect (consecutive poster/demo labels were overwritten); fixed with regression
coverage. The timetable pass found another unique defect (detail breadcrumbs
omitted the day filter); fixed with a browser workflow regression test. It checked
all table column spans and source-room placements without additional findings.

The web-enabled research agent supplied official 39C3 Fahrplan and C3VOC sources;
its input changed the layout to a session-interval table. This preserves truthful
timing while allowing inline abstracts to expand rows, rather than pretending to
have precise individual talk times or a proportional time scale.

## Browser favourites

Baseline saved as Git commit 01823b6 before this feature. Add a star toggle to
each programme session heading, selecting the whole session block. Keep controls
on the overview so file:// storage need not be shared with separate detail files.
Store one localStorage key per session to avoid losing unrelated selections from
another tab; reread on storage events and focus. If storage fails, retain the
current page's selections and explicitly report that they cannot be saved.

- [x] Add browser workflow coverage for save/reload/day links, selected-only,
      multiple tabs and failed storage.
- [x] Add session star buttons, selected-only filter, persistence and styles.
- [x] Rebuild, run data and browser checks, review the diff and commit.

Internal GPT-6 Astra review found no blocking defect after checking key uniqueness,
row-independent identities, cross-tab writes, storage failures, table structure and
navigation. Outcome: added verification, making its coordinate-change check an
automated regression test. External guidance confirmed file:// storage is browser
dependent; real Chrome workflow checks cover reload, restart and cross-tab use.

Selected-view refinement: remove unused room columns per day, neutralise filtered
cell backgrounds, recompute shared colspans and restore original coordinates when
returning to the full programme. Shared-only days use one Shared events column.
Internal GPT-6 Astra delta review found no alignment/reversibility defect; outcome:
added verification for a partial shared span disjoint from selected room columns.

Room/time readability: replace session-category colours with a fixed seven-room
palette keyed by room name, shared by headers and event cells. Keep shared and
filtered-empty cells neutral. Preserve all published time rows in displayed days;
rows with no matching sessions shrink to 22px rather than disappearing.

Shared schedule context: room-spanning events have no star and bypass the
selected-only restriction while respecting day/search filters. They remain visible
without any favourites; the empty-selection notice still refers to selectable
sessions. Existing saved session keys remain unchanged. Verify generation, shared
visibility/counts, compact spans, and persistence in the browser workflow.
Internal GPT-6 Astra read-only review traced nullable star access, selection counts,
filter predicates, all 19 shared entries/partial spans, and layout restoration.
No defects found; outcome: no decision impact. All 11 unit tests and both Chrome
workflows passed, including an actual formerly selectable lunch storage key.

## Phone layout and GitHub Pages

Keep the existing static timetable and native links. On phone widths, enlarge
text and touch targets, show roughly one readable room plus the sticky time axis,
and keep shared-row text within the viewport. Room filtering should collapse
unrelated columns using the existing span-preservation logic. Keep desktop density.
Publish the committed site/ artifact through GitHub Pages Actions on main pushes.
No accounts/backend or cross-device favourite syncing are introduced.

- [x] Add mobile workflow coverage at 320/390px for touch controls, readable shared
      rows after horizontal scrolling, room filtering, details, selection/reload.
- [x] Update CSS and room-filter layout, rebuild and run existing/browser checks.
- [x] Add the official Pages workflow, inspect the user-created origin and Pages
      settings, push, follow Actions, and verify the live nested detail URLs.

Official GitHub guidance confirmed the static artifact workflow action versions;
W3C reflow guidance supports keeping the timetable inside its own scroll area.
Mobile viewport sizing uses svh per WebKit guidance, and shared content sticks
beside the time axis. Research outcome: informed viewport sizing and deployment.
Internal GPT-6 review checked sticky geometry, partial spans/restoration, nested
Pages links and workflow permissions. No defect; outcome: no decision impact.
Chrome emulation passed at 320/390px, including HTTP subpaths and favourites.
Safari/WebKit remains unverified. Desktop/offline workflows and 11 unit tests pass.

Published at https://www.fkarg.me/semantics_2026_schedule/ (the github.io project
URL redirects to the existing account domain). HTTPS enforced. Deployment run
34945979199 passed. A fresh phone-sized Chrome profile verified the live redirect,
exact CSS snapshot, favourites/reload, shared lunch, and nested talk detail URL.

## Live current-time marker

Use Europe/Brussels time and update every 15 seconds plus focus/page visibility.
Match today's published interval (inclusive start, exclusive end), position a red
line proportionally within that rendered row and show Now HH:MM in the time axis.
CSS percentages keep geometry correct through filtering, resize and disclosures.
No autoscroll. Outside programme intervals/dates hide the marker. For the dinner
without a published end, hold the marker at the row start until the day ends.
Verify using a controlled browser clock in a different device timezone, including
slot transitions, compact rows, expanded abstracts, date changes and live ticks.

Internal GPT-6 Astra review found no blocking issue after checking filtering,
expanded heights, sticky layering, interval boundaries and dinner/midnight.
Outcome: added verification of red pseudo-elements and a horizontally scrolled
mobile marker inside the viewport. Clock-controlled tests and all existing unit,
favourites, phone and browser workflows passed. Publish via the existing Pages
workflow and verify its result.

## Selected-session calendar export

Download a snapshot `.ics` of every currently starred session across all days,
independent of view filters. One event per session includes the published start/end,
room, title, chair, session description/notes, all talk titles/speakers/abstracts,
and absolute hosted detail/source links. Shared events are not exported. Generate
structured metadata offline in build.py, converting Europe/Brussels to UTC there;
serialize selected metadata in the browser without requests or new dependencies.
Use stable favourite-based UIDs, CRLF, TEXT escaping and UTF-8 byte-aware folding.
Disable export when nothing is selected; label the all-days scope beside it.
Google documents desktop Settings → Import & export; this does not synchronize
future selection changes. Source: https://support.google.com/calendar/answer/37118
and RFC 5545 https://www.rfc-editor.org/rfc/rfc5545.html.

- [x] Add browser download tests for all-days selection despite filters, full
      details, correct UTC times, stable UIDs, escaping/folding and mobile widths.
- [x] Generate calendar metadata, add the download control/serializer and rebuild.
- [x] Run export, unit, favourites and mobile workflows; review and document.
- [ ] Commit, push, follow Pages deployment and verify published export assets.

Internal GPT-6 Astra review attempted to falsify interval validity, filter
independence, memory-only/cross-tab state, text escaping/folding and metadata
fidelity. No defects found. Outcome: added HTTP touch-download verification.
All 11 unit tests and calendar, favourites, mobile and live-marker workflows pass.
The calendar test checks all 47 selectable sessions fit under Google's 1 MB limit,
as well as full abstracts, stable UIDs, exact UTC intervals, multiline Unicode
round-tripping, native downloads at 320/390/1440px, and empty-selection disabling.
Actual Google-account import and Safari remain untested.
