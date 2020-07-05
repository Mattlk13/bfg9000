import importlib
from collections import namedtuple
from unittest import mock

from .. import *

from bfg9000.environment import Environment
from bfg9000.safe_str import jbos, shell_literal
from bfg9000.shell import shell_list
from bfg9000.tools import _tools, setenv

MockPlatform = namedtuple('MockPlatform', ['family'])


def mock_getvar(self, key, default=None):
    return default


class TestSetEnv(TestCase):
    def setUp(self):
        self.env = make_env(platform='winnt')

    @classmethod
    def tearDownClass(cls):
        cls.reload_import()

    @classmethod
    def reload_import(cls):
        _tools.pop('setenv', None)
        importlib.reload(setenv)

    def _init_setenv(self):
        with mock.patch('bfg9000.platforms.host.platform_info',
                        return_value=MockPlatform('windows')), \
             mock.patch('bfg9000.shell.which', return_value=['command']), \
             mock.patch.object(Environment, 'getvar', mock_getvar):  # noqa
            self.reload_import()
            self.setenv = setenv.SetEnv(self.env)
            return setenv

    def test_env(self):
        setenv = self._init_setenv()
        with mock.patch('bfg9000.shell.which', return_value=['command']):
            self.assertIsInstance(self.env.tool('setenv'), setenv.SetEnv)

    def test_env_nonexist(self):
        with mock.patch('bfg9000.platforms.host.platform_info',
                        return_value=MockPlatform('posix')):
            self.reload_import()
        with self.assertRaises(ValueError):
            self.env.tool('setenv')

    def test_basic(self):
        self._init_setenv()
        self.assertEqual(self.setenv({}, ['echo', 'hi']), ['echo', 'hi'])
        self.assertEqual(self.setenv({}, 'echo hi'), shell_list([
            shell_literal('echo hi')
        ]))

    def test_env_vars(self):
        self._init_setenv()
        env = {'FOO': 'foo'}
        self.assertEqual(self.setenv(env, ['echo', 'hi']), [
            self.setenv, jbos('FOO', shell_literal('='), 'foo'), '--', 'echo',
            'hi'
        ])
        self.assertEqual(self.setenv(env, 'echo hi'), shell_list([
            self.setenv, jbos('FOO', shell_literal('='), 'foo'), '--',
            shell_literal('echo hi')
        ]))

    def test_non_windows(self):
        with mock.patch('bfg9000.platforms.host.platform_info',
                        return_value=MockPlatform('posix')):
            setenv = self.reload_import()
        with self.assertRaises(AttributeError):
            setenv.SetEnv
