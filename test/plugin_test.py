# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The editor plugin, installed and run through the batch mode of CyberiadaPro
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

"""The plugin: its installation and its texts, then in the editor Stage, the
diff, the compare and the commit session from a session script; the editor
part is skipped without a CyberiadaPro binary that starts (CYBERIADA_PRO, PATH,
or the sibling build) or with one before the git token (EDIT-PLUG-55) or the
diff tabs (EDIT-PLUG-58), which rejects the plugin."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from testenv import Repo, report, git_found, binding_diff, write_text, SKIP, REPOSITORY, TEST_DIR, LIGHT, LIGHT_EDITED, DIAGRAM
from testenv import NOTES, NOTES_TEXT, NOTES_EDITED

import hsm_git.plugin  # pylint: disable=wrong-import-position,wrong-import-order

PLUGIN = hsm_git.plugin.PLUGIN_ID
TIMEOUT_S = 120
SESSION_DIR = os.path.join(REPOSITORY, 'test', 'session')
GOOD_COMPARE = os.path.join(TEST_DIR, 'good', 'compare-light.txt')


def installer():
    """The copy of the plugin into a folder: pinned to this Python, replaced
    on a second install, a foreign folder refused."""
    failed = 0
    with tempfile.TemporaryDirectory() as directory:
        folder = hsm_git.plugin.install(directory)
        with open(os.path.join(folder, hsm_git.plugin.DESCRIPTOR), encoding='utf-8') as file:
            descriptor = json.load(file)
        actions = descriptor['actions'] + descriptor.get('session', {}).get('actions', [])
        ok = (folder == os.path.join(directory, PLUGIN) and 'interpreter' not in descriptor and
              all(a['argv'][0] == sys.executable for a in actions) and
              descriptor['env'].get('PYTHONPATH') == REPOSITORY and
              os.path.isfile(os.path.join(folder, 'i18n', 'ru.json')) and
              os.path.isfile(os.path.join(folder, 'icons', 'git.svg')))
        failed += report('install', ok, descriptor)
        failed += report('install twice', hsm_git.plugin.install(directory) == folder)
        foreign = os.path.join(directory, 'other')
        os.makedirs(os.path.join(foreign, PLUGIN))
        try:
            hsm_git.plugin.install(foreign)
            refused = False
        except hsm_git.plugin.PluginError:
            refused = True
        failed += report('a foreign folder refused', refused)
    return failed


def translation():
    """The Russian texts: every key a text of the descriptor, every text translated."""
    with open(os.path.join(REPOSITORY, 'editor-plugin', 'plugin.json'), encoding='utf-8') as file:
        descriptor = json.load(file)
    with open(os.path.join(REPOSITORY, 'editor-plugin', 'i18n', 'ru.json'), encoding='utf-8') as file:
        ru = json.load(file)
    texts = {descriptor['name'], descriptor.get('description', '')}
    sessions = descriptor.get('session', {}).get('actions', [])
    for item in descriptor.get('parameters', []) + descriptor['actions'] + sessions:
        texts.update([item.get('label', ''), item.get('description', ''), item.get('reason', '')])
        texts.update(item.get('choices', []))
    texts.discard('')
    stale = sorted(set(ru) - texts)
    missing = sorted(texts - set(ru))
    return report('translation', not stale and not missing, 'stale {} missing {}'.format(stale, missing))


def environment(profile, repo):
    """A private profile, the repository's git configuration; the plugin's
    python3 finds the modules of this repository."""
    python_dir = os.path.dirname(sys.executable)
    path = python_dir + os.pathsep + os.environ.get('PATH', '')
    pythonpath = os.pathsep.join(p for p in (REPOSITORY, os.environ.get('PYTHONPATH')) if p)
    return dict(os.environ, QT_QPA_PLATFORM='offscreen', PATH=path, PYTHONPATH=pythonpath,
                CYBERIADA_PRO_PLUGIN_PATH='',
                XDG_CONFIG_HOME=os.path.join(profile, 'config'),
                XDG_DATA_HOME=os.path.join(profile, 'data'), **repo.env)


def starts(path, env):
    """The binary runs here."""
    try:
        result = subprocess.run([path, '--help'], env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, check=False, timeout=TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def editor(env):
    """The CyberiadaPro binary, None without one that starts."""
    candidates = [os.environ.get('CYBERIADA_PRO'), shutil.which('CyberiadaPro'),
                  os.path.join(REPOSITORY, '..', 'CyberiadaHSM-Editor', 'build', 'CyberiadaPro')]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK) and starts(path, env):
            return path
    return None


def batch(binary, env, *args):
    """A batch run of the editor from this repository: the exit code and the output."""
    result = subprocess.run([binary, '--batch'] + list(args), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True, env=env,
                            cwd=REPOSITORY, check=False, timeout=TIMEOUT_S)
    return result.returncode, result.stdout


def section(out, name):
    """The lines of a section of a batch dump."""
    lines, inside = [], False
    for line in out.splitlines():
        if line.startswith('== '):
            inside = line == '== ' + name
        elif inside:
            lines.append(line)
    return lines


def counts(lines):
    """The changed, added and removed counts of a summary line of either diff."""
    for line in lines:
        found = re.search(r'(\d+) changed, (\d+) added, (\d+) removed', line)
        if found is None:
            found = re.search(r'changed: (\d+), added: (\d+), removed: (\d+)', line)
        if found is not None:
            return tuple(int(n) for n in found.groups())
    return None


def compare_part(binary, env, repo, document):
    """The compare: the revision as the base of a diff tab, its pairs those of
    the text diff; the failures."""
    failed = 0
    run = ['--plugin-path', '.', '--run-plugin']
    code, out = batch(binary, env, document, *run, PLUGIN + ':compare', '--dump', '--dump-tabs')
    diff = section(out, 'diff')
    with open(GOOD_COMPARE, encoding='utf-8') as file:
        good = file.read().splitlines()
    failed += report('the compare', code == 0 and diff == good and
                     '1 light.graphml ↔ HEAD diff active' in section(out, 'tabs') and
                     'stdout:' in section(out, 'plugin') and '  HEAD:' + DIAGRAM in section(out, 'plugin'), out)
    if binding_diff():
        code, text = batch(binary, env, document, *run, PLUGIN + ':diff', '--dump-plugin')
        failed += report('the compare pairs those of the text diff', code == 0 and counts(diff) is not None and
                         counts(diff) == counts(section(text, 'plugin')), out + text)
    code, out = batch(binary, env, document, *run, PLUGIN + ':compare', '--plugin-param', 'revision=nope', '--dump-plugin')
    failed += report('the compare with a missing revision', code != 0 and "'nope' is not found" in out and
                     'state: failed' in out, out)
    # the index as HEAD: the pairs of the compare, the base named by the action
    repo.git('reset', '-q', '--', DIAGRAM)
    code, out = batch(binary, env, document, *run, PLUGIN + ':compare-index', '--dump', '--dump-tabs')
    repo.git('add', DIAGRAM)
    index_good = ['base: Compare with the Index' if line == 'base: HEAD' else line for line in good]
    failed += report('the compare with the index', code == 0 and section(out, 'diff') == index_good and
                     '1 light.graphml ↔ Compare with the Index diff active' in section(out, 'tabs') and
                     '  index:' + DIAGRAM in section(out, 'plugin'), out)
    return failed


def text_part(binary, env, repo):
    """A Markdown file in a text tab: staged, its line diff and findings, no
    compare; the failures."""
    failed = 0
    notes = write_text(repo.path(NOTES), NOTES_TEXT)
    run = ['--plugin-path', '.', '--run-plugin']
    code, out = batch(binary, env, notes, *run, PLUGIN + ':stage', '--dump-plugin', '--dump-tabs')
    failed += report('stage a text', code == 0 and '0 notes.md markdown active' in section(out, 'tabs') and
                     'A  ' + NOTES in out, out)
    repo.commit('notes')
    code, out = batch(binary, env, notes, *run, PLUGIN + ':history', '--dump-plugin')
    failed += report('the history of a text', code == 0 and
                     any(line.endswith('  Test  notes') for line in section(out, 'plugin')), out)
    write_text(notes, NOTES_EDITED)
    code, out = batch(binary, env, notes, *run, PLUGIN + ':diff', '--dump-plugin')
    failed += report('the line diff of a text and its findings', code == 0 and '  +the light blinks' in out and
                     'info changed - line 3: lines 3-4 changed' in section(out, 'diagnostics'), out)
    code, out = batch(binary, env, notes, *run, PLUGIN + ':compare', '--dump-plugin')
    failed += report('no compare of a text', code != 0 and 'the action works in: HSM diagram' in out, out)
    return failed


def editor_part(binary, env, repo):
    """The plugin in the editor; the failures."""
    failed = 0
    document = repo.put(DIAGRAM, LIGHT)
    run = ['--plugin-path', '.', '--run-plugin']
    code, out = batch(binary, env, document, *run, PLUGIN + ':stage', '--dump-plugin')
    failed += report('stage', code == 0 and 'A  ' + DIAGRAM in out and
                     repo.git('diff', '--cached', '--name-only').strip() == DIAGRAM, out)
    session = ['--session-script', os.path.join(SESSION_DIR, 'commit.session'), '--dump-session']
    code, out = batch(binary, env, document, *run, PLUGIN + ':commit-session', *session)
    failed += report('the commit session', code == 0 and repo.subject() == 'the blinking light', out)
    repo.put(DIAGRAM, LIGHT_EDITED)
    repo.git('add', DIAGRAM)
    count = repo.count()
    session = ['--session-script', os.path.join(SESSION_DIR, 'decline.session'), '--dump-session']
    code, out = batch(binary, env, document, *run, PLUGIN + ':commit-session', *session)
    failed += report('the declined commit', code == 0 and repo.count() == count, out)
    failed += compare_part(binary, env, repo, document)
    if binding_diff():
        code, out = batch(binary, env, document, *run, PLUGIN + ':diff', '--dump-plugin')
        failed += report('the diff', code == 0 and 'transition Red -> Yellow [TICK]' in out and
                         '+ state Blink' in out, out)
        findings = section(out, 'diagnostics')
        failed += report('the findings of the diff', 'count: 12' in findings and
                         'info added n3: state Blink added' in findings and
                         'info removed -: state Green removed' in findings, out)
    else:
        print('skipped the diff in the editor: no CyberiadaML with Document.diff')
    outside = os.path.join(repo.outside, 'light.graphml')
    shutil.copyfile(LIGHT, outside)
    code, out = batch(binary, env, outside, *run, PLUGIN + ':diff', '--dump-plugin')
    failed += report('a file outside a work tree refused by the editor', code != 0 and
                     'error: the document is not in a git repository' in out, out)
    code, out = batch(binary, env, outside, *run, PLUGIN + ':stage', '--dump-plugin')
    failed += report('the reason of Stage', code != 0 and 'error: Save the file of a git work tree' in out, out)
    failed += text_part(binary, env, repo)
    return failed


def main():
    """All the cases; 77 without git."""
    if not git_found():
        print('skipped: no git')
        return SKIP
    failed = installer() + translation()
    repo = Repo()
    try:
        with tempfile.TemporaryDirectory() as profile:
            env = environment(profile, repo)
            binary = editor(env)
            if binary is None:
                print('skipped the editor part: no CyberiadaPro binary')
                return 1 if failed else 0
            _, out = batch(binary, env, '--plugin-path', '.', '--list-plugins')
            if 'needs a newer editor' in out or 'session: commit-session' not in out:
                print('skipped the editor part: the editor has no git token or no sessions\n' + out)
                return 1 if failed else 0
            failed += editor_part(binary, env, repo)
    finally:
        repo.cleanup()
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
