"""Small shims so the same code runs on QGIS 3 (Qt5) and QGIS 4 (Qt6).

Rules of thumb for the rest of the plugin:
  * import Qt only through ``qgis.PyQt`` (never ``PyQt5`` / ``PyQt6``)
  * use fully scoped enums, e.g. ``Qt.DockWidgetArea.RightDockWidgetArea``
  * call ``exec()``, not ``exec_()``
  * ``from qgis.PyQt import sip`` instead of a bare ``import sip``
Anything that cannot be written in a way that works on both goes in this module.
"""
try:  # Qt6: QAction lives in QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:  # Qt5: QAction lives in QtWidgets
    from qgis.PyQt.QtWidgets import QAction

__all__ = ["QAction"]
