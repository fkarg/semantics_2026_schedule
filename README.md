# SEMANTiCS 2026, locally

Open **[site/index.html](site/index.html)** in your browser. No server, installation,
or internet connection is needed to browse the saved programme and abstracts.

On this Mac:

```sh
open site/index.html
```

Talk and session titles are ordinary links: use Command/Ctrl-click, middle-click,
or the browser's “Open Link in New Tab”. “Abstract” expands details in place.
The timetable follows the CCC Congress Fahrplan's room/time comparison approach:
rooms stay in fixed columns in the full view and published session intervals form the rows.
Each room has one distinct colour, shared by its header and session cells across
all days and filtered views. Shared events and empty cells remain neutral.
Room headers stay pinned when scrolling down; the time column stays pinned when
scrolling right. Within a long session, its time range also sticks below the header.
Smaller screens scroll the table horizontally instead of stacking rooms into cards.
The first day opens by default; day links and an all-days view are available.
Search includes titles, speakers, abstracts and workshop descriptions. Day links
retain your search and room filter. Shared events remain visible for every room.

Click **☆** beside a session heading to favourite the whole session, including its
talks. Shared events (coffee, lunch, networking, etc.) have no stars and stay visible
in **Selected only**, alongside favourites within the current day/search/room filters;
choose **All days** to see selections across the conference. Uncheck it to browse
everything again. Selected-only hides unused room columns for each day and gives
empty cells a neutral background. Empty time slots stay visible as thin rows,
preserving the day's timeline. Shared events span the remaining rooms; days
with only shared events use one “Shared events” column. Switching back restores
the full room layout. Stars are saved in this browser and sync between programme tabs.
The star controls live on the timetable, not the separate detail pages.

Saving was verified in Chrome with the directly opened local file, including a
browser restart. Other browsers handle storage for `file:` URLs differently
([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)). Keep
using the same browser and file location; clearing browser data clears favourites.
If saving is blocked, the page says so and keeps selections for the open page only.
Changing a session's time or room during refresh creates a new selection identity.

The copy uses the official programme workbook for session times and rooms, and
the official linked documents for abstracts. Older times in those documents are
flagged on detail pages. Individual talk times are not supplied by the timetable;
the displayed time is the parent session's time. Unpublished abstracts are labeled.
Workshop pages include the supplied descriptions and external workshop links;
independent workshop websites are not mirrored. External source and meeting links
still require internet access.

## Refresh

Viewing needs no dependencies. Rebuilding uses Python 3.10+ and the two packages
in `requirements.txt` (already installed in `.venv` on this machine).

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python build.py --refresh
```

`--refresh` downloads public sources with `curl`, validates the imported programme,
and generates the site. Without `--refresh`, the existing snapshot is rebuilt
offline. The snapshot timestamp is recorded in `sources/snapshot.json` and shown
in each page's footer.

## Check

```sh
.venv/bin/python -m unittest -v test_programme.py
# Optional browser workflow test (Playwright is already installed locally):
uv pip install --python .venv/bin/python playwright
.venv/bin/python test_browser.py
.venv/bin/python test_favourites.py
```

Source: <https://2026-eu.semantics.cc/page/programme>. This is a personal local
reading copy, not an official conference website.

Layout reference: <https://fahrplan.events.ccc.de/congress/2025/fahrplan/>.
