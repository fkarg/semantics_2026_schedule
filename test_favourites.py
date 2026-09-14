"""Browser contract: personal session selection persists independently of filtering."""
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
URL = (ROOT / 'site/index.html').as_uri()
ALL = URL + '?day=all'
FIRST = '[id="2026-09-16-b6"]'
SECOND = '[id="2026-09-17-c7"]'

with sync_playwright() as p, TemporaryDirectory() as profile:
    context = p.chromium.launch_persistent_context(profile, channel='chrome', headless=True)
    context.set_offline(True)
    page = context.pages[0]
    page.goto(ALL)
    first = page.locator(FIRST + ' .favourite')
    expect(first).to_have_attribute('aria-pressed', 'false', timeout=1000)
    before = page.url
    first.click()
    assert page.url == before
    expect(first).to_have_attribute('aria-pressed', 'true')
    page.reload()
    expect(first).to_have_attribute('aria-pressed', 'true')
    page.locator('#selected-only').check()
    expect(page.locator('.session:visible')).to_have_count(1)
    expect(page.locator(FIRST)).to_be_visible()
    expect(page.locator(FIRST).locator('xpath=ancestor::td')).to_have_attribute('data-column', '0')
    page.reload()
    expect(page.locator('#selected-only')).to_be_checked()
    expect(page.locator('.session:visible')).to_have_count(1)
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
    expect(page.locator('.session:visible')).to_have_count(2)
    first.click()
    expect(page.locator('.session:visible')).to_have_count(1)
    expect(other.locator(FIRST + ' .favourite')).to_have_attribute('aria-pressed', 'false')
    expect(other.locator(SECOND + ' .favourite')).to_have_attribute('aria-pressed', 'true')
    # Search and room constraints still intersect with selected-only.
    page.locator('#search').fill('no-matching-session')
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#search').fill('')
    page.locator('#room').select_option('Kabinet')
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#room').select_option('Kraakhuis')
    expect(page.locator('.session:visible')).to_have_count(1)
    context.close()

    # Actual browser-profile restart, not just a retained in-memory page.
    context = p.chromium.launch_persistent_context(profile, channel='chrome', headless=True)
    context.set_offline(True)
    page = context.pages[0]
    page.goto(ALL + '&selected=1')
    expect(page.locator('.session:visible')).to_have_count(1)
    expect(page.locator(SECOND + ' .favourite')).to_have_attribute('aria-pressed', 'true')
    page.locator(SECOND + ' .favourite').click()
    expect(page.locator('#empty')).to_be_visible()
    page.locator('#selected-only').uncheck()
    expect(page.locator('.session:visible')).to_have_count(66)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='/tmp/semantics-favourites-mobile.png')
    context.close()

    browser = p.chromium.launch(channel='chrome', headless=True)
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
    expect(page.locator('.session:visible')).to_have_count(1)
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
    expect(page.locator('.session:visible')).to_have_count(1)
    browser.close()
    print('Favourites checks passed: reload, profile restart, day links, filters, cross-tab changes, unselect, and unavailable storage.')
