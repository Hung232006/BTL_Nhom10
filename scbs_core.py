# -*- coding: utf-8 -*-
"""
SCBS Core Mock Services for Modules 1 & 2
"""
import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta

class AuthService:
    def __init__(self):
        self.users = {}
        self.otp_store = {}
        self.revoked_tokens = set()
        self.audit_logs = []

    def request_otp(self, phone, channel="zalo_zns", current_time=0.0):
        otp = "123456"
        self.otp_store[phone] = {"otp": otp, "created_at": current_time, "channel": channel}
        return otp

    def verify_otp(self, phone, otp, current_time=0.0):
        data = self.otp_store.get(phone)
        if not data:
            return False
        if current_time - data["created_at"] > 120.0:  # Boundary TTL 120s
            return False
        return data["otp"] == otp

    def register_user(self, user_id, phone, name, role="Customer"):
        user = {
            "user_id": user_id,
            "phone": phone,
            "name": name,
            "role": role,
            "status": "Active",
            "skill_badge": "Tập sự",
            "required_deposit_rate": 0.30,
            "no_show_history": [],
            "is_flagged": False
        }
        self.users[user_id] = user
        return user

    def login(self, user_id):
        user = self.users.get(user_id)
        if not user or user["status"] != "Active":
            raise ValueError("Tài khoản không hợp lệ hoặc đã bị khóa")
        
        payload = {
            "sub": user_id,
            "role": user["role"],
            "permissions": ["search_court", "book_court"] if user["role"] == "Customer" else ["search_court", "book_court", "set_pricing"]
        }
        access_token = base64.b64encode(json.dumps(payload).encode()).decode()
        return {
            "token_type": "Bearer",
            "access_token": access_token,
            "refresh_token": "refresh_token_sample",
            "expires_in": 900
        }

    def decode_and_verify_token(self, token):
        if token in self.revoked_tokens:
            raise ValueError("Blacklisted")
        return json.loads(base64.b64decode(token.encode()).decode())

    def authorize(self, token, permission):
        try:
            payload = self.decode_and_verify_token(token)
            return permission in payload.get("permissions", [])
        except ValueError:
            return False

    def update_skill_badge(self, user_id, matches_played, win_rate):
        user = self.users[user_id]
        if matches_played >= 50 and win_rate >= 0.70:
            badge = "Chuyên nghiệp"
        elif matches_played >= 20 and win_rate >= 0.50:
            badge = "Khá"
        elif matches_played >= 5:
            badge = "Phủi"
        else:
            badge = "Tập sự"
        user["skill_badge"] = badge
        return badge

    def record_no_show(self, user_id, timestamp):
        user = self.users[user_id]
        user["no_show_history"].append(timestamp)
        now = timestamp
        recent_no_shows = [t for t in user["no_show_history"] if (now - t).days <= 30]
        if len(recent_no_shows) >= 3:
            user["is_flagged"] = True
            user["required_deposit_rate"] = 1.00
            return True
        return False

    def suspend_user_by_admin(self, admin_id, target_user_id, reason):
        user = self.users[target_user_id]
        user["status"] = "Suspended"
        self.audit_logs.append({"admin_id": admin_id, "target": target_user_id, "action": "SUSPEND_USER", "reason": reason})


class CourtCollisionManager:
    def __init__(self):
        self.hierarchy = {"P11-01": ["P5-01", "P5-02", "P5-03"]}
        self.child_to_parent = {"P5-01": "P11-01", "P5-02": "P11-01", "P5-03": "P11-01"}
        self.slots = {}

    def get_status(self, court_id, date_str, slot):
        return self.slots.get(f"{court_id}:{date_str}:{slot}", "AVAILABLE")

    def lock_court(self, court_id, date_str, slot, target_state="HELD"):
        key = f"{court_id}:{date_str}:{slot}"
        current = self.get_status(court_id, date_str, slot)
        if current in ["HELD", "CONFIRMED", "COLLISION_LOCKED"]:
            raise ValueError("COLLISION_LOCKED")

        self.slots[key] = target_state

        if court_id in self.hierarchy:
            for child_id in self.hierarchy[court_id]:
                self.slots[f"{child_id}:{date_str}:{slot}"] = "COLLISION_LOCKED"
        elif court_id in self.child_to_parent:
            parent_id = self.child_to_parent[court_id]
            self.slots[f"{parent_id}:{date_str}:{slot}"] = "COLLISION_LOCKED"


class SlotScheduler:
    @staticmethod
    def generate_rolling_schedule(court_ids, start_date, duration_mins=90, days=30):
        schedule = []
        for d in range(days):
            day_dt = start_date + timedelta(days=d)
            for court in court_ids:
                for slot_idx in range(4):
                    schedule.append({
                        "court_id": court,
                        "date": day_dt.strftime("%Y-%m-%d"),
                        "slot_index": slot_idx,
                        "status": "AVAILABLE",
                        "color": "#FFFFFF"
                    })
        return schedule


class DynamicPricingEngine:
    @staticmethod
    def calculate_price(base_price, slot_start_hour, is_weekend, coupon_discount=0, custom_deposit_rate=0.30):
        price = base_price
        if slot_start_hour >= 17:
            price *= 1.3
        if is_weekend:
            price *= 1.2
        price -= coupon_discount
        total_price = int(price)
        required_deposit = int(total_price * custom_deposit_rate)
        return {"total_price": total_price, "required_deposit": required_deposit}


class RedisSoftLockSimulator:
    def __init__(self, ttl_seconds=600):
        self.locks = {}
        self.ttl = ttl_seconds

    def acquire_lock(self, slot_key, user_id, current_time=0.0):
        if slot_key in self.locks:
            lock_data = self.locks[slot_key]
            if current_time - lock_data["time"] < self.ttl:
                return False
        self.locks[slot_key] = {"user_id": user_id, "time": current_time}
        return True

    def is_locked(self, slot_key, current_time=0.0):
        if slot_key not in self.locks:
            return False
        return (current_time - self.locks[slot_key]["time"]) < self.ttl


class TieredRefundCalculator:
    @staticmethod
    def calculate_refund(deposit_amount, match_time, cancel_time):
        hours_diff = (match_time - cancel_time).total_seconds() / 3600.0
        if hours_diff > 24:
            rate = 1.00
        elif 12 <= hours_diff <= 24:
            rate = 0.50
        else:
            rate = 0.00
        refund_amount = deposit_amount * rate
        forfeited_amount = deposit_amount - refund_amount
        return {"refund_rate": rate, "refund_amount": refund_amount, "forfeited_amount": forfeited_amount}


class QRCheckInSecurity:
    SECRET_KEY = "SCBS_SECRET_KEY"

    def generate_qr_payload(self, booking_id, court_id, date_str, slot_str):
        payload = f"bid={booking_id}&cid={court_id}&dt={date_str}&sl={slot_str}"
        signature = hmac.new(self.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return {"qr_string": f"{payload}&sig={signature}", "signature": signature}

    def verify_qr(self, qr_string):
        try:
            parts = qr_string.split("&sig=")
            if len(parts) != 2:
                return {"valid": False, "reason": "Mã QR không đúng định dạng"}
            payload, sig = parts[0], parts[1]
            expected_sig = hmac.new(self.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return {"valid": False, "reason": "Mã QR giả mạo"}
            kv_pairs = dict(p.split("=") for p in payload.split("&"))
            return {"valid": True, "payload": kv_pairs}
        except Exception as e:
            return {"valid": False, "reason": str(e)}