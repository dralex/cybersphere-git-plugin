# CyberiadaPro git plugin

The git plugin of CyberiadaPro, the Cyberiada HSM diagram editor: it stages
and unstages the open diagram, commits the index after showing the branch and
the staged files, and shows what changed in the diagram since a revision -
state by state and transition by transition, the unsaved edits included, as
text or side by side in a diff tab of the editor. The
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
| Changes Since a Revision... | prints the changed states, transitions, comments and metadata since the revision (`HEAD` by default); the Diagnostics dock lists them, a click selects the element |
| Compare with a Revision... | opens a diff tab: the revision and the diagram with its unsaved edits side by side, the changes marked; Document > Refresh compares again |
| Compare with the Index | the same diff tab with the staged diagram as the base: what the commit takes against the edits |
| History | the last commits of the file, a rename followed: the revisions to compare with |

The editor greys the actions out unless git is installed and the document is
a file of a git work tree; Stage also needs it saved. In a text tab (plain
text, Markdown, C, C++, C#, Python) Stage, Unstage, Commit..., History and
Changes Since a Revision... work on the text, the changes line by line; the
compares need a diagram, in an HSM, FA or inspection tab, and an editor with
the diff tabs.

## Installation

The Debian package - the module `hsm_git`, `hsm-git`, the editor plugin in
`/usr/share/cyberiada-pro/plugins/git` and the documentation:

    cmake -B build && cd build && ctest && cpack -G DEB
    sudo apt install ./python3-cybersphere-git_0.1.0_all.deb

With pip, then the plugin copied into the user plugin folder of the editor,
bound to that Python:

    pip install /path/to/cybersphere-git-plugin
    hsm-git --install-editor-plugin

`CyberiadaPro --plugin-path /path/to/cybersphere-git-plugin` finds the plugin
in the source tree without a copy; then `python3` needs the repository and the
`CyberiadaML` module on its path.

## Usage

    hsm-git diff diagrams/light.graphml --revision=HEAD~1
    hsm-git revision diagrams/light.graphml --revision=HEAD~1 --output light-old.graphml
    hsm-git diff diagrams/light.graphml --index
    hsm-git history diagrams/light.graphml --count 10
    hsm-git stage diagrams/light.graphml

## git diff on the command line

`hsm-git textconv` lets `git diff` and `git log -p` show a diagram by its
states, transitions and comments instead of its GraphML lines:

    echo '*.graphml diff=cyberiada' >> .gitattributes
    git config diff.cyberiada.textconv "hsm-git textconv"
    git config diff.cyberiada.cachetextconv true

## Tests

    cmake -B build && cd build && ctest

The tests make temporary repositories with a git configuration of their own,
drive the commit session over its pipes and run the plugin in the batch mode
of CyberiadaPro (skipped without the editor).

## Requirements

* python3 (version 3.8+)
* git (version 2.23+)
* the `CyberiadaML` module with `Document.diff`: libcyberiadamlpp-py
  (version 1.2.0+, with its libraries) - for the diff
* cmake (version 3.16+) - for the Debian package
* CyberiadaPro with the plugin conditions (the `git` token) and the sessions
