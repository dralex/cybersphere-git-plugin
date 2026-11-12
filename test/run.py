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

"""Stage, unstage, the one-shot commit, the revision file and the diff
(docs/API.md) on temporary repositories; the diff part is skipped without
Document.diff."""

import contextlib
import io
import json
import os
import re
import sys

from testenv import Repo, report, git_found, binding_diff, write_text, SKIP, LIGHT, LIGHT_EDITED, DIAGRAM, TEST_DIR
from testenv import NOTES, NOTES_TEXT, NOTES_EDITED

from hsm_git import cli, textdiff, EXIT_OK, EXIT_USAGE, EXIT_NOTHING_STAGED, EXIT_FAILED  # pylint: disable=wrong-import-order

GOOD_DIFF = os.path.join(TEST_DIR, 'good', 'diff-light.txt')
GOOD_TEXT_DIFF = os.path.join(TEST_DIR, 'good', 'diff-text.txt')


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


def read_json(path):
    """A JSON file of the run."""
    with open(path, encoding='utf-8') as file:
        return json.load(file)


def same_bytes(first, second):
    """Two files hold the same bytes."""
    with open(first, 'rb') as one, open(second, 'rb') as two:
        return one.read() == two.read()


def revisions():
    """The revision file of a diff tab, which needs no CyberiadaML; the
    failures."""
    failed = 0
    repo = Repo()
    try:
        document = repo.put(DIAGRAM, LIGHT)
        output = os.path.join(repo.tmp, 'revision.graphml')
        code, out, err = hsm_git(repo, 'revision', document, '--output', output)
        failed += report('the revision before the first commit', code == EXIT_OK and
                         out.strip() == '{} is not in HEAD'.format(DIAGRAM) and os.path.getsize(output) == 0,
                         out + err)
        repo.commit()
        repo.put(DIAGRAM, LIGHT_EDITED)
        code, out, err = hsm_git(repo, 'revision', document, '--output', output)
        failed += report('the revision as stored, not the edited file', code == EXIT_OK and
                         out.strip() == 'HEAD:' + DIAGRAM and same_bytes(output, LIGHT), out + err)
        repo.commit('edited')
        repo.git('mv', DIAGRAM, 'diagrams/moved.graphml')
        moved = repo.path('diagrams/moved.graphml')
        code, out, err = hsm_git(repo, 'revision', moved, '--revision=HEAD~1', '--output', output)
        failed += report('the old path of a staged rename', code == EXIT_OK and
                         out.strip() == 'HEAD~1:' + DIAGRAM and same_bytes(output, LIGHT), out + err)
        new = repo.put('diagrams/new.graphml', LIGHT)
        code, out, err = hsm_git(repo, 'revision', new, '--output', output)
        failed += report('a new file: an empty revision', code == EXIT_OK and
                         out.strip() == 'diagrams/new.graphml is not in HEAD' and os.path.getsize(output) == 0,
                         out + err)
        code, out, err = hsm_git(repo, 'revision', moved, '--revision=-x', '--output', output)
        failed += report('a revision like an option refused', code == EXIT_USAGE and 'refused' in err, out + err)
        code, out, err = hsm_git(repo, 'revision', moved, '--revision=nope', '--output', output)
        failed += report('a missing revision for the file', code == EXIT_FAILED and "'nope' is not found" in err,
                         out + err)
        unwritable = os.path.join(repo.tmp, 'no-such-dir', 'revision.graphml')
        code, out, err = hsm_git(repo, 'revision', moved, '--output', unwritable)
        failed += report('an unwritable output', code == EXIT_FAILED and 'is not written' in err and
                         'Traceback' not in err, out + err)
    finally:
        repo.cleanup()
    return failed


def indexes():
    """The index as the base of a diff tab, without the binding; the
    failures."""
    failed = 0
    repo = Repo()
    try:
        document = repo.put(DIAGRAM, LIGHT)
        output = os.path.join(repo.tmp, 'index.graphml')
        code, out, err = hsm_git(repo, 'revision', document, '--index', '--output', output)
        failed += report('a file the index lacks', code == EXIT_OK and
                         out.strip() == '{} is not in the index'.format(DIAGRAM) and os.path.getsize(output) == 0,
                         out + err)
        repo.git('add', DIAGRAM)
        repo.put(DIAGRAM, LIGHT_EDITED)
        code, out, err = hsm_git(repo, 'revision', document, '--index', '--output', output)
        failed += report('the staged file before the first commit, not the edited one', code == EXIT_OK and
                         out.strip() == 'index:' + DIAGRAM and same_bytes(output, LIGHT), out + err)
        blob = repo.git('hash-object', '-w', DIAGRAM).strip()
        repo.git('update-index', '--force-remove', DIAGRAM)
        repo.git('update-index', '--index-info',
                 stdin=''.join('100644 {} {}\t{}\n'.format(blob, stage, DIAGRAM) for stage in (1, 2, 3)))
        code, out, err = hsm_git(repo, 'revision', document, '--index', '--output', output)
        failed += report('an unmerged file refused', code == EXIT_FAILED and not out and 'is unmerged' in err,
                         out + err)
    finally:
        repo.cleanup()
    return failed


def texts():
    """The line diff of a text and its findings, without the binding; the
    failures."""
    failed = 0
    repo = Repo()
    try:
        notes = write_text(repo.path(NOTES), NOTES_TEXT)
        code, out, err = hsm_git(repo, 'diff', notes)
        failed += report('a new text: every line added', code == EXIT_OK and
                         out.startswith('--- /dev/null ({} is not in HEAD)\n+++ working\n@@ -0,0 +1,4 @@\n'
                                        .format(NOTES)) and
                         out.splitlines()[-1] == 'lines: 4 added, 0 removed', out + err)
        repo.commit()
        write_text(notes, NOTES_EDITED)
        findings = os.path.join(repo.tmp, 'diagnostics.json')
        code, out, err = hsm_git(repo, 'diff', notes, '--diagnostics', findings)
        with open(GOOD_TEXT_DIFF, encoding='utf-8') as file:
            good = file.read()
        failed += report('the line diff of the edited text', code == EXIT_OK and out == good, out + err)
        failed += report('the findings of a text', read_json(findings) == [
            {'severity': 'info', 'rule': 'changed', 'line': 3, 'message': 'lines 3-4 changed'}], read_json(findings))
        copy = write_text(os.path.join(repo.tmp, 'input', 'input.md'), NOTES_TEXT, '\r\n')
        code, out, err = hsm_git(repo, 'diff', notes, '--current', copy)
        failed += report('the editor copy compared, its line ends ignored', code == EXIT_OK and
                         out.splitlines()[-1] == 'no changes since HEAD', out + err)
        repo.git('add', NOTES)
        code, out, err = hsm_git(repo, 'diff', notes, '--index')
        failed += report('a text against the index', code == EXIT_OK and
                         out.startswith('--- index:{}\n'.format(NOTES)) and
                         out.splitlines()[-1] == 'no changes since the index', out + err)
        failed += report('the findings of the kinds of blocks', textdiff.findings_of(['a', 'b', 'c'], ['a', 'c']) == [
            {'severity': 'info', 'rule': 'removed', 'line': 2, 'message': '1 line removed'}] and
                         textdiff.findings_of(['a'], ['a', 'b', 'c']) == [
            {'severity': 'info', 'rule': 'added', 'line': 2, 'message': 'lines 2-3 added'}] and
                         textdiff.findings_of(['a', 'b', 'c'], ['a'])[0]['line'] == 1)
        failed += report('a text needs no CyberiadaML', 'CyberiadaML' not in sys.modules)
    finally:
        repo.cleanup()
    return failed


def commit_line(line, subject):
    """A line of the history: the short hash, the date, the author, the subject."""
    return re.match(r'^[0-9a-f]{7,}  \d{4}-\d{2}-\d{2}  Test  ' + re.escape(subject) + '$', line) is not None


def histories():
    """The commits of a file, a rename followed; the failures."""
    failed = 0
    repo = Repo()
    try:
        document = repo.put(DIAGRAM, LIGHT)
        code, out, err = hsm_git(repo, 'history', document)
        failed += report('no history before the first commit', code == EXIT_OK and
                         out == '{} has no commits\n'.format(DIAGRAM), out + err)
        repo.commit('base')
        repo.put(DIAGRAM, LIGHT_EDITED)
        repo.commit('edited')
        code, out, err = hsm_git(repo, 'history', document)
        lines = out.splitlines()
        failed += report('the history, the newest first', code == EXIT_OK and len(lines) == 2 and
                         commit_line(lines[0], 'edited') and commit_line(lines[1], 'base'), out + err)
        repo.git('mv', DIAGRAM, 'diagrams/moved.graphml')
        moved = repo.path('diagrams/moved.graphml')
        code, out, err = hsm_git(repo, 'history', moved)
        failed += report('the history of a staged rename', code == EXIT_OK and len(out.splitlines()) == 2, out + err)
        repo.commit('moved')
        code, out, err = hsm_git(repo, 'history', moved)
        lines = out.splitlines()
        failed += report('the history followed through the rename', code == EXIT_OK and len(lines) == 3 and
                         commit_line(lines[0], 'moved') and commit_line(lines[2], 'base'), out + err)
        code, out, err = hsm_git(repo, 'history', moved, '--count', '1')
        failed += report('the count of the history', code == EXIT_OK and len(out.splitlines()) == 1, out + err)
        new = repo.put('diagrams/new.graphml', LIGHT)
        code, out, err = hsm_git(repo, 'history', new)
        failed += report('no history of a new file', code == EXIT_OK and
                         out == 'diagrams/new.graphml has no commits\n', out + err)
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
        findings = os.path.join(repo.tmp, 'diagnostics.json')
        code, out, err = hsm_git(repo, 'diff', document, '--diagnostics', findings)
        found = read_json(findings)
        failed += report('the findings of the diff', code == EXIT_OK and len(found) == 12 and
                         {'severity': 'info', 'rule': 'changed', 'element': 'n1',
                          'message': 'state Red changed: color'} in found and
                         {'severity': 'info', 'rule': 'added', 'element': 'n3', 'message': 'state Blink added'} in found and
                         {'severity': 'info', 'rule': 'removed', 'message': 'state Green removed'} in found and
                         {'severity': 'info', 'rule': 'changed',
                          'element': 'n1-n5', 'message': 'transition Red -> Blink [NIGHT] changed '
                                                         '(was transition Red -> Night [NIGHT])'} in found and
                         {'severity': 'info', 'rule': 'changed', 'message': 'meta changed: platform'} in found,
                         found)
        code, out, err = hsm_git(repo, 'diff', document, '--current', LIGHT, '--diagnostics', findings)
        failed += report('the editor copy compared, not the file', code == EXIT_OK and
                         out.splitlines()[-1] == 'no changes since HEAD' and read_json(findings) == [], out + err)
        code, out, err = hsm_git(repo, 'diff', document, '--index')
        failed += report('the diff against the index', code == EXIT_OK and
                         out == good.replace('--- HEAD:', '--- index:', 1), out + err)
        repo.git('add', DIAGRAM)
        code, out, err = hsm_git(repo, 'diff', document, '--index')
        failed += report('no changes against the index', code == EXIT_OK and
                         out.splitlines()[-1] == 'no changes since the index', out + err)
        repo.git('reset', '-q', '--', DIAGRAM)
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
    failed = actions() + revisions() + indexes() + texts() + histories()
    if binding_diff():
        failed += diffs()
    else:
        print('skipped the diff: no CyberiadaML with Document.diff')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
