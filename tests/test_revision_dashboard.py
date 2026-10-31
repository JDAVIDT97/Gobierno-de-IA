"""Browser verification of the actual local panel against a synthetic database."""
from playwright.sync_api import sync_playwright

def test_admin_panel_auth_export_and_disconnect(tmp_path):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chromium',headless=True)
        page=browser.new_page(accept_downloads=True)
        page.goto('http://127.0.0.1:8017/',wait_until='domcontentloaded')
        field=page.locator('#audit-admin-token');field.fill('wrong')
        page.locator('#audit-admin-access button[type=submit]').click()
        page.wait_for_function("document.querySelector('#audit-admin-status').textContent.includes('Token no válido')")
        field.fill('synthetic-review-admin');page.locator('#audit-admin-access button[type=submit]').click()
        page.wait_for_function("document.querySelector('#audit-admin-status').textContent.includes('conectado')")
        page.wait_for_function("document.querySelectorAll('#audit-table-body tr').length > 0")
        assert field.input_value()==''
        assert not page.evaluate("JSON.stringify(localStorage)+JSON.stringify(sessionStorage)").find('synthetic-review-admin')>=0
        with page.expect_download() as download:
            page.locator('#btn-export-pdf-nav').click()
        target=tmp_path/'audit.pdf';download.value.save_as(target)
        assert target.read_bytes().startswith(b'%PDF')
        page.locator('#audit-admin-disconnect').click()
        assert page.locator('#audit-table-body').inner_text()==''
        assert page.locator('#audit-admin-status').inner_text()=='Registros protegidos'
        browser.close()
