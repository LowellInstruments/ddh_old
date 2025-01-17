RPi --> QtWebKit
laptop --> QtWebEngine

install QtWebEngine
    pip install PyQtWebEngine

install QtWebKit
    sudo apt-get install -y python3-pyqt5.qtwebkit

# to run on laptop
sed -i 's/from PyQt5 import QtWebKitWidgets/from PyQt5 import QtWebEngineWidgets/g' designer_main.py
sed -i 's/self.webView = QtWebKitWidgets.QWebView(self.tab_trawls)/self.webView = QtWebEngineWidgets.QWebView(self.tab_trawls)/g' designer_main.py

