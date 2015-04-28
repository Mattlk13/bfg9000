import os
import subprocess
import unittest

from integration import IntegrationTest, cleandir

class TestSubdirs(IntegrationTest):
    def __init__(self, *args, **kwargs):
        IntegrationTest.__init__(self, 'subdirs', *args, **kwargs)
        self.distdir = os.path.join(self.srcdir, 'dist')
        self.extra_args = ['--prefix', self.distdir]

    def setUp(self):
        IntegrationTest.setUp(self)
        cleandir(self.distdir)

    def test_all(self):
        subprocess.check_call([self.backend])
        self.assertEqual(subprocess.check_output(
            [os.path.join('bin', 'sub', 'program')],
        ), 'hello, library!\n')

    def test_install(self):
        subprocess.check_call([self.backend, 'install'])
        cleandir(self.builddir)

        self.assertTrue(os.path.exists(os.path.join(
            self.distdir, 'include', 'library.hpp'
        )))
        # TODO: Support other platform naming schemes
        self.assertTrue(os.path.exists(os.path.join(
            self.distdir, 'bin', 'sub', 'program'
        )))
        self.assertTrue(os.path.exists(os.path.join(
            self.distdir, 'lib', 'sub', 'liblibrary.so'
        )))

        self.assertEqual(subprocess.check_output(
            [os.path.join(self.distdir, 'bin', 'sub', 'program')]
        ), 'hello, library!\n')

    def test_install_existing_paths(self):
        os.mkdir(os.path.join(self.distdir, 'include'))
        os.mkdir(os.path.join(self.distdir, 'bin'))
        os.mkdir(os.path.join(self.distdir, 'lib'))
        subprocess.check_call([self.backend, 'install'])
        cleandir(self.builddir)

        self.assertTrue(os.path.exists(os.path.join(
            self.distdir, 'include', 'library.hpp'
        )))
        # TODO: Support other platform naming schemes
        self.assertTrue(os.path.exists(os.path.join(
            self.distdir, 'bin', 'sub', 'program'
        )))
        self.assertTrue(os.path.exists(os.path.join(
            self.distdir, 'lib', 'sub', 'liblibrary.so'
        )))

        self.assertEqual(subprocess.check_output(
            [os.path.join(self.distdir, 'bin', 'sub', 'program')]
        ), 'hello, library!\n')

if __name__ == '__main__':
    unittest.main()
