#!/usr/bin/env python3
import os
import sys
import traceback

# Set the environment variable BEFORE importing Qt
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

try:
    from src.widgets.load_dialog import LoadDialog
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    print("=== LOADDIALOG TEST RESULTS ===")
    print()

    # TEST 1: Initial state
    print("TEST 1: Initial State (No changes)")
    dialog = LoadDialog('test.csv', [])

    time_checked = dialog.time_checkbox.isChecked()
    sample_index_checked = dialog.sample_index_checkbox.isChecked()

    print(f"  Time checkbox checked: {time_checked}")
    print(f"  Sample index checkbox checked: {sample_index_checked}")

    result = dialog.get_result()
    print(f"  get_result() = {result}")
    print(f"  timestamp_type value: {result.get('timestamp_type')}")

    assert time_checked == True, "Time should be checked by default"
    assert sample_index_checked == False, "Sample index should be unchecked by default"
    assert result.get('timestamp_type') == 'time', "timestamp_type should be 'time'"
    print("  ✓ PASS: Defaults are correct")
    print()

    # TEST 2: Check Sample Index
    print("TEST 2: After Checking Sample Index")
    dialog.sample_index_checkbox.setChecked(True)

    time_checked = dialog.time_checkbox.isChecked()
    sample_index_checked = dialog.sample_index_checkbox.isChecked()

    print(f"  Time checkbox checked: {time_checked}")
    print(f"  Sample index checkbox checked: {sample_index_checked}")

    result = dialog.get_result()
    print(f"  get_result() = {result}")
    print(f"  timestamp_type value: {result.get('timestamp_type')}")

    assert sample_index_checked == True, "Sample index should be checked"
    assert time_checked == False, "Time should be unchecked (exclusive group)"
    assert result.get('timestamp_type') == 'sample_index', "timestamp_type should be 'sample_index'"
    print("  ✓ PASS: Sample index toggle works correctly")
    print()

    print("=== ALL TESTS PASSED ===")
    sys.exit(0)

except Exception as e:
    print("ERROR DURING TEST:")
    print(traceback.format_exc())
    sys.exit(1)
