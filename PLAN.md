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
