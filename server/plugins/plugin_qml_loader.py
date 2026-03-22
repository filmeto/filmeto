"""
Plugin QML Loader

Handles loading QML configuration widgets for plugins.
Provides a bridge between Python and QML for plugin configuration UI.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import QUrl, QObject, QSize, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtQuick import QQuickWindow

logger = logging.getLogger(__name__)


class PluginQMLLoader:
    """
    QML configuration UI loader for plugins.

    This class handles:
    - Checking if a plugin has QML UI defined
    - Loading QML configuration widgets
    - Setting up the data model bridge between Python and QML
    """

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize the QML loader.

        Args:
            plugins_dir: Directory containing plugins (default: server/plugins/)
        """
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir)
        else:
            self.plugins_dir = Path(__file__).parent

        # Cache for loaded QML component status
        self._qml_cache: Dict[str, bool] = {}

    def is_qml_available(self, plugin_info: Dict[str, Any], plugin_dir: Path) -> bool:
        """
        Check if the plugin has QML UI available.

        Args:
            plugin_info: Plugin info dictionary (from plugin.yml)
            plugin_dir: Path to the plugin directory

        Returns:
            True if QML UI is available, False otherwise
        """
        cache_key = str(plugin_dir)
        if cache_key in self._qml_cache:
            return self._qml_cache[cache_key]

        # Check if plugin.yml has ui section
        ui_config = plugin_info.get("ui", {})
        if not ui_config:
            self._qml_cache[cache_key] = False
            return False

        # Check for use_default flag (uses default PluginConfigWidget)
        use_default = ui_config.get("use_default", False)
        if use_default:
            self._qml_cache[cache_key] = True
            return True

        # Check for config_widget path
        config_widget = ui_config.get("config_widget")
        if not config_widget:
            self._qml_cache[cache_key] = False
            return False

        # Check if the QML file exists
        qml_path = plugin_dir / config_widget
        if not qml_path.exists():
            logger.warning(f"QML config widget not found: {qml_path}")
            self._qml_cache[cache_key] = False
            return False

        self._qml_cache[cache_key] = True
        return True

    def should_use_default_qml(self, plugin_info: Dict[str, Any]) -> bool:
        """
        Check if plugin should use default QML widget.

        Args:
            plugin_info: Plugin info dictionary

        Returns:
            True if should use default QML widget
        """
        ui_config = plugin_info.get("ui", {})
        return ui_config.get("use_default", False)

    def get_qml_file_path(
        self,
        plugin_info: Dict[str, Any],
        plugin_dir: Path
    ) -> Optional[Path]:
        """
        Get the path to the QML config widget file.

        Args:
            plugin_info: Plugin info dictionary
            plugin_dir: Path to the plugin directory

        Returns:
            Path to QML file or None if not found
        """
        ui_config = plugin_info.get("ui", {})
        config_widget = ui_config.get("config_widget")

        if not config_widget:
            return None

        qml_path = plugin_dir / config_widget
        if qml_path.exists():
            return qml_path

        return None

    def create_qml_config_widget(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Dict[str, Any],
        server_config: Optional[Dict[str, Any]] = None,
        plugin_dir: Optional[Path] = None,
        parent: Optional[QWidget] = None
    ) -> Optional[QWidget]:
        """
        Create a QML configuration widget for a plugin.

        Args:
            plugin_info: Plugin info dictionary
            config_schema: Configuration schema
            server_config: Existing server configuration (for editing)
            plugin_dir: Path to the plugin directory
            parent: Parent widget

        Returns:
            QWidget containing the QML widget, or None if failed
        """
        try:
            # Check if should use default QML widget
            if self.should_use_default_qml(plugin_info):
                return self.create_default_qml_widget(
                    plugin_info,
                    config_schema,
                    server_config,
                    parent
                )

            # Get QML file path
            if plugin_dir:
                qml_path = self.get_qml_file_path(plugin_info, plugin_dir)
            else:
                # Try to find plugin directory from name
                plugin_name = plugin_info.get("name", "")
                plugin_dir = self._find_plugin_dir(plugin_name)
                if not plugin_dir:
                    logger.error(f"Plugin directory not found for: {plugin_name}")
                    return None
                qml_path = self.get_qml_file_path(plugin_info, plugin_dir)

            if not qml_path:
                logger.error("QML file path not found")
                return None

            # Create the QML widget
            return self._create_qml_widget(
                qml_path,
                plugin_info,
                config_schema,
                server_config,
                parent
            )

        except Exception as e:
            logger.error(f"Failed to create QML config widget: {e}", exc_info=True)
            return None

    def _create_qml_widget(
        self,
        qml_path: Path,
        plugin_info: Dict[str, Any],
        config_schema: Dict[str, Any],
        server_config: Optional[Dict[str, Any]],
        parent: Optional[QWidget]
    ) -> Optional[QWidget]:
        """
        Create the actual QML widget with model binding.

        Args:
            qml_path: Path to QML file
            plugin_info: Plugin info dictionary
            config_schema: Configuration schema
            server_config: Existing server configuration
            parent: Parent widget

        Returns:
            QWidget containing the QML widget
        """
        # Create container widget
        container = QWidget(parent)
        container.setObjectName("PluginConfigContainer")

        # Set size policy to expand
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create QQuickWidget
        qml_widget = QQuickWidget()
        qml_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

        # Important: Set correct focus policy to avoid blocking parent widgets
        qml_widget.setFocusPolicy(Qt.StrongFocus)

        # Ensure proper event handling
        qml_widget.setAttribute(Qt.WA_AcceptTouchEvents, False)
        qml_widget.setAttribute(Qt.WA_InputMethodEnabled, False)

        # Set size policy on QML widget
        qml_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set minimum size to ensure the widget is visible
        qml_widget.setMinimumSize(400, 300)

        # Create and set the config model
        config_model = self._create_config_model(
            plugin_info,
            config_schema,
            server_config
        )

        if config_model:
            # Set the model as a context property
            # The model will be accessible in QML as "_pluginConfigModel"
            root_context = qml_widget.rootContext()
            root_context.setContextProperty("_pluginConfigModel", config_model)
            root_context.setContextProperty("configModel", config_model)

            # Store reference to prevent garbage collection
            container._config_model = config_model

        # Set up import paths for QML
        self._setup_qml_import_paths(qml_widget, qml_path)

        # Load the QML file
        qml_url = QUrl.fromLocalFile(str(qml_path))
        qml_widget.setSource(qml_url)

        # Check for errors
        if qml_widget.status() == QQuickWidget.Error:
            errors = qml_widget.errors()
            for error in errors:
                logger.error(f"QML Error: {error.toString()}")
            return None

        layout.addWidget(qml_widget)

        # Store reference to QML widget for later access
        container._qml_widget = qml_widget

        # Add cleanup method to container
        def cleanup():
            """Clean up QML widget resources"""
            try:
                if hasattr(container, '_qml_widget') and container._qml_widget:
                    qml = container._qml_widget
                    # Clear focus first
                    qml.clearFocus()
                    # Release any active focus on the QML window
                    try:
                        qw = qml.quickWindow()
                        if qw:
                            # Release mouse grab
                            qw.releaseResources()
                            # Clear active focus
                            if qw.activeFocusItem():
                                qw.activeFocusItem().setFocus(False)
                    except RuntimeError:
                        # Window might already be destroyed
                        pass
                    # Set source to empty to unload QML
                    try:
                        qml.setSource(QUrl())
                    except RuntimeError:
                        pass
            except Exception as e:
                logger.debug(f"Error during QML cleanup: {e}")

        container.cleanup = cleanup

        # Add methods to container for external access
        def get_config():
            if hasattr(container, '_config_model'):
                return container._config_model.get_config_dict()
            return {}

        def validate():
            if hasattr(container, '_config_model'):
                return container._config_model.validate()
            return True

        def validate_config():
            """Alias for validate() for compatibility with Python widgets"""
            if hasattr(container, '_config_model'):
                return container._config_model.validate()
            return True

        container.get_config = get_config
        container.validate = validate
        container.validate_config = validate_config

        # Add config_changed signal for compatibility with Python widgets
        if hasattr(container._config_model, 'config_changed'):
            container.config_changed = container._config_model.config_changed

        return container

    def _create_config_model(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Dict[str, Any],
        server_config: Optional[Dict[str, Any]]
    ) -> Optional[QObject]:
        """
        Create the appropriate config model for the plugin.

        Args:
            plugin_info: Plugin info dictionary
            config_schema: Configuration schema
            server_config: Existing server configuration

        Returns:
            Config model QObject
        """
        plugin_name = plugin_info.get("name", "").lower()

        # Check for specialized model
        if "bailian" in plugin_name:
            try:
                from server.plugins.plugin_config_qml_model import BailianConfigQMLModel
                return BailianConfigQMLModel(
                    plugin_info,
                    config_schema,
                    server_config
                )
            except Exception as e:
                logger.warning(f"Failed to create BailianConfigQMLModel: {e}")

        # Default model
        from server.plugins.plugin_config_qml_model import PluginConfigQMLModel
        return PluginConfigQMLModel(
            plugin_info,
            config_schema,
            server_config
        )

    def _setup_qml_import_paths(self, qml_widget: QQuickWidget, qml_path: Path):
        """
        Set up QML import paths.

        Args:
            qml_widget: The QQuickWidget
            qml_path: Path to the main QML file
        """
        engine = qml_widget.engine()

        # Add the app QML directory for shared components
        app_dir = Path(__file__).parent.parent.parent / "app" / "ui" / "qml"
        if app_dir.exists():
            engine.addImportPath(str(app_dir))

        # Add plugin directory for local imports
        plugin_dir = qml_path.parent.parent  # Go up from qml/config/ to plugin root
        if plugin_dir.exists():
            engine.addImportPath(str(plugin_dir))

        # Add the qml directory itself
        qml_dir = qml_path.parent
        if qml_dir.exists():
            engine.addImportPath(str(qml_dir))

    def _find_plugin_dir(self, plugin_name: str) -> Optional[Path]:
        """
        Find the plugin directory by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Path to plugin directory or None
        """
        import yaml

        if not self.plugins_dir.exists():
            return None

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith('_'):
                continue

            config_file = plugin_dir / "plugin.yml"
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    if config.get('name', '').lower() == plugin_name.lower():
                        return plugin_dir
                except Exception:
                    continue

        return None

    def create_default_qml_widget(
        self,
        plugin_info: Dict[str, Any],
        config_schema: Dict[str, Any],
        server_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ) -> Optional[QWidget]:
        """
        Create a default QML widget using the built-in PluginConfigWidget.

        This is used as a fallback when a plugin has config_schema but no
        custom QML UI defined.

        Args:
            plugin_info: Plugin info dictionary
            config_schema: Configuration schema
            server_config: Existing server configuration
            parent: Parent widget

        Returns:
            QWidget containing the default QML widget
        """
        try:
            # Get path to default PluginConfigWidget.qml
            default_qml = (
                Path(__file__).parent.parent.parent /
                "app" / "ui" / "qml" / "plugin" /
                "PluginConfigWidget.qml"
            )

            if not default_qml.exists():
                logger.error(f"Default QML widget not found: {default_qml}")
                return None

            return self._create_qml_widget(
                default_qml,
                plugin_info,
                config_schema,
                server_config,
                parent
            )

        except Exception as e:
            logger.error(f"Failed to create default QML widget: {e}", exc_info=True)
            return None