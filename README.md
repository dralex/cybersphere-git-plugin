# CyberiadaPro git plugin

The git plugin of CyberiadaPro, the Cyberiada HSM diagram editor: it stages
and unstages the open diagram, commits the index after showing the branch and
the staged files, and shows what changed in the diagram since a revision -
state by state and transition by transition, the unsaved edits included. The
plugin is written in Python 3 and runs git; the diagrams are compared by the
document diff of libcyberiadaml.

The code is distributed under the Lesser GNU Public License (version 3), the
documentation -- under the GNU Free Documentation License (version 1.3).

## Documentation

The documentation is located in the `docs` directory and contains:

* The architecture - `ARCHITECTURE.md`: the conditions of the actions, the
  repository of a document, stage and unstage, the commit question, the diff
* The interface - `API.md`: the command line, the exit codes, the text of a
  diff, the commit session, the modules

## The editor plugin

Plugins > Git:

| Action | Does |
|---|---|
| Stage | `git add` of the saved diagram |
| Unstage | takes the diagram out of the index, the file kept |
| Commit... | lists the branch and the staged files, asks the message, commits the whole index |
| Changes Since a Revision... | prints the changed states, transitions, comments and metadata since the revision (`HEAD` by default) |

The editor greys the actions out unless git is installed and the diagram is a
file of a git work tree; Stage also needs the diagram saved.

## Usage

    hsm-git diff diagrams/light.graphml --revision=HEAD~1
    hsm-git stage diagrams/light.graphml

## Tests

    cd test && python3 run.py && python3 session_test.py && python3 plugin_test.py

The tests make temporary repositories with a git configuration of their own,
drive the commit session over its pipes and run the plugin in the batch mode
of CyberiadaPro (skipped without the editor).

## Requirements

* python3 (version 3.8+)
* git (version 2.23+)
* the `CyberiadaML` module with `Document.diff`: libcyberiadamlpp-py
  (version 1.1.0+, with its libraries) - for the diff
* CyberiadaPro with the plugin conditions (the `git` token) and the sessions
