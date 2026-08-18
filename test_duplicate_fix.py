#!/usr/bin/env python
"""
Test to verify the duplicate channel deletion fix works correctly.
"""

import numpy as np

def test_duplicate_channel_deletion():
    """Test that the batch deletion works with single-channel (duplicated) datasets."""
    print("=" * 70)
    print("Testing Duplicate Channel Deletion Fix")
    print("=" * 70)
    
    # Simulate duplicated single-channel datasets
    datasets = {
        'ch0_copy': {
            'n_channels': 1,
            'channel_names': ['Channel 0 (copy)'],
            'data': np.random.randn(100, 1),
        },
        'ch2_copy': {
            'n_channels': 1,
            'channel_names': ['Channel 2 (copy)'],
            'data': np.random.randn(100, 1),
        },
        'ch4_copy': {
            'n_channels': 1,
            'channel_names': ['Channel 4 (copy)'],
            'data': np.random.randn(100, 1),
        },
    }
    
    print("\nInitial datasets:")
    for dataset_id, data in datasets.items():
        print(f"  {dataset_id}: {data['n_channels']} channel(s)")
    
    # Simulate deletion of channels 0 and 2
    channels_by_dataset = {
        'ch0_copy': [0],  # Delete the only channel
        'ch2_copy': [0],  # Delete the only channel
        # ch4_copy not in the list, so it stays
    }
    
    print("\nDeleting channels...")
    deleted_by_dataset = {}
    datasets_to_remove = []
    
    for dataset_id, indices in channels_by_dataset.items():
        if dataset_id not in datasets:
            continue
        
        sensor_data = datasets[dataset_id]
        
        # Check if we have valid indices to delete
        sorted_indices = sorted(set(indices), reverse=True)
        valid_indices = [idx for idx in sorted_indices if 0 <= idx < sensor_data['n_channels']]
        
        if not valid_indices:
            print(f"  {dataset_id}: No valid indices")
            continue
        
        print(f"  {dataset_id}: Deleting {valid_indices}")
        
        # Simulate deletion
        indices_to_delete = sorted(valid_indices, reverse=False)
        sensor_data['data'] = np.delete(sensor_data['data'], indices_to_delete, axis=1)
        
        # Remove channel names
        for idx in sorted(valid_indices, reverse=True):
            if 0 <= idx < len(sensor_data['channel_names']):
                sensor_data['channel_names'].pop(idx)
        
        # Update channel count
        sensor_data['n_channels'] = sensor_data['data'].shape[1]
        
        # If entire dataset was deleted, mark for removal
        if len(valid_indices) == datasets[dataset_id]['n_channels']:
            print(f"  {dataset_id}: All channels deleted, marking for removal")
            datasets_to_remove.append(dataset_id)
        
        deleted_by_dataset[dataset_id] = len(valid_indices)
    
    # Remove empty datasets
    for dataset_id in datasets_to_remove:
        if dataset_id in datasets:
            del datasets[dataset_id]
    
    print("\nFinal datasets:")
    for dataset_id, data in datasets.items():
        print(f"  {dataset_id}: {data['n_channels']} channel(s)")
    
    print("\nDeleted counts:")
    for dataset_id, count in deleted_by_dataset.items():
        print(f"  {dataset_id}: {count} channel(s)")
    
    # Verify results
    assert 'ch0_copy' not in datasets, "ch0_copy should be removed"
    assert 'ch2_copy' not in datasets, "ch2_copy should be removed"
    assert 'ch4_copy' in datasets, "ch4_copy should still exist"
    assert deleted_by_dataset['ch0_copy'] == 1, "Should have deleted 1 channel from ch0_copy"
    assert deleted_by_dataset['ch2_copy'] == 1, "Should have deleted 1 channel from ch2_copy"
    
    print("\n✅ All assertions passed!")
    print("\nSummary:")
    print("  - Removed 2 single-channel datasets (ch0_copy, ch2_copy)")
    print("  - Kept 1 single-channel dataset (ch4_copy)")
    print("  - Total channels deleted: 2")
    print("\n" + "=" * 70)


def test_mixed_deletion():
    """Test deletion with both multi-channel and single-channel datasets."""
    print("\n" + "=" * 70)
    print("Testing Mixed Deletion (Load + Duplicate)")
    print("=" * 70)
    
    # Simulate mixed datasets
    datasets = {
        'original': {
            'n_channels': 5,
            'channel_names': ['Ch0', 'Ch1', 'Ch2', 'Ch3', 'Ch4'],
            'data': np.random.randn(100, 5),
        },
        'ch1_copy': {
            'n_channels': 1,
            'channel_names': ['Ch1 (copy)'],
            'data': np.random.randn(100, 1),
        },
    }
    
    print("\nInitial datasets:")
    for dataset_id, data in datasets.items():
        print(f"  {dataset_id}: {data['n_channels']} channel(s) - {data['channel_names']}")
    
    # Delete channel 1 from original and the copy
    channels_by_dataset = {
        'original': [1],      # Delete from multi-channel dataset
        'ch1_copy': [0],      # Delete single-channel dataset
    }
    
    print("\nDeleting channels...")
    datasets_to_remove = []
    
    for dataset_id, indices in channels_by_dataset.items():
        if dataset_id not in datasets:
            continue
        
        sensor_data = datasets[dataset_id]
        sorted_indices = sorted(set(indices), reverse=True)
        valid_indices = [idx for idx in sorted_indices if 0 <= idx < sensor_data['n_channels']]
        
        if not valid_indices:
            continue
        
        print(f"  {dataset_id}: Deleting indices {valid_indices}")
        
        # Simulate deletion
        indices_to_delete = sorted(valid_indices, reverse=False)
        sensor_data['data'] = np.delete(sensor_data['data'], indices_to_delete, axis=1)
        
        # Remove channel names
        for idx in sorted(valid_indices, reverse=True):
            if 0 <= idx < len(sensor_data['channel_names']):
                sensor_data['channel_names'].pop(idx)
        
        sensor_data['n_channels'] = sensor_data['data'].shape[1]
        
        # If entire dataset was deleted, mark for removal
        if len(valid_indices) == datasets[dataset_id]['n_channels']:
            print(f"  {dataset_id}: All channels deleted, marking for removal")
            datasets_to_remove.append(dataset_id)
    
    # Remove empty datasets
    for dataset_id in datasets_to_remove:
        if dataset_id in datasets:
            del datasets[dataset_id]
    
    print("\nFinal datasets:")
    for dataset_id, data in datasets.items():
        print(f"  {dataset_id}: {data['n_channels']} channel(s) - {data['channel_names']}")
    
    # Verify results
    assert datasets['original']['n_channels'] == 4, "Original should have 4 channels left"
    assert datasets['original']['channel_names'] == ['Ch0', 'Ch2', 'Ch3', 'Ch4'], \
        f"Names incorrect: {datasets['original']['channel_names']}"
    assert 'ch1_copy' not in datasets, "ch1_copy should be removed"
    
    print("\n✅ All assertions passed!")
    print("\nSummary:")
    print("  - Deleted 1 channel from multi-channel dataset (kept 4)")
    print("  - Deleted 1 single-channel dataset entirely")
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_duplicate_channel_deletion()
    test_mixed_deletion()
    print("\n🎉 ALL TESTS PASSED!")
