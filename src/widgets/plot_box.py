from __future__ import annotations

from typing import Dict, Optional, Tuple

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QComboBox,
    QToolButton,
    QColorDialog,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from src.models.sensor_data import SensorData


class PlotBox(QWidget):
    view_range_changed = pyqtSignal(float, float)
    collapsed_changed = pyqtSignal(bool)
    time_domain_visibility_changed = pyqtSignal(bool)

    def __init__(self, box_name: str, datasets: Dict[str, SensorData], parent=None):
        super().__init__(parent)
        self.box_name = box_name
        self.datasets = datasets
        self.traces: list[dict] = []
        self._plot_items: dict[tuple[str, int], pg.PlotDataItem] = {}
        self.plot_type: str = 'line'  # 'line' or 'scatter'
        self.show_fft = True
        self.show_time_domain = True

        self._expanded = False
        self._expanded_height = 220
        self.header_button = QToolButton()
        self.header_button.setCheckable(True)
        self.header_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.header_button.setArrowType(Qt.ArrowType.RightArrow)
        self.header_button.setText(f"  {box_name}")
        self.header_button.setToolTip("Expand or collapse this box")
        self.header_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.header_button.setStyleSheet(
            "QToolButton { border: none; background: #d8d8d8; padding: 4px; "
            "font-weight: bold; text-align: left; }"
            "QToolButton:hover { background: #c8c8c8; }"
        )
        self.header_button.clicked.connect(self._toggle_expanded)
        self.gear_button = QPushButton('\u2699')
        self.gear_button.setFixedWidth(32)
        self.gear_button.clicked.connect(self.open_config_dialog)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.set_x_axis_label('time')
        self.plot_widget.getAxis('left').enableAutoSIPrefix(False)
        self.plot_widget.setAntialiasing(True)
        self.plot_widget.setMinimumHeight(22)
        self.plot_widget.setMenuEnabled(False)

        self.region_item = pg.LinearRegionItem(
            brush=pg.mkBrush(100, 100, 200, 50),
            movable=True,
        )
        self.region_item.setZValue(1000)
        self.plot_widget.addItem(self.region_item)

        view_box = self.plot_widget.getViewBox()
        view_box.sigRangeChanged.connect(self._emit_view_range_changed)

        # Y-range spinboxes in the title row
        self._y_min_spin = QDoubleSpinBox()
        self._y_min_spin.setRange(-1e9, 1e9)
        self._y_min_spin.setDecimals(3)
        self._y_min_spin.setFixedWidth(120)
        self._y_min_spin.setToolTip("Y-axis minimum")

        self._y_max_spin = QDoubleSpinBox()
        self._y_max_spin.setRange(-1e9, 1e9)
        self._y_max_spin.setDecimals(3)
        self._y_max_spin.setFixedWidth(120)
        self._y_max_spin.setToolTip("Y-axis maximum")

        y_set_btn = QPushButton("Set Y")
        y_set_btn.setFixedWidth(44)
        y_set_btn.setFixedHeight(20)
        y_set_btn.setToolTip("Apply Y-axis range")

        title_layout.addWidget(QLabel("Y:"))
        title_layout.addWidget(self._y_min_spin)
        title_layout.addWidget(QLabel("–"))
        title_layout.addWidget(self._y_max_spin)
        title_layout.addWidget(y_set_btn)
        title_layout.addStretch()

        def _apply_y():
            lo = self._y_min_spin.value()
            hi = self._y_max_spin.value()
            if lo >= hi:
                return
            x_min, x_max = view_box.viewRange()[0]
            view_box.setYRange(lo, hi, padding=0)
            view_box.setXRange(x_min, x_max, padding=0)

        def _sync_y(vb, ranges):
            lo, hi = ranges[1]
            self._y_min_spin.blockSignals(True)
            self._y_max_spin.blockSignals(True)           
            self._y_min_spin.setValue(lo)

            self._y_max_spin.setValue(hi)
            self._y_min_spin.blockSignals(False)
            self._y_max_spin.blockSignals(False)

        y_set_btn.clicked.connect(_apply_y)
        self._y_min_spin.editingFinished.connect(_apply_y)
        self._y_max_spin.editingFinished.connect(_apply_y)
        view_box.sigRangeChanged.connect(_sync_y)

        # Legend bar below the plot
        self._legend_widget = QWidget()
        self._legend_layout = QHBoxLayout(self._legend_widget)
        self._legend_layout.setContentsMargins(4, 0, 4, 2)
        self._legend_layout.setSpacing(12)
        self._legend_layout.addStretch()

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        content_layout.addLayout(title_layout)
        content_layout.addWidget(self.plot_widget)
        content_layout.addWidget(self._legend_widget)
        self._content.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.header_button)
        layout.addWidget(self._content)

    def set_x_axis_label(self, timestamp_type: str):
        axis = self.plot_widget.getAxis('bottom')
        axis.enableAutoSIPrefix(False)
        if timestamp_type == 'sample_index':
            self.plot_widget.setLabel('bottom', 'Index')
        else:
            self.plot_widget.setLabel('bottom', 'Time', units='s')

    def _toggle_expanded(self):
        if self._expanded:
            self._expanded_height = max(self.height(), self._expanded_height)
        self._expanded = self.header_button.isChecked()
        self.header_button.setArrowType(
            Qt.ArrowType.DownArrow if self._expanded else Qt.ArrowType.RightArrow
        )
        self._content.setVisible(self._expanded)
        if self._expanded:
            self.setFixedHeight(self._expanded_height)
        else:
            self.setFixedHeight(self.header_button.sizeHint().height())
        self.collapsed_changed.emit(not self._expanded)

    def _refresh_title(self):
        names = [
            self._get_channel_name(t["dataset_id"], t["channel_idx"])
            for t in self.traces
        ]
        self.header_button.setText(
            f"{self.box_name}: {', '.join(names)}" if names else self.box_name
        )

    def _emit_view_range_changed(self, *args):
        x_range = self.plot_widget.getViewBox().viewRange()[0]
        self.view_range_changed.emit(x_range[0], x_range[1])

    def _make_pen(self, color: tuple[int, int, int], opacity: float):
        alpha = max(0, min(255, int(opacity * 255)))
        return pg.mkPen(color=(color[0], color[1], color[2], alpha), width=1.5)

    def _get_trace_key(self, dataset_id: str, channel_idx: int) -> tuple[str, int]:
        return dataset_id, channel_idx

    def _get_channel_name(self, dataset_id: str, channel_idx: int) -> str:
        sensor_data = self.datasets.get(dataset_id)
        if sensor_data and 0 <= channel_idx < len(sensor_data.channel_names):
            return sensor_data.channel_names[channel_idx]
        return f'Channel {channel_idx + 1}'

    def _update_axis_label(self):
        if len(self.traces) == 1:
            trace = self.traces[0]
            label = self._get_channel_name(trace['dataset_id'], trace['channel_idx'])
            self.plot_widget.setLabel('left', label)
        elif self.traces:
            self.plot_widget.setLabel('left', 'Signals')
        else:
            self.plot_widget.setLabel('left', '')
        self._rebuild_legend()

    def _rebuild_legend(self):
        """Rebuild the legend bar from current traces."""
        # Clear existing legend items (keep the trailing stretch)
        while self._legend_layout.count() > 1:
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for trace in self.traces:
            r, g, b = trace['color']
            name = self._get_channel_name(trace['dataset_id'], trace['channel_idx'])

            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 2px;"
            )

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-size: 10px;")

            entry = QWidget()
            entry_layout = QHBoxLayout(entry)
            entry_layout.setContentsMargins(0, 0, 0, 0)
            entry_layout.setSpacing(4)
            entry_layout.addWidget(swatch)
            entry_layout.addWidget(name_lbl)

            # Insert before the trailing stretch
            self._legend_layout.insertWidget(self._legend_layout.count() - 1, entry)

        self._legend_widget.setVisible(bool(self.traces))

    def _plot_trace(self, trace: dict):
        sensor_data = self.datasets.get(trace['dataset_id'])
        if sensor_data is None:
            return
        if trace.get('hidden', False):
            return
        channel_idx = trace['channel_idx']           
        if channel_idx < 0 or channel_idx >= sensor_data.n_channels:
            return
        if self.plot_type == 'scatter':
            r, g, b = trace['color']
            alpha = max(0, min(255, int(trace['opacity'] * 255)))
            plot_item = self.plot_widget.plot(
                sensor_data.timestamps,
                sensor_data.get_channel(channel_idx),
                pen=None,
                symbol='o',
                symbolSize=5,
                symbolPen=pg.mkPen(color=(r, g, b, alpha), width=1),
                symbolBrush=pg.mkBrush(r, g, b, alpha),
            )
        else:
            plot_item = self.plot_widget.plot(
                sensor_data.timestamps,
                sensor_data.get_channel(channel_idx),
                pen=self._make_pen(trace['color'], trace['opacity']),
            )
        plot_item.setClipToView(True)
        plot_item.setDownsampling(auto=True, method='peak')
     
        self._plot_items[self._get_trace_key(trace['dataset_id'], channel_idx)] = plot_item

    def set_plot_type(self, plot_type: str):
        """Switch between 'line' and 'scatter' and re-render all traces."""
        if plot_type not in ('line', 'scatter'):
            return
        self.plot_type = plot_type
        self.refresh_traces(self.datasets)

    def add_trace(
        self,
        dataset_id: str,
        channel_idx: int,
        color: tuple[int, int, int],
        opacity: float,
        fft: bool = True,
        time_domain: bool = True,
    ):
        key = self._get_trace_key(dataset_id, channel_idx)
        if key in self._plot_items:
            self.remove_trace(dataset_id, channel_idx)
        trace = {
            'dataset_id': dataset_id,
            'channel_idx': channel_idx,
            'color': tuple(color),
            'opacity': float(opacity),
            'fft': bool(fft),
            'time_domain': bool(time_domain),
            'hidden': False,
        }
        self.traces.append(trace)
        self._plot_trace(trace)
        self._update_axis_label()
        self._refresh_title()

    def remove_trace(self, dataset_id: str, channel_idx: int, defer_update: bool = False):
        """Remove a trace from the plot.
        
        If defer_update=True, skip updating axis label and legend.
        Call finish_batch_remove() after removing multiple traces with defer_update=True.
        """
        key = self._get_trace_key(dataset_id, channel_idx)
        plot_item = self._plot_items.pop(key, None)
        if plot_item is not None:
            self.plot_widget.removeItem(plot_item)
        self.traces = [
            trace for trace in self.traces
            if (trace['dataset_id'], trace['channel_idx']) != key
        ]
        if not defer_update:
            self._update_axis_label()
            self._refresh_title()

    def finish_batch_remove(self):
        """Call after removing multiple traces with defer_update=True to finalize UI updates."""
        self._update_axis_label()
        self._refresh_title()

    def refresh_traces(self, datasets: Dict[str, SensorData]):
        self.datasets = datasets
        for plot_item in self._plot_items.values():
            self.plot_widget.removeItem(plot_item)
        self._plot_items.clear()
        for trace in self.traces:
            self._plot_trace(trace)
        self._update_axis_label()
        self._refresh_title()

    def get_plot_widget(self) -> pg.PlotWidget:
        return self.plot_widget

    def _find_trace(self, dataset_id: str, channel_idx: int) -> Optional[dict]:
        """Return the trace dict for a given dataset/channel, or None."""
        for trace in self.traces:
            if trace['dataset_id'] == dataset_id and trace['channel_idx'] == channel_idx:
                return trace
        return None

    def set_trace_fft(self, dataset_id: str, channel_idx: int, fft: bool):
        """Set whether this trace contributes to the FFT tab."""
        trace = self._find_trace(dataset_id, channel_idx)
        if trace is not None:
            trace['fft'] = bool(fft)

    def set_trace_time_domain(self, dataset_id: str, channel_idx: int, time_domain: bool):
        """Set whether this trace contributes to the Time Series tab."""
        trace = self._find_trace(dataset_id, channel_idx)
        if trace is not None:
            trace['time_domain'] = bool(time_domain)

    def get_fft_traces(self) -> list[dict]:
        """Return traces that should appear in the FFT tab."""
        return [t for t in self.traces if not t.get('hidden', False)]

    def get_time_domain_traces(self) -> list[dict]:
        """Return traces that should appear in the Time Series tab."""
        return [t for t in self.traces if not t.get('hidden', False)]

    def set_trace_hidden(self, dataset_id: str, channel_idx: int, hidden: bool):
        trace = self._find_trace(dataset_id, channel_idx)
        if trace is not None:
            trace['hidden'] = bool(hidden)

    def get_stft_channel(self) -> Optional[Tuple[str, int]]:
        """Return this box's first visible channel enabled for STFT in Channels."""
        for trace in self.traces:
            if trace.get('hidden', False):
                continue
            sensor_data = self.datasets.get(trace['dataset_id'])
            channel_idx = trace['channel_idx']
            if (
                sensor_data is not None
                and channel_idx < len(sensor_data.spectrogram_enabled)
                and sensor_data.spectrogram_enabled[channel_idx]
            ):
                return trace['dataset_id'], channel_idx
        return None

    def set_stft_channel(self, dataset_id: Optional[str], channel_idx: Optional[int]):
        """Deprecated compatibility method; STFT selection is channel-level."""
        return

    def set_show_fft(self, visible: bool):
        self.show_fft = bool(visible)

    def set_show_time_domain(self, visible: bool):
        self.show_time_domain = bool(visible)
        self.setVisible(self.show_time_domain)
        self.time_domain_visibility_changed.emit(self.show_time_domain)

    def set_region(self, start: float, end: float):
        self.region_item.blockSignals(True)
        self.region_item.setRegion([start, end])
        self.region_item.blockSignals(False)

    def set_x_limits(self):
        """Constrain horizontal navigation to the available timestamp range."""
        ranges = [
            data.timestamps for data in self.datasets.values()
            if data.timestamps is not None and len(data.timestamps) > 0
        ]
        if ranges:
            self.plot_widget.getViewBox().setLimits(
                xMin=float(min(values[0] for values in ranges)),
                xMax=float(max(values[-1] for values in ranges)),
            )

    def open_config_dialog(self):
        dialog = PlotBoxConfigDialog(self, self.datasets, self)
        dialog.exec()


class PlotBoxConfigDialog(QDialog):
    def __init__(self, plot_box: PlotBox, datasets: Dict[str, SensorData], parent=None):
        super().__init__(parent)
        self.plot_box = plot_box
        self.datasets = datasets
        self.selected_color = (0, 0, 0)

        self.setWindowTitle(f'Configure {plot_box.box_name}')
        self.resize(480, 420)

        self.trace_list = QListWidget()
        self.remove_button = QPushButton('Remove')
        self.remove_button.clicked.connect(self.remove_selected_trace)

        current_layout = QVBoxLayout()
        current_layout.addWidget(QLabel('Current traces'))
        current_layout.addWidget(self.trace_list)
        current_layout.addWidget(self.remove_button)

        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(sorted(self.datasets.keys()))
        self.dataset_combo.currentTextChanged.connect(self.on_dataset_changed)

        self.channel_combo = QComboBox()

        self.color_button = QPushButton('Choose Color')
        self.color_button.clicked.connect(self.choose_color)

        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.0, 1.0)
        self.opacity_spin.setSingleStep(0.1)
        self.opacity_spin.setValue(1.0)

        self.add_button = QPushButton('Add')
        self.add_button.clicked.connect(self.add_trace)

        add_layout = QVBoxLayout()
        add_layout.addWidget(QLabel('Add Trace'))
        add_layout.addWidget(QLabel('Dataset'))
        add_layout.addWidget(self.dataset_combo)
        add_layout.addWidget(QLabel('Channel'))
        add_layout.addWidget(self.channel_combo)
        add_layout.addWidget(self.color_button)
        add_layout.addWidget(QLabel('Opacity'))
        add_layout.addWidget(self.opacity_spin)
        add_layout.addWidget(self.add_button)

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.accept)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(current_layout)
        main_layout.addLayout(add_layout)
        main_layout.addWidget(close_button)

        self.on_dataset_changed(self.dataset_combo.currentText())
        self.refresh_trace_list()
        self._update_color_button(self.selected_color)

    def _update_color_button(self, color: tuple[int, int, int]):
        self.selected_color = tuple(color)
        self.color_button.setStyleSheet(
            f'background-color: rgb({color[0]}, {color[1]}, {color[2]});'
        )

    def _make_color_icon(self, color: tuple[int, int, int], opacity: float) -> QIcon:
        pixmap = QPixmap(16, 16)
        qcolor = QColor(color[0], color[1], color[2], max(0, min(255, int(opacity * 255))))
        pixmap.fill(qcolor)
        return QIcon(pixmap)

    def on_dataset_changed(self, dataset_id: str):
        self.channel_combo.clear()
        sensor_data = self.datasets.get(dataset_id)
        if sensor_data is None:
            return
        for idx, channel_name in enumerate(sensor_data.channel_names):
            self.channel_combo.addItem(channel_name, idx)
        if sensor_data.n_channels:
            first_idx = 0
            default_color = ((31, 119, 180), (214, 39, 40), (44, 160, 44), (148, 103, 189))[first_idx % 4]
            self._update_color_button(default_color)

    def choose_color(self):
        current = QColor(*self.selected_color)
        color = QColorDialog.getColor(current, self, 'Select Trace Color')
        if color.isValid():
            self._update_color_button((color.red(), color.green(), color.blue()))

    def refresh_trace_list(self):
        self.trace_list.clear()
        for trace in self.plot_box.traces:
            dataset_id = trace['dataset_id']
            channel_idx = trace['channel_idx']
            channel_name = self.plot_box._get_channel_name(dataset_id, channel_idx)
            opacity = trace['opacity']
            item = QListWidgetItem(
                self._make_color_icon(trace['color'], opacity),
                f"{dataset_id} / {channel_name} | opacity {opacity:.2f}",
            )
            item.setData(Qt.ItemDataRole.UserRole, (dataset_id, channel_idx))
            self.trace_list.addItem(item)

    def add_trace(self):
        dataset_id = self.dataset_combo.currentText()
        channel_idx = self.channel_combo.currentData()
        if not dataset_id or channel_idx is None:
            return
        self.plot_box.add_trace(dataset_id, int(channel_idx), self.selected_color, self.opacity_spin.value())
        self.refresh_trace_list()

    def remove_selected_trace(self):
        item = self.trace_list.currentItem()
        if item is None:
            return
        dataset_id, channel_idx = item.data(Qt.ItemDataRole.UserRole)
        self.plot_box.remove_trace(dataset_id, channel_idx)
        self.refresh_trace_list()
