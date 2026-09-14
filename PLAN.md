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
