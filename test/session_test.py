# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The tests of the commit session driven over its pipes
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

"""The commit session (docs/API.md, The commit session): the editor's side
scripted line by line, the plugin's messages read back."""

import contextlib
import io
import json
import os
import sys

from testenv import Repo, report, git_found, SKIP, LIGHT, LIGHT_EDITED, DIAGRAM

from hsm_git import EXIT_OK, EXIT_DECLINED, EXIT_NOTHING_STAGED  # pylint: disable=wrong-import-order
from hsm_git.session import Session  # pylint: disable=wrong-import-order
from hsm_git.i18n import LANGUAGE_VARIABLE  # pylint: disable=wrong-import-order

INITIALIZE = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
              'params': {'session': 1, 'editor': '1.1.0', 'language': 'en', 'plugin': 'git',
                         'action': 'commit-session'}}


def line(message):
    """One message of the editor."""
    return json.dumps(message) + '\n'


def answer(number, text=None, action='accept'):
    """The editor's reply to the question number."""
    result = {'action': action}
    if text is not None:
        result['text'] = text
    return line({'jsonrpc': '2.0', 'id': 'ask-{}'.format(number), 'result': result})


def drive(repo, document, script, request=None):
    """Run a session on the script (lines or callables run before the next
    line); the exit code and the messages of the plugin."""
    def reader():
        for item in script:
            if callable(item):
                item()
            else:
                yield item
    out = io.StringIO()
    with repo.active(), contextlib.redirect_stderr(io.StringIO()):
        code = Session(document, request, reader(), out).run()
    messages = [json.loads(text) for text in out.getvalue().splitlines() if text.strip()]
    return code, messages


def asks(messages):
    """The texts of the questions."""
    return [m['params']['text'] for m in messages if m.get('method') == 'ask']


def logs(messages):
    """The lines of the output tab."""
    return [m['params']['text'] for m in messages if m.get('method') == 'log']


def staged_repo():
    """A repository with a commit and the edited diagram staged."""
    repo = Repo()
    document = repo.put(DIAGRAM, LIGHT)
    repo.commit()
    repo.put(DIAGRAM, LIGHT_EDITED)
    repo.git('add', DIAGRAM)
    return repo, document


def main():
    """All the cases; 77 without git."""
    if not git_found():
        print('skipped: no git')
        return SKIP
    failed = 0

    repo, document = staged_repo()
    try:
        code, messages = drive(repo, document, [line(INITIALIZE), answer(1, 'the blinking light')])
        reply = messages[0]
        questions = asks(messages)
        failed += report('accept commits the index', code == EXIT_OK and repo.subject() == 'the blinking light' and
                         reply.get('result') == {'kind': 'supervised', 'controls': []} and
                         questions[0].startswith('Commit 1 staged file(s) to main? The answer is the message.') and
                         'M  ' + DIAGRAM in questions[0] and
                         messages[-1]['params']['status'] == 'finished', messages)
    finally:
        repo.cleanup()

    repo, document = staged_repo()
    try:
        count = repo.count()
        code, messages = drive(repo, document, [line(INITIALIZE), answer(1, action='decline')])
        failed += report('decline commits nothing', code == EXIT_DECLINED and repo.count() == count and
                         'declined: nothing is committed' in logs(messages), messages)
        code, messages = drive(repo, document, [line(INITIALIZE), answer(1, '   '), answer(2, 'second try')])
        failed += report('an empty answer asked again', code == EXIT_OK and len(asks(messages)) == 2 and
                         repo.subject() == 'second try', messages)
    finally:
        repo.cleanup()

    repo, document = staged_repo()
    try:
        count = repo.count()
        shutdown = line({'jsonrpc': '2.0', 'id': 7, 'method': 'shutdown'})
        code, messages = drive(repo, document, [line(INITIALIZE), shutdown])
        failed += report('a shutdown during the question', code == EXIT_DECLINED and repo.count() == count and
                         {'jsonrpc': '2.0', 'id': 7, 'result': {}} in messages, messages)
        code, messages = drive(repo, document, [line(INITIALIZE)])
        failed += report('the end of the input', code == EXIT_DECLINED and repo.count() == count, messages)
        other = repo.put('notes.txt', LIGHT)

        def stage_other():
            repo.git('add', os.path.basename(other))
        code, messages = drive(repo, document, [line(INITIALIZE), stage_other, answer(1, 'two files'),
                                                answer(2, 'two files')])
        questions = asks(messages)
        failed += report('a changed index asked again', code == EXIT_OK and len(questions) == 2 and
                         questions[1].startswith('Commit 2 staged file(s)') and
                         'the index changed while asking' in logs(messages), messages)
        code, messages = drive(repo, document, [line(INITIALIZE)])
        failed += report('nothing staged', code == EXIT_NOTHING_STAGED and
                         any('nothing is staged' in text for text in logs(messages)), messages)
        repo.put(DIAGRAM, LIGHT)
        repo.git('add', DIAGRAM)
        request = os.path.join(repo.tmp, 'request.json')
        with open(request, 'w', encoding='utf-8') as file:
            json.dump({'document': {'path': document, 'modified': True}}, file)
        code, messages = drive(repo, document, [line(INITIALIZE), answer(1, 'with edits')], request)
        failed += report('the unsaved edits noted', code == EXIT_OK and
                         'light.graphml has unsaved edits: they are not committed.' in asks(messages)[0], messages)
        repo.put(DIAGRAM, LIGHT_EDITED)
        repo.git('add', DIAGRAM)
        repo.env[LANGUAGE_VARIABLE] = 'ru'
        code, messages = drive(repo, document, [line(INITIALIZE), answer(1, 'in russian')])
        failed += report('the question in Russian', code == EXIT_OK and
                         asks(messages)[0].startswith('Зафиксировать файлы индекса (1) в main?') and
                         messages[-1]['params']['text'].startswith('зафиксировано: '), messages)
    finally:
        repo.cleanup()
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
