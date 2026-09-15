"""Current-time marker: Ghent timezone, live updates, geometry and filtering."""
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

URL = (Path(__file__).resolve().parents[1] / 'site/index.html').as_uri() + '?day=all'

def set_time(page, instant):
    page.clock.set_system_time(datetime.fromisoformat(instant))
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(timezone_id='America/Los_Angeles', offline=True)
    page = context.new_page()
    page.clock.install(time=datetime.fromisoformat('2026-09-15T08:10:00+00:00'))
    page.clock.pause_at(datetime.fromisoformat('2026-09-15T08:10:00+00:00'))
    page.goto(URL)
    marker = page.locator('.now-label:visible')
    expect(marker).to_have_text('Now 10:10')
    row = page.locator('.time-group.is-now')
    expect(row.locator('.time-label')).to_have_text('10:00–10:20')
    assert row.evaluate('(el) => el.style.getPropertyValue("--now-position")') == '50%'
    page.clock.run_for(60000)
    expect(marker).to_have_text('Now 10:11')
    assert abs(float(row.evaluate('(el) => el.style.getPropertyValue("--now-position")').rstrip('%')) - 55) < .01
    # A boundary belongs only to the next slot.
    set_time(page, '2026-09-15T08:20:00+00:00')
    expect(page.locator('.time-group.is-now')).to_have_count(1)
    expect(row.locator('.time-label')).to_have_text('10:20–11:50')
    set_time(page, '2026-09-15T09:05:00+00:00')
    # Marker follows row height after an abstract expands, without JS measuring layout.
    detail = page.locator('[id="2026-09-15-c6"] details').first
    detail.locator('summary').click()
    box = row.bounding_box()
    assert abs(marker.bounding_box()['y'] + marker.bounding_box()['height'] - (box['y'] + box['height']/2)) < 3
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#selected-only').check()
    assert 'empty-slot' in row.get_attribute('class')
    expect(marker).to_have_text('Now 11:05')
    assert row.bounding_box()['height'] <= 30
    # Line is present across visible cells and never intercepts touch/clicks.
    for cell in row.locator('th:visible, td:visible').all():
        assert cell.evaluate("el => { const s = getComputedStyle(el, '::after'); return s.height === '2px' && s.backgroundColor === 'rgb(198, 40, 40)' && s.pointerEvents === 'none'; }")
    page.locator('#selected-only').uncheck()
    wrapper = page.locator('.day[data-day="2026-09-15"] .timetable-wrap')
    wrapper.evaluate('(el, y) => { el.scrollTop = y - 80; el.scrollLeft = 400; }', row.evaluate('(el) => el.offsetTop + el.offsetHeight / 2 - 100'))
    assert abs(marker.bounding_box()['x'] - row.locator('.time-cell').bounding_box()['x'] - 68) < 2
    assert marker.bounding_box()['y'] > wrapper.bounding_box()['y'] + 44
    assert marker.bounding_box()['y'] + marker.bounding_box()['height'] < wrapper.bounding_box()['y'] + wrapper.bounding_box()['height']
    page.screenshot(path='/tmp/semantics-now-mobile.png')
    page.locator('.days a[data-day="2026-09-16"]').click()
    expect(marker).to_have_count(0)
    page.goto(URL)
    for instant in ('2026-09-15T05:59:00+00:00', '2026-09-15T16:30:00+00:00', '2026-09-16T16:30:00+00:00', '2026-09-18T08:00:00+00:00'):
        set_time(page, instant)
        expect(page.locator('.time-group.is-now')).to_have_count(0)
    # Dinner has no published end: mark its start, do not invent a duration.
    set_time(page, '2026-09-16T17:30:00+00:00')
    expect(marker).to_have_text('Now 19:30')
    expect(row.locator('.time-label')).to_have_text('19:00 –')
    assert row.evaluate('(el) => el.style.getPropertyValue("--now-position")') == '0%'
    set_time(page, '2026-09-16T22:00:00+00:00')
    expect(page.locator('.time-group.is-now')).to_have_count(0)
    browser.close()
print('Now marker checks passed: Ghent timezone, timer, boundaries, expansion, compact slots, dates and open-ended dinner.')
