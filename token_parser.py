# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Xing Li
import re
from html.parser import HTMLParser


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active = not dict(attrs).get('src')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def extract_token(html):
    parser = Scripts()
    parser.feed(html)
    # Preserve quoted strings while discarding JS line and block comments.
    pattern = r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|//[^\r\n]*|/\*[\s\S]*?\*/'''
    source = re.sub(pattern, lambda m: ' ' if m[0].startswith(('//', '/*')) else m[0], '\n'.join(parser.parts))
    found = re.findall(r'''\b(?:var|let|const)\s+layerToken\s*=\s*(["'])([A-Za-z0-9_.~+/-]{16,2048}={0,2})\1''', source)
    values = {match[1] for match in found}
    if len(values) != 1:
        raise ValueError('主頁未提供唯一有效 layerToken；可能需要瀏覽器驗證或網站格式已改變。')
    return values.pop()
