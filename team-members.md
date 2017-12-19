# New team members

There's many things needed to consider when bringing in a new member on the team. Missing essential points can cause frustration. Therefore we intend to list the most important things to consider in this document.

## Access

New members need access to several tools:

- **Slack**: invite with members _@scilifelab.se_ account by clicking the user menu and selecting "Invite people" in the Slack app or at [scilifelab.slack.com][slack].
- **GitHub**: ask the new member for his/her GitHub account and invite them to [our organisation][github].
  1. Go to "People"
  1. Click "Invite member" and look up the user
  1. Make the user an _owner_ and add him/her to the "Core" team
- **Rasta**: all members of the core production team should have access to the `hiseq.clinical` user and to each of the production servers:
  - `rasta`
  - `clinical-db`
  - `caesar`

## Tools

You will need a few tools to collaborate and work on things within the group.

:exclamation: On macOS you can install all the tools using [Homebrew][brew] with the [cask][cask]-plugin!

    brew cask install visual-studio-code

Here's a list of the essentials:

- **Terminal**: Linux and macOS are bundled with terminal apps. However there are more sophisticated options worth exploring!
  - [iTerm][iterm] (macOS, free)
- **Text editor**: you will need an editor to write code. Once you got it installed you should look for some plugin to support Python and web development.
  - [Visual Studio Code][vscode] (GUI)
  - [Sublime Text][sublime] (GUI)
  - [Atom][atom] (GUI)
  - [VIM][vim] (text-based)
- **Git**: you can either use it on the command line and/or with a standalone graphical interface
  - [Sourcetree][sourcetree] (macOS, free)
- **SQL client**: we rely on MySQL for many of our databases. Accessing them from the command line is not entirely intuitive so I strongly recommend downloading a graphical interface!
  - [Sequel Pro][sequel] (macOS, free)
  - [MySQLWorkbench][mysql] (macOS, Windows, free)
- **MongoDB client**: Scout and LoqusDB are backed by MongoDB databases. If you are working on those tools you need a graphical interface to peek into the data.
  - [Robo T3][robo3t] (macOS, free)
  - [Mongo Compass][compass] (macOS, free)
- **VPN client**: for macOS we use [Tunnelblick][tunnelblick] to access our tools and servers remotely.

## Documentation

Tools, workflows, and methods are documented across a few different sources. You can find links to all of them under: [Apps][apps]. When you are looking for something specific consider the following:

- [AM System][amsystem]: official source for all documentation. _All_ method documents are kept here and any information that we share with the lab.
- [IT Manual][manual]: internal information at a glance. Here you can find workflow overviews that link to more detailed documentation. This guide is geared towards IT/Bioinformatics.
- [Clinical-Genomics/servers][servers]: this is our _private_ deployment repo were we store and describe the setup of our servers along with secrets and passwords.
- [Development Guide][development]: General programming conventions and good practises that we are advocating for.
- _GitHub READMEs_: tool specific information, local development installation, and description of project structure.

[github]: https://github.com/Clinical-Genomics
[slack]: https://scilifelab.slack.com/
[sequel]: https://www.sequelpro.com/
[mysql]: https://www.mysql.com/products/workbench/
[sourcetree]: https://www.sourcetreeapp.com/
[iterm]: https://www.iterm2.com/
[vscode]: https://code.visualstudio.com/
[atom]: https://atom.io/
[vim]: http://www.vim.org/
[sublime]: https://www.sublimetext.com/
[robo3t]: https://robomongo.org/
[compass]: https://www.mongodb.com/products/compass
[tunnelblick]: https://tunnelblick.net/
[brew]: https://brew.sh/
[cask]: https://caskroom.github.io/
[amsystem]: https://jo812.amsystem.com/index.php
[apps]: https://clinical.scilifelab.se/apps
[manual]: http://clinical-manual.surge.sh/
[servers]: https://github.com/Clinical-Genomics/servers
[development]: http://www.clinicalgenomics.se/development/
