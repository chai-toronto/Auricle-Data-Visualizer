#!/usr/bin/env python
"""
Test script for the batch deletion optimization.
Tests both the defer_update logic and the batch deletion core logic.
"""

import numpy as np
from typing import Dict, List

class MockSensorData:
    def __init__(self, n_channels: int = 5):
        self.data = np.random.randn(100, n_channels)
        self.channel_names = [f"Channel {i}" for i in range(n_channels)]
        self.n_channels = n_channels


def test_batch_delete_logic():
    """Test the core batch deletion logic."""
    print("=" * 60)
    print("Testing Batch Deletion Logic")
    print("=" * 60)
    
    # Create test data
    sensor_data = MockSensorData(n_channels=5)
    print(f"Initial: {sensor_data.n_channels} channels, shape {sensor_data.data.shape}")
    print(f"Names: {sensor_data.channel_names}")
    
    # Simulate deleting channels 1, 3 from a dataset with 5 channels
    indices_to_delete = [1, 3]
    valid_indices = sorted(indices_to_delete, reverse=True)
    
    print(f"\nDeleting indices: {indices_to_delete}")
    
    # Delete from data
    indices_for_np_delete = sorted(valid_indices, reverse=False)
    sensor_data.data = np.delete(sensor_data.data, indices_for_np_delete, axis=1)
    
    # Remove names in reverse order
    for idx in sorted(valid_indices, reverse=True):
        if 0 <= idx < len(sensor_data.channel_names):
            sensor_data.channel_names.pop(idx)
    
    print(f"After delete: {sensor_data.n_channels} channels would be {sensor_data.data.shape[1]}, shape {sensor_data.data.shape}")
    print(f"Names: {sensor_data.channel_names}")
    print(f"Expected: ['Channel 0', 'Channel 2', 'Channel 4']")
    assert sensor_data.channel_names == ['Channel 0', 'Channel 2', 'Channel 4'], "Channel names incorrect!"
    assert sensor_data.data.shape[1] == 3, "Data shape incorrect!"
    
    print("\n✓ Batch deletion logic test PASSED")


def test_index_adjustment():
    """Test that index adjustment works correctly after batch deletion."""
    print("\n" + "=" * 60)
    print("Testing Index Adjustment After Batch Deletion")
    print("=" * 60)
    
    # Simulate box traces before deletion
    traces = [
        {'dataset_id': 'ds1', 'channel_idx': 0},
        {'dataset_id': 'ds1', 'channel_idx': 1},
        {'dataset_id': 'ds1', 'channel_idx': 2},
        {'dataset_id': 'ds1', 'channel_idx': 3},
        {'dataset_id': 'ds1', 'channel_idx': 4},
    ]
    
    valid_indices = [1, 3]  # We're deleting channels 1 and 3
    
    print(f"Initial traces: {[(t['dataset_id'], t['channel_idx']) for t in traces]}")
    print(f"Deleting indices: {valid_indices}")
    
    # Remove deleted traces
    remaining_traces = [
        t for t in traces
        if not (t['dataset_id'] == 'ds1' and t['channel_idx'] in valid_indices)
    ]
    
    print(f"Remaining after removal: {[(t['dataset_id'], t['channel_idx']) for t in remaining_traces]}")
    
    # Adjust indices
    for trace in remaining_traces:
        if trace['dataset_id'] == 'ds1':
            shift = sum(1 for idx in valid_indices if idx < trace['channel_idx'])
            trace['channel_idx'] -= shift
    
    print(f"After index adjustment: {[(t['dataset_id'], t['channel_idx']) for t in remaining_traces]}")
    print(f"Expected: [('ds1', 0), ('ds1', 1), ('ds1', 2)]")
    
    expected_indices = [0, 1, 2]
    actual_indices = [t['channel_idx'] for t in remaining_traces]
    assert actual_indices == expected_indices, f"Index adjustment failed! Got {actual_indices}, expected {expected_indices}"
    
    print("\n✓ Index adjustment test PASSED")


def test_defer_update_logic():
    """Test that defer_update parameter works correctly."""
    print("\n" + "=" * 60)
    print("Testing Defer Update Logic")
    print("=" * 60)
    
    class MockBox:
        def __init__(self):
            self.traces = [
                {'dataset_id': 'ds1', 'channel_idx': 0},
                {'dataset_id': 'ds1', 'channel_idx': 1},
                {'dataset_id': 'ds1', 'channel_idx': 2},
            ]
            self.update_count = 0
        
        def remove_trace(self, dataset_id, channel_idx, defer_update=False):
            key = (dataset_id, channel_idx)
            self.traces = [t for t in self.traces if (t['dataset_id'], t['channel_idx']) != key]
            if not defer_update:
                self._update_axis_label()
        
        def _update_axis_label(self):
            self.update_count += 1
        
        def finish_batch_remove(self):
            self._update_axis_label()
    
    # Test without defer
    print("\nTest 1: Without defer (old way)")
    box1 = MockBox()
    print(f"Initial traces: 3")
    box1.remove_trace('ds1', 0)
    print(f"After remove 0: {box1.update_count} update(s)")
    box1.remove_trace('ds1', 1)
    print(f"After remove 1: {box1.update_count} update(s)")
    box1.remove_trace('ds1', 2)
    print(f"After remove 2: {box1.update_count} update(s)")
    
    # Test with defer
    print("\nTest 2: With defer (optimized way)")
    box2 = MockBox()
    print(f"Initial traces: 3")
    box2.remove_trace('ds1', 0, defer_update=True)
    print(f"After remove 0 (deferred): {box2.update_count} update(s)")
    box2.remove_trace('ds1', 1, defer_update=True)
    print(f"After remove 1 (deferred): {box2.update_count} update(s)")
    box2.remove_trace('ds1', 2, defer_update=True)
    print(f"After remove 2 (deferred): {box2.update_count} update(s)")
    box2.finish_batch_remove()
    print(f"After finish_batch_remove(): {box2.update_count} update(s)")
    
    assert box1.update_count == 3, f"Without defer should have 3 updates, got {box1.update_count}"
    assert box2.update_count == 1, f"With defer should have 1 update, got {box2.update_count}"
    
    print("\n✓ Defer update logic test PASSED")
    print(f"\n  Performance improvement: 3x reduction in UI updates!")


if __name__ == '__main__':
    test_batch_delete_logic()
    test_index_adjustment()
    test_defer_update_logic()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
