# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The diff of a diagram against a revision as text, the revision file of a
#  diff tab
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

"""The revision file of a diagram, the documents of a diff, its text and its
findings, the listing (docs/API.md, The text of a diff). The library pairs the
elements, this module only writes the pairs."""

import json
import os
import tempfile

from hsm_git import GitError
from hsm_git.repo import Repository

WORKING = 'working'
NO_FILE = '/dev/null'
# the index as the base: its label in the header, its name in the text
INDEX = 'index'
INDEX_NAME = 'the index'
REVISION_FILE = 'revision.graphml'
# the editor's own metainformation, written at every save: the view state and
# the marker of the stored region frames; shown with the geometry only, as the
# diff tab of the editor does
EDITOR_VIEW = 'cyberiadaEditorView'
REGION_GEOMETRY = 'regionGeometry'
GEOMETRY_META = (EDITOR_VIEW, REGION_GEOMETRY)
CONTEXT = '  '
REMOVED = '- '
ADDED = '+ '
INDENT = '  '
# the findings of the editor (PLUGIN-API.md, The diagnostics file)
SEVERITY = 'info'
RULES = {CONTEXT: 'changed', ADDED: 'added', REMOVED: 'removed'}


def binding():
    """The CyberiadaML module with the revision diff."""
    try:
        import CyberiadaML  # pylint: disable=import-outside-toplevel
    except ImportError as error:
        raise GitError('the diff needs the CyberiadaML module of python3-libcyberiadamlpp 1.2') from error
    if not hasattr(CyberiadaML.Document, 'diff'):
        raise GitError('the diff needs python3-libcyberiadamlpp 1.2 with Document.diff')
    return CyberiadaML


def load(path):
    """The document of a file in any format the library reads; a missing or
    an empty file is an empty document."""
    cml = binding()
    if path is None or not os.path.exists(path) or os.path.getsize(path) == 0:
        return cml.Document()
    document = cml.LocalDocument()
    try:
        document.open(path)
    except cml.Exception as error:
        raise GitError('the diagram {} is not read: {}'.format(os.path.basename(path), error)) from error
    return document


def compare(old, new, geometry=False):
    """The DocumentDiff of two documents."""
    return old.diff(new, binding().DiffOptions(geometry=geometry))


def multiline(prefix, value):
    """A text of several lines continued under its first line."""
    lines = (value or '').splitlines() or ['']
    return [prefix + lines[0]] + [' ' * len(prefix) + line for line in lines[1:]]


def number(value):
    """A coordinate as short as it reads."""
    return '{:g}'.format(round(value, 2))


class Side:
    """One document of the diff: its elements and how the line names them."""

    def __init__(self, cml, document, ids):
        self.cml = cml
        self.document = document
        types = cml.ElementType
        self.words = {
            types.elementSM: 'state machine', types.elementSimpleState: 'state',
            types.elementCompositeState: 'state', types.elementSubmachineState: 'submachine',
            types.elementComment: 'comment', types.elementFormalComment: 'formal comment',
            types.elementInitial: 'initial', types.elementFinal: 'final', types.elementChoice: 'choice',
            types.elementTerminate: 'terminate', types.elementShallowHistory: 'shallow history',
            types.elementDeepHistory: 'deep history', types.elementEntryPoint: 'entry point',
            types.elementExitPoint: 'exit point', types.elementTransition: 'transition'}
        self.counts = {}
        for ident in ids:
            element = self.element(ident)
            if element is not None:
                key = self.key(element)
                self.counts[key] = self.counts.get(key, 0) + 1

    def element(self, ident):
        """The element of the id, None for a region or a missing id."""
        return self.document.find_element_by_id(ident) if ident else None

    def key(self, element):
        """The word and the name of an element."""
        name = element.get_name() if element.has_name() else ''
        return self.words.get(element.get_type(), 'element'), name

    def repeated(self, element):
        """The document has another element of the same word and name."""
        return self.counts.get(self.key(element), 0) > 1

    def label(self, element):
        """The element as a line names it: the word and the name."""
        word, name = self.key(element)
        line = word + (' ' + name if name else '')
        return line + (' ({})'.format(element.get_id()) if self.repeated(element) else '')

    def short(self, element):
        """The end of a transition or a link: the name, or the word of an unnamed one."""
        if element is None:
            return '?'
        word, name = self.key(element)
        line = name or word
        return line + (' ({})'.format(element.get_id()) if self.repeated(element) else '')

    def top_level(self, element):
        """The element is a child of its state machine."""
        parent = element.get_parent()
        return parent is None or parent.get_type() == self.cml.ElementType.elementSM

    def ancestors(self, element):
        """The containing states, from the outermost one."""
        chain = []
        while not self.top_level(element):
            element = element.get_parent()
            chain.insert(0, element)
        return chain

    def head(self, element):
        """The line of a node."""
        line = self.label(element)
        if element.get_type() == self.cml.ElementType.elementSubmachineState:
            line += ' -> ' + element.get_submachine_reference()
        return line

    def node_items(self, element, geometry, parent):
        """The lines of a node, grouped: a group differs as a whole."""
        items = []
        types = self.cml.ActionType
        if hasattr(element, 'get_actions'):
            for action in element.get_actions():
                if action.get_type() == types.actionEntry:
                    prefix = 'entry: '
                elif action.get_type() == types.actionExit:
                    prefix = 'exit: '
                else:
                    prefix = action.get_trigger()
                    if action.get_guard():
                        prefix += ' [{}]'.format(action.get_guard())
                    prefix += ': '
                items.append(multiline(prefix, action.get_behavior()))
        if hasattr(element, 'get_body') and element.has_body():
            items.append(multiline('text: ', element.get_body()))
        if parent:
            outer = element.get_parent()
            items.append(['in: ' + ('the top level' if self.top_level(element) else self.label(outer))])
        if hasattr(element, 'has_color') and element.has_color():
            items.append(['color: ' + element.get_color()])
        if geometry:
            items.extend(self.node_geometry(element))
        return items

    def node_geometry(self, element):
        """The place of a node and its id."""
        items = [['id: ' + element.get_id()]]
        if not hasattr(element, 'has_geometry') or not element.has_geometry():
            return items
        if hasattr(element, 'get_geometry_rect'):
            r = element.get_geometry_rect()
            items.append(['at: ' + ', '.join(number(v) for v in (r.x, r.y, r.width, r.height))])
        elif hasattr(element, 'get_geometry_point'):
            p = element.get_geometry_point()
            items.append(['at: ' + ', '.join(number(v) for v in (p.x, p.y))])
        return items

    def transition_head(self, transition):
        """The line of a transition: its ends and its trigger."""
        source = self.element(transition.get_source_element_id())
        target = self.element(transition.get_target_element_id())
        line = 'transition {} -> {}'.format(self.short(source), self.short(target))
        action = transition.get_action() if transition.has_action() else None
        if action is not None and action.get_trigger():
            line += ' [{}]'.format(action.get_trigger())
        return line

    def transition_items(self, transition, geometry):
        """The lines of a transition."""
        items = []
        action = transition.get_action() if transition.has_action() else None
        if action is not None:
            if action.get_guard():
                items.append(['guard: ' + action.get_guard()])
            if action.get_behavior():
                items.append(multiline('do: ', action.get_behavior()))
            if action.has_propagation():
                items.append(['propagation: ' + str(action.get_propagation()).rsplit('.', maxsplit=1)[-1]])
        if hasattr(transition, 'has_color') and transition.has_color():
            items.append(['color: ' + transition.get_color()])
        if geometry:
            items.append(['id: ' + transition.get_id()])
            points = []
            if transition.has_geometry_source_point():
                points.append(transition.get_geometry_source_point())
            if transition.has_geometry_polyline():
                points.extend(transition.get_geometry_polyline())
            if transition.has_geometry_target_point():
                points.append(transition.get_geometry_target_point())
            if points:
                items.append(['route: ' + '; '.join('{}, {}'.format(number(p.x), number(p.y)) for p in points)])
        return items

    def link(self, comment_id, link_id):
        """The line of a comment link; None when the link is not found."""
        comment = self.element(comment_id)
        if comment is None or not hasattr(comment, 'get_subjects'):
            return None
        for subject in comment.get_subjects():
            if subject.get_id() == link_id:
                line = 'link {} -> {}'.format(self.label(comment), self.short(subject.get_element()))
                if subject.has_fragment():
                    line += ': ' + subject.get_fragment()
                return line
        return None


class Writer:
    """The lines of a diff and the counts of its summary."""

    def __init__(self, cml, sides, geometry):
        self.cml = cml
        self.old, self.new = sides
        self.geometry = geometry
        self.lines = []
        self.findings = []
        # the summary: the changed, the added and the removed elements
        self.counts = {CONTEXT: 0, ADDED: 0, REMOVED: 0}

    def finding(self, mark, element, message):
        """A change for the Diagnostics of the editor, linked to an element of
        the compared diagram when it is there."""
        item = {'severity': SEVERITY, 'rule': RULES[mark], 'message': message}
        if element:
            item['element'] = element
        self.findings.append(item)

    def changed(self, element, heads, names):
        """The finding of a changed pair: the old head when it differs, the
        names of the differing lines."""
        message = heads[1] + ' changed'
        if heads[0] != heads[1]:
            message += ' (was {})'.format(heads[0])
        if names:
            message += ': ' + ', '.join(names)
        self.finding(CONTEXT, element, message)

    def visible(self, flags):
        """The differences the text shows: the geometry only when asked for."""
        if not self.geometry:
            flags &= ~(self.cml.diffGeometry | self.cml.diffCollapsed)
        return flags & ~self.cml.diffElements

    def emit(self, mark, level, lines):
        """Lines of one kind at a level of nesting."""
        for line in lines:
            self.lines.append(mark + INDENT * level + line)

    def pair(self, heads, items, level):
        """A changed pair: the context or the changed head, then the differing
        groups, the old ones first; return the names of the differing groups."""
        names = []
        for item in [i for i in items[0] if i not in items[1]] + [i for i in items[1] if i not in items[0]]:
            name = item[0].split(':', 1)[0].strip()
            if name not in names:
                names.append(name)
        if heads[0] == heads[1]:
            self.emit(CONTEXT, level, [heads[1]])
        else:
            self.emit(REMOVED, level, [heads[0]])
            self.emit(ADDED, level, [heads[1]])
        for item in items[0]:
            if item not in items[1]:
                self.emit(REMOVED, level + 1, item)
        for item in items[1]:
            if item not in items[0]:
                self.emit(ADDED, level + 1, item)
        self.counts[CONTEXT] += 1
        return names

    def single(self, mark, head, items, level):
        """An added or a removed element with all its lines."""
        self.emit(mark, level, [head])
        for item in items:
            self.emit(mark, level + 1, item)
        self.counts[mark] += 1

    def machine_header(self, machine, level):
        """The line of a state machine: its name and its rename."""
        flags = self.visible(machine.flags)
        old_sm, new_sm = self.old.element(machine.first), self.new.element(machine.second)
        sm = new_sm or old_sm
        name = sm.get_name() if sm is not None and sm.has_name() else (machine.second or machine.first)
        mark = ADDED if flags & self.cml.diffAdded else REMOVED if flags & self.cml.diffRemoved else CONTEXT
        self.emit(mark, level, ['state machine ' + name])
        renamed = flags & self.cml.diffTitle and old_sm is not None and new_sm is not None
        if renamed:
            self.emit(REMOVED, level + 1, ['name: ' + old_sm.get_name()])
            self.emit(ADDED, level + 1, ['name: ' + new_sm.get_name()])
        if not flags:
            return
        element = new_sm.get_id() if new_sm is not None else None
        if mark == CONTEXT:
            self.changed(element, ('state machine ' + name,) * 2, ['name'] if renamed else [])
        else:
            self.finding(mark, element if mark == ADDED else None, 'state machine {} {}'.format(name, RULES[mark]))

    def node(self, entry, flags, level, shown):
        """A node with the states holding it as the context."""
        side = self.new if entry.second else self.old
        element = side.element(entry.second or entry.first)
        if element is None:
            return    # a region: its state shows the change
        for outer in side.ancestors(element):
            if (side is self.new, outer.get_id()) not in shown:
                shown.add((side is self.new, outer.get_id()))
                self.emit(CONTEXT, level + len(side.ancestors(outer)), [side.head(outer)])
        shown.add((side is self.new, element.get_id()))
        depth = level + len(side.ancestors(element))
        if flags & (self.cml.diffAdded | self.cml.diffRemoved):
            mark = ADDED if flags & self.cml.diffAdded else REMOVED
            self.single(mark, side.head(element), side.node_items(element, self.geometry, False), depth)
            self.finding(mark, element.get_id() if mark == ADDED else None,
                         '{} {}'.format(side.head(element), RULES[mark]))
            return
        first = self.old.element(entry.first)
        moved = bool(flags & self.cml.diffParent)
        heads = (self.old.head(first), self.new.head(element))
        names = self.pair(heads, (self.old.node_items(first, self.geometry, moved),
                                  self.new.node_items(element, self.geometry, moved)), depth)
        self.changed(element.get_id(), heads, names)

    def transition(self, entry, flags, level):
        """A transition."""
        if flags & (self.cml.diffAdded | self.cml.diffRemoved):
            side = self.new if flags & self.cml.diffAdded else self.old
            mark = ADDED if side is self.new else REMOVED
            t = side.element(entry.second or entry.first)
            self.single(mark, side.transition_head(t), side.transition_items(t, self.geometry), level)
            self.finding(mark, t.get_id() if mark == ADDED else None,
                         '{} {}'.format(side.transition_head(t), RULES[mark]))
            return
        t1, t2 = self.old.element(entry.first), self.new.element(entry.second)
        heads = (self.old.transition_head(t1), self.new.transition_head(t2))
        names = self.pair(heads, (self.old.transition_items(t1, self.geometry),
                                  self.new.transition_items(t2, self.geometry)), level)
        self.changed(t2.get_id(), heads, names)

    def link(self, entry, level):
        """A comment link."""
        head1 = self.old.link(entry.first_comment, entry.first) if entry.first else None
        head2 = self.new.link(entry.second_comment, entry.second) if entry.second else None
        if head1 is None and head2 is not None:
            self.single(ADDED, head2, [], level)
            self.finding(ADDED, entry.second, head2 + ' added')
        elif head1 is not None and head2 is None:
            self.single(REMOVED, head1, [], level)
            self.finding(REMOVED, None, head1 + ' removed')
        elif head1 is not None:
            self.pair((head1, head2), ([], []), level)
            self.changed(entry.second, (head1, head2), [])

    def machine(self, machine, header):
        """The lines of one state machine: the nodes in the order of the diff,
        then the transitions, then the comment links."""
        level = 0
        if header:
            self.machine_header(machine, level)
            level = 1
        shown = set()
        entries = [(entry, self.visible(entry.flags)) for entry in machine.elements]
        entries = [(entry, flags) for entry, flags in entries if flags]
        for entry, flags in entries:
            if entry.kind == self.cml.diffKindNode:
                self.node(entry, flags, level, shown)
        for entry, flags in entries:
            if entry.kind == self.cml.diffKindTransition:
                self.transition(entry, flags, level)
        for entry, flags in entries:
            if entry.kind == self.cml.diffKindCommentLink:
                self.link(entry, level)

    def meta(self, result):
        """The differing metainformation, last."""
        entries = [m for m in result.meta if self.geometry or m.name not in GEOMETRY_META]
        if not entries:
            return
        self.emit(CONTEXT, 0, ['meta'])
        for m in entries:
            if m.in_first:
                self.emit(REMOVED, 1, ['{}: {}'.format(m.name, m.first)])
            if m.in_second:
                self.emit(ADDED, 1, ['{}: {}'.format(m.name, m.second)])
        self.counts[CONTEXT] += 1
        names = []
        for m in entries:
            if m.name not in names:
                names.append(m.name)
        self.changed(None, ('meta', 'meta'), names)


def text(old, new, result, revision, geometry=False, findings=None):
    """The lines of the diff of two documents after the header: the elements
    and the summary; the findings are appended to the list findings."""
    cml = binding()
    ids1 = [e.first for m in result.machines for e in m.elements if e.first]
    ids2 = [e.second for m in result.machines for e in m.elements if e.second]
    out = Writer(cml, (Side(cml, old, ids1), Side(cml, new, ids2)), geometry)
    several = len(result.machines) > 1
    for machine in result.machines:
        sm_flags = out.visible(machine.flags)
        if not sm_flags and not any(out.visible(e.flags) for e in machine.elements):
            continue
        out.machine(machine, several or bool(sm_flags))
    out.meta(result)
    if any(out.counts.values()):
        out.lines.append('{} changed, {} added, {} removed'.format(out.counts[CONTEXT], out.counts[ADDED],
                                                                  out.counts[REMOVED]))
    else:
        out.lines.append('no changes since {}'.format(revision))
    if findings is not None:
        findings.extend(out.findings)
    return out.lines


def write_findings(path, findings):
    """The diagnostics file of the editor."""
    try:
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(findings, file, ensure_ascii=False, indent=1)
            file.write('\n')
    except OSError as error:
        raise GitError('the findings are not written: {}'.format(error)) from error


def base(repo, revision, out):
    """Write the diagram of the revision into out, an empty file when the
    revision lacks it; return its path in the repository, or None. Needs no
    CyberiadaML."""
    path = None
    # a repository without a commit has an empty HEAD
    if revision != 'HEAD' or repo.has_commits:
        path = repo.blob(repo.revision(revision), out)
    if path is None:
        with open(out, 'wb'):
            pass
    return path


def base_index(repo, out):
    """Write the diagram as the index stages it into out, an empty file when
    the index lacks it; return its path, or None."""
    path = repo.index_blob(out)
    if path is None:
        with open(out, 'wb'):
            pass
    return path


def fetch(repo, revision, index, out):
    """Write the base of a diff into out - the revision, or the index; return
    its path (None without the file), its label and its name."""
    if index:
        return base_index(repo, out), INDEX, INDEX_NAME
    return base(repo, revision, out), revision, revision


def header(repo, path, label, name):
    """The first line of a diff."""
    if path is None:
        return '--- {} ({} is not in {})'.format(NO_FILE, repo.path, name)
    return '--- {}:{}'.format(label, path)


def write_revision(document, output, revision='HEAD', index=False):
    """Write the diagram as the revision or the index has it into output, the
    base of a diff tab of the editor (docs/ARCHITECTURE.md, The compare)."""
    repo = Repository.locate(document)
    try:
        path, label, name = fetch(repo, revision, index, output)
    except OSError as error:
        raise GitError('the revision file is not written: {}'.format(error)) from error
    if path is None:
        print('{} is not in {}'.format(repo.path, name))
    else:
        print('{}:{}'.format(label, path))


def run(document, current=None, revision='HEAD', geometry=False, diagnostics=None, index=False):
    """Print the changes of the diagram (the file, or current: the editor's
    copy) since the revision or against the index; write their findings into
    diagnostics."""
    binding()
    repo = Repository.locate(document)
    with tempfile.TemporaryDirectory() as tmp:
        blob = os.path.join(tmp, REVISION_FILE)
        path, label, name = fetch(repo, revision, index, blob)
        print(header(repo, path, label, name))
        print('+++ ' + WORKING)
        old = load(blob)
        new = load(current if current is not None else document)
        findings = []
        for line in text(old, new, compare(old, new, geometry), name, geometry, findings):
            print(line)
    if diagnostics is not None:
        write_findings(diagnostics, findings)
