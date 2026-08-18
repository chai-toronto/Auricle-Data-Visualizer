"""
Export utilities for annotations and channel data.
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.models.annotation import Annotation
from src.models.sensor_data import SensorData


def export_to_json(annotations: List[Annotation], filepath: str):
    """
    Export annotations to JSON file.
    
    Args:
        annotations: List of Annotation objects
        filepath: Output file path
    """
    data = {
        'annotations': [ann.to_dict() for ann in annotations],
        'count': len(annotations)
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def export_to_csv(annotations: List[Annotation], filepath: str):
    """
    Export annotations to CSV file.
    
    Args:
        annotations: List of Annotation objects
        filepath: Output file path
    """
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Determine if we have sample information
        has_samples = annotations and annotations[0].sample_rate is not None
        
        # Write header
        if has_samples:
            writer.writerow([
                'Label', 'Start Time (s)', 'End Time (s)', 'Duration (s)', 
                'Start Sample', 'End Sample', 'N Samples', 'Sample Rate (Hz)',
                'Color (RGB)', 'Notes'
            ])
        else:
            writer.writerow([
                'Label', 'Start Time (s)', 'End Time (s)', 'Duration (s)', 
                'Color (RGB)', 'Notes'
            ])
        
        # Write data
        for ann in annotations:
            if has_samples:
                writer.writerow([
                    ann.label,
                    f"{ann.start_time:.6f}",
                    f"{ann.end_time:.6f}",
                    f"{ann.duration:.6f}",
                    ann.start_sample,
                    ann.end_sample,
                    ann.n_samples,
                    ann.sample_rate,
                    f"{ann.color}",
                    ann.notes
                ])
            else:
                writer.writerow([
                    ann.label,
                    f"{ann.start_time:.6f}",
                    f"{ann.end_time:.6f}",
                    f"{ann.duration:.6f}",
                    f"{ann.color}",
                    ann.notes
                ])


def load_from_json(filepath: str) -> List[Annotation]:
    """
    Load annotations from JSON file.
    
    Args:
        filepath: Input file path
        
    Returns:
        List of Annotation objects
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    annotations = [Annotation.from_dict(ann_dict) for ann_dict in data['annotations']]
    return annotations


def save_session(annotations: List[Annotation], filepath: str, sensor_filename: str = None):
    """
    Save complete annotation session including metadata.
    
    Args:
        annotations: List of Annotation objects
        filepath: Output file path
        sensor_filename: Original sensor data filename
    """
    data = {
        'sensor_file': sensor_filename,
        'annotation_count': len(annotations),
        'annotations': [ann.to_dict() for ann in annotations]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_session(filepath: str) -> tuple[List[Annotation], str]:
    """
    Load annotation session from file.
    
    Args:
        filepath: Input file path
        
    Returns:
        Tuple of (annotations list, sensor_filename)
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    annotations = [Annotation.from_dict(ann_dict) for ann_dict in data['annotations']]
    sensor_filename = data.get('sensor_file')
    
    return annotations, sensor_filename


# ---------------------------------------------------------------------------
# Channel data export
# ---------------------------------------------------------------------------

def _get_channel_export_data(
    sensor_data: SensorData,
    channel_idx: int,
    region: Optional[Tuple[float, float]] = None,
):
    """
    Return (timestamps, values, channel_name) for export.

    If ``region`` is provided, the data is sliced to that time range.
    """
    if channel_idx < 0 or channel_idx >= sensor_data.n_channels:
        raise ValueError(
            f"Channel index {channel_idx} out of range for dataset "
            f"with {sensor_data.n_channels} channels"
        )

    if region is not None:
        start, end = region
        timestamps, data = sensor_data.get_time_slice(start, end)
        values = data[:, channel_idx]
    else:
        timestamps = sensor_data.timestamps
        values = sensor_data.get_channel(channel_idx)

    channel_name = sensor_data.channel_names[channel_idx]
    return timestamps, values, channel_name


def export_channel_to_csv(
    sensor_data: SensorData,
    channel_idx: int,
    filepath: str,
    region: Optional[Tuple[float, float]] = None,
):
    """
    Export a single channel to CSV.

    The first column is time in seconds; the second column is the channel value.
    """
    timestamps, values, channel_name = _get_channel_export_data(
        sensor_data, channel_idx, region
    )
    path = Path(filepath)
    if path.suffix.lower() != '.csv':
        path = path.with_suffix('.csv')

    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Time (s)', channel_name])
        for t, v in zip(timestamps, values):
            writer.writerow([f"{t:.6f}", f"{v:.6f}"])

    return str(path)


def export_channel_to_npy(
    sensor_data: SensorData,
    channel_idx: int,
    filepath: str,
    region: Optional[Tuple[float, float]] = None,
):
    """
    Export a single channel to a NumPy binary file.

    The saved array has shape (n_samples, 2) with columns [timestamps, values].
    """
    timestamps, values, _channel_name = _get_channel_export_data(
        sensor_data, channel_idx, region
    )
    path = Path(filepath)
    if path.suffix.lower() != '.npy':
        path = path.with_suffix('.npy')

    arr = np.column_stack([timestamps, values])
    np.save(path, arr)
    return str(path)


def export_channel_to_hdf5(
    sensor_data: SensorData,
    channel_idx: int,
    filepath: str,
    region: Optional[Tuple[float, float]] = None,
    dataset_name: str = 'data',
):
    """
    Export a single channel to an HDF5 file.

    The dataset has shape (n_samples, 2) with columns [timestamps, values].
    Attributes ``sample_rate`` and ``channel_names`` are stored for round-trip
    loading with ``load_hdf5``.
    """
    try:
        import h5py
    except ImportError:
        raise ImportError("h5py is required to export HDF5 files. Install with: pip install h5py")

    timestamps, values, channel_name = _get_channel_export_data(
        sensor_data, channel_idx, region
    )
    path = Path(filepath)
    if path.suffix.lower() not in ('.h5', '.hdf5'):
        path = path.with_suffix('.h5')

    arr = np.column_stack([timestamps, values])
    with h5py.File(path, 'w') as f:
        dset = f.create_dataset(dataset_name, data=arr)
        dset.attrs['sample_rate'] = float(sensor_data.sample_rate)
        dset.attrs['channel_names'] = [channel_name]

    return str(path)


def _common_timestamps(datasets: Dict[str, SensorData]) -> Optional[np.ndarray]:
    """
    Return a common timestamp array if all datasets share one exactly.
    Otherwise return None.
    """
    arrays = [sd.timestamps for sd in datasets.values()]
    if not arrays:
        return None
    first = arrays[0]
    if not all(np.array_equal(ts, first) for ts in arrays[1:]):
        return None
    return first


def export_all_channels_to_csv(
    datasets: Dict[str, SensorData],
    filepath: str,
    region: Optional[Tuple[float, float]] = None,
    one_file_per_dataset: bool = False,
):
    """
    Export all channels from all datasets to CSV.

    If ``one_file_per_dataset`` is False (default), a single combined CSV is
    written with columns prefixed by ``dataset_id/channel_name``.  Datasets
    must share the same timestamp array for combined output; otherwise each
    dataset is written to its own file.

    Returns the path or list of paths written.
    """
    if not datasets:
        raise ValueError("No datasets available to export")

    path = Path(filepath)
    if path.suffix.lower() != '.csv':
        path = path.with_suffix('.csv')

    if one_file_per_dataset or _common_timestamps(datasets) is None:
        written = []
        for dataset_id, sensor_data in datasets.items():
            safe_id = "".join(c if c.isalnum() else "_" for c in dataset_id)
            ds_path = path.parent / f"{path.stem}_{safe_id}.csv"
            _write_dataset_csv(sensor_data, ds_path, region)
            written.append(str(ds_path))
        return written

    timestamps = _common_timestamps(datasets)
    if region is not None:
        start, end = region
        mask = (timestamps >= start) & (timestamps <= end)
        timestamps = timestamps[mask]

    headers = ['Time (s)']
    columns = [timestamps]
    for dataset_id, sensor_data in datasets.items():
        for ch_idx, ch_name in enumerate(sensor_data.channel_names):
            headers.append(f"{dataset_id}/{ch_name}")
            if region is not None:
                values = sensor_data.data[mask, ch_idx]
            else:
                values = sensor_data.get_channel(ch_idx)
            columns.append(values)

    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in zip(*columns):
            writer.writerow([f"{v:.6f}" for v in row])

    return str(path)


def _write_dataset_csv(
    sensor_data: SensorData,
    filepath: Path,
    region: Optional[Tuple[float, float]] = None,
):
    """Write one dataset to CSV, optionally sliced by region."""
    if region is not None:
        timestamps, data = sensor_data.get_time_slice(*region)
    else:
        timestamps = sensor_data.timestamps
        data = sensor_data.data

    headers = ['Time (s)', *sensor_data.channel_names]
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i, t in enumerate(timestamps):
            writer.writerow([f"{t:.6f}", *[f"{v:.6f}" for v in data[i]]])


def export_all_channels_to_npy(
    datasets: Dict[str, SensorData],
    filepath: str,
    region: Optional[Tuple[float, float]] = None,
):
    """
    Export all channels from all datasets to a NumPy binary file.

    Because ``.npy`` is a single array, each dataset is written to its own
    file with shape (n_samples, n_channels+1).  The returned value is a list
    of paths.
    """
    if not datasets:
        raise ValueError("No datasets available to export")

    path = Path(filepath)
    if path.suffix.lower() != '.npy':
        path = path.with_suffix('.npy')

    written = []
    for dataset_id, sensor_data in datasets.items():
        safe_id = "".join(c if c.isalnum() else "_" for c in dataset_id)
        ds_path = path.parent / f"{path.stem}_{safe_id}.npy"

        if region is not None:
            timestamps, data = sensor_data.get_time_slice(*region)
        else:
            timestamps = sensor_data.timestamps
            data = sensor_data.data

        arr = np.column_stack([timestamps, data])
        np.save(ds_path, arr)
        written.append(str(ds_path))

    return written


def export_all_channels_to_hdf5(
    datasets: Dict[str, SensorData],
    filepath: str,
    region: Optional[Tuple[float, float]] = None,
):
    """
    Export all channels from all datasets to an HDF5 file.

    Each dataset is stored as a separate dataset inside the HDF5 file named
    after the dataset_id.  Every dataset has shape (n_samples, n_channels+1)
    with the first column being timestamps.
    """
    try:
        import h5py
    except ImportError:
        raise ImportError("h5py is required to export HDF5 files. Install with: pip install h5py")

    if not datasets:
        raise ValueError("No datasets available to export")

    path = Path(filepath)
    if path.suffix.lower() not in ('.h5', '.hdf5'):
        path = path.with_suffix('.h5')

    with h5py.File(path, 'w') as f:
        for dataset_id, sensor_data in datasets.items():
            safe_name = "".join(c if c.isalnum() or c == '_' else "_" for c in dataset_id)
            if not safe_name[0].isalpha():
                safe_name = 'dataset_' + safe_name

            if region is not None:
                timestamps, data = sensor_data.get_time_slice(*region)
            else:
                timestamps = sensor_data.timestamps
                data = sensor_data.data

            arr = np.column_stack([timestamps, data])
            dset = f.create_dataset(safe_name, data=arr)
            dset.attrs['sample_rate'] = float(sensor_data.sample_rate)
            dset.attrs['channel_names'] = list(sensor_data.channel_names)

    return str(path)
