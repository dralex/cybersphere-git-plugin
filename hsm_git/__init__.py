# -----------------------------------------------------------------------------
#  The CyberiadaPro git plugin
#
#  The package: the version, the exit codes, the errors
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

"""The git plugin of CyberiadaPro (docs/API.md): stage, unstage, the commit of
the index after a question, the diff of a diagram against a revision."""

__version__ = '0.1.0'

# the exit codes (docs/API.md, The command line)
EXIT_OK = 0
EXIT_DECLINED = 1
EXIT_USAGE = 2
EXIT_NOTHING_STAGED = 3
EXIT_FAILED = 4


class GitError(Exception):
    """A failed git call, a refused input or an unreadable diagram: the one
    line printed, the exit code and git's own stderr."""

    def __init__(self, message, code=EXIT_FAILED, details=''):
        super().__init__(message)
        self.code = code
        self.details = details
