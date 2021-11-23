import os.path
import re

from . import *


class TestSafeStr(IntegrationTest):
    def __init__(self, *args, **kwargs):
        super().__init__('safe_str', *args, **kwargs)

    def test_foo(self):
        f = re.escape(os.path.normpath(os.path.join(
            test_data_dir, 'safe_str', 'foo.txt'
        )))
        if env.host_platform.family == 'windows':
            f = '"?' + f + '"?'
        self.assertRegex(self.build('foo'), r'(?m)^\s*{}$'.format(f))

    def test_bar(self):
        f = re.escape(os.path.normpath(os.path.join(
            test_data_dir, 'safe_str', 'bar.txt'
        )))
        if env.host_platform.family == 'windows':
            f = '"?' + f + '"?'
        self.assertRegex(self.build('bar'), r'(?m)^\s*{}$'.format(f))
