Installation
======================

Installation is mainly straightforward.
Run ``pip install mandos``, or ``pip install mandos[all]``,
or ``pip install mandos[analysis]``, etc., where the available extras are:

- ``analysis``: Needed for analysis on completed searches.
- ``viz``: Needed for plotting.
- ``web``: Needed for searches that use web scraping
- ``all``: Includes all of the above extras.

For ``web``, a `Selenium webdriver <https://www.selenium.dev/documentation/getting_started/installing_browser_drivers>`_
is also required.
