# -*- coding: utf-8 -*-
"""
SCBS Complete Unified Test Runner for All 8 Modules (71 Test Cases)
Run directly via: python tests/run_all_tests.py
"""
import os
import sys

# Thêm đường dẫn gốc vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_modules_1_2 import TestModule1And2DataDriven
from tests.test_modules_3_4_5 import TestModules345DataDriven, CSV_TEST_DATA as CSV_345
from tests.test_modules_6_7_8 import TestSCBSModules678, CSV_TEST_DATA as CSV_678, CSV_PATH as PATH_678

def run_suite():
    print("=" * 85)
    print("SCBS UNIFIED AUTOMATED TEST SUITE - ALL 8 MODULES (71 TEST CASES TOTAL)")
    print("=" * 85)
    
    passed, failed = 0, 0
    
    # 1. RUN MODULE 01 & 02 (22 TCs)
    print("\n--- [PHASE 1] MODULE 01 & 02 (AUTH, RBAC, PRICING, SLOTS) ---")
    t1_2 = TestModule1And2DataDriven()
    m12_methods = [m for m in dir(t1_2) if m.startswith("test_tc")]
    for method_name in sorted(m12_methods):
        try:
            getattr(t1_2, method_name)()
            tc_code = method_name.split("_")[1].upper()
            print(f"[{tc_code}] [MOD-01/02] {method_name} ... PASSED")
            passed += 1
        except Exception as e:
            print(f"[{method_name}] [MOD-01/02] ... FAILED ({e})")
            failed += 1

    # 2. RUN MODULE 03, 04 & 05 (25 TCs)
    print("\n--- [PHASE 2] MODULE 03, 04 & 05 (BOOKING, PAYMENT, POS) ---")
    if not CSV_345:
        print("[ERROR] Không tìm thấy dữ liệu CSV cho Module 3, 4 & 5 (FPBMS_Test_Data.csv)!")
    else:
        t345 = TestModules345DataDriven()
        for row in CSV_345:
            tc_id = row['case_id']
            mod = row['module']
            try:
                t345.test_ddt_csv_scenarios(row)
                print(f"[{tc_id}] [MOD-03/04/05-{mod}] Test {tc_id} ... PASSED")
                passed += 1
            except Exception as e:
                print(f"[{tc_id}] [MOD-03/04/05-{mod}] ... FAILED ({e})")
                failed += 1

    # 3. RUN MODULE 06, 07 & 08 (24 TCs)
    print("\n--- [PHASE 3] MODULE 06, 07 & 08 (MATCHMAKING, ANALYTICS, NOTIF/CRM) ---")
    if not CSV_678:
        print("[ERROR] Không tìm thấy dữ liệu CSV cho Module 6, 7 & 8!")
    else:
        t678 = TestSCBSModules678()
        for row in CSV_678:
            tc_id = row["tc_id"]
            mod = row["module"]
            test_name = row["test_name"]
            try:
                if mod == "MOD-06":
                    t678.test_module_06_matchmaking(row)
                elif mod == "MOD-07":
                    t678.test_module_07_analytics(row)
                elif mod == "MOD-08":
                    t678.test_module_08_notification_crm(row)
                print(f"[{tc_id}] [{mod}] {test_name} ... PASSED")
                passed += 1
            except Exception as e:
                print(f"[{tc_id}] [{mod}] {test_name} ... FAILED ({e})")
                failed += 1

    print("\n" + "=" * 85)
    print(f"FINAL SUMMARY: {passed} PASSED, {failed} FAILED | TOTAL: {passed + failed}/71 TEST CASES")
    print("=" * 85)

if __name__ == "__main__":
    run_suite()