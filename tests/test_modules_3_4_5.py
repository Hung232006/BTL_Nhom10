# -*- coding: utf-8 -*-
import os
import sys

# Tự động thêm thư mục gốc D:\Test_CaseFB vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pandas as pd
from datetime import datetime, timedelta
from services.booking_payment_pos_service import MockBookingService, MockPaymentService, MockPOS

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

CSV_PATH = find_csv_file(["FPBMS_Test_Data.csv", "test_module_3_4_5.csv"])

def load_csv_data():
    if not CSV_PATH:
        return []
    return pd.read_csv(CSV_PATH).fillna("").to_dict(orient="records")

CSV_TEST_DATA = load_csv_data()

class TestModules345DataDriven:

    @pytest.mark.parametrize("row", CSV_TEST_DATA, ids=[f"{r.get('case_id')}" for r in CSV_TEST_DATA])
    def test_ddt_csv_scenarios(self, row):
        case_id = row['case_id']
        module = row['module']
        expected_status = str(row['expected_status'])
        expected_code = int(float(row['expected_code'])) if row.get('expected_code') else 200

        if module == 'Booking':
            svc = MockBookingService()
            if case_id == 'TC-03-01':
                res = svc.lock_slot(row['user_id'], row['slot_id'])
                assert res['is_success'] is True
                assert svc.get_slot_status(row['slot_id']) == expected_status
            elif case_id == 'TC-03-02':
                svc.lock_slot('U1', row['slot_id'])
                res2 = svc.lock_slot('U2', row['slot_id'])
                assert res2['message'] == expected_status
            elif case_id == 'TC-03-03':
                svc.lock_slot(row['user_id'], row['slot_id'])
                svc.expire_slots(datetime.now() + timedelta(minutes=11))
                assert svc.get_slot_status(row['slot_id']) == expected_status
            elif case_id == 'TC-03-04':
                svc.lock_slot(row['user_id'], row['slot_id'])
                svc.expire_slots(datetime.now() + timedelta(minutes=9))
                assert svc.get_slot_status(row['slot_id']) == expected_status
            elif case_id == 'TC-03-05':
                res = svc.lock_slot(row['user_id'], row['slot_id'])
                assert res['is_success'] is False
                assert res['message'] == expected_status
            elif case_id == 'TC-03-06':
                svc.lock_slot('U1', row['slot_id'])
                assert svc.cancel_booking('U1', row['slot_id']) is True
            elif case_id == 'TC-03-07':
                svc.lock_slot('U1', row['slot_id'])
                assert svc.cancel_booking('U2', row['slot_id']) is False

        elif module == 'Payment':
            svc = MockPaymentService()
            if case_id in ['TC-04-01', 'TC-04-02', 'TC-04-03']:
                amount = float(row['amount'])
                rate = float(row['rate'])
                assert svc.calculate_deposit(amount, rate) == float(expected_status)
            elif case_id == 'TC-04-04':
                res = svc.process_webhook({'order_id': 'O1', 'amount': 1000}, 'OK', 'OK')
                assert res['status_code'] == expected_code
                assert res['order_status'] == expected_status
            elif case_id == 'TC-04-05':
                res = svc.process_webhook({'order_id': 'O1'}, 'BAD', 'OK')
                assert res['status_code'] == expected_code
                assert res['message'] == expected_status
            elif case_id == 'TC-04-06':
                res = svc.process_webhook({'order_id': 'O1'}, 'OK', 'OK')
                assert res['status_code'] == expected_code
                assert res['message'] == expected_status
            elif case_id == 'TC-04-07':
                res = svc.process_webhook({'order_id': 'O1', 'amount': float(row['amount'])}, 'OK', 'OK')
                assert res['status_code'] == expected_code
                assert res['message'] == expected_status
            elif case_id == 'TC-04-08':
                payload = {'order_id': 'O1', 'amount': float(row['amount']), 'tx_id': row['tx_id']}
                svc.process_webhook(payload, 'OK', 'OK')
                res = svc.process_webhook(payload, 'OK', 'OK')
                assert res['message'] == expected_status
            elif case_id == 'TC-04-09':
                assert svc.calculate_refund(float(row['amount']), int(float(row['hours_before']))) == float(expected_status)
            elif case_id == 'TC-04-10':
                res = svc.process_webhook({'order_id': 'O1', 'amount': 1000}, 'OK', 'OK')
                assert res.get('latency_ms', 999) < 500

        elif module == 'POS':
            pos = MockPOS({'water': 10, 'bib': 0})
            if case_id == 'TC-05-01':
                assert pos.add_item('water', 2) is True
                assert pos.inventory['water'] == 8
            elif case_id == 'TC-05-02':
                assert pos.add_item('bib', 1) is False
            elif case_id == 'TC-05-03':
                pos = MockPOS({'water': 10, 'bib': 5})
                pos.add_item('water', 2)
                pos.add_item('bib', 1)
                assert pos.get_bill_total() == float(expected_status)
            elif case_id == 'TC-05-04':
                assert pos.add_item('water', -1) is False
            elif case_id == 'TC-05-05':
                pos = MockPOS({'water': 8})
                pos.cart = {'water': 2}
                assert pos.remove_item('water', 1) is True
                assert pos.inventory['water'] == 9
            elif case_id == 'TC-05-06':
                pos = MockPOS({'water': 5})
                assert pos.add_item('water', 5) is True
                assert pos.inventory['water'] == 0
            elif case_id == 'TC-05-07':
                pos.add_item('water', 2)
                assert pos.get_bill_total(overtime_fee=float(row['overtime_fee'])) == float(expected_status)
            elif case_id == 'TC-05-08':
                assert pos.get_bill_total(overtime_fee=float(row['overtime_fee'])) is False

if __name__ == "__main__":
    t = TestModules345DataDriven()
    passed = 0
    print("=" * 80)
    print("RUNNING MODULE 03, 04 & 05 DIRECTLY (25 TEST CASES)")
    print("=" * 80)
    for row in CSV_TEST_DATA:
        t.test_ddt_csv_scenarios(row)
        print(f"[{row['case_id']}] [MOD-03/04/05-{row['module']}] Test {row['case_id']} ... PASSED")
        passed += 1
    print("=" * 80)
    print(f"MODULE 3, 4 & 5 RESULT: {passed}/25 PASSED")
    print("=" * 80)