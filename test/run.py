# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The tests of the actions and of the diff on temporary repositories
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

"""Stage, unstage, the one-shot commit and the diff (docs/API.md) on
temporary repositories; the diff part is skipped without Document.diff."""

import contextlib
import io
import os
import sys

from testenv import Repo, report, git_found, binding_diff, SKIP, LIGHT, LIGHT_EDITED, DIAGRAM, TEST_DIR

from hsm_git import cli, EXIT_OK, EXIT_USAGE, EXIT_NOTHING_STAGED, EXIT_FAILED  # pylint: disable=wrong-import-order

GOOD_DIFF = os.path.join(TEST_DIR, 'good', 'diff-light.txt')


def hsm_git(repo, *args):
    """hsm-git in this process with the repository's environment: the exit
    code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with repo.active(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(args))
    return code, out.getvalue(), err.getvalue()


def message_file(repo, text):
    """A commit message in a file beside the repository."""
    path = os.path.join(repo.tmp, 'message')
    with open(path, 'w', encoding='utf-8') as file:
        file.write(text)
    return path


def actions():
    """Stage, unstage, commit; the failures."""
    failed = 0
    repo = Repo()
    try:
        document = repo.put(DIAGRAM, LIGHT)
        code, out, err = hsm_git(repo, 'stage', document)
        failed += report('stage a new file', code == EXIT_OK and out.strip() == 'A  ' + DIAGRAM, out + err)
        code, out, err = hsm_git(repo, 'unstage', document)
        failed += report('unstage before the first commit', code == EXIT_OK and out.strip() == '?? ' + DIAGRAM,
                         out + err)
        code, out, err = hsm_git(repo, 'unstage', document)
        failed += report('nothing to unstage', code == EXIT_OK and out.strip() == 'nothing to unstage', out + err)
        code, out, err = hsm_git(repo, 'commit', document, '--message-file', message_file(repo, 'first'))
        failed += report('nothing staged', code == EXIT_NOTHING_STAGED and 'nothing is staged' in err, out + err)
        hsm_git(repo, 'stage', document)
        code, out, err = hsm_git(repo, 'commit', document, '--message-file', message_file(repo, '\nthe light\nmore'))
        failed += report('commit the index', code == EXIT_OK and repo.subject() == 'the light' and
                         'Committing 1 staged file(s) to main:' in out and 'A  ' + DIAGRAM in out, out + err)
        code, out, err = hsm_git(repo, 'commit', document, '--message-file', message_file(repo, '  \n'))
        failed += report('an empty message refused', code == EXIT_USAGE, out + err)
        repo.put(DIAGRAM, LIGHT_EDITED)
        hsm_git(repo, 'stage', document)
        code, out, err = hsm_git(repo, 'unstage', document)
        failed += report('unstage after a commit', code == EXIT_OK and out.rstrip('\n') == ' M ' + DIAGRAM,
                         out + err)
        hook = repo.path('.git/hooks/pre-commit')
        with open(hook, 'w', encoding='utf-8') as file:
            file.write('#!/bin/sh\necho refused by the hook >&2\nexit 1\n')
        os.chmod(hook, 0o755)
        hsm_git(repo, 'stage', document)
        count = repo.count()
        code, out, err = hsm_git(repo, 'commit', document, '--message-file', message_file(repo, 'hooked'))
        failed += report('a failing hook fails the commit', code == EXIT_FAILED and repo.count() == count and
                         'refused by the hook' in err, out + err)
        outside = os.path.join(repo.outside, 'light.graphml')
        code, out, err = hsm_git(repo, 'stage', outside)
        failed += report('a file outside a work tree', code == EXIT_FAILED and 'is not in a git work tree' in err,
                         out + err)
    finally:
        repo.cleanup()
    return failed


def diffs():
    """The text of the diff; the failures."""
    failed = 0
    repo = Repo()
    try:
        document = repo.put(DIAGRAM, LIGHT)
        code, out, err = hsm_git(repo, 'diff', document)
        failed += report('the diff before the first commit', code == EXIT_OK and
                         out.startswith('--- /dev/null ({} is not in HEAD)\n+++ working\n'.format(DIAGRAM)) and
                         '+ state machine Light' in out and '+   state Red' in out and
                         ' 0 removed' in out.splitlines()[-1],
                         out + err)
        repo.commit()
        code, out, err = hsm_git(repo, 'diff', document)
        failed += report('no changes', code == EXIT_OK and out.splitlines()[-1] == 'no changes since HEAD', out + err)
        repo.put(DIAGRAM, LIGHT_EDITED)
        code, out, err = hsm_git(repo, 'diff', document)
        with open(GOOD_DIFF, encoding='utf-8') as file:
            good = file.read()
        failed += report('the diff of the edited light', code == EXIT_OK and out == good, out + err)
        code, out, err = hsm_git(repo, 'diff', document, '--current', LIGHT)
        failed += report('the editor copy compared, not the file', code == EXIT_OK and
                         out.splitlines()[-1] == 'no changes since HEAD', out + err)
        code, out, err = hsm_git(repo, 'diff', document, '--geometry')
        lines = out.splitlines()
        failed += report('the geometry', code == EXIT_OK and any(line.startswith('-   at: ') for line in lines) and
                         any(line.startswith('+   at: ') for line in lines) and '+   id: n3' in lines, out + err)
        code, out, err = hsm_git(repo, 'diff', document, '--revision=-x')
        failed += report('a revision like an option refused', code == EXIT_USAGE and 'refused' in err, out + err)
        code, out, err = hsm_git(repo, 'diff', document, '--revision=nope')
        failed += report('a missing revision', code == EXIT_FAILED and "'nope' is not found" in err, out + err)
        repo.commit('edited')
        repo.git('mv', DIAGRAM, 'diagrams/moved.graphml')
        moved = repo.path('diagrams/moved.graphml')
        code, out, err = hsm_git(repo, 'diff', moved, '--revision=HEAD~1')
        failed += report('a staged rename compared with the old path', code == EXIT_OK and
                         out.startswith('--- HEAD~1:{}\n'.format(DIAGRAM)) and '+ state Blink' in out, out + err)
    finally:
        repo.cleanup()
    return failed


def main():
    """All the tests; 77 without git."""
    if not git_found():
        print('skipped: no git')
        return SKIP
    failed = actions()
    if binding_diff():
        failed += diffs()
    else:
        print('skipped the diff: no CyberiadaML with Document.diff')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
