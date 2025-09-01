import sys
import os
import shutil
from pathlib import Path
from typing import List, Tuple

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                               QPushButton, QFileDialog, QListWidget, QComboBox,
                               QSpinBox, QGroupBox, QProgressBar, QMessageBox,
                               QCheckBox, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QFont

from PIL import Image, ImageOps
import pillow_heif


class ImageProcessor(QThread):
    progress_updated = Signal(int)
    progress_count_updated = Signal(int, int)  # current, total
    status_updated = Signal(str)
    finished_processing = Signal()
    
    def __init__(self, files: List[str], operation: str, output_dir: str, **kwargs):
        super().__init__()
        self.files = files
        self.operation = operation
        self.output_dir = output_dir
        self.kwargs = kwargs
        
    def run(self):
        total_files = len(self.files)
        
        for i, file_path in enumerate(self.files):
            try:
                self.status_updated.emit(f"Processing: {os.path.basename(file_path)}")
                
                if self.operation == "resize":
                    self._resize_image(file_path)
                elif self.operation == "invert":
                    self._invert_image(file_path)
                elif self.operation == "rename":
                    self._rename_file(file_path)
                    
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                self.progress_count_updated.emit(i + 1, total_files)
                
            except Exception as e:
                self.status_updated.emit(f"Error processing {os.path.basename(file_path)}: {str(e)}")
                
        self.status_updated.emit("Processing complete!")
        self.finished_processing.emit()
        
    def _resize_image(self, file_path: str):
        width = self.kwargs.get('width', 800)
        height = self.kwargs.get('height', 600)
        output_format = self.kwargs.get('format', 'JPEG')
        
        with Image.open(file_path) as img:
            print(f"Original: {img.mode}, size: {img.size}")
            
            # Convert to a standard format first before resizing
            if img.mode in ('I;16', 'I', 'F'):
                print(f"Converting {img.mode} to L")
                try:
                    if img.mode == 'I;16':
                        # Convert I;16 to numpy array, scale down, then back to PIL
                        import numpy as np
                        img_array = np.array(img)
                        # Scale from 16-bit (0-65535) to 8-bit (0-255)
                        img_array = (img_array / 256).astype(np.uint8)
                        img = Image.fromarray(img_array, mode='L')
                    else:
                        img = img.convert('L')
                    print(f"After conversion: {img.mode}")
                except Exception as e:
                    print(f"Conversion error: {e}")
                    # Fallback - convert to RGB directly
                    img = img.convert('RGB')
                    print(f"Fallback conversion to: {img.mode}")
            
            resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
            print(f"After resize: {resized_img.mode}, size: {resized_img.size}")
            
            # Convert to RGB for JPEG format
            if output_format.upper() == 'JPEG':
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    if resized_img.mode == 'P':
                        # Convert palette to RGBA first
                        resized_img = resized_img.convert('RGBA')
                    
                    # Create white background for transparency
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    if resized_img.mode == 'RGBA':
                        background.paste(resized_img, mask=resized_img.split()[-1])
                    else:
                        background.paste(resized_img)
                    resized_img = background
                elif resized_img.mode == 'L':
                    # Convert grayscale to RGB
                    resized_img = resized_img.convert('RGB')
                elif resized_img.mode != 'RGB':
                    resized_img = resized_img.convert('RGB')
            
            output_path = self._get_output_path(file_path, output_format)
            print(f"Final mode before save: {resized_img.mode}")
            print(f"Saving to: {output_path}")
            
            # Save with appropriate parameters
            save_kwargs = {'format': output_format.upper()}
            if output_format.upper() == 'JPEG':
                save_kwargs['quality'] = 95
                save_kwargs['optimize'] = True
            
            try:
                resized_img.save(output_path, **save_kwargs)
                print(f"Successfully saved: {output_path}")
            except Exception as e:
                print(f"Error saving: {e}")
                raise
            
    def _invert_image(self, file_path: str):
        output_format = self.kwargs.get('format', 'JPEG')
        
        with Image.open(file_path) as img:
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                inverted_img = ImageOps.invert(rgb_img)
            else:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                inverted_img = ImageOps.invert(img)
            
            output_path = self._get_output_path(file_path, output_format)
            inverted_img.save(output_path, format=output_format.upper())
            
    def _rename_file(self, file_path: str):
        replace_text = self.kwargs.get('replace_text', '')
        with_text = self.kwargs.get('with_text', '')
        preserve_format = self.kwargs.get('preserve_format', True)
        
        original_path = Path(file_path)
        original_name = original_path.stem
        original_extension = original_path.suffix
        
        # Apply replace and prefix operations
        new_name = original_name
        if replace_text:
            new_name = new_name.replace(replace_text, with_text)
        
        prefix_text = self.kwargs.get('prefix_text', '')
        if prefix_text:
            new_name = prefix_text + new_name
        
        # Copy file with new name
        if preserve_format:
            new_extension = original_extension
        else:
            output_format = self.kwargs.get('format', 'JPEG')
            new_extension = '.jpg' if output_format.upper() == 'JPEG' else f'.{output_format.lower()}'
            
        # Determine output directory
        if self.output_dir == "":  # Use original directory
            output_dir = str(original_path.parent)
        else:
            output_dir = self.output_dir
            
        output_path = os.path.join(output_dir, f"{new_name}{new_extension}")
        
        if preserve_format:
            # Just copy the file with new name
            shutil.copy2(file_path, output_path)
        else:
            # Convert format and save with new name
            with Image.open(file_path) as img:
                output_format = self.kwargs.get('format', 'JPEG')
                if output_format.upper() == 'JPEG' and img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                img.save(output_path, format=output_format.upper())
    
    def _get_output_path(self, file_path: str, output_format: str) -> str:
        original_path = Path(file_path)
        base_name = original_path.stem
        
        # Apply rename if specified
        replace_text = self.kwargs.get('replace_text', '')
        with_text = self.kwargs.get('with_text', '')
        prefix_text = self.kwargs.get('prefix_text', '')
        
        if replace_text:
            base_name = base_name.replace(replace_text, with_text)
        
        if prefix_text:
            base_name = prefix_text + base_name
        
        extension = '.jpg' if output_format.upper() == 'JPEG' else f'.{output_format.lower()}'
        
        # Determine output directory
        if self.output_dir == "":  # Use original directory
            output_dir = str(original_path.parent)
        else:
            output_dir = self.output_dir
            
        return os.path.join(output_dir, f"{base_name}{extension}")


class ImageWranglerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        pillow_heif.register_heif_opener()
        self.init_ui()
        self.selected_files = []
        self.output_directory = ""
        self.processor_thread = None
        self.current_progress = 0
        
    def init_ui(self):
        self.setWindowTitle("ImageWrangler - Batch Image Processor")
        self.setMinimumSize(800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # File selection section
        file_group = QGroupBox("Select Images")
        file_layout = QVBoxLayout(file_group)
        
        file_buttons_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("Select Images")
        self.select_files_btn.clicked.connect(self.select_files)
        self.clear_files_btn = QPushButton("Clear All")
        self.clear_files_btn.clicked.connect(self.clear_files)
        
        file_buttons_layout.addWidget(self.select_files_btn)
        file_buttons_layout.addWidget(self.clear_files_btn)
        file_buttons_layout.addStretch()
        
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(120)
        
        file_layout.addLayout(file_buttons_layout)
        file_layout.addWidget(self.files_list)
        
        # Output directory section
        output_group = QGroupBox("Output Directory")
        output_layout = QVBoxLayout(output_group)
        
        # Directory selection row
        dir_row = QHBoxLayout()
        self.output_path_label = QLabel("No directory selected")
        self.select_output_btn = QPushButton("Select Output Directory")
        self.select_output_btn.clicked.connect(self.select_output_directory)
        
        dir_row.addWidget(self.output_path_label)
        dir_row.addWidget(self.select_output_btn)
        
        # Use original directory checkbox
        self.use_original_dir_cb = QCheckBox("Use original directory (may overwrite files)")
        self.use_original_dir_cb.toggled.connect(self._on_use_original_toggled)
        
        output_layout.addLayout(dir_row)
        output_layout.addWidget(self.use_original_dir_cb)
        
        # Rename options section (applies to all operations)
        rename_group = QGroupBox("Rename Options (applies to all operations)")
        rename_layout = QGridLayout(rename_group)
        
        rename_layout.addWidget(QLabel("Replace:"), 0, 0)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Text to replace (optional)")
        rename_layout.addWidget(self.replace_input, 0, 1)
        
        rename_layout.addWidget(QLabel("With:"), 0, 2)
        self.with_input = QLineEdit()
        self.with_input.setPlaceholderText("Replacement text")
        rename_layout.addWidget(self.with_input, 0, 3)
        
        rename_layout.addWidget(QLabel("Add prefix:"), 0, 4)
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("Prefix (optional)")
        rename_layout.addWidget(self.prefix_input, 0, 5)
        
        # Standalone rename button
        self.rename_only_btn = QPushButton("Rename Only")
        self.rename_only_btn.clicked.connect(self.rename_files_only)
        rename_layout.addWidget(self.rename_only_btn, 1, 0, 1, 6)
        
        # Operations section
        operations_layout = QHBoxLayout()
        
        # Resize operation
        resize_group = QGroupBox("Resize Images")
        resize_layout = QGridLayout(resize_group)
        
        resize_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(800)
        resize_layout.addWidget(self.width_input, 0, 1)
        
        resize_layout.addWidget(QLabel("Height:"), 1, 0)
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(600)
        resize_layout.addWidget(self.height_input, 1, 1)
        
        resize_layout.addWidget(QLabel("Format:"), 2, 0)
        self.resize_format = QComboBox()
        self.resize_format.addItems(["JPEG", "PNG", "WEBP"])
        resize_layout.addWidget(self.resize_format, 2, 1)
        
        self.resize_btn = QPushButton("Resize Images")
        self.resize_btn.clicked.connect(self.resize_images)
        resize_layout.addWidget(self.resize_btn, 3, 0, 1, 2)
        
        # Color inversion operation
        invert_group = QGroupBox("Invert Colors")
        invert_layout = QVBoxLayout(invert_group)
        
        invert_layout.addWidget(QLabel("Output Format:"))
        self.invert_format = QComboBox()
        self.invert_format.addItems(["JPEG", "PNG", "WEBP"])
        invert_layout.addWidget(self.invert_format)
        
        self.invert_btn = QPushButton("Invert Colors")
        self.invert_btn.clicked.connect(self.invert_colors)
        invert_layout.addWidget(self.invert_btn)
        invert_layout.addStretch()
        
        operations_layout.addWidget(resize_group)
        operations_layout.addWidget(invert_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready (0/0)")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        # Add all sections to main layout
        layout.addWidget(file_group)
        layout.addWidget(output_group)
        layout.addWidget(rename_group)
        layout.addLayout(operations_layout)
        layout.addWidget(progress_group)
        
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.heic *.heif);;All Files (*)"
        )
        
        if files:
            self.selected_files.extend(files)
            self.update_files_list()
            
    def clear_files(self):
        self.selected_files.clear()
        self.update_files_list()
        
    def update_files_list(self):
        self.files_list.clear()
        for file_path in self.selected_files:
            self.files_list.addItem(os.path.basename(file_path))
        self._update_status_count()
            
    def select_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_directory = directory
            self.output_path_label.setText(directory)
            
    def resize_images(self):
        if not self._validate_inputs():
            return
            
        width = self.width_input.value()
        height = self.height_input.value()
        output_format = self.resize_format.currentText()
        
        # Include rename options
        kwargs = {
            'width': width,
            'height': height,
            'format': output_format,
            'replace_text': self.replace_input.text(),
            'with_text': self.with_input.text(),
            'prefix_text': self.prefix_input.text()
        }
        
        self._start_processing("resize", **kwargs)
        
    def invert_colors(self):
        if not self._validate_inputs():
            return
            
        output_format = self.invert_format.currentText()
        
        # Include rename options
        kwargs = {
            'format': output_format,
            'replace_text': self.replace_input.text(),
            'with_text': self.with_input.text(),
            'prefix_text': self.prefix_input.text()
        }
        
        self._start_processing("invert", **kwargs)
        
    def rename_files_only(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select some images first.")
            return
            
        replace_text = self.replace_input.text()
        with_text = self.with_input.text()
        prefix_text = self.prefix_input.text()
        
        if not replace_text and not prefix_text:
            QMessageBox.warning(self, "Warning", "Please enter text to replace or add a prefix.")
            return
        
        kwargs = {
            'replace_text': replace_text,
            'with_text': with_text,
            'prefix_text': prefix_text,
            'preserve_format': True,
            'use_original_dir': self.use_original_dir_cb.isChecked()
        }
        
        self._start_processing("rename", **kwargs)
        
        
    def _validate_inputs(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select some images first.")
            return False
            
        if not self.use_original_dir_cb.isChecked() and not self.output_directory:
            QMessageBox.warning(self, "Warning", "Please select an output directory or check 'Use original directory'.")
            return False
            
        return True
        
    def _start_processing(self, operation: str, **kwargs):
        self.progress_bar.setValue(0)
        self.current_progress = 0
        count = len(self.selected_files)
        self.status_label.setText(f"Starting processing... (0/{count})")
        
        # Disable buttons during processing
        self._set_buttons_enabled(False)
        
        # Determine output directory
        if self.use_original_dir_cb.isChecked():
            output_dir = ""  # Special flag for original directory
        else:
            output_dir = self.output_directory
        
        # Start processing thread
        self.processor_thread = ImageProcessor(
            self.selected_files, operation, output_dir, **kwargs
        )
        self.processor_thread.progress_updated.connect(self.progress_bar.setValue)
        self.processor_thread.progress_count_updated.connect(self._update_progress_count)
        self.processor_thread.status_updated.connect(self._update_status_text)
        self.processor_thread.finished_processing.connect(self._processing_finished)
        self.processor_thread.start()
        
    def _update_status_count(self):
        count = len(self.selected_files)
        current_text = self.status_label.text()
        if '(' in current_text:
            base_text = current_text.split('(')[0].strip()
        else:
            base_text = current_text
        self.status_label.setText(f"{base_text} (0/{count})")
    
    def _update_progress_count(self, current: int, total: int):
        self.current_progress = current
        current_text = self.status_label.text()
        if '(' in current_text:
            base_text = current_text.split('(')[0].strip()
        else:
            base_text = current_text
        self.status_label.setText(f"{base_text} ({current}/{total})")
    
    def _update_status_text(self, text: str):
        count = len(self.selected_files)
        self.status_label.setText(f"{text} ({self.current_progress}/{count})")
    
    def _processing_finished(self):
        self._set_buttons_enabled(True)
        count = len(self.selected_files)
        self.status_label.setText(f"Processing complete! ({count}/{count})")
        QMessageBox.information(self, "Success", "Image processing completed successfully!")
        
    def _on_use_original_toggled(self, checked: bool):
        self.select_output_btn.setEnabled(not checked)
        self.output_path_label.setEnabled(not checked)
        if checked:
            self.output_path_label.setText("Will use original directories")
        else:
            self.output_path_label.setText("No directory selected")
    
    def _set_buttons_enabled(self, enabled: bool):
        self.select_files_btn.setEnabled(enabled)
        self.clear_files_btn.setEnabled(enabled)
        self.select_output_btn.setEnabled(not self.use_original_dir_cb.isChecked() and enabled)
        self.resize_btn.setEnabled(enabled)
        self.invert_btn.setEnabled(enabled)
        self.rename_only_btn.setEnabled(enabled)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = ImageWranglerApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()