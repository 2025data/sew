import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QLabel,
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
import pystitch

class EmbroideryCanvas(QWidget):
    """Widget to display the embroidery preview"""
    def __init__(self):
        super().__init__()
        self.drawing_data = None
        self.setMinimumSize(600, 600)
        
    def load_drawing(self, data):
        """Load drawing data from JSON"""
        self.drawing_data = data
        self.update()
        
    def paintEvent(self, event):
        """Paint the drawing preview"""
        if not self.drawing_data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # Calculate scaling to fit widget
        if self.drawing_data.get('width') and self.drawing_data.get('height'):
            scale_x = self.width() / self.drawing_data['width']
            scale_y = self.height() / self.drawing_data['height']
            scale = min(scale_x, scale_y, 1.0)  # Don't scale up, only down
        else:
            scale = 1.0
            
        # Draw each stroke
        for stroke in self.drawing_data.get('strokes', []):
            color = QColor(stroke['color'])
            width = stroke['width'] * scale
            coords = stroke['coordinates']
            
            pen = QPen(color, width, Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            if stroke.get('type') == 'dot':
                # Draw dot
                if coords:
                    x, y = coords[0]
                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(QPointF(x * scale, y * scale), 
                                      width / 2, width / 2)
            else:
                # Draw line
                if len(coords) > 1:
                    for i in range(len(coords) - 1):
                        x1, y1 = coords[i]
                        x2, y2 = coords[i + 1]
                        painter.drawLine(QPointF(x1 * scale, y1 * scale),
                                       QPointF(x2 * scale, y2 * scale))

class SewViewer(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.sew_folder = os.path.join(os.path.dirname(__file__), 'SewCustom')
        os.makedirs(self.sew_folder, exist_ok=True)
        
        self.init_ui()
        self.load_file_list()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('Embroidery Viewer & Converter')
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        
        # Left panel - file list
        left_panel = QVBoxLayout()
        
        left_panel.addWidget(QLabel('Saved Drawings:'))
        
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.load_drawing)
        left_panel.addWidget(self.file_list)
        
        refresh_btn = QPushButton('🔄 Refresh List')
        refresh_btn.clicked.connect(self.load_file_list)
        left_panel.addWidget(refresh_btn)
        
        main_layout.addLayout(left_panel, 1)
        
        # Right panel - preview and controls
        right_panel = QVBoxLayout()
        
        right_panel.addWidget(QLabel('Preview:'))
        
        self.canvas = EmbroideryCanvas()
        right_panel.addWidget(self.canvas)
        
        # Button panel
        button_layout = QHBoxLayout()
        
        self.convert_btn = QPushButton('🧵 Convert to PES')
        self.convert_btn.clicked.connect(self.convert_to_pes)
        self.convert_btn.setEnabled(False)
        button_layout.addWidget(self.convert_btn)
        
        self.export_svg_btn = QPushButton('📄 Export SVG')
        self.export_svg_btn.clicked.connect(self.export_svg)
        self.export_svg_btn.setEnabled(False)
        button_layout.addWidget(self.export_svg_btn)
        
        right_panel.addLayout(button_layout)
        
        # Info label
        self.info_label = QLabel('Select a drawing file to preview')
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(self.info_label)
        
        main_layout.addLayout(right_panel, 2)
        
    def load_file_list(self):
        """Load list of JSON/TXT files from SewCustom folder"""
        self.file_list.clear()
        
        if not os.path.exists(self.sew_folder):
            return
            
        files = [f for f in os.listdir(self.sew_folder) if f.endswith('.json') or f.endswith('.txt')]
        files.sort(reverse=True)  # Most recent first
        
        for filename in files:
            self.file_list.addItem(filename)
            
        self.info_label.setText(f'Found {len(files)} drawing(s)')
        
    def load_drawing(self, item):
        """Load and display selected drawing"""
        filename = item.text()
        filepath = os.path.join(self.sew_folder, filename)
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            self.canvas.load_drawing(data)
            self.current_file = filepath
            self.convert_btn.setEnabled(True)
            self.export_svg_btn.setEnabled(True)
            
            # Update info
            num_strokes = len(data.get('strokes', []))
            timestamp = data.get('timestamp', 'Unknown')
            self.info_label.setText(f'{filename}\n{num_strokes} strokes | {timestamp}')
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load file:\n{e}')
            
    def convert_to_pes(self):
        """Convert current drawing to PES embroidery format"""
        if not self.current_file:
            return
            
        try:
            # Load JSON data
            with open(self.current_file, 'r') as f:
                data = json.load(f)
                
            # Create embroidery pattern
            pattern = pystitch.EmbPattern()
            
            # Get canvas dimensions from saved data
            canvas_width = data.get('width', 800)  # Kindle canvas width in pixels
            canvas_height = data.get('height', 900)  # Kindle canvas height in pixels
            
            print(f"Canvas dimensions: {canvas_width} x {canvas_height} pixels")
            
            # Calculate the aspect ratio of the Kindle canvas
            canvas_aspect = canvas_width / canvas_height
            
            # Target dimensions - maintain Kindle aspect ratio but scale to reasonable size
            # Let's use 3.5" as the width and calculate height to maintain aspect ratio
            target_width_inches = 3.5
            target_height_inches = target_width_inches / canvas_aspect
            
            print(f"Target dimensions: {target_width_inches:.2f}\" x {target_height_inches:.2f}\"")
            
            # Convert inches to pystitch units (1 unit = 0.1mm, 1 inch = 25.4mm)
            target_width_units = target_width_inches * 254  # 254 units per inch
            target_height_units = target_height_inches * 254
            
            # Calculate uniform scale to maintain aspect ratio
            scale = target_width_units / canvas_width
            
            # Verify the scale produces correct dimensions
            print(f"Scale factor: {scale:.4f}")
            print(f"Output size: {canvas_width * scale / 254:.2f}\" x {canvas_height * scale / 254:.2f}\"")
            
            # Count stroke types for debugging
            stroke_counts = {}
            
            # Convert each stroke
            for stroke in data.get('strokes', []):
                coords = stroke['coordinates']
                color = stroke['color']
                width = stroke.get('width', 12)  # Default to 12px if not specified
                
                if len(coords) < 2:
                    continue  # Skip single points
                    
                # Scale coordinates with uniform scaling to maintain aspect ratio
                scaled_coords = [(x * scale, y * scale) for x, y in coords]
                
                # Determine stitch type based on line width and color
                if color == '#FFFFFF':  # White - skip (no stitching)
                    print(f"Skipping white stroke (width: {width})")
                    continue
                elif width in [1, 2, 4, 7, 12, 20, 33]:
                    # Thin lines - use satin stitch (running stitch for lines)
                    stitch_type = 'satin'
                    stroke_counts[f'satin_{width}'] = stroke_counts.get(f'satin_{width}', 0) + 1
                elif width in [55, 92, 153, 300]:
                    # Thick lines - use fill/tatami stitch
                    stitch_type = 'fill'
                    stroke_counts[f'fill_{width}'] = stroke_counts.get(f'fill_{width}', 0) + 1
                else:
                    # Default to satin for unknown widths
                    stitch_type = 'satin'
                    stroke_counts[f'satin_{width}'] = stroke_counts.get(f'satin_{width}', 0) + 1
                
                # Add to pattern
                try:
                    pattern.add_block(scaled_coords, color)
                except Exception as e:
                    print(f"Warning: Could not add stroke with width {width}: {e}")
            
            # Print conversion summary
            print("\nStroke conversion summary:")
            for stitch_info, count in stroke_counts.items():
                print(f"  {stitch_info}: {count} strokes")
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            default_name = f'{base_name}.pes'
            
            # Save dialog
            output_file, _ = QFileDialog.getSaveFileName(
                self, 'Save PES File', default_name, 'PES Files (*.pes)'
            )
            
            if output_file:
                # Write PES file with settings for different stitch types
                pystitch.write_pes(pattern, output_file, {
                    'max_stitch': 120,
                    'tie_on': True,
                    'tie_off': True,
                    'auto_fill': True,      # Enable automatic fill detection
                    'fill_angle': 45,       # Angle for fill stitches
                    'satin_max_width': 10,  # Maximum width for satin before switching to fill
                    'density': 4.0          # Stitch density (stitches per mm)
                })
                
                QMessageBox.information(
                    self, 'Success', 
                    f'Successfully converted to PES!\n\nSaved to:\n{output_file}'
                )
                
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to convert:\n{e}')
            
    def export_svg(self):
        """Export current drawing to SVG format"""
        if not self.current_file:
            return
            
        try:
            # Load JSON data
            with open(self.current_file, 'r') as f:
                data = json.load(f)
                
            # Create embroidery pattern
            pattern = pystitch.EmbPattern()
            
            # Get canvas dimensions and calculate scale (same as PES conversion)
            canvas_width = data.get('width', 800)
            canvas_height = data.get('height', 900)
            
            # Calculate the aspect ratio and uniform scale
            canvas_aspect = canvas_width / canvas_height
            target_width_inches = 3.5
            target_height_inches = target_width_inches / canvas_aspect
            target_width_units = target_width_inches * 254
            scale = target_width_units / canvas_width
            
            # Convert each stroke
            for stroke in data.get('strokes', []):
                coords = stroke['coordinates']
                color = stroke['color']
                
                if len(coords) < 2:
                    continue
                    
                scaled_coords = [(x * scale, y * scale) for x, y in coords]
                pattern.add_block(scaled_coords, color)
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            default_name = f'{base_name}.svg'
            
            # Save dialog
            output_file, _ = QFileDialog.getSaveFileName(
                self, 'Save SVG File', default_name, 'SVG Files (*.svg)'
            )
            
            if output_file:
                pystitch.write_svg(pattern, output_file)
                
                QMessageBox.information(
                    self, 'Success', 
                    f'Successfully exported to SVG!\n\nSaved to:\n{output_file}'
                )
                
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to export:\n{e}')

def main():
    app = QApplication(sys.argv)
    viewer = SewViewer()
    viewer.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
