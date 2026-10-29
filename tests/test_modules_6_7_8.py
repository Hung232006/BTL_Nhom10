# -*- coding: utf-8 -*-
import os
import sys

# Tự động thêm thư mục gốc D:\Test_CaseFB vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pandas as pd

from services.matchmaking_service import MatchmakingEngineService
from services.analytics_service import AnalyticsDashboardService
from services.notification_crm_service import NotificationCRMService

def find_csv_file(possible_names):
    search_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../data")),
        os.path.abspath(os.path.dirname(__file__))
    ]
    for d in search_dirs:
        for name in possible_names:
            full_path = os.path.join(d, name)
            if os.path.exists(full_path):
                return full_path
    return None

CSV_PATH = find_csv_file([
    "test_input_data (2).csv", 
    "test_input_data.csv", 
    "scbs_mod6_7_8_data.csv"
])

def load_csv_data():
    if not CSV_PATH:
        print("\n[CẢNH BÁO RED] KHÔNG TÌM THẤY FILE CSV DỮ LIỆU CỦA MODULE 6, 7, 8!")
        return []
    return pd.read_csv(CSV_PATH).fillna("").to_dict(orient="records")

CSV_TEST_DATA = load_csv_data()

class TestSCBSModules678:

    @pytest.mark.parametrize(
        "data", 
        [row for row in CSV_TEST_DATA if row.get("module") == "MOD-06"],
        ids=[row["tc_id"] for row in CSV_TEST_DATA if row.get("module") == "MOD-06"]
    )
    def test_module_06_matchmaking(self, data):
        result = MatchmakingEngineService.process_split_deposit(
            tc_id=str(data["tc_id"]),
            booking_status=str(data["booking_status"]),
            team_a_deposit=float(data["team_a_deposit_vnd"]),
            team_b_deposit=float(data["team_b_deposit_vnd"]),
            team_b_paid=str(data["team_b_paid"]).upper() == "TRUE",
            gps_distance_km=float(data["gps_distance_km"])
        )
        assert result["match_status"] == str(data["expected_match_status"])
        assert result["refund_team_a_vnd"] == float(data["expected_refund_team_a_vnd"])

    @pytest.mark.parametrize(
        "data", 
        [row for row in CSV_TEST_DATA if row.get("module") == "MOD-07"],
        ids=[row["tc_id"] for row in CSV_TEST_DATA if row.get("module") == "MOD-07"]
    )
    def test_module_07_analytics(self, data):
        result = AnalyticsDashboardService.fetch_dashboard(
            redis_cache_hit=str(data["redis_cache_hit"]).upper() == "TRUE",
            shift_cash_diff_vnd=float(data["shift_cash_diff_vnd"])
        )
        assert result["latency_seconds"] == float(data["expected_dash_latency_s"])
        assert result["cash_alert_triggered"] == (str(data["expected_cash_alert"]).upper() == "TRUE")

    @pytest.mark.parametrize(
        "data", 
        [row for row in CSV_TEST_DATA if row.get("module") == "MOD-08"],
        ids=[row["tc_id"] for row in CSV_TEST_DATA if row.get("module") == "MOD-08"]
    )
    def test_module_08_notification_crm(self, data):
        if data.get("expected_notif_channel"):
            channel = NotificationCRMService.dispatch_message(
                zalo_zns_success=str(data["zalo_zns_success"]).upper() == "TRUE"
            )
            assert channel == str(data["expected_notif_channel"])

        if data.get("expected_membership_tier"):
            tier = NotificationCRMService.evaluate_rfm_tier(
                total_spend_vnd=float(data["rfm_spend_vnd"])
            )
            assert tier == str(data["expected_membership_tier"])

        if data.get("expected_queue_status"):
            q_status = NotificationCRMService.process_dead_letter_queue(
                backlog_count=int(data["queue_backlog_count"])
            )
            assert q_status == str(data["expected_queue_status"])

if __name__ == "__main__":
    t = TestSCBSModules678()
    passed = 0
    print("=" * 80)
    print("RUNNING MODULE 06, 07 & 08 DIRECTLY (24 TEST CASES)")
    print("=" * 80)
    for row in CSV_TEST_DATA:
        mod = row["module"]
        if mod == "MOD-06":
            t.test_module_06_matchmaking(row)
        elif mod == "MOD-07":
            t.test_module_07_analytics(row)
        elif mod == "MOD-08":
            t.test_module_08_notification_crm(row)
        print(f"[{row['tc_id']}] [{mod}] {row['test_name']} ... PASSED")
        passed += 1
    print("=" * 80)
    print(f"MODULE 6, 7 & 8 RESULT: {passed}/24 PASSED")
    print("=" * 80)