from __future__ import annotations

from urllib.parse import urlparse

from app.models.schemas import BrowserProbeResult


class SeleniumProbe:
    def probe(self, target_url: str) -> BrowserProbeResult:
        if not self._is_http_url(target_url):
            raise ValueError("Selenium probe requires an http or https URL.")

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.common.by import By
        except Exception as exc:
            return BrowserProbeResult(
                status="error",
                url=target_url,
                notes=["Selenium is not available in the current environment."],
                error_message=str(exc),
            )

        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1440,960")

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(20)
            driver.get(target_url)
            title = driver.title or ""
            current_url = driver.current_url
            forms_detected = len(driver.find_elements(By.TAG_NAME, "form"))
            buttons_detected = len(driver.find_elements(By.TAG_NAME, "button"))
            links_detected = len(driver.find_elements(By.TAG_NAME, "a"))

            notes = [
                f"Loaded page title: {title or 'untitled'}",
                f"Detected {forms_detected} forms, {buttons_detected} buttons, and {links_detected} links.",
            ]
            return BrowserProbeResult(
                status="passed",
                url=target_url,
                final_url=current_url,
                title=title or None,
                forms_detected=forms_detected,
                buttons_detected=buttons_detected,
                links_detected=links_detected,
                notes=notes,
            )
        except Exception as exc:
            return BrowserProbeResult(
                status="error",
                url=target_url,
                notes=["Browser automation could not complete for this URL."],
                error_message=str(exc),
            )
        finally:
            if driver is not None:
                driver.quit()

    def _is_http_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
