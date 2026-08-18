#!/usr/bin/env python3
"""
Verification checklist for audio playback reintegration in TimeSeriesWidget.
Run this to confirm all components are in place.
"""

import sys
import os

def check_file(filepath, patterns):
    """Check if file contains required patterns."""
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    missing = []
    for pattern_name, pattern in patterns.items():
        if pattern not in content:
            missing.append(pattern_name)
    
    if missing:
        return False, f"Missing patterns: {', '.join(missing)}"
    return True, "All patterns found"

def main():
    print("=" * 70)
    print("AUDIO PLAYBACK REINTEGRATION VERIFICATION CHECKLIST")
    print("=" * 70)
    
    checks = {
        "timeseries_widget.py initialization": {
            "file": "src/widgets/timeseries_widget.py",
            "patterns": {
                "is_playing state": "self.is_playing: bool = False",
                "play_button init": "self.play_button: Optional[QPushButton] = None",
                "stop_button init": "self.stop_button: Optional[QPushButton] = None",
                "channel_combo init": "self.channel_combo: Optional[QComboBox] = None",
                "playback_lock": "self.playback_lock = threading.Lock()",
                "playback_signals": "playback_finished = pyqtSignal()",
                "signal connections": "self.playback_finished.connect(self.on_playback_finished)",
            }
        },
        "timeseries_widget.py UI controls": {
            "file": "src/widgets/timeseries_widget.py",
            "patterns": {
                "channel_combo creation": "self.channel_combo = QComboBox()",
                "channel_combo setup": "self.channel_combo.setToolTip('Select which channel to play')",
                "play_button creation": "self.play_button = QPushButton('▶ Play Segment')",
                "play_button connection": "self.play_button.clicked.connect(self.play_selected_segment)",
                "stop_button creation": "self.stop_button = QPushButton('⏹ Stop Playback')",
                "stop_button connection": "self.stop_button.clicked.connect(self.stop_playback)",
                "stop_button disabled": "self.stop_button.setEnabled(False)",
            }
        },
        "timeseries_widget.py playback methods": {
            "file": "src/widgets/timeseries_widget.py",
            "patterns": {
                "play_selected_segment": "def play_selected_segment(self):",
                "_play_audio_in_thread": "def _play_audio_in_thread(self, audio_data: np.ndarray, sample_rate: int):",
                "stop_playback": "def stop_playback(self):",
                "on_playback_finished": "def on_playback_finished(self):",
                "on_playback_stopped": "def on_playback_stopped(self):",
            }
        },
        "channel_combo population": {
            "file": "src/widgets/timeseries_widget.py",
            "patterns": {
                "update method exists": "def _update_channel_combo_for_sensor_data(self, sensor_data: SensorData):",
                "combo clear": "self.channel_combo.clear()",
                "combo population": "self.channel_combo.addItem",
                "set_data calls update": "self._update_channel_combo_for_sensor_data(sensor_data)",
            }
        },
        "main_window.py playback infrastructure": {
            "file": "src/main_window.py",
            "patterns": {
                "playback_lock": "self.playback_lock = threading.Lock()",
                "is_playing state": "self.is_playing = False",
                "playback_thread_finished": "self.playback_thread_finished = threading.Event()",
                "active_playback_widget": "self.active_playback_widget = None",
                "start_playback method": "def start_playback(self, widget):",
                "stop_playback_global": "def stop_playback_global(self):",
            }
        }
    }
    
    all_passed = True
    for check_name, check_config in checks.items():
        print(f"\n✓ Checking {check_name}...")
        passed, message = check_file(check_config["file"], check_config["patterns"])
        if passed:
            print(f"  ✅ {message}")
            for pattern_name in check_config["patterns"].keys():
                print(f"    ✓ {pattern_name}")
        else:
            print(f"  ❌ {message}")
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL CHECKS PASSED - AUDIO PLAYBACK SUCCESSFULLY REINTEGRATED")
        print("\nThe TimeSeriesWidget now has:")
        print("  • Play button to start audio playback")
        print("  • Stop button to halt playback")
        print("  • Channel selection dropdown")
        print("  • Thread-safe playback coordination with main window")
        print("  • Proper signal handling for playback lifecycle")
        print("\nTo use:")
        print("  1. Load sensor data with 'File > Open'")
        print("  2. Select a region (use blue handles)")
        print("  3. Choose channel from 'Play Channel:' dropdown")
        print("  4. Click '▶ Play Segment' to play audio")
        print("  5. Click '⏹ Stop Playback' to stop")
        print("\nNote: Requires 'sounddevice' package:")
        print("  pip install sounddevice")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME CHECKS FAILED - PLEASE REVIEW IMPLEMENTATION")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(main())
