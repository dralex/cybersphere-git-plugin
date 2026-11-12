# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  Stage, unstage and the one-shot commit
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

"""Stage, unstage, the one-shot commit and the history (docs/ARCHITECTURE.md,
Stage and unstage, The commit, The history)."""

import sys

from hsm_git import GitError, EXIT_NOTHING_STAGED, EXIT_USAGE
from hsm_git import git
from hsm_git.repo import Repository

HISTORY_COUNT = 30
HISTORY_SEPARATOR = '  '


def status_line(repo):
    """The status of the file after an action."""
    line = repo.status()
    return line if line else '{} has no changes'.format(repo.path)


def stage(document):
    """git add of the saved diagram."""
    repo = Repository.locate(document)
    git.output(['add', '--', repo.path], repo.top, '{} is not staged'.format(repo.path))
    print(status_line(repo))


def unstage(document):
    """The diagram out of the index, its file kept; before the first commit
    there is no HEAD to restore from."""
    repo = Repository.locate(document)
    if not repo.has_staged_change():
        print('nothing to unstage')
        return
    if repo.has_commits:
        args = ['restore', '--staged', '--', repo.path]
    else:
        args = ['rm', '--cached', '-q', '--', repo.path]
    git.output(args, repo.top, '{} is not unstaged'.format(repo.path))
    print(status_line(repo))


def first_line(text):
    """The commit message: the first non-empty line, stripped."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ''


def staged_files(repo):
    """The staged changes of the index; nothing staged is a failure."""
    staged = repo.staged()
    if not staged:
        raise GitError('nothing is staged: stage the files first', EXIT_NOTHING_STAGED)
    return staged


def commit_text(message):
    """The message on the standard input of git commit -F -."""
    return (message + '\n').encode('utf-8')


def commit(document, message_file):
    """git commit of the whole index with the first line of the file."""
    repo = Repository.locate(document)
    try:
        with open(message_file, encoding='utf-8') as file:
            message = first_line(file.read())
    except OSError as error:
        raise GitError('the message is not read: {}'.format(error), EXIT_USAGE) from error
    if not message:
        raise GitError('the commit message is empty', EXIT_USAGE)
    staged = staged_files(repo)
    print('Committing {} staged file(s) to {}:'.format(len(staged), repo.branch))
    for status, path in staged:
        print('  {}  {}'.format(status, path))
    sys.stdout.flush()
    out = git.output(['commit', '-F', '-'], repo.top, 'the commit failed', stdin=commit_text(message))
    sys.stdout.write(git.text(out))


def history(document, count=HISTORY_COUNT):
    """The last commits of the file, a rename followed."""
    repo = Repository.locate(document)
    commits = repo.history(count)
    if not commits:
        print('{} has no commits'.format(repo.path))
    for commit in commits:
        print(HISTORY_SEPARATOR.join(commit))
