"""
Annotation panel for managing annotation labels and categories.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QPushButton,
    QHBoxLayout, QInputDialog, QColorDialog, QListWidgetItem, QMessageBox,
    QDialog, QLineEdit, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, Optional
from src.widgets.parameter_panel import CollapsibleSection


class AnnotationPanel(QWidget):
    """
    Panel for managing annotation labels and selecting active annotation category.
    """
    
    # Signal emitted when active label changes
    label_selected = pyqtSignal(str, tuple)  # label_name, color_rgb
    
    # Signal emitted when labels are modified
    labels_changed = pyqtSignal()
    create_annotation_requested = pyqtSignal()
    delete_selected_requested = pyqtSignal()
    delete_all_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Dictionary mapping label names to colors (RGB tuples)
        self.labels: Dict[str, tuple] = {
            'Label1': (255, 0, 0),      # Red
            'Label2': (0, 255, 0),      # Green
            'Label3': (0, 0, 255),      # Blue
        }
        
        self.active_label: Optional[str] = 'Label1'
        
        self.init_ui()
        self.populate_label_list()
    
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Annotation Labels collapsible section
        labels_section = CollapsibleSection("Annotation Labels")

        manage_btn = QPushButton("Manage Annotation Labels")
        manage_btn.clicked.connect(self.manage_labels)
        labels_section.add_widget(manage_btn)

        # Active label list
        self.label_list = QListWidget()
        self.label_list.itemClicked.connect(self.on_label_clicked)
        self.label_list.itemDoubleClicked.connect(self.edit_label)
        labels_section.add_widget(self.label_list)

        # Buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.create_annotation_requested)
        btn_layout.addWidget(create_btn)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_requested)
        btn_layout.addWidget(delete_btn)
        clear_btn = QPushButton("Delete All")
        clear_btn.clicked.connect(self.delete_all_requested)
        btn_layout.addWidget(clear_btn)
        labels_section.add_widget(btn_widget)

        main_layout.addWidget(labels_section)

        # Add stretch
        main_layout.addStretch()

    def manage_labels(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Annotation Labels")
        layout = QVBoxLayout(dialog)
        rows = []
        for name, color in self.labels.items():
            row = QHBoxLayout()
            name_edit = QLineEdit(name)
            color_btn = QPushButton()
            color_btn.setStyleSheet(
                f"background-color: rgb({color[0]}, {color[1]}, {color[2]});"
            )
            color_btn.clicked.connect(
                lambda checked=False, button=color_btn, current=color:
                self._choose_dialog_color(button, current)
            )
            delete_btn = QPushButton("Delete")
            row.addWidget(name_edit)
            row.addWidget(color_btn)
            row.addWidget(delete_btn)
            layout.addLayout(row)
            rows.append((name, name_edit, color_btn, delete_btn))
            delete_btn.clicked.connect(
                lambda checked=False, edit=name_edit, color=color_btn, button=delete_btn:
                self._mark_label_deleted(edit, color, button)
            )
        add_btn = QPushButton("Add Label")
        add_btn.clicked.connect(lambda: self._add_label_dialog_row(layout, rows))
        layout.addWidget(add_btn)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self._save_label_dialog(dialog, rows))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _add_label_dialog_row(self, layout, rows):
        row = QHBoxLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("New label name")
        color_btn = QPushButton()
        color_btn.setProperty("label_color", (128, 128, 128))
        color_btn.setStyleSheet("background-color: rgb(128, 128, 128);")
        color_btn.clicked.connect(
            lambda checked=False, button=color_btn:
            self._choose_dialog_color(button, button.property("label_color"))
        )
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(
            lambda checked=False, edit=name_edit, color=color_btn, button=delete_btn:
            self._mark_label_deleted(edit, color, button)
        )
        row.addWidget(name_edit)
        row.addWidget(color_btn)
        row.addWidget(delete_btn)
        layout.insertLayout(layout.count() - 2, row)
        rows.append((None, name_edit, color_btn, delete_btn))

    def _choose_dialog_color(self, button, current):
        chosen = QColorDialog.getColor(QColor(*current), self, "Choose Label Color")
        if chosen.isValid():
            button.setProperty("label_color", (chosen.red(), chosen.green(), chosen.blue()))
            button.setStyleSheet(
                f"background-color: rgb({chosen.red()}, {chosen.green()}, {chosen.blue()});"
            )

    def _mark_label_deleted(self, name_edit, color_btn, delete_btn):
        name_edit.clear()
        name_edit.setEnabled(False)
        color_btn.setEnabled(False)
        delete_btn.setEnabled(False)

    def _save_label_dialog(self, dialog, rows):
        updated = {}
        for old_name, name_edit, color_btn, _ in rows:
            name = name_edit.text().strip()
            if not name:
                continue
            color = color_btn.property("label_color")
            if color is None:
                color = self.labels[old_name] if old_name is not None else (128, 128, 128)
            updated[name] = tuple(color)
        self.labels = updated
        self.active_label = next(iter(updated), None)
        self.populate_label_list()
        self.labels_changed.emit()
        dialog.accept()

    def set_labels(self, labels: Dict[str, tuple], active_label: Optional[str] = None):
        """Replace displayed labels without emitting a change notification."""
        self.labels = dict(labels)
        self.active_label = active_label if active_label in self.labels else next(
            iter(self.labels), None
        )
        self.populate_label_list()
    
    def populate_label_list(self):
        """Populate the label list widget."""
        self.label_list.clear()
        
        for label_name, color in self.labels.items():
            item = QListWidgetItem(label_name)
            
            # Set background color
            qcolor = QColor(*color)
            item.setBackground(QBrush(qcolor))
            
            # Set text color (white for dark backgrounds, black for light)
            luminance = (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])
            text_color = QColor(0, 0, 0) if luminance > 128 else QColor(255, 255, 255)
            item.setForeground(QBrush(text_color))
            
            self.label_list.addItem(item)
        
        # Select active label
        if self.active_label:
            for i in range(self.label_list.count()):
                if self.label_list.item(i).text() == self.active_label:
                    self.label_list.setCurrentRow(i)
                    break
    
    def on_label_clicked(self, item: QListWidgetItem):
        """Handle label selection."""
        label_name = item.text()
        self.active_label = label_name
        color = self.labels[label_name]
        self.label_selected.emit(label_name, color)
    
    def add_label(self):
        """Add a new label."""
        label_name, ok = QInputDialog.getText(
            self,
            "Add Label",
            "Enter label name:"
        )
        
        if ok and label_name:
            # Check if label already exists
            if label_name in self.labels:
                QMessageBox.warning(
                    self,
                    "Duplicate Label",
                    f"Label '{label_name}' already exists."
                )
                return
            
            # Add with default color (random-ish)
            import random
            color = (
                random.randint(50, 255),
                random.randint(50, 255),
                random.randint(50, 255)
            )
            self.labels[label_name] = color
            
            # Update UI
            self.populate_label_list()
            self.labels_changed.emit()
    
    def edit_label(self):
        """Edit the selected label name."""
        current_item = self.label_list.currentItem()
        if not current_item:
            return
        
        old_name = current_item.text()
        
        new_name, ok = QInputDialog.getText(
            self,
            "Edit Label",
            "Enter new label name:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            # Check if new name already exists
            if new_name in self.labels:
                QMessageBox.warning(
                    self,
                    "Duplicate Label",
                    f"Label '{new_name}' already exists."
                )
                return
            
            # Rename label
            color = self.labels[old_name]
            del self.labels[old_name]
            self.labels[new_name] = color
            
            # Update active label if it was renamed
            if self.active_label == old_name:
                self.active_label = new_name
            
            # Update UI
            self.populate_label_list()
            self.labels_changed.emit()
    
    def remove_label(self):
        """Remove the selected label."""
        current_item = self.label_list.currentItem()
        if not current_item:
            return
        
        label_name = current_item.text()
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Remove Label",
            f"Remove label '{label_name}'?\n\nExisting annotations with this label will remain but won't have a label category.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.labels[label_name]
            
            # Update active label
            if self.active_label == label_name:
                self.active_label = list(self.labels.keys())[0] if self.labels else None
            
            # Update UI
            self.populate_label_list()
            self.labels_changed.emit()
    
    def change_label_color(self):
        """Change the color of the selected label."""
        current_item = self.label_list.currentItem()
        if not current_item:
            return
        
        label_name = current_item.text()
        current_color = self.labels[label_name]
        
        # Open color dialog
        qcolor = QColorDialog.getColor(QColor(*current_color), self)
        
        if qcolor.isValid():
            new_color = (qcolor.red(), qcolor.green(), qcolor.blue())
            self.labels[label_name] = new_color
            
            # Update UI
            self.populate_label_list()
            self.labels_changed.emit()
    
    def get_active_label(self):
        """
        Get the currently active label and its color.
        
        Returns:
            Tuple of (label_name, color_rgb) or (None, None)
        """
        if self.active_label and self.active_label in self.labels:
            return self.active_label, self.labels[self.active_label]
        return None, None
    
    def get_all_labels(self):
        """
        Get all labels and their colors.
        
        Returns:
            List of tuples (label_name, color_tuple)
        """
        return [(name, color) for name, color in self.labels.items()]
    
    def clear_labels(self):
        """Clear all labels."""
        self.labels.clear()
        self.active_label = None
        self.populate_label_list()
        self.labels_changed.emit()
    
    def add_label(self, label_name: str, color: tuple):
        """
        Add a label programmatically (for config loading).
        
        Args:
            label_name: Name of the label
            color: RGB color tuple
        """
        self.labels[label_name] = color
        self.populate_label_list()
        
        # Set as active if it's the first label
        if not self.active_label:
            self.active_label = label_name
            self.label_selected.emit(label_name, color)
