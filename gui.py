#!/usr/bin/env python3
"""Launch the RFP Generator desktop app."""
import webview
from app import API

api = API()

window = webview.create_window(
    title='Central Lab RFP Generator',
    url='ui/index.html',
    js_api=api,
    width=800,
    height=950,
    resizable=True,
    text_select=True,
    easy_drag=False,
)

if __name__ == '__main__':
    webview.start(debug=True, http_server=True)
