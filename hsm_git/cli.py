# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The command line: hsm-git
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

"""hsm-git: stage, unstage, commit and diff of a diagram, the revision file of
a diff tab (docs/API.md, The command line)."""

import argparse
import os
import sys

from hsm_git import __version__, GitError, EXIT_OK, EXIT_USAGE, EXIT_FAILED
from hsm_git import actions


def parser():
    """The arguments of hsm-git."""
    main_parser = argparse.ArgumentParser(
        prog='hsm-git', description='The git plugin of CyberiadaPro: stage, unstage, commit and diff of a diagram')
    main_parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    main_parser.add_argument('--install-editor-plugin', nargs='?', const='', metavar='DIR',
                             help='copy the editor plugin into DIR or the user plugin folder of CyberiadaPro')
    commands = main_parser.add_subparsers(dest='command', metavar='command')
    stage = commands.add_parser('stage', help='git add of the diagram')
    stage.add_argument('document')
    unstage = commands.add_parser('unstage', help='the diagram out of the index, its file kept')
    unstage.add_argument('document')
    commit = commands.add_parser('commit', help='commit the index')
    commit.add_argument('document')
    how = commit.add_mutually_exclusive_group(required=True)
    how.add_argument('--message-file', metavar='FILE', help='the first line of FILE is the message')
    how.add_argument('--session', action='store_true', help='the commit session of the editor')
    commit.add_argument('--request', metavar='FILE', help='the request.json of the editor')
    diff = commands.add_parser('diff', help='the changes of the diagram since a revision')
    diff.add_argument('document')
    diff.add_argument('--current', metavar='FILE', help='the diagram to compare, the file by default')
    diff.add_argument('--revision', default='HEAD', help='the revision, HEAD by default')
    diff.add_argument('--geometry', action='store_true', help='the geometry, the ids and the view state too')
    diff.add_argument('--diagnostics', metavar='FILE', help='also write the changes as the findings of the editor')
    revision = commands.add_parser('revision', help='the diagram as a revision has it, into a file')
    revision.add_argument('document')
    revision.add_argument('--revision', default='HEAD', help='the revision, HEAD by default')
    revision.add_argument('--output', metavar='FILE', required=True,
                          help='the file to write, empty when the revision lacks the diagram')
    return main_parser


def install(target):
    """--install-editor-plugin [DIR]."""
    from hsm_git import plugin  # pylint: disable=import-outside-toplevel
    try:
        folder = plugin.install(target or None)
    except plugin.PluginError as error:
        sys.stderr.write('hsm-git: {}\n'.format(error))
        return EXIT_FAILED
    print('the editor plugin is installed into {}'.format(folder))
    return EXIT_OK


def run(args):
    """One command; the errors are raised."""
    if args.command == 'stage':
        actions.stage(args.document)
    elif args.command == 'unstage':
        actions.unstage(args.document)
    elif args.command == 'commit' and args.session:
        from hsm_git import session  # pylint: disable=import-outside-toplevel
        return session.run(args.document, args.request)
    elif args.command == 'commit':
        actions.commit(args.document, args.message_file)
    elif args.command == 'diff':
        from hsm_git import diff  # pylint: disable=import-outside-toplevel
        diff.run(args.document, args.current, args.revision, args.geometry, args.diagnostics)
    elif args.command == 'revision':
        from hsm_git import diff  # pylint: disable=import-outside-toplevel
        diff.write_revision(args.document, args.output, args.revision)
    return EXIT_OK


def main(argv=None):
    """hsm-git."""
    args = parser().parse_args(argv)
    if args.install_editor_plugin is not None:
        return install(args.install_editor_plugin)
    if not args.command:
        parser().print_usage(sys.stderr)
        return EXIT_USAGE
    try:
        return run(args)
    except GitError as error:
        sys.stdout.flush()
        details = error.details.strip()
        if details:
            sys.stderr.write(details + '\n')
        sys.stderr.write('git: {}: {}\n'.format(os.path.basename(args.document), error))
        return error.code
