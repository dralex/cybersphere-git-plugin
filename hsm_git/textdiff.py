# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The line diff of a text against a revision or the index
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

"""The line diff of a text of a text tab and its findings (docs/API.md, The
text of a line diff); needs no CyberiadaML."""

import difflib
import os
import tempfile

from hsm_git import GitError
from hsm_git import diff
from hsm_git.i18n import tr
from hsm_git.repo import Repository

BASE_FILE = 'revision.txt'
CONTEXT_LINES = 3
ENCODING = 'utf-8'
# the header difflib writes itself: the base writes its own
DIFFLIB_HEADER = 2


def lines(path):
    """The lines of a text without their ends, an undecodable byte replaced."""
    try:
        with open(path, 'rb') as file:
            return file.read().decode(ENCODING, 'replace').splitlines()
    except OSError as error:
        raise GitError(tr('the text {} is not read: {}').format(os.path.basename(path), error)) from error


def span(first, last):
    """Lines of a text as a finding names them."""
    return 'line {}'.format(first) if first == last else 'lines {}-{}'.format(first, last)


def findings_of(old, new):
    """A finding per changed block, at its first line in the new text."""
    found = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if tag == 'equal':
            continue
        item = {'severity': diff.SEVERITY}
        if tag == 'delete':
            count = i2 - i1
            item['rule'] = 'removed'
            # the line after the removed block, the last one at the end
            item['line'] = max(1, min(j1 + 1, len(new)))
            item['message'] = '{} line{} removed'.format(count, '' if count == 1 else 's')
        else:
            item['rule'] = 'changed' if tag == 'replace' else 'added'
            item['line'] = j1 + 1
            item['message'] = '{} {}'.format(span(j1 + 1, j2), item['rule'])
        found.append(item)
    return found


def text(old, new, revision, findings=None):
    """The lines of the line diff of two texts after the header: the hunks and
    the summary; the findings are appended to the list findings."""
    out = list(difflib.unified_diff(old, new, lineterm='', n=CONTEXT_LINES))[DIFFLIB_HEADER:]
    added = sum(1 for line in out if line.startswith('+'))
    removed = sum(1 for line in out if line.startswith('-'))
    if out:
        out.append('lines: {} added, {} removed'.format(added, removed))
    else:
        out.append('no changes since {}'.format(revision))
    if findings is not None:
        findings.extend(findings_of(old, new))
    return out


def run(document, current=None, revision='HEAD', diagnostics=None):
    """Print the changed lines of the text (the file, or current: the editor's
    copy) since the revision - against the index when it is None; write their
    findings into diagnostics."""
    repo = Repository.locate(document)
    with tempfile.TemporaryDirectory() as tmp:
        blob = os.path.join(tmp, BASE_FILE)
        path, label, name = diff.fetch(repo, revision, blob)
        old = lines(blob)
    new = lines(current if current is not None else document)
    print(diff.header_line(repo, path, label, name))
    print('+++ ' + diff.WORKING)
    findings = []
    for line in text(old, new, name, findings):
        print(line)
    if diagnostics is not None:
        diff.write_findings(diagnostics, findings)
