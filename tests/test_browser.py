"""Exercise native links, inline details and filters on the offline file:// site."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = (ROOT / 'site/index.html').as_uri()
URL = BASE_URL + '?day=all'

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(offline=True, viewport={'width': 1440, 'height': 1050})
    page = context.new_page()
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url))
    page.goto(URL)
    expect(page.locator('.session:visible')).to_have_count(66)
    expect(page.locator('a.talk-title')).to_have_count(61)

    # Room colours identify physical rooms, not tracks or changing column positions.
    colours = page.locator('.event-cell').evaluate_all('''cells => cells.flatMap(cell => {
      const room = cell.querySelector('.session').dataset.room;
      return room ? [{room, colour: getComputedStyle(cell).backgroundColor}] : [];
    })''')
    by_room = {}
    for item in colours:
        by_room.setdefault(item['room'], set()).add(item['colour'])
    assert len(by_room) == 7
    assert all(len(values) == 1 for values in by_room.values()), by_room
    assert len({next(iter(values)) for values in by_room.values()}) == 7, by_room
    for header in page.locator('thead th:not(.time-cell)').all():
        assert header.evaluate('(cell) => getComputedStyle(cell).backgroundColor') in by_room[header.inner_text()]

    # Native middle-click must open a separate detail page without changing the schedule.
    title = page.locator('a.talk-title').first
    title_text = title.inner_text()
    with context.expect_page() as popup:
        title.click(button='middle')
    talk = popup.value
    talk.wait_for_load_state()
    assert '/talks/' in talk.url
    expect(talk.locator('h1')).to_have_text(title_text)
    assert page.url == URL
    talk.close()

    disclosure = page.locator('details').first
    disclosure.locator('summary').click()
    expect(disclosure).to_have_attribute('open', '')
    assert page.url == URL
    # Multiple abstracts stay open, allowing comparison.
    second = page.locator('.talk details').nth(1)
    second.locator('summary').click()
    expect(disclosure).to_have_attribute('open', '')

    page.locator('#search').fill('KGXL-Query')
    expect(page.locator('.session:visible')).to_have_count(1)
    expect(page.locator('.session:visible .session-title')).to_have_text('Querying Knowledge Graphs')
    page.locator('#search').fill('no-such-talk-xyz')
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#clear').click()
    expect(page.locator('.session:visible')).to_have_count(66)

    page.locator('.days a[data-day="2026-09-16"]').click()
    assert 'day=2026-09-16' in page.url
    expect(page.locator('.day:visible')).to_have_count(1)
    page.reload()
    expect(page.locator('.day:visible')).to_have_count(1)
    # Returning from a Wednesday detail must keep Wednesday visible, not default to Tuesday.
    page.locator('[id="2026-09-16-b6"] a.talk-title').first.click()
    page.get_by_role('link', name='Programme', exact=True).click()
    expect(page.locator('.day:visible')).to_have_attribute('data-day', '2026-09-16')
    expect(page.locator('[id="2026-09-16-b6"]')).to_be_visible()
    page.locator('#room').select_option('Kabinet')
    rooms = page.locator('.session:visible').evaluate_all('(items) => items.map(item => item.dataset.room)')
    assert set(rooms) == {'', 'Kabinet'}, rooms
    page.locator('#clear').click()
    page.goto(URL)
    page.screenshot(path='/tmp/semantics-desktop.png')
    page.goto(BASE_URL + '?day=2026-09-16')
    page.screenshot(path='/tmp/semantics-talks.png')

    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(BASE_URL)
    expect(page.locator('.session:visible')).to_have_count(31)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path='/tmp/semantics-mobile.png')
    # Fixed columns survive horizontal scrolling; headers survive vertical scrolling.
    wrapper = page.locator('.day:visible .timetable-wrap')
    wrapper.evaluate('(element) => { element.scrollLeft = 450; element.scrollTop = 280; }')
    page.wait_for_function('document.querySelector(".day:not([hidden]) .timetable-wrap").scrollTop === 280')
    bounds = wrapper.bounding_box()
    corner = page.locator('.day:visible thead .time-cell').bounding_box()
    room_header = page.locator('.day:visible thead th').nth(3).bounding_box()
    assert abs(corner['x'] - bounds['x'] - 1) < 2
    assert abs(corner['y'] - bounds['y'] - 1) < 2
    assert abs(room_header['y'] - corner['y']) < 2
    page.screenshot(path='/tmp/semantics-sticky.png')
    # A long session's time stays in view even after its row's top has scrolled away.
    page.goto(BASE_URL + '?day=2026-09-16')
    wrapper = page.locator('.day:visible .timetable-wrap')
    target_row = page.locator('[id="2026-09-16-b6"]').locator('xpath=ancestor::tr')
    row_offset = target_row.evaluate('(row) => row.offsetTop')
    wrapper.evaluate('(element, y) => { element.scrollTop = y + 90; element.scrollLeft = 300; }', row_offset)
    label = target_row.locator('.time-label')
    expect(label).to_have_text('11:15–12:40')
    bounds = wrapper.bounding_box()
    position = label.bounding_box()
    assert bounds['y'] + 35 <= position['y'] <= bounds['y'] + 55, (bounds, position)
    assert bounds['x'] <= position['x'] <= bounds['x'] + 10
    assert not errors, errors
    assert not [url for url in requests if url.startswith(('http:', 'https:'))], requests
    context.close()

    # Content and navigation must work without JavaScript, too.
    no_js = browser.new_context(java_script_enabled=False, offline=True)
    page = no_js.new_page()
    page.goto(URL)
    expect(page.locator('a.talk-title')).to_have_count(61)
    page.locator('a.talk-title').first.click()
    expect(page.locator('h1')).to_have_text(title_text)
    browser.close()
    print('Browser checks passed: offline, native new tabs, disclosures, filters, fixed room/time axes, sticky long-session time, mobile width, no JavaScript.')
