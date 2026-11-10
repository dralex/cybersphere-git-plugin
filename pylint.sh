#!/bin/bash

FILES="hsm_git test/run.py test/session_test.py test/plugin_test.py test/testenv.py"
pylint --disable=I1101,C0301,W0703 $FILES
