"""Prueba automatizada End-to-End (Playwright) para la extensión Chrome MV3.

NOTA IMPORTANTE:
Este archivo es una suite de PRUEBAS AUTOMATIZADAS con Playwright, NO es el lanzador
de la extensión para uso diario. Playwright abre un Chromium temporal y aísla la red
con un fixture local en chatgpt.com.

Para USAR la extensión normalmente en Chrome sin alterar su red ni otras aplicaciones:
1. Inicie la API: python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
2. Abra Chrome en chrome://extensions -> Activar Modo desarrollador -> Cargar descomprimida
3. Seleccione la carpeta 'extension' de este repositorio.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import shutil
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extension"
FIXTURE = """<!doctype html><html><body>
<main><textarea id='prompt-textarea'></textarea>
<button data-testid='send-button' aria-label='Send'>Send</button>
<output id='sent'>0</output></main>
<script>document.querySelector('button').addEventListener('click',()=>{
 document.querySelector('#sent').textContent=String(Number(document.querySelector('#sent').textContent)+1);
});</script></body></html>"""


def check_backend_alive(url="http://127.0.0.1:8000/health"):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def main(fail_open=False):
    if not fail_open and not check_backend_alive():
        print("\n[!] AVISO: El backend FastAPI no está activo en http://127.0.0.1:8000")
        print("[!] Para verificar el bloqueo DLP, inicie primero la API en otra terminal:")
        print("    python -m uvicorn api.main:app --host 127.0.0.1 --port 8000\n")
        print("[!] O pruebe la retención del envío en ChatGPT cuando el servidor no está disponible:")
        print("    python tests/live_chrome_extension.py --fail-open\n")
        print("[*] RECORDATORIO: Si desea usar la extensión en su Chrome real sin aislamiento:")
        print("    Vaya a chrome://extensions -> 'Cargar descomprimida' -> seleccione la carpeta 'extension'.\n")
        return
    with TemporaryDirectory(prefix="aegis_chrome_") as profile, TemporaryDirectory(prefix="aegis_ext_") as ext_copy, sync_playwright() as pw:
        shutil.copytree(EXTENSION, ext_copy, dirs_exist_ok=True)
        if fail_open:
            bg_path = Path(ext_copy) / "background.js"
            bg_path.write_text(
                bg_path.read_text(encoding="utf-8").replace('const API = "http://127.0.0.1:8000";', 'const API = "http://127.0.0.1:9999";'),
                encoding="utf-8"
            )
        context = pw.chromium.launch_persistent_context(profile, headless=False,
            args=[f"--disable-extensions-except={ext_copy}", f"--load-extension={ext_copy}",
                  "--no-first-run", "--no-default-browser-check"])
        page = context.pages[0] if context.pages else context.new_page()
        page.route("https://chatgpt.com/**", lambda route: route.fulfill(status=200, content_type="text/html", body=FIXTURE))
        page.goto("https://chatgpt.com/aegis-controlled-test")
        page.wait_for_selector("#aegis-policy-banner", timeout=10000)
        page.locator("#aegis-policy-banner button").click()

        if fail_open:
            page.locator("#prompt-textarea").fill("DNI: 12345678 correo: ana@example.com")
            page.locator("#prompt-textarea").press("Enter")
            page.wait_for_selector("#aegis-audit-error", timeout=10000)
            assert page.locator("#sent").text_content() == "0"
            print("LIVE_CHROMIUM_FAIL_CLOSED_OK: ChatGPT backend unavailable; prompt retained")
            context.close(); return

        page.locator("#prompt-textarea").fill("DNI: 12345678 correo: ana@example.com")
        page.locator("#prompt-textarea").press("Enter")
        page.wait_for_selector("#dlp-guard-modal-root", timeout=10000)
        assert page.locator("#sent").text_content() == "0", "Sensitive prompt was sent"

        page.locator("#dlp-modal-close").click()
        page.locator("#prompt-textarea").fill("Explícame qué es una API pública")
        page.locator("button[data-testid='send-button']").click()
        page.wait_for_function("document.querySelector('#sent').textContent === '1'")
        print("LIVE_CHROME_OK: BLOCK prevented send; ALLOW resumed send; policy banner rendered")
        context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--fail-open", action="store_true", help="Simula API caída; conserva el nombre histórico, pero ChatGPT ahora retiene el envío.")
    main(parser.parse_args().fail_open)
