from unittest import mock

from .. import *

from bfg9000 import file_types, options as opts
from bfg9000.exceptions import PackageResolutionError
from bfg9000.iterutils import merge_dicts
from bfg9000.languages import Languages
from bfg9000.packages import Framework
from bfg9000.path import Path, Root
from bfg9000.tools.msvc import MsvcBuilder
from bfg9000.versioning import Version

known_langs = Languages()
with known_langs.make('c') as x:
    x.vars(compiler='CC', flags='CFLAGS')
with known_langs.make('c++') as x:
    x.vars(compiler='CXX', flags='CXXFLAGS')


def mock_which(*args, **kwargs):
    return ['command']


class TestMsvcBuilder(CrossPlatformTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(clear_variables=True, *args, **kwargs)

    def test_properties(self):
        with mock.patch('bfg9000.shell.which', mock_which):
            cc = MsvcBuilder(self.env, known_langs['c++'], ['cl'], 'version')

        self.assertEqual(cc.flavor, 'msvc')
        self.assertEqual(cc.compiler.flavor, 'msvc')
        self.assertEqual(cc.pch_compiler.flavor, 'msvc')
        self.assertEqual(cc.linker('executable').flavor, 'msvc')
        self.assertEqual(cc.linker('shared_library').flavor, 'msvc')
        self.assertEqual(cc.linker('static_library').flavor, 'msvc')

        self.assertEqual(cc.family, 'native')
        self.assertEqual(cc.auto_link, True)
        self.assertEqual(cc.can_dual_link, False)

        self.assertEqual(cc.compiler.num_outputs, 'all')
        self.assertEqual(cc.pch_compiler.num_outputs, 2)
        self.assertEqual(cc.linker('executable').num_outputs, 'all')
        self.assertEqual(cc.linker('shared_library').num_outputs, 2)

        self.assertEqual(cc.compiler.deps_flavor, 'msvc')
        self.assertEqual(cc.pch_compiler.deps_flavor, 'msvc')

        self.assertEqual(cc.compiler.needs_libs, False)
        self.assertEqual(cc.pch_compiler.needs_libs, False)

        self.assertEqual(cc.compiler.accepts_pch, True)
        self.assertEqual(cc.pch_compiler.accepts_pch, False)

        self.assertRaises(KeyError, lambda: cc.linker('unknown'))

    def test_msvc(self):
        version = ('Microsoft (R) C/C++ Optimizing Compiler Version ' +
                   '19.12.25831 for x86')

        with mock.patch('bfg9000.shell.which', mock_which):
            cc = MsvcBuilder(self.env, known_langs['c++'], ['cl'], version)

        self.assertEqual(cc.brand, 'msvc')
        self.assertEqual(cc.compiler.brand, 'msvc')
        self.assertEqual(cc.pch_compiler.brand, 'msvc')
        self.assertEqual(cc.linker('executable').brand, 'msvc')
        self.assertEqual(cc.linker('shared_library').brand, 'msvc')

        self.assertEqual(cc.version, Version('19.12.25831'))
        self.assertEqual(cc.compiler.version, Version('19.12.25831'))
        self.assertEqual(cc.pch_compiler.version, Version('19.12.25831'))
        self.assertEqual(cc.linker('executable').version,
                         Version('19.12.25831'))
        self.assertEqual(cc.linker('shared_library').version,
                         Version('19.12.25831'))

    def test_unknown_brand(self):
        version = 'unknown'

        with mock.patch('bfg9000.shell.which', mock_which):
            cc = MsvcBuilder(self.env, known_langs['c++'], ['c++'], version)

        self.assertEqual(cc.brand, 'unknown')
        self.assertEqual(cc.compiler.brand, 'unknown')
        self.assertEqual(cc.pch_compiler.brand, 'unknown')
        self.assertEqual(cc.linker('executable').brand, 'unknown')
        self.assertEqual(cc.linker('shared_library').brand, 'unknown')

        self.assertEqual(cc.version, None)
        self.assertEqual(cc.compiler.version, None)
        self.assertEqual(cc.pch_compiler.version, None)
        self.assertEqual(cc.linker('executable').version, None)
        self.assertEqual(cc.linker('shared_library').version, None)


class TestMsvcCompiler(CrossPlatformTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(clear_variables=True, *args, **kwargs)

    def setUp(self):
        with mock.patch('bfg9000.shell.which', mock_which):
            self.compiler = MsvcBuilder(self.env, known_langs['c++'], ['cl'],
                                        'version').compiler

    def test_call(self):
        extra = self.compiler._always_flags
        self.assertEqual(self.compiler('in', 'out'),
                         [self.compiler] + extra + ['/c', 'in', '/Foout'])
        self.assertEqual(
            self.compiler('in', 'out', flags=['flags']),
            [self.compiler] + extra + ['flags', '/c', 'in', '/Foout']
        )

        self.assertEqual(
            self.compiler('in', 'out', 'out.d'),
            [self.compiler] + extra + ['/showIncludes', '/c', 'in', '/Foout']
        )
        self.assertEqual(
            self.compiler('in', 'out', 'out.d', ['flags']),
            [self.compiler] + extra + ['flags', '/showIncludes', '/c', 'in',
                                       '/Foout']
        )

    def test_default_name(self):
        src = file_types.SourceFile(Path('file.cpp', Root.srcdir), 'c++')
        self.assertEqual(self.compiler.default_name(src, None), 'file')

    def test_output_file(self):
        fmt = self.env.target_platform.object_format
        self.assertEqual(self.compiler.output_file('file', None),
                         file_types.ObjectFile(Path('file.obj'), fmt, 'c++'))

    def test_flags_empty(self):
        self.assertEqual(self.compiler.flags(opts.option_list()), ['/MD'])

    def test_flags_include_dir(self):
        p = self.Path('/path/to/include')
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.include_dir(file_types.HeaderDirectory(p))
        )), ['/I' + p, '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.include_dir(file_types.HeaderDirectory(p))
        ), mode='pkg-config'), ['-I' + p])

    def test_flags_define(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.define('NAME')
        )), ['/DNAME', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.define('NAME')
        ), mode='pkg-config'), ['-DNAME'])

        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.define('NAME', 'value')
        )), ['/DNAME=value', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.define('NAME', 'value')
        ), mode='pkg-config'), ['-DNAME=value'])

    def test_flags_std(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.std('c++14')
        )), ['/std:c++14', '/MD'])

    def test_flags_static(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.static()
        )), ['/MT'])

        self.assertEqual(self.compiler.flags(
            opts.option_list(),
            opts.option_list(opts.static()),
        ), ['/MT'])

    def test_flags_debug(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.debug()
        )), ['/Zi', '/MDd'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.debug(), opts.static()
        )), ['/Zi', '/MTd'])

        self.assertEqual(self.compiler.flags(
            opts.option_list(),
            opts.option_list(opts.debug()),
        ), ['/MDd'])
        self.assertEqual(self.compiler.flags(
            opts.option_list(opts.static()),
            opts.option_list(opts.debug()),
        ), ['/MTd'])

    def test_flags_warning(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.warning('disable')
        )), ['/w', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.warning('all')
        )), ['/W3', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.warning('extra')
        )), ['/W4', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.warning('error')
        )), ['/WX', '/MD'])

        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.warning('all', 'extra', 'error')
        )), ['/W3', '/W4', '/WX', '/MD'])

        with self.assertRaises(ValueError):
            self.compiler.flags(opts.option_list(opts.warning('unknown')))

    def test_flags_optimize(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.optimize('disable')
        )), ['/Od', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.optimize('size')
        )), ['/O1', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.optimize('speed')
        )), ['/O2', '/MD'])
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.optimize('linktime')
        )), ['/GL', '/MD'])

        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.optimize('speed', 'linktime')
        )), ['/O2', '/GL', '/MD'])

    def test_flags_include_pch(self):
        p = self.Path('/path/to/header.hpp')
        self.assertEqual(self.compiler.flags(opts.option_list(opts.pch(
            file_types.MsvcPrecompiledHeader(p, p, 'header', 'native', 'c++')
        ))), ['/Yuheader', '/MD'])

    def test_flags_sanitize(self):
        self.assertEqual(self.compiler.flags(opts.option_list(
            opts.sanitize()
        )), ['/RTC1', '/MD'])

    def test_flags_string(self):
        self.assertEqual(self.compiler.flags(opts.option_list('-v')),
                         ['-v', '/MD'])

    def test_flags_invalid(self):
        with self.assertRaises(TypeError):
            self.compiler.flags(opts.option_list(123))

    def test_parse_flags(self):
        default = {
            'debug': None,
            'defines': [],
            'extra': [],
            'includes': [],
            'nologo': None,
            'pch': {'create': None, 'use': None},
            'runtime': None,
            'warnings': {'as_error': None, 'level': None}
        }

        def assertFlags(flags, extra={}):
            self.assertEqual(self.compiler.parse_flags(flags),
                             merge_dicts(default, extra))

        assertFlags([])
        assertFlags(['/un', 'known'], {'extra': ['/un', 'known']})
        assertFlags(['/nologo'], {'nologo': True})
        assertFlags(['/Dfoo'], {'defines': ['foo']})
        assertFlags(['/Idir'], {'includes': ['dir']})

        assertFlags(['/Z7'], {'debug': 'old'})
        assertFlags(['/Zi'], {'debug': 'pdb'})
        assertFlags(['/ZI'], {'debug': 'edit'})

        assertFlags(['/W0'], {'warnings': {'level': '0'}})
        assertFlags(['/Wall'], {'warnings': {'level': 'all'}})
        assertFlags(['/WX'], {'warnings': {'as_error': True}})
        assertFlags(['/WX-'], {'warnings': {'as_error': False}})
        assertFlags(['/w'], {'warnings': {'level': '0'}})

        assertFlags(['/Yufoo'], {'pch': {'use': 'foo'}})
        assertFlags(['/Ycfoo'], {'pch': {'create': 'foo'}})


class TestMsvcPchCompiler(TestMsvcCompiler):
    def setUp(self):
        with mock.patch('bfg9000.shell.which', mock_which):
            self.compiler = MsvcBuilder(self.env, known_langs['c++'], ['cl'],
                                        'version').pch_compiler

    def test_call(self):
        extra = self.compiler._always_flags
        self.assertEqual(self.compiler('in', ['out_pch', 'out']),
                         [self.compiler] + extra + ['/c', 'in', '/Foout',
                                                    '/Fpout_pch'])
        self.assertEqual(
            self.compiler('in', ['out_pch', 'out'], flags=['flags']),
            [self.compiler] + extra + ['flags', '/c', 'in', '/Foout',
                                       '/Fpout_pch']
        )

        self.assertEqual(
            self.compiler('in', ['out_pch', 'out'], 'out.d'),
            [self.compiler] + extra + ['/showIncludes', '/c', 'in', '/Foout',
                                       '/Fpout_pch']
        )
        self.assertEqual(
            self.compiler('in', ['out_pch', 'out'], 'out.d', ['flags']),
            [self.compiler] + extra + ['flags', '/showIncludes', '/c', 'in',
                                       '/Foout', '/Fpout_pch']
        )

    def test_default_name(self):
        hdr = file_types.HeaderFile(Path('file.hpp', Root.srcdir), 'c++')
        self.assertEqual(self.compiler.default_name(hdr, None), 'file.hpp')

    def test_output_file(self):
        fmt = self.env.target_platform.object_format
        out = file_types.MsvcPrecompiledHeader(
            Path('hdr.pch'), Path('src.obj'), 'hdr.h', fmt, 'c++'
        )
        self.assertEqual(self.compiler.output_file('hdr.h', AttrDict(
            pch_source=file_types.SourceFile(Path('src.c'), 'c')
        )), [out, out.object_file])


class TestMsvcLinker(CrossPlatformTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(clear_variables=True, *args, **kwargs)

    def _get_linker(self, lang):
        version = ('Microsoft (R) C/C++ Optimizing Compiler Version ' +
                   '19.12.25831 for x86')
        with mock.patch('bfg9000.shell.which', mock_which):  # noqa
            return MsvcBuilder(self.env, known_langs[lang], ['cl'],
                               version).linker('executable')

    def setUp(self):
        self.linker = self._get_linker('c++')

    def test_call(self):
        extra = self.linker._always_flags
        self.assertEqual(self.linker(['in'], 'out'),
                         [self.linker] + extra + ['in', '/OUT:out'])
        self.assertEqual(self.linker(['in'], 'out', flags=['flags']),
                         [self.linker] + extra + ['flags', 'in', '/OUT:out'])

        self.assertEqual(self.linker(['in'], 'out', ['lib']),
                         [self.linker] + extra + ['in', 'lib', '/OUT:out'])
        self.assertEqual(
            self.linker(['in'], 'out', ['lib'], ['flags']),
            [self.linker] + extra + ['flags', 'in', 'lib', '/OUT:out']
        )

    def test_output_file(self):
        fmt = self.env.target_platform.object_format
        ext = self.env.target_platform.executable_ext
        self.assertEqual(self.linker.output_file('prog', None),
                         file_types.Executable(Path('prog' + ext), fmt, 'c++'))

    def test_can_link(self):
        fmt = self.env.target_platform.object_format
        self.assertTrue(self.linker.can_link(fmt, ['c', 'c++']))
        self.assertTrue(self.linker.can_link(fmt, ['goofy']))
        self.assertFalse(self.linker.can_link('goofy', ['c']))

        c_linker = self._get_linker('c')
        self.assertFalse(c_linker.can_link(fmt, ['c++']))

    def test_flags_empty(self):
        self.assertEqual(self.linker.flags(opts.option_list()), [])

    def test_flags_lib_dir(self):
        libdir = self.Path('/path/to/lib')
        lib = self.Path('/path/to/lib/foo.so')

        # Lib dir
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.lib_dir(file_types.Directory(libdir))
        )), ['/LIBPATH:' + libdir])
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.lib_dir(file_types.Directory(libdir))
        ), mode='pkg-config'), ['-L' + libdir])

        # Shared library
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.lib(file_types.SharedLibrary(lib, 'native'))
        )), [])

        # Static library
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.lib(file_types.StaticLibrary(lib, 'native'))
        )), [])

        # Mixed
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.lib_dir(file_types.Directory(libdir)),
            opts.lib(file_types.SharedLibrary(lib, 'native'))
        )), ['/LIBPATH:' + libdir])

    def test_flags_module_def(self):
        path = self.Path('/path/to/module.def')
        self.assertEqual(
            self.linker.flags(opts.option_list(
                opts.module_def(file_types.ModuleDefFile(path))
            )), ['/DEF:' + path]
        )

    def test_flags_static(self):
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.static()
        )), [])

    def test_flags_debug(self):
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.debug()
        )), ['/DEBUG'])

    def test_flags_optimize(self):
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.optimize('disable')
        )), [])
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.optimize('size')
        )), [])
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.optimize('speed')
        )), [])
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.optimize('linktime')
        )), ['/LTCG'])

        self.assertEqual(self.linker.flags(opts.option_list(
            opts.optimize('speed', 'linktime')
        )), ['/LTCG'])

    def test_flags_entry_point(self):
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.entry_point('symbol')
        )), ['/ENTRY:symbol'])

    def test_flags_gui(self):
        self.assertEqual(self.linker.flags(opts.option_list(opts.gui())),
                         ['/SUBSYSTEM:WINDOWS'])
        self.assertEqual(self.linker.flags(opts.option_list(opts.gui(False))),
                         ['/SUBSYSTEM:WINDOWS'])
        self.assertEqual(self.linker.flags(opts.option_list(opts.gui(True))),
                         ['/SUBSYSTEM:WINDOWS', '/ENTRY:mainCRTStartup'])

        self.assertEqual(self.linker.flags(opts.option_list(
            opts.entry_point('symbol'), opts.gui(True)
        )), ['/ENTRY:symbol', '/SUBSYSTEM:WINDOWS'])
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.gui(True), opts.entry_point('symbol')
        )), ['/SUBSYSTEM:WINDOWS', '/ENTRY:symbol'])

    def test_flags_string(self):
        self.assertEqual(self.linker.flags(opts.option_list('-v')), ['-v'])

    def test_flags_lib_literal(self):
        self.assertEqual(self.linker.flags(opts.option_list(
            opts.lib_literal('-lfoo')
        )), [])

    def test_flags_invalid(self):
        with self.assertRaises(TypeError):
            self.linker.flags(opts.option_list(123))

    def test_lib_flags_empty(self):
        self.assertEqual(self.linker.lib_flags(opts.option_list()), [])

    def test_lib_flags_lib(self):
        lib = self.Path('/path/to/lib/foo.lib')

        self.assertEqual(self.linker.lib_flags(opts.option_list(
            opts.lib(file_types.SharedLibrary(lib, 'native'))
        )), [lib])
        self.assertEqual(self.linker.lib_flags(opts.option_list(
            opts.lib(file_types.SharedLibrary(lib, 'native'))
        ), mode='pkg-config'), ['-lfoo'])

        self.assertEqual(self.linker.lib_flags(opts.option_list(
            opts.lib(file_types.WholeArchive(
                file_types.SharedLibrary(lib, 'native'))
            )
        )), ['/WHOLEARCHIVE:' + lib])

        version = ('Microsoft (R) C/C++ Optimizing Compiler Version ' +
                   '18.00.25831 for x86')
        with mock.patch('bfg9000.shell.which', mock_which):
            linker = MsvcBuilder(self.env, known_langs['c++'], ['cl'],
                                 version).linker('executable')
        with self.assertRaises(TypeError):
            linker.lib_flags(opts.option_list(
                opts.lib(file_types.WholeArchive(
                    file_types.StaticLibrary(lib, 'native')
                ))
            ))

        with self.assertRaises(TypeError):
            self.linker.lib_flags(opts.option_list(
                opts.lib(Framework('cocoa'))
            ))

    def test_lib_flags_lib_literal(self):
        self.assertEqual(self.linker.lib_flags(opts.option_list(
            opts.lib_literal('/?')
        )), ['/?'])

    def test_lib_flags_ignored(self):
        self.assertEqual(self.linker.lib_flags(opts.option_list('-Lfoo')), [])

    def test_parse_flags(self):
        default = {
            'debug': None,
            'extra': [],
            'libs': [],
            'nologo': None,
        }

        def assertFlags(flags, libflags, extra={}):
            self.assertEqual(self.linker.parse_flags(flags, libflags),
                             merge_dicts(default, extra))

        assertFlags([], [])
        assertFlags(['/foo', 'bar'], ['/baz', 'quux'],
                    {'libs': ['quux'], 'extra': ['/foo', 'bar', '/baz']})
        assertFlags(['/nologo'], [], {'nologo': True})
        assertFlags([], ['/nologo'], {'nologo': True})
        assertFlags(['/nologo'], ['/nologo'], {'nologo': True})
        assertFlags(['/DEBUG'], [], {'debug': True})


class TestMsvcSharedLinker(TestMsvcLinker):
    def _get_linker(self, lang):
        version = ('Microsoft (R) C/C++ Optimizing Compiler Version ' +
                   '19.12.25831 for x86')
        with mock.patch('bfg9000.shell.which', mock_which):  # noqa
            return MsvcBuilder(self.env, known_langs[lang], ['cl'],
                               version).linker('shared_library')

    def test_call(self):
        extra = self.linker._always_flags
        self.assertEqual(
            self.linker(['in'], ['out', 'imp']),
            [self.linker] + extra + ['in', '/OUT:out', '/IMPLIB:imp']
        )
        self.assertEqual(
            self.linker(['in'], ['out', 'imp'], flags=['flags']),
            [self.linker] + extra + ['flags', 'in', '/OUT:out', '/IMPLIB:imp']
        )

        self.assertEqual(
            self.linker(['in'], ['out', 'imp'], ['lib']),
            [self.linker] + extra + ['in', 'lib', '/OUT:out', '/IMPLIB:imp']
        )
        self.assertEqual(
            self.linker(['in'], ['out', 'imp'], ['lib'], ['flags']),
            [self.linker] + extra + ['flags', 'in', 'lib', '/OUT:out',
                                     '/IMPLIB:imp']
        )

    def test_output_file(self):
        fmt = self.env.target_platform.object_format
        ext = self.env.target_platform.shared_library_ext
        out = file_types.DllBinary(Path('lib' + ext), fmt, 'c++',
                                   Path('lib.lib'), Path('lib.exp'))
        self.assertEqual(self.linker.output_file('lib', None),
                         [out, out.import_lib, out.export_file])


class TestMsvcStaticLinker(CrossPlatformTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(clear_variables=True, *args, **kwargs)

    def setUp(self):
        with mock.patch('bfg9000.shell.which', mock_which):
            self.linker = MsvcBuilder(self.env, known_langs['c++'], ['cl'],
                                      'version').linker('static_library')

    def test_call(self):
        self.assertEqual(self.linker(['in'], 'out'),
                         [self.linker, 'in', '/OUT:out'])
        self.assertEqual(self.linker(['in'], 'out', flags=['flags']),
                         [self.linker, 'flags', 'in', '/OUT:out'])

    def test_output_file(self):
        fmt = self.env.target_platform.object_format
        self.assertEqual(
            self.linker.output_file('lib', AttrDict(input_langs=['c++'])),
            file_types.StaticLibrary(Path('lib.lib'), fmt, ['c++'])
        )

    def test_can_link(self):
        fmt = self.env.target_platform.object_format
        self.assertTrue(self.linker.can_link(fmt, ['c', 'c++']))
        self.assertTrue(self.linker.can_link(fmt, ['goofy']))
        self.assertFalse(self.linker.can_link('goofy', ['c']))

    def test_flags_empty(self):
        self.assertEqual(self.linker.flags(opts.option_list()), [])

    def test_flags_string(self):
        self.assertEqual(self.linker.flags(opts.option_list('-v')), ['-v'])

    def test_flags_invalid(self):
        with self.assertRaises(TypeError):
            self.linker.flags(opts.option_list(123))

    def test_parse_flags(self):
        self.assertEqual(self.linker.parse_flags([]), {'extra': []})
        self.assertEqual(self.linker.parse_flags(['/foo', 'bar']),
                         {'extra': ['/foo', 'bar']})


class TestMsvcPackageResolver(CrossPlatformTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(clear_variables=True, *args, **kwargs)

    def setUp(self):
        with mock.patch('bfg9000.shell.which', mock_which):
            self.packages = MsvcBuilder(self.env, known_langs['c++'], ['cl'],
                                        'version').packages

    def test_header_not_found(self):
        with mock.patch('bfg9000.tools.msvc.exists', return_value=False):
            with self.assertRaises(PackageResolutionError):
                self.packages.header('foo.hpp')

    def test_header_relpath(self):
        with self.assertRaises(ValueError):
            self.packages.header('foo.hpp', [Path('dir', Root.srcdir)])

    def test_library_not_found(self):
        with mock.patch('bfg9000.tools.msvc.exists', return_value=False):
            with self.assertRaises(PackageResolutionError):
                self.packages.library('foo')

    def test_library_relpath(self):
        with self.assertRaises(ValueError):
            p = Path('dir', Root.srcdir)
            self.packages.library('foo', search_dirs=[p])
