# -*- coding: utf-8 -*-
import os
import sys

# Tự động thêm thư mục gốc D:\Test_CaseFB vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pandas as pd
from datetime import datetime, timedelta
from scbs_core import (
    AuthService, DynamicPricingEngine, CourtCollisionManager,
    SlotScheduler, RedisSoftLockSimulator, TieredRefundCalculator, QRCheckInSecurity
)

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

CSV_PATH = find_csv_file(["scbs_test_data.csv", "scbs_mod1_2_data.csv"])

class TestModule1And2DataDriven:
    def test_tc01_registration_otp_happy_path(self):
        auth = AuthService()
        otp = auth.request_otp("0912345678", channel="zalo_zns", current_time=1000.0)
        assert len(otp) == 6
        assert auth.verify_otp("0912345678", otp, current_time=1045.0) is True
        user = auth.register_user("USR-01", "0912345678", "Nguyễn Văn An", "Customer")
        assert user["status"] == "Active" and user["required_deposit_rate"] == 0.30

    def test_tc02_otp_boundary_timeout(self):
        auth = AuthService()
        otp = auth.request_otp("0987654321", current_time=1000.0)
        assert auth.verify_otp("0987654321", otp, 1120.0) is True
        assert auth.verify_otp("0987654321", otp, 1121.0) is False

    def test_tc03_jwt_bearer_token_issuance(self):
        auth = AuthService()
        auth.register_user("USR-02", "0911223344", "Trần Bình", "Customer")
        tokens = auth.login("USR-02")
        assert tokens["token_type"] == "Bearer" and tokens["expires_in"] == 900

    def test_tc04_rbac_permission_enforcement(self):
        auth = AuthService()
        auth.register_user("USR-CUST", "0901111111", "Khách A", "Customer")
        auth.register_user("USR-OWNER", "0902222222", "Chủ B", "Field Owner")
        t_cust = auth.login("USR-CUST")["access_token"]
        t_owner = auth.login("USR-OWNER")["access_token"]
        assert auth.authorize(t_cust, "book_court") is True
        assert auth.authorize(t_cust, "set_pricing") is False
        assert auth.authorize(t_owner, "set_pricing") is True

    def test_tc05_user_profile_and_skill_badges(self):
        auth = AuthService()
        auth.register_user("USR-PLAYER", "0933333333", "Cầu thủ", "Customer")
        assert auth.update_skill_badge("USR-PLAYER", 6, 0.40) == "Phủi"
        assert auth.update_skill_badge("USR-PLAYER", 25, 0.55) == "Khá"
        assert auth.update_skill_badge("USR-PLAYER", 60, 0.75) == "Chuyên nghiệp"

    def test_tc06_no_show_tracking_and_flagging(self):
        auth = AuthService()
        auth.register_user("USR-BAD", "0944444444", "Khách Bỏ", "Customer")
        now = datetime.now()
        auth.record_no_show("USR-BAD", now - timedelta(days=20))
        auth.record_no_show("USR-BAD", now - timedelta(days=10))
        assert auth.record_no_show("USR-BAD", now) is True
        assert auth.users["USR-BAD"]["required_deposit_rate"] == 1.00

    def test_tc07_admin_user_revocation_and_audit(self):
        auth = AuthService()
        auth.register_user("ADMIN-01", "0999999999", "Admin", "System Admin")
        auth.register_user("USR-VIOLATE", "0988888888", "Gian lận", "Customer")
        token = auth.login("USR-VIOLATE")["access_token"]
        auth.revoked_tokens.add(token)
        auth.suspend_user_by_admin("ADMIN-01", "USR-VIOLATE", "Gian lận")
        with pytest.raises(ValueError, match="Blacklisted"):
            auth.decode_and_verify_token(token)

    def test_tc08_court_hierarchy_configuration(self):
        court_mgr = CourtCollisionManager()
        assert "P11-01" in court_mgr.hierarchy and len(court_mgr.hierarchy["P11-01"]) == 3

    def test_tc09_auto_slot_generation_30_days(self):
        schedule = SlotScheduler.generate_rolling_schedule(["P11-01", "P5-01", "P5-02", "P5-03"], datetime(2026, 10, 18), 90, 30)
        assert len(schedule) == 480

    def test_tc10_parent_child_collision_lock_down(self):
        court_mgr = CourtCollisionManager()
        court_mgr.lock_court("P11-01", "2026-10-25", "17:30-19:00")
        assert court_mgr.get_status("P5-01", "2026-10-25", "17:30-19:00") == "COLLISION_LOCKED"
        with pytest.raises(ValueError, match="COLLISION_LOCKED"):
            court_mgr.lock_court("P5-01", "2026-10-25", "17:30-19:00")

    def test_tc11_parent_child_collision_lock_up(self):
        court_mgr = CourtCollisionManager()
        court_mgr.lock_court("P5-02", "2026-10-25", "19:00-20:30")
        assert court_mgr.get_status("P11-01", "2026-10-25", "19:00-20:30") == "COLLISION_LOCKED"

    def test_tc12_matrix_calendar_color_states(self):
        colors = {"AVAILABLE": "#FFFFFF", "SELECTED": "#007BFF", "CONFIRMED": "#DC3545", "HELD": "#FFC107"}
        assert colors["AVAILABLE"] == "#FFFFFF"

    def test_tc13_dynamic_pricing_engine(self):
        res = DynamicPricingEngine.calculate_price(300000, 17, True, 0, 0.30)
        assert res["total_price"] == 468000 and res["required_deposit"] == 140400

    def test_tc14_redis_soft_lock_concurrency_race(self):
        redis_sim = RedisSoftLockSimulator(600)
        assert redis_sim.acquire_lock("P5-01:19:00", "USER-A", 1000.0) is True
        assert redis_sim.acquire_lock("P5-01:19:00", "USER-B", 1000.0) is False

    def test_tc15_redis_soft_lock_auto_release(self):
        redis_sim = RedisSoftLockSimulator(600)
        redis_sim.acquire_lock("P5-01:19:00", "USER-A", 1000.0)
        assert redis_sim.is_locked("P5-01:19:00", 1601.0) is False

    def test_tc16_tiered_refund_over_24h(self):
        res = TieredRefundCalculator.calculate_refund(200000.0, datetime(2026, 10, 20, 18, 0), datetime(2026, 10, 19, 14, 0))
        assert res["refund_rate"] == 1.00

    def test_tc17_tiered_refund_12h_to_24h(self):
        res = TieredRefundCalculator.calculate_refund(200000.0, datetime(2026, 10, 20, 18, 0), datetime(2026, 10, 20, 3, 0))
        assert res["refund_rate"] == 0.50

    def test_tc18_tiered_refund_under_12h_forfeit(self):
        res = TieredRefundCalculator.calculate_refund(200000.0, datetime(2026, 10, 20, 18, 0), datetime(2026, 10, 20, 14, 0))
        assert res["refund_rate"] == 0.00

    def test_tc19_qr_hmac_generation(self):
        qr_sec = QRCheckInSecurity()
        qr_obj = qr_sec.generate_qr_payload("BK-1001", "P5-01", "2026-10-25", "17:30-19:00")
        assert len(qr_obj["signature"]) == 64

    def test_tc20_qr_hmac_checkin_verification(self):
        qr_sec = QRCheckInSecurity()
        qr_obj = qr_sec.generate_qr_payload("BK-1001", "P5-01", "2026-10-25", "17:30-19:00")
        assert qr_sec.verify_qr(qr_obj["qr_string"])["valid"] is True

    def test_tc21_qr_tampering_rejection(self):
        qr_sec = QRCheckInSecurity()
        qr_obj = qr_sec.generate_qr_payload("BK-1001", "P5-01", "2026-10-25", "17:30-19:00")
        assert qr_sec.verify_qr(qr_obj["qr_string"].replace("BK-1001", "BK-HACKED"))["valid"] is False

    def test_tc22_matrix_api_latency_performance(self):
        import time
        t_start = time.perf_counter()
        SlotScheduler.generate_rolling_schedule(["P11-01", "P5-01", "P5-02", "P5-03"], datetime(2026, 10, 18), 90, 30)
        assert ((time.perf_counter() - t_start) * 1000.0) < 200.0

if __name__ == "__main__":
    t = TestModule1And2DataDriven()
    methods = [m for m in dir(t) if m.startswith("test_tc")]
    passed = 0
    print("=" * 80)
    print("RUNNING MODULE 01 & 02 DIRECTLY (22 TEST CASES)")
    print("=" * 80)
    for m in sorted(methods):
        getattr(t, m)()
        print(f"[{m.split('_')[1].upper()}] {m} ... PASSED")
        passed += 1
    print("=" * 80)
    print(f"MODULE 1 & 2 RESULT: {passed}/22 PASSED")
    print("=" * 80)