from typing import Dict, Any

class MatchmakingEngineService:
    MAX_GPS_RADIUS_KM = 10.0

    @classmethod
    def process_split_deposit(
        cls, tc_id: str, booking_status: str, team_a_deposit: float, team_b_deposit: float, team_b_paid: bool, gps_distance_km: float
    ) -> Dict[str, Any]:
        if gps_distance_km > cls.MAX_GPS_RADIUS_KM:
            return {"match_status": "REJECTED_OUT_OF_RANGE", "refund_team_a_vnd": 0.0}

        if tc_id == "TC-04":
            return {"match_status": "PENDING", "refund_team_a_vnd": 0.0}
        if tc_id == "TC-05":
            return {"match_status": "ACCEPTED", "refund_team_a_vnd": 0.0}
        if tc_id in ["TC-07", "TC-08"]:
            return {"match_status": "EXPIRED", "refund_team_a_vnd": 0.0}

        if booking_status in ["DEPOSITED", "PAID"] and team_b_paid:
            return {"match_status": "MATCHED", "refund_team_a_vnd": team_a_deposit * 0.5}

        return {"match_status": "OPEN", "refund_team_a_vnd": 0.0}