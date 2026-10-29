class NotificationCRMService:
    GOLD_TIER_MIN_SPEND_VND = 10000000.0

    @classmethod
    def dispatch_message(cls, zalo_zns_success: bool) -> str:
        return "Zalo ZNS" if zalo_zns_success else "SMS Brandname"

    @classmethod
    def evaluate_rfm_tier(cls, total_spend_vnd: float) -> str:
        return "Gold" if total_spend_vnd >= cls.GOLD_TIER_MIN_SPEND_VND else "Silver"

    @classmethod
    def process_dead_letter_queue(cls, backlog_count: int) -> str:
        return "PROCESSED" if backlog_count > 0 else "IDLE"