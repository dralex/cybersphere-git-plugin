cmake_minimum_required(VERSION 3.16)

# the Debian package of the git plugin, its command and its editor plugin;
# nothing is compiled
project(cybersphere-git-plugin VERSION 0.1.0 LANGUAGES NONE)

# the place of the pure Python packages on Debian
set(PYTHON_INSTALL_DIR "lib/python3/dist-packages" CACHE STRING
    "the directory of the hsm_git package under the prefix")
# the system plugin folder of CyberiadaPro
set(PLUGIN_INSTALL_DIR "share/cyberiada-pro/plugins/git")
set(DOC_INSTALL_DIR "share/doc/python3-cybersphere-git")
# the package directories do not follow the umask of the build
set(CMAKE_INSTALL_DEFAULT_DIRECTORY_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
    GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/__init__.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/__main__.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/cli.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/git.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/repo.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/actions.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/diff.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/textdiff.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/session.py
              ${CMAKE_CURRENT_SOURCE_DIR}/hsm_git/plugin.py
        DESTINATION ${PYTHON_INSTALL_DIR}/hsm_git)

# the command, as the wheel's entry point makes it
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/hsm-git
     "#!/usr/bin/python3\nimport sys\nfrom hsm_git.cli import main\nsys.exit(main())\n")
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/hsm-git DESTINATION bin)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/editor-plugin/plugin.json
        DESTINATION ${PLUGIN_INSTALL_DIR})
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/editor-plugin/i18n/ru.json
        DESTINATION ${PLUGIN_INSTALL_DIR}/i18n)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/editor-plugin/icons
        DESTINATION ${PLUGIN_INSTALL_DIR})

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/ChangeLog.md
              ${CMAKE_CURRENT_SOURCE_DIR}/README.md
              ${CMAKE_CURRENT_SOURCE_DIR}/LICENSE
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/ARCHITECTURE.md
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/API.md
        DESTINATION ${DOC_INSTALL_DIR})

# the machine-readable (DEP-5) copyright, where the Debian policy wants it
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/debian-copyright
        DESTINATION ${DOC_INSTALL_DIR} RENAME copyright)

# the tests make their own repositories; the diff needs the CyberiadaML binding
# with Document.diff in this Python (-DPython3_EXECUTABLE=... selects another
# one), a missing git or binding skips them (77)
find_package(Python3 3.8 COMPONENTS Interpreter)
if(Python3_FOUND)
  enable_testing()
  add_test(NAME actions
           COMMAND ${Python3_EXECUTABLE} -B run.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  add_test(NAME session
           COMMAND ${Python3_EXECUTABLE} -B session_test.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  # the plugin installed and run through CyberiadaPro; the editor part is
  # skipped without the editor
  add_test(NAME plugin
           COMMAND ${Python3_EXECUTABLE} -B plugin_test.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  set_tests_properties(actions session plugin PROPERTIES SKIP_RETURN_CODE 77)
endif()

# optional per-release suffix (e.g. ubuntu2404) for the package version
set(DISTRO_TAG "" CACHE STRING "distribution suffix appended to the package version")
configure_file("${PROJECT_SOURCE_DIR}/CybersphereGitPackOptions.cmake.in"
               "${PROJECT_BINARY_DIR}/CybersphereGitPackOptions.cmake"
               @ONLY)
set(CPACK_PROJECT_CONFIG_FILE "${PROJECT_BINARY_DIR}/CybersphereGitPackOptions.cmake")

include(CPack)
