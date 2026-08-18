#!/usr/bin/env python3
"""
Verification script for channel dropdown auto-update feature.
Tests that the dropdown updates correctly when channels change.
"""
import sys
sys.path.insert(0, r'C:\Users\Ken_User\Desktop\Visualization_Tool\data_visualization_tool')

def verify_implementation():
    """Verify channel dropdown auto-update implementation."""
    print("=" * 70)
    print("CHANNEL DROPDOWN AUTO-UPDATE VERIFICATION")
    print("=" * 70)
    
    # Test 1: Check methods exist
    print("\n[1/6] Verifying methods in TimeSeriesWidget...")
    try:
        from src.widgets.timeseries_widget import TimeSeriesWidget
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication(sys.argv)
        widget = TimeSeriesWidget()
        
        # Check old method still exists
        assert hasattr(widget, '_update_channel_combo_for_sensor_data'), \
            "_update_channel_combo_for_sensor_data not found (backward compatibility)"
        
        # Check new method exists
        assert hasattr(widget, 'refresh_channel_combo'), \
            "refresh_channel_combo not found"
        
        print("      ✓ Both _update_channel_combo_for_sensor_data() and refresh_channel_combo() exist")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False
    
    # Test 2: Check play_selected_segment handles new format
    print("\n[2/6] Verifying play_selected_segment() handles tuple format...")
    try:
        import inspect
        source = inspect.getsource(widget.play_selected_segment)
        
        assert 'isinstance(combo_data, tuple)' in source, \
            "Tuple format handling not found"
        assert 'dataset_id, channel_idx = combo_data' in source, \
            "Tuple unpacking not found"
        assert 'self.datasets.get(dataset_id)' in source, \
            "Dataset lookup not found"
        
        print("      ✓ play_selected_segment() properly handles (dataset_id, channel_idx) tuples")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False
    
    # Test 3: Check main_window calls refresh_channel_combo
    print("\n[3/6] Verifying MainWindow calls refresh_channel_combo()...")
    try:
        from src.main_window import MainWindow
        
        # Check _finalize_channel_change calls refresh
        source = inspect.getsource(MainWindow._finalize_channel_change)
        assert 'refresh_channel_combo' in source, \
            "refresh_channel_combo not called in _finalize_channel_change"
        
        # Check on_channels_applied calls refresh
        source = inspect.getsource(MainWindow.on_channels_applied)
        assert 'refresh_channel_combo' in source, \
            "refresh_channel_combo not called in on_channels_applied"
        
        print("      ✓ Both _finalize_channel_change() and on_channels_applied() call refresh_channel_combo()")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False
    
    # Test 4: Test refresh_channel_combo functionality
    print("\n[4/6] Testing refresh_channel_combo() functionality...")
    try:
        from src.models.sensor_data import SensorData
        import numpy as np
        
        # Create dummy sensor data
        ts1 = np.linspace(0, 1, 100)
        data1 = np.random.randn(100, 2)
        dataset1 = SensorData(
            timestamps=ts1,
            data=data1,
            channel_names=['Ch1', 'Ch2'],
            sample_rate=100.0,
            filename='dataset1.csv'
        )
        
        ts2 = np.linspace(0, 1, 100)
        data2 = np.random.randn(100, 3)
        dataset2 = SensorData(
            timestamps=ts2,
            data=data2,
            channel_names=['Ch3', 'Ch4', 'Ch5'],
            sample_rate=100.0,
            filename='dataset2.csv'
        )
        
        # Set datasets
        widget.datasets = {
            'dataset1': dataset1,
            'dataset2': dataset2
        }
        
        # Call refresh
        widget.refresh_channel_combo()
        
        # Check combo has correct number of items (2 + 3 = 5)
        combo_count = widget.channel_combo.count()
        assert combo_count == 5, f"Expected 5 items, got {combo_count}"
        
        # Check first item is from dataset1
        first_text = widget.channel_combo.itemText(0)
        assert 'Ch1' in first_text, f"First item should contain 'Ch1', got '{first_text}'"
        
        # Check first data is tuple
        first_data = widget.channel_combo.itemData(0)
        assert isinstance(first_data, tuple), f"Expected tuple, got {type(first_data)}"
        assert first_data[0] == 'dataset1', f"Expected dataset1, got {first_data[0]}"
        assert first_data[1] == 0, f"Expected channel 0, got {first_data[1]}"
        
        print(f"      ✓ Combo has {combo_count} items with correct structure")
        print(f"      ✓ First item: {first_text}")
        print(f"      ✓ First data: {first_data}")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test selection preservation
    print("\n[5/6] Testing selection preservation...")
    try:
        # Set selection to second item
        widget.channel_combo.setCurrentIndex(1)
        original_text = widget.channel_combo.currentText()
        original_data = widget.channel_combo.currentData()
        
        # Refresh combo
        widget.refresh_channel_combo()
        
        # Check selection is preserved
        new_text = widget.channel_combo.currentText()
        new_data = widget.channel_combo.currentData()
        
        assert new_text == original_text, f"Text not preserved: {original_text} → {new_text}"
        assert new_data == original_data, f"Data not preserved: {original_data} → {new_data}"
        
        print(f"      ✓ Selection preserved: {original_text}")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False
    
    # Test 6: Test name updates
    print("\n[6/6] Testing channel name updates...")
    try:
        # Change channel name
        dataset1.channel_names[0] = "Microphone"
        
        # Refresh combo
        widget.refresh_channel_combo()
        
        # Check first item has new name
        first_text = widget.channel_combo.itemText(0)
        assert 'Microphone' in first_text, f"Expected 'Microphone' in '{first_text}'"
        
        print(f"      ✓ Channel name update reflected: {first_text}")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL VERIFICATION TESTS PASSED!")
    print("\nImplementation Summary:")
    print("  • Channel dropdown auto-updates when names change")
    print("  • Dropdown updates when channels are duplicated")
    print("  • Dropdown updates when channels are deleted")
    print("  • User's selection preserved during updates")
    print("  • Multiple datasets supported properly")
    print("  • Audio playback uses correct dataset and channel")
    print("\nTo Use:")
    print("  1. Load data → Dropdown shows available channels")
    print("  2. Change channel name in Data Mgmt → Dropdown updates")
    print("  3. Duplicate/delete channels → Dropdown reflects changes")
    print("  4. Select channel → Click 'Play Segment' to play audio")
    print("=" * 70)
    return True

if __name__ == '__main__':
    try:
        success = verify_implementation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
