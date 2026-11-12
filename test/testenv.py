# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The environment of the tests: temporary repositories, the binding
#
#  Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3 of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program. If not, see https://www.gnu.org/licenses/
#
#  -----------------------------------------------------------------------------

"""Temporary repositories with a git configuration of their own: no user or
system configuration of the machine leaks into the tests."""

import contextlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.dirname(TEST_DIR)
sys.path.insert(0, REPOSITORY)

SKIP = 77
LIGHT = os.path.join(TEST_DIR, 'diagrams', 'light.graphml')
LIGHT_EDITED = os.path.join(TEST_DIR, 'diagrams', 'light-edited.graphml')
DIAGRAM = 'diagrams/light.graphml'


def report(name, ok, detail=''):
    """One line per check; the count of the failures."""
    print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '\n' + str(detail)))
    return 0 if ok else 1


def git_found():
    """git is on PATH."""
    return shutil.which('git') is not None


def binding_diff():
    """The CyberiadaML binding with the revision diff."""
    try:
        import CyberiadaML  # pylint: disable=import-outside-toplevel
    except ImportError:
        return False
    return hasattr(CyberiadaML.Document, 'diff')


def _writable(function, path, _info):
    """The objects of git are read-only on Windows."""
    os.chmod(path, stat.S_IWRITE)
    function(path)


class Repo:
    """A temporary repository on the branch main with an author; a directory
    beside it is outside any work tree (the ceiling stops the lookup)."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='hsm-git-test-')
        self.top = os.path.join(self.tmp, 'repo')
        self.outside = os.path.join(self.tmp, 'outside')
        self.home = os.path.join(self.tmp, 'home')
        for directory in (self.top, self.outside, self.home):
            os.makedirs(directory)
        self.env = {'HOME': self.home, 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CONFIG_GLOBAL': os.path.join(self.home, 'gitconfig'),
                    'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.org',
                    'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.org',
                    'GIT_CEILING_DIRECTORIES': self.tmp}
        self.git('init', '-q')
        self.git('symbolic-ref', 'HEAD', 'refs/heads/main')

    def git(self, *args, stdin=None):
        """Run git in the repository, stdin the text of its input; its stdout."""
        result = subprocess.run(['git'] + list(args), cwd=self.top, env=dict(os.environ, **self.env),
                                input=None if stdin is None else stdin.encode('utf-8'),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.stdout.decode('utf-8')

    def path(self, name):
        """A file of the work tree."""
        return os.path.join(self.top, *name.split('/'))

    def put(self, name, source):
        """A file of the work tree copied from source."""
        target = self.path(name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(source, target)
        return target

    def commit(self, message='base'):
        """Stage everything and commit it."""
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)

    def subject(self):
        """The message of the last commit."""
        return self.git('log', '-1', '--format=%s').strip()

    def count(self):
        """The number of commits."""
        return int(self.git('rev-list', '--count', '--all').strip() or 0)

    @contextlib.contextmanager
    def active(self):
        """The environment of the repository for the calls in this process."""
        saved = dict(os.environ)
        os.environ.update(self.env)
        try:
            yield self
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def cleanup(self):
        """Remove the repository."""
        # onexc came in Python 3.12, the tests run on 3.8 too
        shutil.rmtree(self.tmp, onerror=_writable)  # pylint: disable=deprecated-argument
