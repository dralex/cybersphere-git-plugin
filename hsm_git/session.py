# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The commit session of the editor
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

"""The supervised commit session: the staged files and the branch asked
about, the answer the message, then git commit (docs/API.md, The commit
session). JSON-RPC 2.0 over stdin and stdout, one object per line."""

import json
import os
import sys

from hsm_git import GitError, EXIT_OK, EXIT_DECLINED, EXIT_FAILED
from hsm_git import actions
from hsm_git import git
from hsm_git.i18n import tr
from hsm_git.repo import Repository

METHOD_NOT_FOUND = -32601
# the files the question lists, the log lists them all
ASK_LISTED_FILES = 20


class Stopped(Exception):
    """The editor stopped the session: Stop, the tab closed, the end of stdin."""


class Session:
    """The commit session over a reader and a writer of lines."""

    def __init__(self, document, request=None, reader=None, writer=None):
        self.document = document
        self.request = request
        self.reader = reader if reader is not None else sys.stdin
        self.out = writer if writer is not None else sys.stdout
        self.next_id = 0

    def send(self, message):
        """One message, one line, flushed."""
        message = dict(message, jsonrpc='2.0')
        self.out.write(json.dumps(message, ensure_ascii=False, separators=(',', ':')) + '\n')
        self.out.flush()

    def notify(self, method, params):
        """A notification to the editor."""
        self.send({'method': method, 'params': params})

    def log(self, text, level=None):
        """A line of the output tab."""
        params = {'text': text}
        if level is not None:
            params['level'] = level
        self.notify('log', params)

    def state(self, status, text=None):
        """The status of the session in the dock."""
        params = {'status': status}
        if text is not None:
            params['text'] = text
        self.notify('state', params)

    def receive(self):
        """The next message of the editor; Stopped at the end of the input."""
        for line in self.reader:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict):
                return message
        raise Stopped()

    def serve(self, message):
        """The editor's request or notification while the session waits: a
        shutdown stops it, a control is ignored, an unknown request refused."""
        method = message.get('method')
        ident = message.get('id')
        if method == 'shutdown':
            self.send({'id': ident, 'result': {}})
            raise Stopped()
        if method is not None and ident is not None:
            self.send({'id': ident, 'error': {'code': METHOD_NOT_FOUND,
                                              'message': 'unknown method {}'.format(method)}})

    def initialize(self):
        """The first message is initialize: the model of the session."""
        while True:
            message = self.receive()
            if message.get('method') == 'initialize':
                self.send({'id': message.get('id'), 'result': {'kind': 'supervised', 'controls': []}})
                return
            self.serve(message)

    def ask(self, text):
        """A question; the reply of the editor."""
        self.next_id += 1
        ident = 'ask-{}'.format(self.next_id)
        self.send({'id': ident, 'method': 'ask', 'params': {'text': text}})
        while True:
            message = self.receive()
            if message.get('id') == ident and 'method' not in message:
                result = message.get('result')
                return result if isinstance(result, dict) else {'action': 'cancel'}
            self.serve(message)

    def unsaved(self):
        """The document has edits the commit does not take: request.json."""
        if not self.request:
            return False
        try:
            with open(self.request, encoding='utf-8') as file:
                return bool(json.load(file).get('document', {}).get('modified'))
        except (OSError, ValueError, AttributeError):
            return False

    def question(self, repo, staged):
        """The text of the question: the branch, the files, the unsaved edits."""
        lines = [tr('Commit {} staged file(s) to {}? The answer is the message.').format(len(staged), repo.branch)]
        for status, path in staged[:ASK_LISTED_FILES]:
            lines.append('{}  {}'.format(status, path))
        if len(staged) > ASK_LISTED_FILES:
            lines.append(tr('... and {} more').format(len(staged) - ASK_LISTED_FILES))
        if self.unsaved():
            lines.append(tr('{} has unsaved edits: they are not committed.').format(os.path.basename(self.document)))
        return '\n'.join(lines)

    def commit(self):
        """The whole session after initialize; the exit code."""
        self.state('running', tr('reading the index'))
        repo = Repository.locate(self.document)
        staged = actions.staged_files(repo)
        while True:
            fingerprint = repo.fingerprint()
            for status, path in staged:
                self.log('{}  {}'.format(status, path))
            self.state('waiting')
            reply = self.ask(self.question(repo, staged))
            if reply.get('action') != 'accept':
                self.log(tr('declined: nothing is committed'))
                return EXIT_DECLINED
            message = actions.first_line(str(reply.get('text', '')))
            if not message:
                self.log(tr('the message is empty'), 'warning')
                continue
            if repo.fingerprint() != fingerprint:
                self.log(tr('the index changed while asking'), 'warning')
                staged = actions.staged_files(repo)
                continue
            break
        self.state('running', tr('committing'))
        code, out, err = git.run(['commit', '-F', '-'], repo.top, stdin=actions.commit_text(message))
        for line in (git.text(out) + err).splitlines():
            self.log(line, None if code == 0 else 'error')
        if code != 0:
            raise GitError(tr('the commit failed'))
        head = git.text(git.output(['rev-parse', '--short', 'HEAD'], repo.top, tr('the commit is not read'),
                                   read_only=True)).strip()
        self.state('finished', tr('committed {}').format(head))
        return EXIT_OK

    def run(self):
        """initialize, the question, the commit; the exit code."""
        try:
            self.initialize()
            return self.commit()
        except Stopped:
            return EXIT_DECLINED
        except GitError as error:
            if error.details.strip():
                for line in error.details.strip().splitlines():
                    self.log(line, 'error')
            self.log(str(error), 'error')
            sys.stderr.write('git: {}: {}\n'.format(os.path.basename(self.document), error))
            return error.code if error.code else EXIT_FAILED


def run(document, request=None):
    """hsm-git commit DOCUMENT --session."""
    return Session(document, request).run()
