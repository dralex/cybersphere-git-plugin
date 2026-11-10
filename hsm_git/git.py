# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  Running git
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

"""Running git in a directory: no terminal, the paths taken literally, the
output as bytes (docs/ARCHITECTURE.md, The repository of a document)."""

import os
import subprocess

from hsm_git import GitError

GIT = 'git'


def environment(read_only=False):
    """The environment of git: it never asks on a terminal and takes the paths
    literally; a read-only call takes no optional lock."""
    env = dict(os.environ)
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GIT_LITERAL_PATHSPECS'] = '1'
    if read_only:
        env['GIT_OPTIONAL_LOCKS'] = '0'
    return env


def run(args, cwd, stdin=None, read_only=False):
    """Run git with args in cwd; return the exit code, stdout as bytes and
    stderr as text. stdin is bytes, or None for the null device: in a session
    the standard input is the channel of the editor."""
    command = [GIT] + list(args)
    streams = {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE}
    if stdin is None:
        streams['stdin'] = subprocess.DEVNULL
    else:
        streams['input'] = stdin
    try:
        proc = subprocess.run(command, cwd=cwd, env=environment(read_only), check=False, **streams)
    except OSError as error:
        raise GitError('git does not start: {}'.format(error)) from error
    return proc.returncode, proc.stdout, proc.stderr.decode('utf-8', 'replace')


def output(args, cwd, failure, stdin=None, read_only=False):
    """The stdout of a successful call; a failed one raises GitError with the
    failure text and git's stderr."""
    code, out, err = run(args, cwd, stdin, read_only)
    if code != 0:
        raise GitError(failure, details=err)
    return out


def text(data):
    """The bytes of git as text."""
    return data.decode('utf-8', 'replace')


def fields(data):
    """The fields of a -z output."""
    return [text(field) for field in data.split(b'\0') if field]
