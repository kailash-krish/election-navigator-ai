"""
services/analytics_service.py — Google BigQuery + Cloud Logging integration.

Logs anonymized usage events to BigQuery for analysis.
No PII stored — only query category, response type, language, timestamp.
"""

import logging
import datetime
from typing import Optional
import threading
import queue

logger = logging.getLogger(__name__)

try:
    from google.cloud import bigquery
    _BQ_AVAILABLE = True
except ImportError:
    _BQ_AVAILABLE = False
    logger.info("google-cloud-bigquery not installed; analytics in local-only mode.")

try:
    import google.cloud.logging as cloud_logging
    _CL_AVAILABLE = True
except ImportError:
    _CL_AVAILABLE = False


def _categorize_query(query: str) -> str:
    """Classify query into broad category for analytics (no PII)."""
    q = query.lower()
    if any(w in q for w in ["eligib", "qualify", "am i"]):
        return "eligibility"
    if any(w in q for w in ["register", "form 6", "voter id", "epic", "nvsp"]):
        return "registration"
    if any(w in q for w in ["document", "id proof", "papers"]):
        return "documents"
    if any(w in q for w in ["timeline", "phases", "schedule", "date"]):
        return "timeline"
    if any(w in q for w in ["evm", "electronic voting", "machine"]):
        return "evm"
    if any(w in q for w in ["vvpat", "paper trail"]):
        return "vvpat"
    if any(w in q for w in ["booth", "polling center"]):
        return "booth_finder"
    if any(w in q for w in ["first", "new voter", "beginner"]):
        return "first_time_voter"
    if any(w in q for w in ["vote", "voting day", "election day"]):
        return "voting_process"
    return "general"


class AnalyticsService:
    """
    Logs events to BigQuery and Google Cloud Logging.
    Gracefully degrades when credentials are unavailable (local dev).
    """

    TABLE_INTERACTIONS = "interactions"
    TABLE_BOOTH_SEARCHES = "booth_searches"

    def __init__(self, project_id: Optional[str], dataset_id: str = "election_navigator"):
        self._project   = project_id
        self._dataset   = dataset_id
        self._bq_client  = None
        self._cl_client  = None
        self._ready     = False
        self._local_log: list = []  # fallback in-memory log
        self._queue = queue.Queue()

        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        if not project_id:
            logger.info("GOOGLE_CLOUD_PROJECT not set; analytics in local mode.")
            return

        if _BQ_AVAILABLE:
            try:
                self._bq_client = bigquery.Client(project=project_id)
                self._ready = True
                logger.info("BigQuery analytics ready (project=%s, dataset=%s).", project_id, dataset_id)
            except Exception as e:
                logger.warning("BigQuery init failed: %s", e)

        if _CL_AVAILABLE:
            try:
                self._cl_client = cloud_logging.Client(project=project_id)
                self._cl_client.setup_logging()
                logger.info("Cloud Logging attached.")
            except Exception as e:
                logger.warning("Cloud Logging init failed: %s", e)

    def is_ready(self) -> bool:
        return self._ready

    # ── Public methods ────────────────────────────────────────────────────────

    def log_interaction(
        self,
        query: str,
        response_type: str,
        source: str,
        language: str = "en",
    ) -> None:
        """Log an anonymized chat interaction."""
        category = _categorize_query(query)
        row = {
            "ts":            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "category":      category,
            "response_type": response_type,
            "source":        source,
            "language":      language,
        }
        self._local_log.append(row)
        if self._ready and self._bq_client:
            self._queue.put((self.TABLE_INTERACTIONS, row))

    def log_booth_search(self, pincode: Optional[str], has_location: bool) -> None:
        """Log a booth-finder search (no exact location stored)."""
        row = {
            "ts":           datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "has_pincode":  bool(pincode),
            "has_location": has_location,
            "region":       pincode[:3] + "XXX" if pincode else "geo",  # partial only
        }
        self._local_log.append({"_table": self.TABLE_BOOTH_SEARCHES, **row})
        if self._ready and self._bq_client:
            self._queue.put((self.TABLE_BOOTH_SEARCHES, row))

    def get_summary(self) -> dict:
        """Return anonymized aggregated stats."""
        if self._ready and self._bq_client:
            return self._bq_summary()
        # Fallback: summarize in-memory log
        from collections import Counter
        cats = Counter(e.get("category") for e in self._local_log if "category" in e)
        langs = Counter(e.get("language") for e in self._local_log if "language" in e)
        return {
            "total_interactions": len(self._local_log),
            "top_categories": dict(cats.most_common(5)),
            "top_languages": dict(langs.most_common(5)),
            "source": "in_memory",
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _worker_loop(self):
        while True:
            try:
                table_name, row = self._queue.get()
                self._insert_rows(table_name, [row])
                self._queue.task_done()
            except Exception as e:
                logger.error("Analytics worker error: %s", e)

    def _insert_rows(self, table_name: str, rows: list) -> None:
        if not self._bq_client:
            return
        table_id = f"{self._project}.{self._dataset}.{table_name}"
        try:
            errors = self._bq_client.insert_rows_json(table_id, rows)
            if errors:
                logger.warning("BigQuery insert errors for %s: %s", table_name, errors)
        except Exception as e:
            logger.warning("BigQuery insert failed (%s): %s", table_name, e)

    def _bq_summary(self) -> dict:
        try:
            query = f"""
                SELECT
                  category,
                  COUNT(*) AS count,
                  COUNTIF(source = 'gemini') AS ai_calls,
                  COUNTIF(source = 'flow') AS scripted_calls
                FROM `{self._project}.{self._dataset}.{self.TABLE_INTERACTIONS}`
                WHERE DATE(ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                GROUP BY category
                ORDER BY count DESC
                LIMIT 10
            """
            rows = list(self._bq_client.query(query).result())
            return {
                "period": "last_30_days",
                "top_categories": [dict(r) for r in rows],
                "source": "bigquery",
            }
        except Exception as e:
            logger.warning("BigQuery summary query failed: %s", e)
            return {"error": "BigQuery query failed", "source": "bigquery"}
