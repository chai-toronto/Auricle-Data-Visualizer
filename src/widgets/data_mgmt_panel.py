"""
Data Management panel — lists all plot boxes with editable trace names and colors.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.models.sensor_data import SensorData
from src.widgets.parameter_panel import CollapsibleSection


class _EditChannelsDialog(QDialog):
    """
    Dialog that shows all available channels across all datasets.
    Those currently displayed in the target PlotBox are pre-checked.
    On accept, adds/removes traces accordingly.
    """

    # Default colors cycled for new traces
    _COLORS = [
        (31, 119, 180), (214, 39, 40), (44, 160, 44), (148, 103, 189),
        (255, 127, 14), (23, 190, 207), (140, 86, 75), (227, 119, 194),
    ]

    def __init__(self, plot_box, datasets: Dict[str, SensorData], parent=None):
        super().__init__(parent)
        self.plot_box = plot_box
        self.datasets = datasets
        self.setWindowTitle(f"Edit Channels — {plot_box.box_name}")
        self.resize(420, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Check the channels to display in this box:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._cb_layout = QVBoxLayout(container)
        self._cb_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Build current-trace set for pre-checking
        active = {(t["dataset_id"], t["channel_idx"]) for t in plot_box.traces}
        self._color_counter = len(active)

        self._checkboxes: List[Tuple[QCheckBox, str, int]] = []  # (cb, dataset_id, ch_idx)

        for dataset_id, sensor_data in datasets.items():
            if sensor_data.n_channels == 0:
                continue
            header = QLabel(f"<b>{dataset_id}</b>")
            header.setStyleSheet("margin-top: 6px;")
            self._cb_layout.addWidget(header)
            for ch_idx, ch_name in enumerate(sensor_data.channel_names):
                cb = QCheckBox(ch_name)
                cb.setChecked((dataset_id, ch_idx) in active)
                self._cb_layout.addWidget(cb)
                self._checkboxes.append((cb, dataset_id, ch_idx))

        self._cb_layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self):
        active_now = {(t["dataset_id"], t["channel_idx"]) for t in self.plot_box.traces}

        for cb, dataset_id, ch_idx in self._checkboxes:
            key = (dataset_id, ch_idx)
            if cb.isChecked() and key not in active_now:
                # Pick a default color
                color = self._COLORS[self._color_counter % len(self._COLORS)]
                self._color_counter += 1
                self.plot_box.add_trace(dataset_id, ch_idx, color, 1.0)
                # If this box had no STFT selection, default to the new trace.
                if self.plot_box.get_stft_channel() is None:
                    self.plot_box.set_stft_channel(dataset_id, ch_idx)
            elif not cb.isChecked() and key in active_now:
                self.plot_box.remove_trace(dataset_id, ch_idx)
                # If the removed trace was the STFT selection, clear it.
                stft_channel = self.plot_box.get_stft_channel()
                if stft_channel == key:
                    self.plot_box.set_stft_channel(None, None)

        self.accept()


class _TraceRow(QWidget):
    """Single row for one trace — shows identifier, FFT/Time Domain toggles, and color."""

    def __init__(
        self,
        dataset_id: str,
        channel_idx: int,
        channel_name: str,
        color: tuple,
        fft: bool = True,
        time_domain: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.dataset_id = dataset_id
        self.channel_idx = channel_idx
        self._color = tuple(color)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(6)

        id_label = QLabel(f"{dataset_id} / {channel_name}")
        id_label.setStyleSheet("color: #444; font-size: 10px;")
        layout.addWidget(id_label)

        layout.addStretch()

        self.fft_cb = QCheckBox("FFT")
        self.fft_cb.setChecked(fft)
        self.fft_cb.setToolTip("Include this trace in the FFT tab")
        layout.addWidget(self.fft_cb)

        self.time_domain_cb = QCheckBox("Time Domain")
        self.time_domain_cb.setChecked(time_domain)
        self.time_domain_cb.setToolTip("Include this trace in the Time Series tab")
        layout.addWidget(self.time_domain_cb)

        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(36)
        self.color_btn.setToolTip("Click to change trace color")
        self.color_btn.clicked.connect(self._pick_color)
        self._refresh_color_btn()
        layout.addWidget(self.color_btn)

    def _refresh_color_btn(self):
        r, g, b = self._color
        self.color_btn.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #888;"
        )

    def _pick_color(self):
        current = QColor(*self._color)
        chosen = QColorDialog.getColor(current, self, "Choose Trace Color")
        if chosen.isValid():
            self._color = (chosen.red(), chosen.green(), chosen.blue())
            self._refresh_color_btn()

    def get_color(self) -> tuple:
        return self._color

    def get_fft(self) -> bool:
        return self.fft_cb.isChecked()

    def get_time_domain(self) -> bool:
        return self.time_domain_cb.isChecked()


class _ChannelRow(QWidget):
    """Editable row for one dataset channel — selection checkbox and name edit."""

    def __init__(
        self,
        dataset_id: str,
        channel_idx: int,
        channel_name: str,
        selected: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.dataset_id = dataset_id
        self.channel_idx = channel_idx

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(6)

        self.select_cb = QCheckBox()
        self.select_cb.setChecked(selected)
        self.select_cb.setToolTip("Select this channel for bulk actions")
        layout.addWidget(self.select_cb)

        id_label = QLabel(f"{dataset_id}:")
        id_label.setStyleSheet("color: #888; font-size: 10px;")
        id_label.setFixedWidth(80)
        layout.addWidget(id_label)

        self.name_edit = QLineEdit(channel_name)
        self.name_edit.setToolTip("Edit display name for this channel")
        layout.addWidget(self.name_edit)

    def is_selected(self) -> bool:
        return self.select_cb.isChecked()

    def get_name(self) -> str:
        return self.name_edit.text().strip() or self.name_edit.placeholderText()


class DataMgmtPanel(QWidget):
    """
    Tab content for managing loaded datasets and plot box trace configuration.

    - "Channels" section: edit channel names and select channels for bulk actions.
    - Per-box sections: edit trace colors, FFT/Time Domain inclusion, and per-box
      STFT channel selection.
    """

    load_data_requested = pyqtSignal()
    load_config_requested = pyqtSignal()
    clear_all_data_requested = pyqtSignal()
    # Emits list of dicts: {dataset_id, channel_idx, name}
    channels_applied = pyqtSignal(list)
    # Bulk channel actions: list of (dataset_id, channel_idx)
    channels_export_requested = pyqtSignal(list)
    channels_duplicate_requested = pyqtSignal(list)
    channels_delete_requested = pyqtSignal(list)
    export_all_channels_requested = pyqtSignal()
    # Emitted when a box's trace config (colors/fft/time-domain/stft) is applied.
    box_config_applied = pyqtSignal()
    box_deleted = pyqtSignal(str)       # box_name
    box_duplicated = pyqtSignal(str)    # box_name
    new_box_requested = pyqtSignal()    # Create a new empty plot box

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plot_boxes = []
        self._datasets: Dict[str, SensorData] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(6)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        config_btn = QPushButton("📂  Load Config")
        config_btn.setToolTip("Load a configuration file (same as File → Load Config)")
        config_btn.clicked.connect(self.load_config_requested)
        btn_layout.addWidget(config_btn)
        self._config_btn = config_btn

        load_btn = QPushButton("💻  Load Data")
        load_btn.setToolTip("Open a data file (same as File → Open)")
        load_btn.clicked.connect(self.load_data_requested)
        btn_layout.addWidget(load_btn)

        clear_btn = QPushButton("💣  Clear All Data")
        clear_btn.setToolTip("Remove all loaded datasets and plot boxes (config is preserved)")
        clear_btn.clicked.connect(self.clear_all_data_requested)
        btn_layout.addWidget(clear_btn)

        outer.addWidget(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(scroll.horizontalScrollBarPolicy().ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark_config_loaded(self):
        """Update the Load Config button to indicate a config is active."""
        self._config_btn.setText("📂  Load Config ✅")

    def refresh(self, plot_boxes: list, datasets: Dict[str, SensorData]):
        """Rebuild the panel from current plot boxes and datasets."""
        self._plot_boxes = plot_boxes
        self._datasets = datasets

        # Remove existing widgets (keep trailing stretch)
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self._add_channels_section()
        for box in plot_boxes:
            self._add_box_section(box)

        # Add "New Box" button at the bottom
        new_box_btn = QPushButton("➕  New Box")
        new_box_btn.setToolTip("Create a new empty plot box")
        new_box_btn.clicked.connect(self.new_box_requested.emit)
        self._insert_widget(new_box_btn)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _insert_widget(self, widget: QWidget):
        """Insert before the trailing stretch."""
        self._container_layout.insertWidget(self._container_layout.count() - 1, widget)

    def _add_channels_section(self):
        if not self._datasets:
            return

        section = CollapsibleSection("Channels")
        channel_rows: List[_ChannelRow] = []

        for dataset_id, sensor_data in self._datasets.items():
            for ch_idx, ch_name in enumerate(sensor_data.channel_names):
                row = _ChannelRow(dataset_id, ch_idx, ch_name)
                channel_rows.append(row)
                section.add_widget(row)

        # Apply names + bulk action buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        apply_btn = QPushButton("Apply Names")
        apply_btn.setToolTip("Apply channel name changes")
        apply_btn.clicked.connect(
            lambda checked=False, rows=channel_rows: self._apply_channels(rows)
        )
        btn_layout.addWidget(apply_btn)

        export_all_btn = QPushButton("Export All Channels")
        export_all_btn.setToolTip("Export all loaded channels to a file")
        export_all_btn.clicked.connect(self.export_all_channels_requested.emit)
        btn_layout.addWidget(export_all_btn)

        btn_layout.addStretch()
        section.add_widget(btn_row)

        # Bulk action buttons for selected channels
        bulk_row = QWidget()
        bulk_layout = QHBoxLayout(bulk_row)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setSpacing(4)

        export_selected_btn = QPushButton("Export Selected")
        export_selected_btn.setToolTip("Export selected channels")
        export_selected_btn.clicked.connect(
            lambda checked=False, rows=channel_rows: self._export_selected_channels(rows)
        )
        bulk_layout.addWidget(export_selected_btn)

        duplicate_selected_btn = QPushButton("Duplicate Selected")
        duplicate_selected_btn.setToolTip("Duplicate selected channels as new datasets")
        duplicate_selected_btn.clicked.connect(
            lambda checked=False, rows=channel_rows: self._duplicate_selected_channels(rows)
        )
        bulk_layout.addWidget(duplicate_selected_btn)

        delete_selected_btn = QPushButton("Delete Selected")
        delete_selected_btn.setToolTip("Delete selected channels")
        delete_selected_btn.clicked.connect(
            lambda checked=False, rows=channel_rows: self._delete_selected_channels(rows)
        )
        bulk_layout.addWidget(delete_selected_btn)

        bulk_layout.addStretch()
        section.add_widget(bulk_row)
        self._insert_widget(section)

    def _add_box_section(self, plot_box):
        section = CollapsibleSection(plot_box.box_name)
        trace_rows: List[_TraceRow] = []

        if not plot_box.traces:
            section.add_widget(QLabel("  (no traces)"))
        else:
            for trace in plot_box.traces:
                dataset_id = trace["dataset_id"]
                channel_idx = trace["channel_idx"]
                sensor_data = self._datasets.get(dataset_id)
                ch_name = (
                    sensor_data.channel_names[channel_idx]
                    if sensor_data and channel_idx < len(sensor_data.channel_names)
                    else f"Channel {channel_idx + 1}"
                )
                row = _TraceRow(
                    dataset_id,
                    channel_idx,
                    ch_name,
                    trace["color"],
                    fft=trace.get("fft", True),
                    time_domain=trace.get("time_domain", True),
                )
                trace_rows.append(row)
                section.add_widget(row)

        # Plot type + STFT channel selector
        type_row = QWidget()
        type_layout = QHBoxLayout(type_row)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(4)

        type_layout.addWidget(QLabel("Plot type:"))
        plot_type_combo = QComboBox()
        plot_type_combo.addItems(["Line", "Scatter"])
        plot_type_combo.setCurrentText("Line" if plot_box.plot_type == 'line' else "Scatter")
        plot_type_combo.setToolTip("Toggle between line and scatter plot")
        plot_type_combo.currentTextChanged.connect(
            lambda text, pb=plot_box: pb.set_plot_type(text.lower())
        )
        type_layout.addWidget(plot_type_combo)

        type_layout.addWidget(QLabel("STFT:"))
        stft_combo = QComboBox()
        stft_combo.addItem("(none)", None)
        for trace in plot_box.traces:
            sensor_data = self._datasets.get(trace["dataset_id"])
            ch_name = (
                sensor_data.channel_names[trace["channel_idx"]]
                if sensor_data and trace["channel_idx"] < len(sensor_data.channel_names)
                else f"Channel {trace['channel_idx'] + 1}"
            )
            label = f"{trace['dataset_id']} / {ch_name}"
            stft_combo.addItem(label, (trace["dataset_id"], trace["channel_idx"]))
        # Restore previous selection if it still exists in this box.
        current_stft = plot_box.get_stft_channel()
        if current_stft is not None:
            for i in range(stft_combo.count()):
                data = stft_combo.itemData(i)
                if data == current_stft:
                    stft_combo.setCurrentIndex(i)
                    break
        stft_combo.setToolTip("Select the channel whose STFT is shown for this box")
        stft_combo.currentIndexChanged.connect(
            lambda idx, pb=plot_box, combo=stft_combo: pb.set_stft_channel(*combo.itemData(idx))
            if combo.itemData(idx) is not None else pb.set_stft_channel(None, None)
        )
        type_layout.addWidget(stft_combo)

        type_layout.addStretch()
        section.add_widget(type_row)

        # Button row: Apply + Edit Channels + Duplicate + Delete
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        apply_btn = QPushButton("Apply")
        apply_btn.setToolTip("Apply color, FFT, Time Domain, and STFT settings")
        apply_btn.clicked.connect(
            lambda checked=False, pb=plot_box, rows=trace_rows: self._apply_box_config(pb, rows)
        )
        btn_layout.addWidget(apply_btn)

        edit_btn = QPushButton("Edit Channels")
        edit_btn.setToolTip("Add or remove channels displayed in this box")
        edit_btn.clicked.connect(
            lambda checked=False, pb=plot_box: self._open_edit_channels(pb)
        )
        btn_layout.addWidget(edit_btn)

        dup_btn = QPushButton("⧉")
        dup_btn.setFixedWidth(28)
        dup_btn.setToolTip("Duplicate this display box")
        dup_btn.setStyleSheet("font-size: 13px; padding: 0;")
        dup_btn.clicked.connect(
            lambda checked=False, name=plot_box.box_name: self.box_duplicated.emit(name)
        )
        btn_layout.addWidget(dup_btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(28)
        del_btn.setToolTip("Remove this display box")
        del_btn.setStyleSheet("font-size: 13px; padding: 0;")
        del_btn.clicked.connect(
            lambda checked=False, name=plot_box.box_name: self.box_deleted.emit(name)
        )
        btn_layout.addWidget(del_btn)

        section.add_widget(btn_row)
        self._insert_widget(section)

    def _open_edit_channels(self, plot_box):
        dialog = _EditChannelsDialog(plot_box, self._datasets, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh this panel so trace rows update after add/remove
            self.refresh(self._plot_boxes, self._datasets)

    def _apply_channels(self, rows: List[_ChannelRow]):
        configs = []
        for row in rows:
            configs.append({
                'dataset_id': row.dataset_id,
                'channel_idx': row.channel_idx,
                'name': row.get_name(),
            })
        self.channels_applied.emit(configs)

    def _apply_box_config(self, plot_box, trace_rows: List[_TraceRow]):
        for row in trace_rows:
            for trace in plot_box.traces:
                if trace["dataset_id"] == row.dataset_id and trace["channel_idx"] == row.channel_idx:
                    trace["color"] = row.get_color()
                    trace["fft"] = row.get_fft()
                    trace["time_domain"] = row.get_time_domain()
                    break
        plot_box.refresh_traces(self._datasets)
        self.box_config_applied.emit()

    def _get_selected_channel_rows(self, rows: List[_ChannelRow]) -> list[tuple[str, int]]:
        return [
            (row.dataset_id, row.channel_idx)
            for row in rows
            if row.is_selected()
        ]

    def _export_selected_channels(self, rows: List[_ChannelRow]):
        selected = self._get_selected_channel_rows(rows)
        if selected:
            self.channels_export_requested.emit(selected)

    def _duplicate_selected_channels(self, rows: List[_ChannelRow]):
        selected = self._get_selected_channel_rows(rows)
        if selected:
            self.channels_duplicate_requested.emit(selected)

    def _delete_selected_channels(self, rows: List[_ChannelRow]):
        selected = self._get_selected_channel_rows(rows)
        if selected:
            self.channels_delete_requested.emit(selected)
