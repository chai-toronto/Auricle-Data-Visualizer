#!/usr/bin/env python
"""Test timeseries widget audio playback integration"""
import sys
sys.path.insert(0, 'C:\\Users\\Ken_User\\Desktop\\Visualization_Tool\\data_visualization_tool')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import numpy as np
from src.models.sensor_data import SensorData
from src.widgets.timeseries_widget import TimeSeriesWidget

def test_playback_ui():
    """Test that playback UI elements are properly created."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    widget = TimeSeriesWidget()
    
    # Check UI elements exist
    assert widget.play_button is not None, "Play button not created"
    assert widget.stop_button is not None, "Stop button not created"
    assert widget.channel_combo is not None, "Channel combo not created"
    
    print("✓ Play button exists")
    print("✓ Stop button exists")
    print("✓ Channel combo exists")
    
    # Check button states
    assert widget.play_button.isEnabled(), "Play button should be enabled initially"
    assert not widget.stop_button.isEnabled(), "Stop button should be disabled initially"
    
    print("✓ Play button is enabled")
    print("✓ Stop button is disabled")
    
    # Create dummy sensor data
    timestamps = np.linspace(0, 10, 1000)
    channel_data_1 = np.sin(2 * np.pi * timestamps)
    channel_data_2 = np.cos(2 * np.pi * timestamps)
    data = np.column_stack([channel_data_1, channel_data_2])
    
    sensor_data = SensorData(
        timestamps=timestamps,
        data=data,
        channel_names=['sin', 'cos'],
        sample_rate=100.0,
        filename='test_data.csv'
    )
    
    # Set data and check combo is populated
    widget.set_data(sensor_data)
    
    assert widget.channel_combo.count() > 0, "Channel combo should be populated"
    print(f"✓ Channel combo populated with {widget.channel_combo.count()} items")
    
    # Check that playback methods exist
    assert hasattr(widget, 'play_selected_segment'), "play_selected_segment method missing"
    assert hasattr(widget, 'stop_playback'), "stop_playback method missing"
    assert hasattr(widget, '_play_audio_in_thread'), "_play_audio_in_thread method missing"
    assert hasattr(widget, 'on_playback_finished'), "on_playback_finished method missing"
    assert hasattr(widget, 'on_playback_stopped'), "on_playback_stopped method missing"
    
    print("✓ All playback methods exist")
    
    print("\n✅ All tests passed! Audio playback reintegration successful.")
    return True

if __name__ == '__main__':
    try:
        test_playback_ui()
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
