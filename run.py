#!/usr/bin/env python3
"""Dev launcher. Run: python run.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gui import webview, window, api
webview.start(debug=True, http_server=True)
