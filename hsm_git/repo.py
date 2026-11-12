# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The repository of a diagram file
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

"""The work tree, the path, the branch, the index and the revisions of a
diagram file (docs/ARCHITECTURE.md, The repository of a document)."""

import os

from hsm_git import GitError, EXIT_USAGE
from hsm_git import git

DETACHED = 'detached at {}'
# the name-status letters followed by two paths: a rename, a copy
TWO_PATHS = 'RC'
RENAME_PATHS = 2
# a commit of the history: the short hash, the date, the author, the subject
LOG_SEPARATOR = '\x1f'
LOG_FORMAT = '%h%x1f%ad%x1f%an%x1f%s'
LOG_FIELDS = 4
# the fields of an ls-files --stage entry; stage 0 is a merged file
HASH_FIELD = 1
STAGE_FIELD = 2
MERGED_STAGE = '0'


def name_status(data):
    """The (status letter, paths) entries of a --name-status -z output."""
    items = git.fields(data)
    entries = []
    i = 0
    while i < len(items):
        status = items[i][:1]
        count = RENAME_PATHS if status in TWO_PATHS else 1
        entries.append((status, items[i + 1:i + 1 + count]))
        i += 1 + count
    return entries


class Repository:
    """The repository of a diagram file; git runs in its work tree."""

    def __init__(self, top, path, branch, has_commits):
        self.top = top
        self.path = path            # the file in the repository, with '/'
        self.branch = branch        # the branch, or 'detached at <hash>'
        self.has_commits = has_commits

    @classmethod
    def locate(cls, document):
        """The repository of a diagram file; GitError outside a work tree."""
        document = os.path.abspath(document)
        directory = os.path.dirname(document)
        name = os.path.basename(document)
        code, out, err = git.run(['rev-parse', '--show-toplevel'], directory, read_only=True)
        if code != 0:
            raise GitError('{} is not in a git work tree'.format(name), details=err)
        top = git.text(out).strip()
        prefix = git.text(git.output(['rev-parse', '--show-prefix'], directory,
                                     'the path in the repository is not found', read_only=True)).strip()
        code, out, _ = git.run(['symbolic-ref', '--short', '-q', 'HEAD'], directory, read_only=True)
        branch = git.text(out).strip() if code == 0 else None
        code, out, _ = git.run(['rev-parse', '--verify', '-q', '--short', 'HEAD^{commit}'], directory,
                               read_only=True)
        has_commits = code == 0
        if branch is None:
            branch = DETACHED.format(git.text(out).strip())
        return cls(top, prefix + name, branch, has_commits)

    def staged(self):
        """The staged changes of the whole index: (status, path) pairs, a
        rename shown as 'old -> new'."""
        out = git.output(['diff', '--cached', '--name-status', '-z', '-M'], self.top,
                         'the index is not read', read_only=True)
        return [(status, ' -> '.join(paths)) for status, paths in name_status(out)]

    def fingerprint(self):
        """The staged changes with their blobs: a change of the index changes it."""
        return git.output(['diff', '--cached', '--raw', '-z', '-M', '--no-abbrev'], self.top,
                          'the index is not read', read_only=True)

    def status(self):
        """The short status line of the file, empty when it has no changes."""
        out = git.output(['status', '--porcelain', '-z', '--', self.path], self.top,
                         'the status is not read', read_only=True)
        items = git.fields(out)
        return items[0] if items else ''

    def has_staged_change(self):
        """The index holds a change of the file."""
        out = git.output(['diff', '--cached', '--name-only', '-z', '--', self.path], self.top,
                         'the index is not read', read_only=True)
        return bool(git.fields(out))

    def revision(self, rev):
        """The commit hash of a revision; a revision like an option is refused."""
        if not rev or rev.startswith('-'):
            raise GitError("the revision '{}' is refused".format(rev), EXIT_USAGE)
        code, out, _ = git.run(['rev-parse', '--verify', '-q', rev + '^{commit}'], self.top, read_only=True)
        if code != 0:
            raise GitError("the revision '{}' is not found".format(rev))
        return git.text(out).strip()

    def renamed_from(self, commit):
        """The path the file had in the commit when a staged rename moved it."""
        out = git.output(['diff', '--cached', '-M', '--name-status', '-z', commit], self.top,
                         'the renames are not read', read_only=True)
        for status, paths in name_status(out):
            if status == 'R' and len(paths) == RENAME_PATHS and paths[1] == self.path:
                return paths[0]
        return None

    def path_in(self, commit):
        """The path the file has in the commit, a staged rename followed; None
        when the commit lacks it."""
        code, _, _ = git.run(['cat-file', '-e', '{}:{}'.format(commit, self.path)], self.top, read_only=True)
        return self.path if code == 0 else self.renamed_from(commit)

    def blob(self, commit, out):
        """Write the file as the commit has it into out, exactly as stored;
        return the path it has there, None when the commit lacks it."""
        path = self.path_in(commit)
        if path is None:
            return None
        data = git.output(['cat-file', 'blob', '{}:{}'.format(commit, path)], self.top,
                          'the file of the revision is not read', read_only=True)
        with open(out, 'wb') as file:
            file.write(data)
        return path

    def history(self, count):
        """The last count commits of the file, the newest first, a rename
        followed: (hash, date, author, subject) tuples."""
        if not self.has_commits:
            return []
        head = self.revision('HEAD')
        path = self.path_in(head)
        if path is None:
            return []
        out = git.output(['log', '--follow', '-n', str(count), '-z', '--date=short', '--format=' + LOG_FORMAT,
                          head, '--', path], self.top, 'the history is not read', read_only=True)
        return [tuple(record.split(LOG_SEPARATOR, LOG_FIELDS - 1)) for record in git.fields(out)]

    def index_blob(self, out):
        """Write the file as the index stages it into out; return its path,
        None when the index lacks it; an unmerged file is refused."""
        data = git.output(['ls-files', '--stage', '-z', '--', self.path], self.top,
                          'the index is not read', read_only=True)
        # an entry: <mode> <hash> <stage>\t<path>
        entries = [item.split('\t', 1)[0].split() for item in git.fields(data)]
        if not entries:
            return None
        if any(entry[STAGE_FIELD] != MERGED_STAGE for entry in entries):
            raise GitError('{} is unmerged: resolve the conflict first'.format(self.path))
        data = git.output(['cat-file', 'blob', entries[0][HASH_FIELD]], self.top,
                          'the file of the index is not read', read_only=True)
        with open(out, 'wb') as file:
            file.write(data)
        return self.path
