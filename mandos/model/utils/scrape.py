from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.exceptions import MissingResourceError, ImportFailedWarning
from pocketutils.core.query_utils import QueryExecutor

from mandos.model.settings import MANDOS_SETTINGS

from mandos.model.utils.setup import logger


try:
    import selenium
except ImportError:
    selenium = None
    logger.info("Selenium is not installed")


# noinspection PyBroadException
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement
except Exception:
    webdriver = None
    WebDriver = None
    By = None

if webdriver is not None:
    MANDOS_SETTINGS.set_path_for_selenium()
    # noinspection PyBroadException
    try:
        driver_fn = getattr(webdriver, MANDOS_SETTINGS.selenium_driver)
    except AttributeError:
        driver_fn = None
        logger.caution(
            f"Selenium driver {MANDOS_SETTINGS.selenium_driver} not found", exc_info=True
        )
    else:
        logger.info(f"Selenium installed; expecting driver {MANDOS_SETTINGS.selenium_driver}")


@dataclass(frozen=True)
class Scraper:
    driver: WebDriver
    executor: QueryExecutor

    @classmethod
    def create(cls, executor: QueryExecutor) -> Scraper:
        if WebDriver is None:
            raise MissingResourceError("Selenium is not installed")
        if driver_fn is None:
            raise MissingResourceError(
                f"Selenium driver {MANDOS_SETTINGS.selenium_driver} not found"
            )
        if MANDOS_SETTINGS.selenium_driver_path is None:
            driver = driver_fn()
        else:
            driver = driver_fn(MANDOS_SETTINGS.selenium_driver_path)
        logger.info(f"Loaded Selenium driver {driver}")
        return Scraper(driver, executor)

    def go(self, url: str) -> Scraper:
        self.driver.get(url)
        # self.driver.find_elements_by_link_text("1")
        return self

    def find_element(self, thing: str, by: str) -> WebElement:
        by = by.upper()
        return self.driver.find_element(thing, by)

    def find_elements(self, thing: str, by: str) -> Sequence[WebElement]:
        by = by.upper()
        return self.driver.find_elements(thing, by)

    def click_element(self, thing: str, by: str) -> None:
        by = by.upper()
        element = self.driver.find_element(thing, by)
        element.click()


if __name__ == "__main__":
    exe = QueryExecutor()
    scraper = Scraper.create(exe)
    time.sleep(1)
    logger.notice("Done. All ok.")


__all__ = ["Scraper", "By"]
