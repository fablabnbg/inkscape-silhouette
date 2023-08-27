# inkscape-silhouette contributing

This file outlines guidelines and instructions for contributors who wish to contribute to the project. It may include information on how to submit bug reports, suggest enhancements, or create pull requests.

## Developer Commands

Use `make help` to find all makefile commands you can use as a developer

 - **clean**: Cleanup generated/compiled files and restore project back to nominal state
 - **dist**: Genearate OS specific packagings and install files (Windows, Linux Distros, etc...)
 - **help**: Show help for each of the Makefile recipes.
 - **install-local**: Use this with `make install-local` to install just in your user account
 - **install**: Install is used by dist or use this with this command `sudo make install` to install for all users
 - **mdhelp**: Render help for each of the Makefile recipes in a markdown friendly manner
 - **mo**: Compile transations for different human languages into binary .mo file for internationalisation and localisation purposes. (e.g. ./po/de.po)
 - **test**: run local test (Must have umockdev installed)
