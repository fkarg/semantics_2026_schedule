"""Phone workflows against a static HTTP server, including a Pages-style subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{server.server_port}/site/index.html'

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        for width in (320, 390):
            context = browser.new_context(viewport={'width': width, 'height': 844}, is_mobile=True, has_touch=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(URL)
            expect(page.locator('.session:visible')).to_have_count(31)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            for selector in ('#search', '#room', '#clear', '#export-calendar', '.selected-filter', '.days a', '.favourite'):
                target = page.locator(selector + ':visible').first
                assert target.bounding_box()['height'] >= 44, selector
            assert page.locator('#search').evaluate('(el) => parseFloat(getComputedStyle(el).fontSize)') >= 16
            wrapper = page.locator('.day:visible .timetable-wrap')
            lunch = page.locator('[id="2026-09-15-b7"]')
            wrapper.evaluate('(el, y) => { el.scrollTop = y - 100; el.scrollLeft = 430; }', lunch.locator('xpath=ancestor::tr').evaluate('(el) => el.offsetTop'))
            text = lunch.locator('.session-title').bounding_box()
            assert text['x'] >= 60 and text['x'] + text['width'] <= width, text
            corner = page.locator('.day:visible thead .time-cell').bounding_box()
            bounds = wrapper.bounding_box()
            assert abs(corner['x'] - bounds['x'] - 1) < 2
            assert abs(corner['y'] - bounds['y'] - 1) < 2
            room_header = page.locator('.day:visible thead th').nth(3).bounding_box()
            assert abs(room_header['y'] - corner['y']) < 2
            page.locator('#room').select_option('Kraakhuis')
            expect(page.locator('.day:visible thead th:visible')).to_have_text(['Time · CEST', 'Kraakhuis'])
            assert wrapper.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
            star = page.locator('[id="2026-09-15-c6"] .favourite')
            star.tap()
            page.locator('#selected-only').check()
            page.reload()
            expect(star).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#selected-only')).to_be_checked()
            with page.expect_download() as pending:
                page.locator('#export-calendar').tap()
            calendar = Path(pending.value.path()).read_text().replace('\n ', '')
            assert calendar.count('BEGIN:VEVENT') == 1
            assert 'DTSTART:20260915T082000Z' in calendar
            assert 'SUMMARY:Trustworthy Knowledge Graph Systems and Infrastructure' in calendar
            expect(lunch).to_be_visible()
            details = page.locator('[id="2026-09-15-c6"] details').first
            details.locator('summary').tap()
            expect(details).to_have_attribute('open', '')
            page.screenshot(path=f'/tmp/semantics-phone-{width}.png')
            page.locator('[id="2026-09-15-c6"] .talk-title').first.tap()
            expect(page.locator('.detail-page h1')).to_be_visible()
            assert '/site/talks/' in page.url
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.get_by_role('link', name='Programme', exact=True).tap()
            expect(star).to_have_attribute('aria-pressed', 'true')
            assert not errors, errors
            context.close()
        browser.close()
finally:
    server.shutdown()
print('Phone checks passed: 320/390px, touch controls, sticky axes, shared rows, room filter, favourites, nested HTTP links.')
