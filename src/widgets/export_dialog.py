"""
Export dialog for channel data.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.sensor_data import SensorData


class ExportDialog(QDialog):
    """
    Dialog for exporting channel data.

    Supports two modes:
      - Single channel: show dataset/channel selector.
      - All channels: hide channel selector, optionally show "one file per dataset".

    The dialog returns a result dict via :meth:`get_result` when accepted.
    """

    FORMATS = ['CSV', 'NumPy (.npy)', 'HDF5 (.h5)']
    SCOPES = ['Full dataset', 'Current selection']

    def __init__(
        self,
        datasets: Dict[str, SensorData],
        mode: str = 'channel',
        default_region: Optional[Tuple[float, float]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.datasets = datasets
        self.mode = mode  # 'channel' or 'all'
        self.default_region = default_region
        self._result: Optional[dict] = None

        self.setWindowTitle('Export Channel' if mode == 'channel' else 'Export All Channels')
        self.resize(520, 260)

        layout = QVBoxLayout(self)

        form = QGridLayout()
        form.setSpacing(8)
        form.setColumnStretch(1, 1)

        row = 0

        # Dataset / channel selector (single channel only)
        self._dataset_combo: Optional[QComboBox] = None
        self._channel_combo: Optional[QComboBox] = None
        if mode == 'channel':
            form.addWidget(QLabel('Dataset:'), row, 0)
            self._dataset_combo = QComboBox()
            self._dataset_combo.addItems(sorted(datasets.keys()))
            self._dataset_combo.currentTextChanged.connect(self._on_dataset_changed)
            form.addWidget(self._dataset_combo, row, 1)
            row += 1

            form.addWidget(QLabel('Channel:'), row, 0)
            self._channel_combo = QComboBox()
            form.addWidget(self._channel_combo, row, 1)
            row += 1

        # Scope selector
        form.addWidget(QLabel('Scope:'), row, 0)
        self._scope_combo = QComboBox()
        self._scope_combo.addItems(self.SCOPES)
        if default_region is None:
            self._scope_combo.setCurrentIndex(0)
            self._scope_combo.setEnabled(False)
        else:
            self._scope_combo.setCurrentIndex(1)
        form.addWidget(self._scope_combo, row, 1)
        row += 1

        # Format selector
        form.addWidget(QLabel('Format:'), row, 0)
        self._format_combo = QComboBox()
        self._format_combo.addItems(self.FORMATS)
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        form.addWidget(self._format_combo, row, 1)
        row += 1

        # One file per dataset (all channels only)
        self._one_file_cb: Optional[QCheckBox] = None
        if mode == 'all':
            self._one_file_cb = QCheckBox('One file per dataset')
            self._one_file_cb.setChecked(False)
            self._one_file_cb.setToolTip(
                'When checked, each dataset is exported to its own file. '
                'Required when datasets have different timestamps.'
            )
            form.addWidget(self._one_file_cb, row, 1)
            row += 1

        layout.addLayout(form)

        # Output path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel('Output:'))
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText('Choose output file...')
        path_layout.addWidget(self._path_edit)
        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # HDF5 note
        self._hdf5_note = QLabel(
            'HDF5 export stores each dataset as a separate group/dataset inside the file.'
        )
        self._hdf5_note.setWordWrap(True)
        self._hdf5_note.setStyleSheet('color: #666; font-size: 11px;')
        self._hdf5_note.setVisible(False)
        layout.addWidget(self._hdf5_note)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initialize channel list for first dataset
        if mode == 'channel':
            self._on_dataset_changed(self._dataset_combo.currentText())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_dataset_changed(self, dataset_id: str):
        if self._channel_combo is None:
            return
        self._channel_combo.clear()
        sensor_data = self.datasets.get(dataset_id)
        if sensor_data is None:
            return
        for idx, name in enumerate(sensor_data.channel_names):
            self._channel_combo.addItem(f'{idx}: {name}', idx)

    def _on_format_changed(self, text: str):
        self._hdf5_note.setVisible('HDF5' in text)
        current = self._path_edit.text()
        if not current:
            return
        path = current.strip()
        if 'CSV' in text:
            new_ext = '.csv'
        elif 'NumPy' in text:
            new_ext = '.npy'
        else:
            new_ext = '.h5'
        if '.' in path:
            path = path.rsplit('.', 1)[0] + new_ext
        else:
            path += new_ext
        self._path_edit.setText(path)

    def _browse(self):
        fmt = self._format_combo.currentText()
        if 'CSV' in fmt:
            filter_str = 'CSV Files (*.csv)'
            default_ext = '.csv'
        elif 'NumPy' in fmt:
            filter_str = 'NumPy Files (*.npy)'
            default_ext = '.npy'
        else:
            filter_str = 'HDF5 Files (*.h5 *.hdf5)'
            default_ext = '.h5'

        filename, _ = QFileDialog.getSaveFileName(
            self,
            'Export Channel Data',
            self._path_edit.text(),
            filter_str,
        )
        if filename:
            if not filename.lower().endswith(('.csv', '.npy', '.h5', '.hdf5')):
                filename += default_ext
            self._path_edit.setText(filename)

    def _accept(self):
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, 'No Output Path', 'Please choose an output file.')
            return

        fmt = self._format_combo.currentText()
        scope = self._scope_combo.currentText()
        region = self.default_region if scope == 'Current selection' else None

        result: dict = {
            'filepath': path,
            'format': fmt,
            'region': region,
        }

        if self.mode == 'channel':
            dataset_id = self._dataset_combo.currentText()
            channel_idx = self._channel_combo.currentData()
            if dataset_id not in self.datasets or channel_idx is None:
                QMessageBox.warning(self, 'Invalid Selection', 'Please select a valid channel.')
                return
            result.update({
                'dataset_id': dataset_id,
                'channel_idx': channel_idx,
            })
        else:
            result['one_file_per_dataset'] = (
                self._one_file_cb.isChecked() if self._one_file_cb else False
            )

        self._result = result
        self.accept()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_result(self) -> Optional[dict]:
        """Return the export configuration dict if the dialog was accepted."""
        return self._result
