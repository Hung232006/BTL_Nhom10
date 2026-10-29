from typing import Dict, Any

class AnalyticsDashboardService:
    CASH_DISCREPANCY_THRESHOLD_VND = 50000.0

    @classmethod
    def fetch_dashboard(cls, redis_cache_hit: bool, shift_cash_diff_vnd: float) -> Dict[str, Any]:
        latency = 0.2 if redis_cache_hit else 1.8
        cash_alert = shift_cash_diff_vnd > cls.CASH_DISCREPANCY_THRESHOLD_VND
        return {"latency_seconds": latency, "cash_alert_triggered": cash_alert}