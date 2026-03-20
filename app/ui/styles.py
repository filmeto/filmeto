"""
样式库文件，用于定义全局样式和组件样式
"""

# Drawing tools widget styles
DRAWING_TOOLS_WIDGET_STYLE = """
/* Tool buttons */
QPushButton[objectName^="tool_"] {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 6px;
    width: 32px;
    height: 32px;
    margin: 2px;
    color: #ffffff;
    font-size: 14px;
    text-align: center;
}

QPushButton[objectName^="tool_"]:hover {
    background-color: #4c5052;
    border: 1px solid #666666;
}

QPushButton[objectName^="tool_"]:checked {
    background-color: #365880;
    border: 1px solid #4a80b0;
    font-weight: bold;
}

QPushButton[objectName^="tool_"]:pressed {
    background-color: #2c2f31;
}

/* Floating panel for tool configurations */
QFrame {
    background-color: #2d2d2d;
    border: 1px solid #555555;
    border-radius: 8px;
    padding: 10px;
    min-width: 200px;
    color: #ffffff;
}

/* Labels in the configuration panel */
QLabel {
    font-size: 12px;
    color: #ffffff;
    padding: 2px;
}

/* Comboboxes in the configuration panel */
QComboBox {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
    min-width: 120px;
}

QComboBox:hover {
    border: 1px solid #666666;
}

/* Spin boxes in the configuration panel */
QSpinBox {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
    color: #ffffff;
    min-width: 80px;
}

QSpinBox:hover {
    border: 1px solid #666666;
}

/* Buttons in the configuration panel */
QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
    color: #ffffff;
}

QPushButton:hover {
    background-color: #4c5052;
    border: 1px solid #666666;
}

QPushButton:pressed {
    background-color: #2c2f31;
}
"""

# 图层管理组件样式
LAYERS_WIDGET_STYLE = """
LayersWidget {
    background-color: #1e1e1e;
    border-right: 1px solid #333333;
}

LayersWidget QScrollArea {
    background-color: #1e1e1e;
    border: none;
}

LayersWidget QScrollArea > QWidget {
    background-color: #1e1e1e;
}

LayerItemWidget {
    background-color: #2d2d2d;
    border-bottom: 1px solid #252525;
    border-radius: 0px;
    padding: 0px;
    margin: 0px;
}

LayerItemWidget:hover {
    background-color: #3a3a3a;
    border-bottom: 1px solid #2a2a2a;
}

QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #555555;
    border-radius: 4px;
    color: white;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

QLabel {
    color: white;
    background-color: transparent;
    border: none;
}
"""

LAYER_ITEM_STYLE = """
LayerItemWidget {
    background-color: #2d2d2d;
    border-bottom: 1px solid #252525;
    border-radius: 0px;
    padding: 0px;
    margin: 0px;
}

LayerItemWidget:hover {
    background-color: #3a3a3a;
    border-bottom: 1px solid #2a2a2a;
}
"""

# Canvas工具组件样式
CANVAS_TOOLS_WIDGET_STYLE = """
CanvasToolsWidget {
    background-color: #2b2b2b;
    border-right: 1px solid #333333;
}

CanvasToolsWidget QGroupBox {
    background-color: #2b2b2b;
    border: 1px solid #555555;
    border-radius: 4px;
    margin-top: 1ex;
    color: #ffffff;
    font-weight: bold;
}

CanvasToolsWidget QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    background-color: #2b2b2b;
}

CanvasToolsWidget QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
    color: #ffffff;
    min-height: 20px;
}

CanvasToolsWidget QPushButton:hover {
    background-color: #4c5052;
    border: 1px solid #666666;
}

CanvasToolsWidget QPushButton:pressed {
    background-color: #2c2f31;
}

CanvasToolsWidget QPushButton:checked {
    background-color: #365880;
    border: 1px solid #4a80b0;
}

CanvasToolsWidget QPushButton[selected="true"] {
    background-color: #365880;
    border: 1px solid #4a80b0;
}

CanvasToolsWidget #DrawingTools QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    color: #ffffff;
    min-height: 36px;
    min-width: 36px;
    max-height: 36px;
    max-width: 36px;
}

CanvasToolsWidget #DrawingTools QPushButton:hover {
    background-color: #4c5052;
    border: 1px solid #666666;
}

CanvasToolsWidget #DrawingTools QPushButton:pressed {
    background-color: #2c2f31;
}

CanvasToolsWidget #DrawingTools QPushButton[selected="true"] {
    background-color: #365880;
    border: 1px solid #4a80b0;
}

CanvasToolsWidget QLabel {
    color: #ffffff;
    background-color: transparent;
}

CanvasToolsWidget QComboBox {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px 4px;
    color: #ffffff;
    min-height: 20px;
}

CanvasToolsWidget QComboBox:hover {
    border: 1px solid #666666;
}

CanvasToolsWidget QComboBox::drop-down {
    border: none;
}

CanvasToolsWidget QComboBox QAbstractItemView {
    background-color: #3c3f41;
    border: 1px solid #555555;
    selection-background-color: #4c5052;
}

CanvasToolsWidget QSlider::groove:horizontal {
    border: 1px solid #555555;
    height: 4px;
    background: #3c3f41;
    margin: 2px 0;
    border-radius: 2px;
}

CanvasToolsWidget QSlider::handle:horizontal {
    background: #555555;
    border: 1px solid #666666;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}

CanvasToolsWidget QSpinBox {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px 4px;
    color: #ffffff;
    min-height: 20px;
}

CanvasToolsWidget QSpinBox:hover {
    border: 1px solid #666666;
}

CanvasToolsWidget QSpinBox::up-button, 
CanvasToolsWidget QSpinBox::down-button {
    border: none;
    background: #3c3f41;
    width: 12px;
}

CanvasToolsWidget QSpinBox::up-button:hover, 
CanvasToolsWidget QSpinBox::down-button:hover {
    background: #4c5052;
}
"""

# 全局样式
GLOBAL_STYLE = """ 
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: "Segoe UI", Arial, sans-serif;
}

QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
    color: #ffffff;
}

QPushButton:hover {
    background-color: #4c5052;
    border: 1px solid #666666;
}

QPushButton:pressed {
    background-color: #2c2f31;
}

QLabel {
    color: #ffffff;
}

QComboBox {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px 4px;
    color: #ffffff;
}

QComboBox:hover {
    border: 1px solid #666666;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #3c3f41;
    border: 1px solid #555555;
    selection-background-color: #4c5052;
}
"""

# 对话框样式 - Custom Dialog 和 Left Panel Dialog 的基础样式
DIALOG_STYLE = """
/* Custom Dialog Title Bar */
#CustomDialogTitleBar {
    background-color: #3d3f4e;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border: none;
}

/* Custom Dialog Title Label */
#CustomDialogTitleLabel {
    color: #E1E1E1;
    font-size: 14px;
    font-weight: bold;
}

/* Custom Dialog Content Container */
#CustomDialogContentContainer {
    background-color: #2b2d30;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
    border: 1px solid #505254;
    border-top: none;
}

/* Left Panel Dialog - Left Panel */
#LeftPanelDialogLeftPanel {
    background-color: #3d3f4e;
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
    border: 1px solid #505254;
    border-right: none;
}

/* Left Panel Dialog - Left Content */
#LeftPanelDialogLeftContent {
    background-color: transparent;
}

/* Left Panel Dialog - Right Work Area */
#LeftPanelDialogRightWorkArea {
    background-color: #2b2d30;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
    border: 1px solid #505254;
    border-left: none;
}

/* Left Panel Dialog - Right Title Bar */
#LeftPanelDialogRightTitleBar {
    background-color: #3d3f4e;
    border-top-right-radius: 10px;
    border: none;
}

/* Left Panel Dialog - Right Title Label */
#LeftPanelDialogRightTitleLabel {
    color: #E1E1E1;
    font-size: 14px;
    font-weight: bold;
}

/* Left Panel Dialog - Settings Button */
#LeftPanelDialogSettingsButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: #888888;
    font-family: iconfont;
    font-size: 18px;
}
#LeftPanelDialogSettingsButton:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #E1E1E1;
}

/* Left Panel Dialog - Right Work Container */
#LeftPanelDialogRightWorkContainer {
    background-color: transparent;
}
"""

# Navigation Button Style (for dialog title bars)
DIALOG_NAV_BUTTON_STYLE = """
QPushButton {
    background-color: transparent;
    color: #888888;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton:hover:enabled {
    background-color: #4c4f52;
    color: #E1E1E1;
}
QPushButton:pressed:enabled {
    background-color: #3c3f42;
}
QPushButton:disabled {
    color: #444444;
}
"""

# Dialog Button Styles (for dialog action buttons)
def get_dialog_button_style(role="default"):
    """获取对话框按钮样式
    
    Args:
        role: 按钮角色 - 'accept', 'reject', 'danger', 'default'
    """
    if role == "accept":
        color = "#4CAF50"  # Green for accept/save
    elif role == "reject":
        color = "#555555"  # Gray for cancel
    elif role == "danger":
        color = "#F44336"  # Red for dangerous actions
    else:
        color = "#4c5052"  # Default color
    
    return f"""
QPushButton {{
    background-color: {color};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {_lighten_color(color)};
}}
QPushButton:pressed {{
    background-color: {_darken_color(color)};
}}
"""

def _lighten_color(color: str) -> str:
    """Lighten a hex color"""
    color = color.lstrip('#')
    if len(color) != 6:
        return color
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    r = min(255, r + 20)
    g = min(255, g + 20)
    b = min(255, b + 20)
    return f"#{r:02x}{g:02x}{b:02x}"

def _darken_color(color: str) -> str:
    """Darken a hex color"""
    color = color.lstrip('#')
    if len(color) != 6:
        return color
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    r = max(0, r - 20)
    g = max(0, g - 20)
    b = max(0, b - 20)
    return f"#{r:02x}{g:02x}{b:02x}"