"""Browser dependency is loaded only when discovering the official report."""


def discover_meteo():
    import os

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.support import expected_conditions as conditions
    from selenium.webdriver.support.ui import WebDriverWait

    options = Options()
    options.add_argument("--headless")
    if os.environ.get("WEATHER_FIREFOX_BINARY"):
        options.binary_location = os.environ["WEATHER_FIREFOX_BINARY"]
    browser = webdriver.Firefox(options=options)
    try:
        browser.set_page_load_timeout(120)
        browser.get("https://meteo.gov.lk/")
        wait = WebDriverWait(browser, 45)
        for label in ("Observation Data", "24 Hour Weather Report"):
            button = wait.until(
                conditions.element_to_be_clickable(
                    (By.XPATH, f"//button[contains(., '{label}')]")
                )
            )
            button.click()
        link = wait.until(
            conditions.presence_of_element_located(
                (By.XPATH, "//a[contains(., '24 Hour Weather Report')]")
            )
        )
        url = link.get_attribute("href")
        if not url or not url.startswith(("https://", "http://")):
            raise ValueError("Official report link is missing or invalid")
        return [url]
    finally:
        browser.quit()
