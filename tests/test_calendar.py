"""Download contract: every starred session, full details, portable UTC iCalendar."""
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright, expect
from build import build_site

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = json.loads((ROOT / 'site/programme.json').read_text())
IDS = ['2026-09-15-c6', '2026-09-16-b6', '2026-09-17-c7']
HOST = 'https://www.fkarg.me/semantics_2026_schedule/'


def download_events(page):
    with page.expect_download() as pending:
        page.locator('#export-calendar').click()
    download = pending.value
    assert download.suggested_filename == 'semantics-2026-selected.ics'
    raw = Path(download.path()).read_bytes()
    assert len(raw) < 1_000_000
    assert raw.endswith(b'END:VCALENDAR\r\n')
    assert b'\n' not in raw.replace(b'\r\n', b'')
    for line in raw.split(b'\r\n'):
        assert len(line) <= 75, line
        line.decode('utf-8')  # Never split a multibyte codepoint at a fold.
    unfolded = raw.decode().replace('\r\n ', '')
    assert unfolded.startswith('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:')
    events = []
    for body in re.findall(r'BEGIN:VEVENT\r\n(.*?)END:VEVENT', unfolded, re.S):
        props = dict(line.split(':', 1) for line in body.strip().split('\r\n'))
        for name in ('SUMMARY', 'LOCATION', 'DESCRIPTION'):
            props[name] = re.sub(r'\\([nN,;\\])', lambda match: '\n' if match[1].lower() == 'n' else match[1], props[name])
        assert re.fullmatch(r'\d{8}T\d{6}Z', props['DTSTAMP'])
        events.append(props)
    return events


with sync_playwright() as p, TemporaryDirectory() as folder:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for width in (320, 390, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 900},
                                      timezone_id='America/Los_Angeles', offline=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((ROOT / 'site/index.html').as_uri() + '?day=all')
        export = page.locator('#export-calendar')
        expect(export).to_be_visible(timeout=1000)
        expect(export).to_be_disabled()
        for session_id in IDS:
            page.locator(f'[id="{session_id}"] .favourite').click()
        page.locator('.days a[data-day="2026-09-15"]').click()
        page.locator('#selected-only').check()
        page.locator('#room').select_option('Kabinet')
        page.locator('#search').fill('nothing-matches-this')
        expect(page.locator('#empty')).to_be_visible()
        events = download_events(page)
        assert len(events) == 3
        assert [(e['DTSTART'], e['DTEND']) for e in events] == [
            ('20260915T082000Z', '20260915T095000Z'),
            ('20260916T091500Z', '20260916T104000Z'),
            ('20260917T110000Z', '20260917T124000Z')]
        for event, session_id in zip(events, IDS):
            session = next(s for s in SESSIONS if s['id'] == session_id)
            assert event['SUMMARY'] == session['title']
            assert event['LOCATION'] == session['room'] + ', Ghent'
            assert event['URL'] == HOST + 'sessions/' + session_id + '.html'
            assert 'Chair: ' + session['chair'] in event['DESCRIPTION']
            for talk in session['talks']:
                assert talk['title'] in event['DESCRIPTION']
                assert talk['speaker'] in event['DESCRIPTION']
                if talk['abstract']:
                    assert talk['abstract'] in event['DESCRIPTION']
                assert HOST + 'talks/' + talk['id'] + '.html' in event['DESCRIPTION']
        assert [e['UID'] for e in download_events(page)] == [e['UID'] for e in events]
        assert len({e['UID'] for e in events}) == 3
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if width < 600:
            assert export.bounding_box()['height'] >= 44
        else:
            # The full programme must remain below Google's 1 MB import limit.
            # Seed this size-check fixture; star interactions are covered above.
            page.locator('.favourite').evaluate_all('''buttons => buttons.forEach(button =>
                localStorage.setItem('semantics2026:favourite:' + button.dataset.favouriteId, '1'))''')
            page.goto((ROOT / 'site/index.html').as_uri() + '?day=all')
            assert len(download_events(page)) == len([s for s in SESSIONS if s['room']])
        assert not errors, errors
        context.close()

    # Structured source fixture exercises text escaping and UTF-8 folding end to end.
    special = next(s for s in SESSIONS if s['id'] == IDS[0])
    special['title'] = 'Café 🧭, graphs; ' + 'é' * 80 + '\\ paths\nBEGIN:VEVENT'
    special['description'] = '<p>Workshop details &amp; discussion.</p>'
    special['notes'] = ['Bring a laptop; hands-on session.']
    build_site(SESSIONS, Path(folder), 'test snapshot')
    page = browser.new_page()
    page.goto((Path(folder) / 'index.html').as_uri())
    page.locator(f'[id="{IDS[0]}"] .favourite').click()
    events = download_events(page)
    assert len(events) == 1
    assert events[0]['SUMMARY'] == special['title']
    assert 'Workshop details & discussion.' in events[0]['DESCRIPTION']
    assert special['notes'][0] in events[0]['DESCRIPTION']
    browser.close()
print('Calendar checks passed: full details, all selections, UTC, stable IDs, escaping, folding, 320/390/1440px downloads.')
