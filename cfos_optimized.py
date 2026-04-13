"""
CFOS-XG PRO 75 TITAN - Optimized Wrapper

Wraps LUCKY-7-92.py with:
- Result caching (5 min TTL)
- Parallel Monte Carlo processing
- Structured logging
- Performance metrics
- Graceful error handling
"""
import os
import sys
import time
import logging
from io import StringIO
from typing import Optional

# Load config
try:
    import yaml
    with open(os.path.join(os.path.dirname(__file__), "config.yaml"), "r") as _f:
        _CONFIG = yaml.safe_load(_f)
except Exception:
    _CONFIG = {}

# Setup logging
from utils.logging_config import setup_logging, get_logger

_log_cfg = _CONFIG.get("logging", {})
setup_logging(
    level=_log_cfg.get("level", "INFO"),
    log_file=_log_cfg.get("file"),
    use_json=_log_cfg.get("format", "json") == "json",
)

logger = get_logger(__name__)

# Import core engine
try:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "lucky_7_92",
        os.path.join(os.path.dirname(__file__), "LUCKY-7-92.py"),
    )
    _lucky = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_lucky)
    logger.info("LUCKY-7-92.py engine loaded successfully")
except Exception as e:
    logger.error(f"Failed to load LUCKY-7-92.py: {e}")
    _lucky = None

# Import engine modules
from engine.bet_scorer import BetScorer
from utils.cache import ResultCache

# Initialize cache
_cache_cfg = _CONFIG.get("cache", {})
_cache = ResultCache(
    ttl=_cache_cfg.get("ttl_seconds", 300),
    max_entries=_cache_cfg.get("max_entries", 1000),
)


def analyze_csv(csv_line: str, use_cache: bool = True) -> Optional[dict]:
    """
    Analyze a CSV line using the CFOS-XG PRO 75 TITAN engine.

    Args:
        csv_line: Comma-separated match statistics string (32+ columns)
        use_cache: Whether to use cached results (default: True)

    Returns:
        Result dict from izracunaj_model(), or None on error.
        Includes extra keys:
            - _cached (bool): Whether result was from cache
            - _duration_ms (float): Computation time in milliseconds
            - _decision (dict): Structured bet decision from BetScorer
    """
    if not _lucky:
        logger.error("Engine not loaded")
        return None

    cache_key = ResultCache.make_key(csv_line)

    # Check cache
    if use_cache:
        cached = _cache.get(cache_key)
        if cached is not None:
            logger.info("Returning cached result", extra={"duration_ms": 0})
            return {**cached, "_cached": True, "_duration_ms": 0}

    start_time = time.time()
    try:
        data = _lucky.parse_csv_line(csv_line)
        result = _lucky.izracunaj_model(data)
    except Exception as e:
        logger.error(f"Model computation error: {e}", exc_info=True)
        return None

    duration_ms = round((time.time() - start_time) * 1000, 1)
    logger.info(
        "Model computation complete",
        extra={"duration_ms": duration_ms, "match": f"{result.get('home')} vs {result.get('away')}"},
    )

    if result is None:
        return None

    # Enrich with structured decision
    decision = BetScorer.extract_decision(result)
    result["_decision"] = decision
    result["_cached"] = False
    result["_duration_ms"] = duration_ms

    # Cache the result (without the meta keys to keep it clean)
    cache_copy = {k: v for k, v in result.items() if not k.startswith("_")}
    _cache.set(cache_key, cache_copy)

    return result


def get_bet_decision_text(result: dict, score_home: int = 0, score_away: int = 0) -> str:
    """
    Get formatted Telegram-ready bet decision text.

    Args:
        result: Output from analyze_csv()
        score_home / score_away: Current score for display

    Returns:
        Formatted message string
    """
    decision = result.get("_decision") or BetScorer.extract_decision(result)
    return BetScorer.format_telegram_message(decision, score_home, score_away)


def get_full_analysis_text(csv_line: str) -> str:
    """
    Get full text analysis output (captures stdout from LUCKY-7-92.py).

    Args:
        csv_line: CSV input string

    Returns:
        Full analysis text as string
    """
    if not _lucky:
        return "Engine not loaded"

    old_stdout = sys.stdout
    sys.stdout = captured = StringIO()

    try:
        data = _lucky.parse_csv_line(csv_line)
        result = _lucky.izracunaj_model(data)
        if result:
            _lucky.izpis_rezultata(result)
    except Exception as e:
        sys.stdout = old_stdout
        return f"Analysis error: {e}"
    finally:
        sys.stdout = old_stdout

    return captured.getvalue()


def invalidate_cache(csv_line: str):
    """Invalidate cached result for a CSV input."""
    key = ResultCache.make_key(csv_line)
    _cache.invalidate(key)
    logger.info(f"Cache invalidated for key: {key[:16]}...")


def get_cache_stats() -> dict:
    """Return cache statistics."""
    return {"size": _cache.size(), "ttl": _cache.ttl, "max_entries": _cache.max_entries}
