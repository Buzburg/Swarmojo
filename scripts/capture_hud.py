import os
from playwright.sync_api import sync_playwright

html_path = os.path.abspath('docs/index.html')
file_url = 'file:///' + html_path.replace('\\', '/')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1600, 'height': 1000})
    page.goto(file_url, wait_until='load')
    page.wait_for_timeout(500)

    tabs = [
        ('telemetry', 'assets/screenshots/swarmojo_hud_telemetry.png'),
        ('orgchart', 'assets/screenshots/swarmojo_hud_orgchart.png'),
        ('tasks', 'assets/screenshots/swarmojo_hud_tasks.png'),
        ('budgets', 'assets/screenshots/swarmojo_hud_budgets.png'),
        ('governance', 'assets/screenshots/swarmojo_hud_governance.png'),
        ('settings', 'assets/screenshots/swarmojo_hud_settings.png'),
    ]

    for tab_id, out_path in tabs:
        page.evaluate(f'switchTab("{tab_id}")')
        page.wait_for_timeout(400)
        page.screenshot(path=out_path)
        print(f'Captured {tab_id} -> {out_path}')

    page.evaluate('switchTab("telemetry")')
    page.wait_for_timeout(300)
    page.screenshot(path='docs/screenshot.png')
    print('Captured telemetry -> docs/screenshot.png')

    browser.close()
