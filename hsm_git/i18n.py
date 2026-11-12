# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The language of the run and the catalogs of its messages
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

"""The messages of the run in the language of the editor (docs/ARCHITECTURE.md,
The messages): the English format string is the key."""

import os

# set by the editor for every run (PLUGIN-API.md, The command line)
LANGUAGE_VARIABLE = 'CYBERIADA_PRO_LANGUAGE'

RU = {
    # the repository
    'detached at {}': 'отсоединённый HEAD на {}',
    '{} is not in a git work tree': '{} не в рабочем дереве git',
    'the path in the repository is not found': 'путь в репозитории не найден',
    "the revision '{}' is refused": "ревизия '{}' отклонена",
    "the revision '{}' is not found": "ревизия '{}' не найдена",
    'the index is not read': 'индекс не прочитан',
    'the status is not read': 'состояние не прочитано',
    'the renames are not read': 'переименования не прочитаны',
    'the file of the revision is not read': 'файл ревизии не прочитан',
    'the history is not read': 'история не прочитана',
    '{} is unmerged: resolve the conflict first': '{} не слит: сначала разрешите конфликт',
    'the file of the index is not read': 'файл индекса не прочитан',
    'git does not start: {}': 'git не запускается: {}',
    # the actions
    '{} has no changes': 'в {} нет изменений',
    '{} is not staged': '{} не добавлен в индекс',
    'nothing to unstage': 'нечего убирать из индекса',
    '{} is not unstaged': '{} не убран из индекса',
    'nothing is staged: stage the files first': 'индекс пуст: сначала добавьте файлы',
    'the message is not read: {}': 'сообщение не прочитано: {}',
    'the commit message is empty': 'сообщение коммита пусто',
    'Committing {} staged file(s) to {}:': 'Фиксация файлов индекса ({}) в {}:',
    'the commit failed': 'коммит не выполнен',
    'the commit is not read': 'коммит не прочитан',
    '{} has no commits': 'у {} нет коммитов',
    # the diffs
    'the diff needs the CyberiadaML module of python3-libcyberiadamlpp 1.2':
        'для сравнения нужен модуль CyberiadaML из python3-libcyberiadamlpp 1.2',
    'the diff needs python3-libcyberiadamlpp 1.2 with Document.diff':
        'для сравнения нужен python3-libcyberiadamlpp 1.2 с Document.diff',
    'the diagram {} is not read: {}': 'диаграмма {} не прочитана: {}',
    'the text {} is not read: {}': 'текст {} не прочитан: {}',
    'the findings are not written: {}': 'замечания не записаны: {}',
    'the revision file is not written: {}': 'файл ревизии не записан: {}',
    '{} is not in {}': '{} нет в {}',
    '{} is not in the index': '{} нет в индексе',
    # the commit session
    'Commit {} staged file(s) to {}? The answer is the message.':
        'Зафиксировать файлы индекса ({}) в {}? Ответ — сообщение коммита.',
    '... and {} more': '... и ещё {}',
    '{} has unsaved edits: they are not committed.': 'в {} есть несохранённые правки: они не войдут в коммит.',
    'reading the index': 'чтение индекса',
    'declined: nothing is committed': 'отклонено: ничего не зафиксировано',
    'the message is empty': 'сообщение пусто',
    'the index changed while asking': 'индекс изменился во время вопроса',
    'committing': 'фиксация',
    'committed {}': 'зафиксировано: {}',
}

CATALOGS = {'ru': RU}


def language():
    """The language of the run: ru of ru or ru_RU, empty without one."""
    return os.environ.get(LANGUAGE_VARIABLE, '').split('_')[0].lower()


def tr(text):
    """The text in the language of the run, the English one without a
    translation."""
    return CATALOGS.get(language(), {}).get(text, text)
