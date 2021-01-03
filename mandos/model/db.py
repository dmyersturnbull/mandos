"""
TODO: I'll delete this.
"""
from __future__ import annotations

import sqlite3 as sq

import abc
import logging
import shutil
from pathlib import Path
from typing import Union

import pandas as pd
import requests
from pocketutils.core.hashers import Hasher

from mandos import MandosResources
from mandos.model.taxonomy import Taxonomy

logger = logging.getLogger(__package__)
hasher = Hasher("sha1")
