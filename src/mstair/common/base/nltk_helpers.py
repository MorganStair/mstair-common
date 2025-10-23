"""
Helpers for working with NLTK resources, including persistent caching of stopwords.

This module provides utility functions to cache and retrieve NLTK resources,
such as English stopwords, using diskcache for efficient reuse across sessions.
It ensures that NLTK data is downloaded as needed and stored in a virtual environment-
specific cache directory.
"""

import os
from functools import cache
from pathlib import Path
from typing import cast

import diskcache
import nltk
from nltk.downloader import download as nltk_download


@cache
def nltk_cache() -> diskcache.Cache:
    """Return a diskcache.Cache instance for NLTK-related caching."""
    cache_dir = Path(os.environ.get("VIRTUAL_ENV", str(Path.cwd()))) / ".cache" / "nltk"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return diskcache.Cache(
        directory=str(cache_dir), size_limit=100 * 1024 * 1024
    )  # diskcache prefers str  # 100MB limit


@cache
def load_stopwords() -> set[str]:
    """Retrieve English stopwords using NLTK, cached."""
    STOPWORDS_CACHE_KEY = "nltk.corpus.stopwords.en"
    cached_value = nltk_cache().get(STOPWORDS_CACHE_KEY)
    value: set[str] = cast(set[str], cached_value)

    # Validate cached data
    if isinstance(value, set) and cached_value and all(isinstance(item, str) for item in value):
        return cast(set[str], cached_value)

    # Cache miss or invalid data - reload
    nltk_download("stopwords", quiet=True)
    value = set(nltk.corpus.stopwords.words("english"))
    nltk_cache().set(STOPWORDS_CACHE_KEY, value)
    return value
