import mock
import unittest

from bfg9000.environment import Environment
from bfg9000.tools.jvm import JvmBuilder
from bfg9000.versioning import Version

env = Environment(None, None, None, None, None, {}, (False, False), None)


def mock_which(*args, **kwargs):
    return ['command']


class TestJvmBuilder(unittest.TestCase):
    def test_properties(self):
        def mock_execute(*args, **kwargs):
            return 'version'

        with mock.patch('bfg9000.shell.which', mock_which), \
             mock.patch('bfg9000.shell.execute', mock_execute):  # noqa
            jvm = JvmBuilder(env, 'java', 'JAVAC', ['javac'], 'JAVAFLAGS', [],
                             'version')

        self.assertEqual(jvm.flavor, 'jvm')
        self.assertEqual(jvm.compiler.flavor, 'jvm')
        self.assertEqual(jvm.linker('executable').flavor, 'jar')
        self.assertEqual(jvm.linker('shared_library').flavor, 'jar')

        self.assertEqual(jvm.family, 'jvm')
        self.assertEqual(jvm.can_dual_link, False)

        self.assertEqual(jvm.compiler.deps_flavor, None)
        self.assertEqual(jvm.compiler.needs_libs, True)
        self.assertEqual(jvm.compiler.accepts_pch, False)

        self.assertRaises(AttributeError, lambda: jvm.pch_compiler)
        self.assertRaises(KeyError, lambda: jvm.linker('unknown'))
        self.assertRaises(ValueError, lambda: jvm.linker('static_library'))

    def test_oracle(self):
        def mock_execute(*args, **kwargs):
            return ('java version "1.7.0_55"\n' +
                    'Java(TM) SE Runtime Environment (build 1.7.0_55-b13)')

        version = 'javac 1.7.0_55'
        with mock.patch('bfg9000.shell.which', mock_which), \
             mock.patch('bfg9000.shell.execute', mock_execute):  # noqa
            jvm = JvmBuilder(env, 'java', 'JAVAC', ['javac'], 'JAVAFLAGS', [],
                             version)

        self.assertEqual(jvm.brand, 'oracle')
        self.assertEqual(jvm.compiler.brand, 'oracle')
        self.assertEqual(jvm.linker('executable').brand, 'oracle')
        self.assertEqual(jvm.linker('shared_library').brand, 'oracle')

        self.assertEqual(jvm.version, Version('1.7.0'))
        self.assertEqual(jvm.compiler.version, Version('1.7.0'))
        self.assertEqual(jvm.linker('executable').version, Version('1.7.0'))
        self.assertEqual(jvm.linker('shared_library').version,
                         Version('1.7.0'))

    def test_openjdk(self):
        def mock_execute(*args, **kwargs):
            return ('openjdk version "1.8.0_151"\n' +
                    'OpenJDK Runtime Environment (build ' +
                    '1.8.0_151-8u151-b12-0ubuntu0.16.04.2-b12)')

        version = 'javac 1.8.0_151'
        with mock.patch('bfg9000.shell.which', mock_which), \
             mock.patch('bfg9000.shell.execute', mock_execute):  # noqa
            jvm = JvmBuilder(env, 'java', 'JAVAC', ['javac'], 'JAVAFLAGS', [],
                             version)

        self.assertEqual(jvm.brand, 'openjdk')
        self.assertEqual(jvm.compiler.brand, 'openjdk')
        self.assertEqual(jvm.linker('executable').brand, 'openjdk')
        self.assertEqual(jvm.linker('shared_library').brand, 'openjdk')

        self.assertEqual(jvm.version, Version('1.8.0'))
        self.assertEqual(jvm.compiler.version, Version('1.8.0'))
        self.assertEqual(jvm.linker('executable').version, Version('1.8.0'))
        self.assertEqual(jvm.linker('shared_library').version,
                         Version('1.8.0'))

    def test_scala(self):
        version = ('Scala code runner version 2.11.6 -- ' +
                   'Copyright 2002-2013, LAMP/EPFL')
        with mock.patch('bfg9000.shell.which', mock_which):  # noqa
            jvm = JvmBuilder(env, 'scala', 'SCALAC', ['scalac'], 'SCALAFLAGS',
                             [], version)

        self.assertEqual(jvm.brand, 'epfl')
        self.assertEqual(jvm.compiler.brand, 'epfl')
        self.assertEqual(jvm.linker('executable').brand, 'epfl')
        self.assertEqual(jvm.linker('shared_library').brand, 'epfl')

        self.assertEqual(jvm.version, Version('2.11.6'))
        self.assertEqual(jvm.compiler.version, Version('2.11.6'))
        self.assertEqual(jvm.linker('executable').version, Version('2.11.6'))
        self.assertEqual(jvm.linker('shared_library').version,
                         Version('2.11.6'))

    def test_unknown_brand(self):
        def mock_execute(*args, **kwargs):
            return 'unknown'

        with mock.patch('bfg9000.shell.which', mock_which), \
             mock.patch('bfg9000.shell.execute', mock_execute):  # noqa
            jvm = JvmBuilder(env, 'java', 'JAVAC', ['javac'], 'JAVAFLAGS', [],
                             'unknown')

        self.assertEqual(jvm.brand, 'unknown')
        self.assertEqual(jvm.compiler.brand, 'unknown')
        self.assertEqual(jvm.linker('executable').brand, 'unknown')
        self.assertEqual(jvm.linker('shared_library').brand, 'unknown')

        self.assertEqual(jvm.version, None)
        self.assertEqual(jvm.compiler.version, None)
        self.assertEqual(jvm.linker('executable').version, None)
        self.assertEqual(jvm.linker('shared_library').version, None)

    def test_broken_brand(self):
        def mock_execute(*args, **kwargs):
            raise OSError()

        with mock.patch('bfg9000.shell.which', mock_which), \
             mock.patch('bfg9000.shell.execute', mock_execute):  # noqa
            jvm = JvmBuilder(env, 'java', 'JAVAC', ['javac'], 'JAVAFLAGS', [],
                             'version')

        self.assertEqual(jvm.brand, 'unknown')
        self.assertEqual(jvm.compiler.brand, 'unknown')
        self.assertEqual(jvm.linker('executable').brand, 'unknown')
        self.assertEqual(jvm.linker('shared_library').brand, 'unknown')

        self.assertEqual(jvm.version, None)
        self.assertEqual(jvm.compiler.version, None)
        self.assertEqual(jvm.linker('executable').version, None)
        self.assertEqual(jvm.linker('shared_library').version, None)