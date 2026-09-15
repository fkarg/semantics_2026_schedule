"""Browser contract: personal session selection persists independently of filtering."""
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
URL = (ROOT / 'site/index.html').as_uri()
ALL = URL + '?day=all'
FIRST = '[id="2026-09-16-b6"]'
SECOND = '[id="2026-09-17-c7"]'

with sync_playwright() as p, TemporaryDirectory() as profile:
    context = p.chromium.launch_persistent_context(profile, channel='chrome', headless=True)
    context.set_offline(True)
    page = context.pages[0]
    page.goto(ALL)
    # Previously saved Tuesday lunch must no longer count as a favourite.
    page.evaluate("localStorage.setItem('semantics2026:favourite:2550bea2c5e82e74', '1')")
    first = page.locator(FIRST + ' .favourite')
    expect(first).to_have_attribute('aria-pressed', 'false', timeout=1000)
    before = page.url
    first.click()
    assert page.url == before
    expect(first).to_have_attribute('aria-pressed', 'true')
    page.reload()
    expect(first).to_have_attribute('aria-pressed', 'true')
    page.locator('#selected-only').check()
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    expect(page.locator(FIRST)).to_be_visible()
    expect(page.locator(FIRST).locator('xpath=ancestor::td')).to_have_attribute('data-column', '0')
    expect(page.locator('[data-day="2026-09-16"] thead th:visible')).to_have_text(['Time · CEST', 'Concertzaal', 'Kraakhuis'])
    expect(page.locator('.session[data-room=""]:visible')).to_have_count(19)
    expect(page.locator('.session[data-room=""] .favourite')).to_have_count(0)
    expect(page.locator('#selected-count')).to_have_text('(1)')
    page.reload()
    expect(page.locator('#selected-only')).to_be_checked()
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    page.locator('.days a[data-day="2026-09-17"]').click()
    expect(page.locator('#selected-only')).to_be_checked()
    expect(page.locator('#empty')).to_be_visible()
    page.locator('.days a[data-day=""]').click()
    expect(first).to_have_attribute('aria-pressed', 'true')

    # Different tabs edit different keys, preserving each other's selections.
    other = context.new_page()
    other.goto(ALL)
    expect(other.locator(FIRST + ' .favourite')).to_have_attribute('aria-pressed', 'true')
    other.locator(SECOND + ' .favourite').click()
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(2)
    first.click()
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    expect(other.locator(FIRST + ' .favourite')).to_have_attribute('aria-pressed', 'false')
    expect(other.locator(SECOND + ' .favourite')).to_have_attribute('aria-pressed', 'true')
    # Search and room constraints still intersect with selected-only.
    page.locator('#search').fill('no-matching-session')
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#search').fill('')
    page.locator('#room').select_option('Kabinet')
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#room').select_option('Kraakhuis')
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    context.close()

    # Collapse unused rooms, neutralise hidden-event colours and resize shared spans.
    browser = p.chromium.launch(channel='chrome', headless=True)
    compact_context = browser.new_context(offline=True, viewport={'width': 1440, 'height': 1000})
    compact = compact_context.new_page()
    compact.goto(URL + '?day=2026-09-15')
    room_colours = compact.locator('.day:visible thead th:not(.time-cell)').evaluate_all(
        'cells => Object.fromEntries(cells.map(cell => [cell.textContent, getComputedStyle(cell).backgroundColor]))')
    # Distinct rooms and times leave a gap where an unselected industry event sat.
    for session_id in ['2026-09-15-c6', '2026-09-15-d10']:
        compact.locator(f'[id="{session_id}"] .favourite').click()
    compact.locator('#selected-only').check()
    expect(compact.locator('.day:visible thead th:visible')).to_have_text(['Time · CEST', 'Kraakhuis', 'Kabinet'])
    # Preserve all published intervals, including gaps between selected events.
    expect(compact.locator('.day:visible tbody tr:visible')).to_have_count(12)
    gap = compact.locator('[id="2026-09-15-b8"]').locator('xpath=ancestor::tr')
    expect(gap).to_be_visible()
    expect(gap.locator('.time-label')).to_have_text('12:40–14:10')
    assert gap.bounding_box()['height'] <= 30
    for header in compact.locator('.day:visible thead th:not(.time-cell):visible').all():
        assert header.evaluate('(cell) => getComputedStyle(cell).backgroundColor') == room_colours[header.inner_text()]
    empty = compact.locator('[id="2026-09-15-d6"]').locator('xpath=ancestor::td')
    expect(empty).to_be_visible()
    assert empty.evaluate('(cell) => getComputedStyle(cell).backgroundColor') == 'rgb(237, 241, 243)'
    lunch = compact.locator('[id="2026-09-15-b7"]').locator('xpath=ancestor::td')
    expect(lunch).to_have_attribute('colspan', '2')
    compact.screenshot(path='/tmp/semantics-selected-rooms.png')
    # With no selections, shared events remain as context in one column.
    for session_id in ['2026-09-15-c6', '2026-09-15-d10']:
        compact.locator(f'[id="{session_id}"] .favourite').click()
    expect(compact.locator('.day:visible thead th:visible')).to_have_text(['Time · CEST', 'Shared events'])
    shared_header = compact.locator('.day:visible thead th:not(.time-cell):visible')
    assert shared_header.evaluate('(cell) => getComputedStyle(cell).backgroundColor') not in room_colours.values()
    expect(lunch).to_have_attribute('colspan', '1')
    expect(compact.locator('[id="2026-09-15-b7"]')).to_be_visible()
    expect(compact.locator('.session[data-room=""]:visible')).to_have_count(6)
    expect(compact.locator('#selected-count')).to_have_text('(0)')
    expect(compact.locator('#empty')).to_be_visible()
    expect(compact.locator('.day:visible tbody tr:visible')).to_have_count(12)
    assert gap.bounding_box()['height'] <= 30
    for row in compact.locator('.day:visible tbody tr').all():
        expect(row.locator('td:visible')).to_have_count(1)
    compact.locator('#selected-only').uncheck()
    expect(compact.locator('.day:visible thead th:visible')).to_have_text(
        ['Time · CEST', 'Concertzaal', 'Kraakhuis', 'Kabinet', 'Anatomisch Theater', 'Suite +1', 'Meeting Room', 'Baudelo'])
    expect(lunch).to_have_attribute('colspan', '7')
    for header in compact.locator('.day:visible thead th:not(.time-cell)').all():
        assert header.evaluate('(cell) => getComputedStyle(cell).backgroundColor') == room_colours[header.inner_text()]
    assert empty.evaluate('(cell) => getComputedStyle(cell).backgroundColor') != 'rgb(237, 241, 243)'
    # Partial shared spans must not disappear when disjoint from selected rooms.
    compact.goto(URL + '?day=2026-09-16')
    compact.locator('[id="2026-09-16-b6"] .favourite').click()
    compact.locator('#selected-only').check()
    expect(compact.locator('.day:visible thead th:visible')).to_have_text(['Time · CEST', 'Concertzaal', 'Kraakhuis'])
    partial = compact.locator('[id="2026-09-16-c10"]')
    expect(partial).to_be_visible()
    expect(partial.locator('xpath=ancestor::td')).to_have_attribute('colspan', '1')
    compact.locator('#selected-only').uncheck()
    expect(partial.locator('xpath=ancestor::td')).to_have_attribute('colspan', '3')
    compact_context.close()

    # Actual browser-profile restart, not just a retained in-memory page.
    context = p.chromium.launch_persistent_context(profile, channel='chrome', headless=True)
    context.set_offline(True)
    page = context.pages[0]
    page.goto(ALL + '&selected=1')
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    expect(page.locator(SECOND + ' .favourite')).to_have_attribute('aria-pressed', 'true')
    page.locator(SECOND + ' .favourite').click()
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#selected-only').uncheck()
    expect(page.locator('.session:visible')).to_have_count(66)
    context.close()

    context = browser.new_context(offline=True)
    # Browser privacy policies may reject the localStorage getter itself.
    context.add_init_script("Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('Blocked', 'SecurityError'); }});")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(ALL)
    page.locator(FIRST + ' .favourite').click()
    expect(page.locator('#storage-notice')).to_be_visible()
    page.locator('#selected-only').check()
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    assert not errors, errors
    context.close()
    # Reading may work even when writes are rejected (for example, quota limits).
    context = browser.new_context(offline=True)
    context.add_init_script("Storage.prototype.setItem = () => { throw new DOMException('Full', 'QuotaExceededError'); };")
    page = context.new_page()
    page.goto(ALL)
    page.locator(FIRST + ' .favourite').click()
    expect(page.locator('#storage-notice')).to_be_visible()
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator(FIRST + ' .favourite')).to_have_attribute('aria-pressed', 'true')
    page.locator('#selected-only').check()
    expect(page.locator('.session[data-room]:not([data-room=""]):visible')).to_have_count(1)
    browser.close()
    print('Favourites checks passed: reload, profile restart, day links, filters, cross-tab changes, unselect, and unavailable storage.')
