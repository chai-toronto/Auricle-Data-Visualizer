"""
FFT viewer widget for frequency domain analysis.
"""
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, 
    QScrollArea, QHBoxLayout, QDoubleSpinBox, QPushButton, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QAction
from typing import Optional, List
import numpy as np
from src.models.sensor_data import SensorData
from src.utils.signal_processing import compute_fft, find_peaks
from src.widgets.parameter_panel import CollapsiblePlotContainer, ResizeHandle


class FFTWidget(QWidget):
    """
    Widget for displaying FFT (frequency domain) of selected time region.

    One plot is created per Time Series box.  Within each box, the FFTs of
    traces with ``fft=True`` are overlaid so multiple channels can be compared
    in the frequency domain.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sensor_data: Optional[SensorData] = None
        self.boxes: List = []
        self._display_boxes: List = []
        self.plot_widgets: List[pg.PlotWidget] = []
        self.info_labels: List[QLabel] = []
        
        # Y-axis range controls for each plot
        self.y_min_spins: List[QDoubleSpinBox] = []
        self.y_max_spins: List[QDoubleSpinBox] = []
        self.normalization_checkboxes: List[QCheckBox] = []
        self.normalized_boxes: set[int] = set()

        # Hover info labels (one per plot, displayed in upper left)
        self.hover_info_labels: List[QLabel] = []

        # FFT parameters
        self.fft_nperseg: int = 256
        self.fft_window: str = 'hann'
        
        # Cache FFT data to avoid recomputation
        # Structure: {(dataset_id, channel_idx): (frequencies, magnitudes)}
        self.fft_cache: dict = {}
        
        # Track current displayed time range for FFT recomputation
        self.current_fft_start_time: Optional[float] = None
        self.current_fft_end_time: Optional[float] = None

        # Legacy channel filter (kept for API compatibility).
        self.active_channels: Optional[List[int]] = None
        self._active_channel_indices: List[int] = []

        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Enable keyboard focus for shortcut handling
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Create scroll area for plots
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container widget for plots
        self.plots_container = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setSpacing(2)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.addStretch()
        
        self.scroll_area.setWidget(self.plots_container)
        main_layout.addWidget(self.scroll_area)
        
        # Overall info panel at bottom
        self.overall_info = QLabel()
        self.overall_info.setMaximumHeight(30)
        self.overall_info.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        main_layout.addWidget(self.overall_info)
    
    def set_data(self, sensor_data: SensorData):
        """
        Store reference to sensor data.

        The actual plot layout is driven by :meth:`set_boxes`.  This method
        is kept for callers that only need to update the underlying data.
        """
        self.sensor_data = sensor_data
        if self.boxes:
            self.set_boxes(self.boxes)
        else:
            self._build_legacy_channel_plots()

    def set_boxes(self, boxes: list):
        """
        Create one FFT plot per box, using the box's FFT-enabled traces.

        Args:
            boxes: List of PlotBox widgets from the Time Series tab.
        """
        self.boxes = boxes
        self._display_boxes = [box for box in boxes if box.show_fft]
        self.clear_plots()

        if not boxes or self.sensor_data is None:
            return

        for pos, box in enumerate(self._display_boxes):
            fft_traces = box.get_fft_traces()

            trace_names = ", ".join(
                box._get_channel_name(trace["dataset_id"], trace["channel_idx"])
                for trace in fft_traces
            )
            container = CollapsiblePlotContainer(
                f"{box.box_name}: {trace_names}" if trace_names else box.box_name
            )
            layout = container.content_layout

            # Add Y-axis control row
            y_control_layout = QHBoxLayout()
            y_control_layout.setContentsMargins(0, 0, 0, 0)
            y_control_layout.setSpacing(4)
            
            y_min_spin = QDoubleSpinBox()
            y_min_spin.setRange(-1e9, 1e9)
            y_min_spin.setDecimals(3)
            y_min_spin.setFixedWidth(80)
            y_min_spin.setToolTip("Y-axis minimum")
            
            y_max_spin = QDoubleSpinBox()
            y_max_spin.setRange(-1e9, 1e9)
            y_max_spin.setDecimals(3)
            y_max_spin.setFixedWidth(80)
            y_max_spin.setToolTip("Y-axis maximum")
            
            y_set_btn = QPushButton("Set Y")
            y_set_btn.setFixedWidth(44)
            y_set_btn.setFixedHeight(20)
            y_set_btn.setToolTip("Apply Y-axis range")
            
            y_autoscale_btn = QPushButton("Auto Y")
            y_autoscale_btn.setFixedWidth(50)
            y_autoscale_btn.setFixedHeight(20)
            y_autoscale_btn.setToolTip("Autoscale Y-axis (Ctrl+Y)")
            
            y_control_layout.addWidget(QLabel("Y:"))
            y_control_layout.addWidget(y_min_spin)
            y_control_layout.addWidget(QLabel("–"))
            y_control_layout.addWidget(y_max_spin)
            y_control_layout.addWidget(y_set_btn)
            y_control_layout.addWidget(y_autoscale_btn)
            normalize_cb = QCheckBox("Norm magnitude")
            normalize_cb.setToolTip("Normalize each FFT trace in this box to 0-1")
            normalize_cb.setChecked(pos in self.normalized_boxes)
            normalize_cb.toggled.connect(
                lambda checked, index=pos: self._set_box_normalized(index, checked)
            )
            y_control_layout.addWidget(normalize_cb)
            y_control_layout.addStretch()
            
            layout.addLayout(y_control_layout)

            # Create a container for the plot and hover info overlay
            plot_container = QWidget()
            plot_container_layout = QVBoxLayout(plot_container)
            plot_container_layout.setContentsMargins(0, 0, 0, 0)
            plot_container_layout.setSpacing(0)

            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            plot_widget.setLabel('left', 'Magnitude')
            plot_widget.setLabel('bottom', 'Frequency', units='Hz')

            plot_widget.setAntialiasing(True)
            plot_widget.setMenuEnabled(False)
            plot_widget.getViewBox().setLimits(xMin=0)

            # Create hover info label (positioned in upper left of plot)
            hover_info = QLabel("")
            hover_info.setStyleSheet(
                "background-color: rgba(255, 255, 255, 220); "
                "padding: 4px; border: 1px solid #999; border-radius: 3px; "
                "font-family: monospace; font-size: 10px;"
            )
            hover_info.setMaximumWidth(200)
            hover_info.setVisible(False)
            
            plot_container_layout.addWidget(plot_widget, stretch=1)
            plot_container_layout.addWidget(hover_info, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            
            layout.addWidget(plot_container)

            info_label = QLabel("Showing full signal. Select a region in Time Series to zoom.")
            info_label.setWordWrap(True)
            info_label.setMaximumHeight(60)
            info_label.setStyleSheet(
                "background-color: #f9f9f9; padding: 5px; border: 1px solid #ddd;"
            )
            layout.addWidget(info_label)

            self.plot_widgets.append(plot_widget)
            self.info_labels.append(info_label)
            self.hover_info_labels.append(hover_info)
            self.y_min_spins.append(y_min_spin)
            self.y_max_spins.append(y_max_spin)
            self.normalization_checkboxes.append(normalize_cb)
            self.plots_layout.insertWidget(self.plots_layout.count() - 1, container)
            resize_handle = ResizeHandle(container)
            resize_handle.setVisible(False)
            container.collapsed_changed.connect(
                lambda collapsed, handle=resize_handle: handle.setVisible(not collapsed)
            )
            self.plots_layout.insertWidget(self.plots_layout.count() - 1, resize_handle)
            
            # Connect Y-axis controls
            view_box = plot_widget.getViewBox()
            
            def _apply_y_impl(vb, y_min, y_max):
                lo = y_min.value()
                hi = y_max.value()
                if lo >= hi:
                    return
                x_min, x_max = vb.viewRange()[0]
                vb.setYRange(lo, hi, padding=0)
                vb.setXRange(x_min, x_max, padding=0)

            
            def _sync_y_factory(y_min_spinbox, y_max_spinbox):
                def _sync_y(vb, ranges):
                    lo, hi = ranges[1]
                    y_min_spinbox.blockSignals(True)
                    y_max_spinbox.blockSignals(True)
                    y_min_spinbox.setValue(lo)
                    y_max_spinbox.setValue(hi)
                    y_min_spinbox.blockSignals(False)
                    y_max_spinbox.blockSignals(False)
                return _sync_y
            
            def _autoscale_y_factory(vb, box):
                """Factory for per-plot autoscale using frequency-range-aware logic."""
                def _autoscale_y():
                    x_min, x_max = vb.viewRange()[0]
                    y_min_global = np.inf
                    y_max_global = -np.inf
                    
                    # Get all traces in this box
                    for (dataset_id, channel_idx) in box._plot_items:
                        # Use cached FFT data
                        cache_key = (dataset_id, channel_idx)
                        if cache_key not in self.fft_cache:
                            continue
                        
                        frequencies, magnitudes = self.fft_cache[cache_key]
                        
                        # Get indices for visible frequency range
                        i_lo = np.searchsorted(frequencies, x_min, side='left')
                        i_hi = np.searchsorted(frequencies, x_max, side='right')
                        
                        if i_lo >= i_hi or i_lo >= len(magnitudes):
                            continue
                        
                        i_hi = min(i_hi, len(magnitudes))
                        mag_slice = magnitudes[i_lo:i_hi]
                        
                        if len(mag_slice) > 0:
                            y_min_global = min(y_min_global, float(np.min(mag_slice)))
                            y_max_global = max(y_max_global, float(np.max(mag_slice)))
                    
                    # Set Y range with padding
                    if np.isfinite(y_min_global) and np.isfinite(y_max_global):
                        y_range = y_max_global - y_min_global
                        if y_range > 0:
                            padding = y_range * 0.05
                            vb.setYRange(y_min_global - padding, y_max_global + padding, padding=0)
                        else:
                            vb.setYRange(y_min_global - 1, y_max_global + 1, padding=0)
                    else:
                        vb.autoRange(padding=0.05)
                    
                    vb.setXRange(x_min, x_max, padding=0)
                
                return _autoscale_y
            
            y_set_btn.clicked.connect(lambda: _apply_y_impl(view_box, y_min_spin, y_max_spin))
            y_autoscale_btn.clicked.connect(_autoscale_y_factory(view_box, box))
            y_min_spin.editingFinished.connect(lambda: _apply_y_impl(view_box, y_min_spin, y_max_spin))
            y_max_spin.editingFinished.connect(lambda: _apply_y_impl(view_box, y_min_spin, y_max_spin))
            view_box.sigRangeChanged.connect(_sync_y_factory(y_min_spin, y_max_spin))

            # Set up mouse move event to track cursor and display freq/magnitude
            self._setup_hover_tracking(plot_widget, view_box, box, hover_info)


        if len(self.plot_widgets) > 1:
            for i in range(1, len(self.plot_widgets)):
                self.plot_widgets[i].setXLink(self.plot_widgets[0])

    def _setup_hover_tracking(self, plot_widget, view_box, box, hover_info_label):
        """
        Set up mouse move event tracking for cursor hover info display.
        
        As the cursor moves over the plot, the hover_info_label is updated to show
        the frequency and magnitude at the cursor's x-position for all visible traces.
        """
        def _on_mouse_moved(pos):
            # Get the data coordinates from the mouse position
            try:
                mouse_point = view_box.mapSceneToView(pos)
                freq_at_cursor = mouse_point.x()
                
                # Build info string showing frequency and magnitude for each trace
                info_parts = [f"<b>Frequency: {freq_at_cursor:.2f} Hz</b>"]
                
                # Look up magnitude values for all traces in this box at this frequency
                has_data = False
                for (dataset_id, channel_idx) in box._plot_items:
                    cache_key = (dataset_id, channel_idx)
                    if cache_key not in self.fft_cache:
                        continue
                    
                    has_data = True
                    frequencies, magnitudes = self.fft_cache[cache_key]
                    
                    # Find closest frequency point
                    if len(frequencies) > 0:
                        idx = np.searchsorted(frequencies, freq_at_cursor)
                        idx = np.clip(idx, 0, len(magnitudes) - 1)
                        mag = magnitudes[idx]
                        
                        # Get channel name for display
                        # For normal mode, get datasets from box; for legacy mode (dataset_id=None), use self.sensor_data
                        if dataset_id is not None and hasattr(box, 'datasets'):
                            sensor_data = box.datasets.get(dataset_id)
                        else:
                            sensor_data = self.sensor_data
                        
                        if sensor_data and channel_idx < len(sensor_data.channel_names):
                            ch_name = sensor_data.channel_names[channel_idx]
                        else:
                            ch_name = f"Ch{channel_idx}"
                        
                        info_parts.append(f"{ch_name}: {mag:.3e}")
                
                if has_data:
                    hover_info_label.setText("<br>".join(info_parts))
                    hover_info_label.setVisible(True)
                else:
                    hover_info_label.setVisible(False)
                    
            except Exception:
                hover_info_label.setVisible(False)
        
        # Connect mouse move events through the ViewBox
        view_box.scene().sigMouseMoved.connect(_on_mouse_moved)

    def _set_box_normalized(self, box_index: int, normalized: bool):
        if normalized:
            self.normalized_boxes.add(box_index)
        else:
            self.normalized_boxes.discard(box_index)
        if self.current_fft_start_time is not None and self.current_fft_end_time is not None:
            self.update_fft(self.current_fft_start_time, self.current_fft_end_time)

    def _build_legacy_channel_plots(self):
        """Fallback layout when no boxes are available."""
        self.clear_plots()
        if self.sensor_data is None:
            return

        channels = self._get_channels_to_show()
        self._active_channel_indices = channels

        for pos, ch_idx in enumerate(channels):
            container = QWidget()
            container.setFixedHeight(220)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            # Add Y-axis control row
            y_control_layout = QHBoxLayout()
            y_control_layout.setContentsMargins(0, 0, 0, 0)
            y_control_layout.setSpacing(4)
            
            y_min_spin = QDoubleSpinBox()
            y_min_spin.setRange(-1e9, 1e9)
            y_min_spin.setDecimals(3)
            y_min_spin.setFixedWidth(80)
            y_min_spin.setToolTip("Y-axis minimum")
            
            y_max_spin = QDoubleSpinBox()
            y_max_spin.setRange(-1e9, 1e9)
            y_max_spin.setDecimals(3)
            y_max_spin.setFixedWidth(80)
            y_max_spin.setToolTip("Y-axis maximum")
            
            y_set_btn = QPushButton("Set Y")
            y_set_btn.setFixedWidth(44)
            y_set_btn.setFixedHeight(20)
            y_set_btn.setToolTip("Apply Y-axis range")
            
            y_autoscale_btn = QPushButton("Auto Y")
            y_autoscale_btn.setFixedWidth(50)
            y_autoscale_btn.setFixedHeight(20)
            y_autoscale_btn.setToolTip("Autoscale Y-axis (Ctrl+Y)")
            
            y_control_layout.addWidget(QLabel("Y:"))
            y_control_layout.addWidget(y_min_spin)
            y_control_layout.addWidget(QLabel("–"))
            y_control_layout.addWidget(y_max_spin)
            y_control_layout.addWidget(y_set_btn)
            y_control_layout.addWidget(y_autoscale_btn)
            y_control_layout.addStretch()
            
            layout.addLayout(y_control_layout)

            # Create a container for the plot and hover info overlay
            plot_container = QWidget()
            plot_container_layout = QVBoxLayout(plot_container)
            plot_container_layout.setContentsMargins(0, 0, 0, 0)
            plot_container_layout.setSpacing(0)

            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            plot_widget.setLabel('left', f'{self.sensor_data.channel_names[ch_idx]} - Magnitude')
            plot_widget.setLabel('bottom', 'Frequency', units='Hz')

            plot_widget.setAntialiasing(True)
            plot_widget.setMenuEnabled(False)

            # Create hover info label
            hover_info = QLabel("")
            hover_info.setStyleSheet(
                "background-color: rgba(255, 255, 255, 220); "
                "padding: 4px; border: 1px solid #999; border-radius: 3px; "
                "font-family: monospace; font-size: 10px;"
            )
            hover_info.setMaximumWidth(200)
            hover_info.setVisible(False)
            
            plot_container_layout.addWidget(plot_widget, stretch=1)
            plot_container_layout.addWidget(hover_info, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            
            layout.addWidget(plot_container)

            info_label = QLabel("Showing full signal. Select a region in Time Series to zoom.")
            info_label.setWordWrap(True)
            info_label.setMaximumHeight(60)
            info_label.setStyleSheet(
                "background-color: #f9f9f9; padding: 5px; border: 1px solid #ddd;"
            )
            layout.addWidget(info_label)

            self.plot_widgets.append(plot_widget)
            self.info_labels.append(info_label)
            self.hover_info_labels.append(hover_info)
            self.y_min_spins.append(y_min_spin)
            self.y_max_spins.append(y_max_spin)
            self.plots_layout.insertWidget(self.plots_layout.count() - 1, container)
            self.plots_layout.insertWidget(
                self.plots_layout.count() - 1, ResizeHandle(container)
            )
             
            # Connect Y-axis controls
            view_box = plot_widget.getViewBox()
             
            def _apply_y_impl(vb, y_min, y_max):
                lo = y_min.value()
                hi = y_max.value()
                if lo >= hi:
                    return
                x_min, x_max = vb.viewRange()[0]
                vb.setYRange(lo, hi, padding=0)
                vb.setXRange(x_min, x_max, padding=0)
             
            def _sync_y_factory(y_min_spinbox, y_max_spinbox):
                def _sync_y(vb, ranges):
                    lo, hi = ranges[1]
                    y_min_spinbox.blockSignals(True)
                    y_max_spinbox.blockSignals(True)
                    y_min_spinbox.setValue(lo)
                    y_max_spinbox.setValue(hi)
                    y_min_spinbox.blockSignals(False)
                    y_max_spinbox.blockSignals(False)
                return _sync_y
             
            def _autoscale_y_factory(vb, ch_idx):
                """Factory for per-plot autoscale using frequency-range-aware logic (legacy mode)."""
                def _autoscale_y():
                    x_min, x_max = vb.viewRange()[0]
                    y_min_global = np.inf
                    y_max_global = -np.inf
                     
                    # Use cached FFT data for this channel
                    cache_key = (None, ch_idx)  # In legacy mode, dataset_id is None
                    if cache_key not in self.fft_cache:
                        vb.autoRange(padding=0.05)
                        return
                     
                    frequencies, magnitudes = self.fft_cache[cache_key]
                     
                    # Get indices for visible frequency range
                    i_lo = np.searchsorted(frequencies, x_min, side='left')
                    i_hi = np.searchsorted(frequencies, x_max, side='right')
                     
                    if i_lo >= i_hi or i_lo >= len(magnitudes):
                        vb.autoRange(padding=0.05)
                        return
                     
                    i_hi = min(i_hi, len(magnitudes))
                    mag_slice = magnitudes[i_lo:i_hi]
                     
                    if len(mag_slice) > 0:
                        y_min_global = min(y_min_global, float(np.min(mag_slice)))
                        y_max_global = max(y_max_global, float(np.max(mag_slice)))
                     
                    # Set Y range with padding
                    if np.isfinite(y_min_global) and np.isfinite(y_max_global):
                        y_range = y_max_global - y_min_global
                        if y_range > 0:
                            padding = y_range * 0.05
                            vb.setYRange(y_min_global - padding, y_max_global + padding, padding=0)
                        else:
                            vb.setYRange(y_min_global - 1, y_max_global + 1, padding=0)
                    else:
                        vb.autoRange(padding=0.05)
                     
                    vb.setXRange(x_min, x_max, padding=0)
                 
                return _autoscale_y
             
            y_set_btn.clicked.connect(lambda: _apply_y_impl(view_box, y_min_spin, y_max_spin))
            y_autoscale_btn.clicked.connect(_autoscale_y_factory(view_box, ch_idx))
            y_min_spin.editingFinished.connect(lambda: _apply_y_impl(view_box, y_min_spin, y_max_spin))
            y_max_spin.editingFinished.connect(lambda: _apply_y_impl(view_box, y_min_spin, y_max_spin))
            view_box.sigRangeChanged.connect(_sync_y_factory(y_min_spin, y_max_spin))

            # Set up mouse move event to track cursor and display freq/magnitude
            # For legacy mode, create a simple box object with _plot_items
            legacy_box = type('obj', (object,), {'_plot_items': [(None, ch_idx)]})()
            self._setup_hover_tracking(plot_widget, view_box, legacy_box, hover_info)


        if len(self.plot_widgets) > 1:
            for i in range(1, len(self.plot_widgets)):
                self.plot_widgets[i].setXLink(self.plot_widgets[0])
    
    def clear_plots(self):
        """Clear all existing plots."""
        while self.plots_layout.count() > 1:
            item = self.plots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.plot_widgets.clear()
        self.info_labels.clear()
        self.hover_info_labels.clear()
        self.normalization_checkboxes.clear()
        self.y_min_spins.clear()
        self.y_max_spins.clear()
    
    def update_fft(self, start_time: float, end_time: float, channel_idx: int = -1):
        """
        Compute and display FFT for the selected time region.

        When boxes are configured, one plot per box is updated with the FFTs of
        the traces marked for FFT inclusion.  The legacy ``channel_idx`` argument
        is ignored in box mode.
        """
        if self.sensor_data is None:
            return
        
        # Track current time range for FFT recomputation
        self.current_fft_start_time = start_time
        self.current_fft_end_time = end_time
        
        # Clear cache when updating FFT (new region selected)
        self.fft_cache.clear()

        timestamps, data_slice = self.sensor_data.get_time_slice(start_time, end_time)

        if len(timestamps) == 0:
            for plot_widget in self.plot_widgets:
                plot_widget.clear()
            for info_label in self.info_labels:
                info_label.setText("No data in selected region")
            self.overall_info.setText("No data in selected region")
            return

        if self.boxes:
            self._update_fft_for_boxes(start_time, end_time, data_slice, timestamps)
        else:
            self._update_fft_for_channels(start_time, end_time, data_slice, timestamps)

    def _update_fft_for_boxes(
        self, start_time: float, end_time: float, data_slice: np.ndarray, timestamps: np.ndarray
    ):
        """Update box-based FFT plots."""
        for pos, box in enumerate(self._display_boxes):
            if pos >= len(self.plot_widgets):
                break
            plot_widget = self.plot_widgets[pos]
            info_label = self.info_labels[pos]
            plot_widget.clear()

            fft_traces = box.get_fft_traces()
            if not fft_traces:
                info_label.setText("No FFT traces enabled for this box")
                continue

            peak_texts = []
            for trace in fft_traces:
                dataset_id = trace['dataset_id']
                ch_idx = trace['channel_idx']
                sensor_data = box.datasets.get(dataset_id)
                if sensor_data is None or ch_idx >= sensor_data.n_channels:
                    continue

                channel_data = data_slice[:, ch_idx]
                frequencies, magnitudes = compute_fft(
                    channel_data, sensor_data.sample_rate, self.fft_nperseg, self.fft_window
                )
                plot_widget.getViewBox().setLimits(
                    xMin=float(frequencies[0]),
                    xMax=float(frequencies[-1]),
                )
                 
                # Cache FFT data for later use (e.g., autoscale)
                self.fft_cache[(dataset_id, ch_idx)] = (frequencies, magnitudes)
                displayed_magnitudes = magnitudes
                if pos in self.normalized_boxes:
                    max_magnitude = float(np.max(np.abs(magnitudes), initial=0.0))
                    if max_magnitude > 0:
                        displayed_magnitudes = magnitudes / max_magnitude

                color = trace.get('color', (0, 0, 0))
                plot_widget.plot(
                    frequencies,
                    displayed_magnitudes,
                    pen=pg.mkPen(color=color, width=1.5),
                )

                peak_indices = find_peaks(frequencies, displayed_magnitudes, num_peaks=5)
                if len(peak_indices) > 0:
                    peak_freqs = frequencies[peak_indices]
                    peak_mags = displayed_magnitudes[peak_indices]
                    plot_widget.plot(
                        peak_freqs,
                        peak_mags,
                        pen=None,
                        symbol='o',
                        symbolBrush=color,
                        symbolSize=8,
                    )
                    ch_name = sensor_data.channel_names[ch_idx]
                    peak_strs = [f"{frequencies[idx]:.2f} Hz" for idx in peak_indices[:3]]
                    text = f"<b>{ch_name}:</b> " + ", ".join(peak_strs)
                    if len(peak_indices) > 3:
                        text += f" (+{len(peak_indices)-3} more)"
                    peak_texts.append(text)

            info_label.setText(
                "  |  ".join(peak_texts)
                if peak_texts else "No significant peaks found"
            )

        self.overall_info.setText(
            f"FFT Region: {start_time:.3f}s to {end_time:.3f}s "
            f"({end_time - start_time:.3f}s, {len(timestamps)} samples)"
        )

    def _update_fft_for_channels(
        self, start_time: float, end_time: float, data_slice: np.ndarray, timestamps: np.ndarray
    ):
        """Legacy channel-based FFT update."""
        for pos, ch_idx in enumerate(self._active_channel_indices):
            if pos >= len(self.plot_widgets):
                break
            plot_widget = self.plot_widgets[pos]
            info_label = self.info_labels[pos]
            plot_widget.clear()

            channel_data = data_slice[:, ch_idx]
            frequencies, magnitudes = compute_fft(
                channel_data, self.sensor_data.sample_rate, self.fft_nperseg, self.fft_window
            )
            plot_widget.getViewBox().setLimits(
                xMin=float(frequencies[0]),
                xMax=float(frequencies[-1]),
            )

            plot_widget.plot(
                frequencies,
                magnitudes,
                pen=pg.mkPen(color='k', width=1)
            )

            peak_indices = find_peaks(frequencies, magnitudes, num_peaks=5)
            if len(peak_indices) > 0:
                peak_freqs = frequencies[peak_indices]
                peak_mags = magnitudes[peak_indices]
                plot_widget.plot(
                    peak_freqs,
                    peak_mags,
                    pen=None,
                    symbol='o',
                    symbolBrush='r',
                    symbolSize=8
                )
                peak_text = f"<b>{self.sensor_data.channel_names[ch_idx]} Peaks:</b> "
                peak_strs = [f"{frequencies[idx]:.2f} Hz" for idx in peak_indices[:3]]
                peak_text += ", ".join(peak_strs)
                if len(peak_indices) > 3:
                    peak_text += f" (+{len(peak_indices)-3} more)"
                info_label.setText(peak_text)
            else:
                info_label.setText(
                    f"{self.sensor_data.channel_names[ch_idx]}: No significant peaks found"
                )

        self.overall_info.setText(
            f"FFT Region: {start_time:.3f}s to {end_time:.3f}s "
            f"({end_time - start_time:.3f}s, {len(timestamps)} samples)"
        )
    
    def set_fft_parameters(self, nperseg: int, window: str, selected_channel: int = -1):
        """
        Set FFT parameters and trigger recomputation if data exists.
        
        Args:
            nperseg: Number of samples per segment
            window: Window function type
            selected_channel: Channel index to recompute (-1 = all channels)
        """
        self.fft_nperseg = nperseg
        self.fft_window = window
        
        # Recompute FFT if we have a current time range and data
        if (self.sensor_data is not None and 
            self.current_fft_start_time is not None and 
            self.current_fft_end_time is not None):
            
            if selected_channel == -1:
                # Recompute all FFTs - trigger full update
                self.update_fft(self.current_fft_start_time, self.current_fft_end_time)
            else:
                # Recompute only selected channel - update cache and plots
                self._recompute_channel_fft(selected_channel)
    
    def _recompute_channel_fft(self, channel_idx: int):
        """Recompute FFT for a specific channel and update its plots."""
        if self.sensor_data is None or self.current_fft_start_time is None:
            return
        
        timestamps, data_slice = self.sensor_data.get_time_slice(
            self.current_fft_start_time, self.current_fft_end_time
        )
        
        if len(timestamps) == 0:
            return
        
        # Recompute FFT for all traces with this channel index across all boxes
        for box_idx, box in enumerate(self.boxes):
            if box_idx >= len(self.plot_widgets):
                break
            
            plot_widget = self.plot_widgets[box_idx]
            
            # Find traces matching this channel in this box
            for (dataset_id, ch_idx) in box._plot_items:
                if ch_idx != channel_idx:
                    continue
                
                sensor_data = box.datasets.get(dataset_id)
                if sensor_data is None or ch_idx >= sensor_data.n_channels:
                    continue
                
                # Get data for this channel
                channel_data = data_slice[:, ch_idx]
                
                # Compute FFT with new parameters
                frequencies, magnitudes = compute_fft(
                    channel_data, sensor_data.sample_rate, self.fft_nperseg, self.fft_window
                )
                
                # Update cache
                self.fft_cache[(dataset_id, ch_idx)] = (frequencies, magnitudes)
                
                # Clear and redraw plot
                plot_widget.clear()
                
                fft_traces = [t for t in box.get_fft_traces() if t['channel_idx'] == ch_idx]
                for trace in fft_traces:
                    color = trace.get('color', (0, 0, 0))
                    plot_widget.plot(
                        frequencies,
                        magnitudes,
                        pen=pg.mkPen(color=color, width=1.5),
                    )
                    
                    # Plot peaks
                    peak_indices = find_peaks(frequencies, magnitudes, num_peaks=5)
                    if len(peak_indices) > 0:
                        peak_freqs = frequencies[peak_indices]
                        peak_mags = magnitudes[peak_indices]
                        plot_widget.plot(
                            peak_freqs,
                            peak_mags,
                            pen=None,
                            symbol='o',
                            symbolBrush=color,
                            symbolSize=8,
                        )

    def _get_channels_to_show(self) -> List[int]:
        """Return channel indices to display, respecting active_channels filter."""
        if self.sensor_data is None:
            return []
        all_ch = list(range(self.sensor_data.n_channels))
        if self.active_channels is None:
            return all_ch
        return [i for i in self.active_channels if 0 <= i < self.sensor_data.n_channels]

    def set_active_channels(self, channel_indices: List[int]):
        """Filter which channels are shown. Rebuilds plots immediately if data is loaded."""
        self.active_channels = channel_indices
        if self.boxes:
            self.set_boxes(self.boxes)
        elif self.sensor_data is not None:
            self._build_legacy_channel_plots()
    
    def autoscale_y_axis(self):
        """Autoscale Y-axis for each FFT plot independently based on visible frequency range."""
        for i, plot_widget in enumerate(self.plot_widgets):
            view_box = plot_widget.getViewBox()
            x_min, x_max = view_box.viewRange()[0]
            
            # Calculate y-range specific to this plot only
            y_min_for_this_plot = np.inf
            y_max_for_this_plot = -np.inf
            
            # For box-based layout: each plot corresponds to a box
            if self.boxes and i < len(self.boxes):
                box = self.boxes[i]
                # Get all traces in this specific box only
                for (dataset_id, channel_idx) in box._plot_items:
                    # Use cached FFT data (computed during _update_fft_for_boxes)
                    cache_key = (dataset_id, channel_idx)
                    if cache_key not in self.fft_cache:
                        continue
                    
                    frequencies, magnitudes = self.fft_cache[cache_key]
                    
                    # Get indices for visible frequency range
                    i_lo = np.searchsorted(frequencies, x_min, side='left')
                    i_hi = np.searchsorted(frequencies, x_max, side='right')
                    
                    if i_lo >= i_hi or i_lo >= len(magnitudes):
                        continue
                    
                    i_hi = min(i_hi, len(magnitudes))
                    mag_slice = magnitudes[i_lo:i_hi]
                    
                    if len(mag_slice) > 0:
                        y_min_for_this_plot = min(y_min_for_this_plot, float(np.min(mag_slice)))
                        y_max_for_this_plot = max(y_max_for_this_plot, float(np.max(mag_slice)))
            
            # Set Y range with padding - apply ONLY to this plot
            if np.isfinite(y_min_for_this_plot) and np.isfinite(y_max_for_this_plot):
                y_range = y_max_for_this_plot - y_min_for_this_plot
                if y_range > 0:
                    padding = y_range * 0.05
                    view_box.setYRange(y_min_for_this_plot - padding, y_max_for_this_plot + padding, padding=0)
                else:
                    view_box.setYRange(y_min_for_this_plot - 1, y_max_for_this_plot + 1, padding=0)
            else:
                view_box.autoRange(padding=0.05)
            
            # Maintain x-range
            view_box.setXRange(x_min, x_max, padding=0)
