# Development :computer:

Should contain content moved from the [Clinical-Genomics/development](https://github.com/Clinical-Genomics/development) repo.

## Local development

This describes what any developer ought to setup to do local development within the team.

Prerequisites:

- Unix
- Git
- SciLifeLab LAN/VPN access

### Miniconda

We manage virtual environments and non-pip dependencies using `conda`. The esiest way to get started is to install it through [Miniconda][miniconda]. Just download the installer for your OS and run. We develop for Python 3.6+ so make sure to pick that installer.

The first thing to do is to create a development environment:

```bash
conda create -n develop python=3 pip ipython
source activate develop
```

### Clone repositories

Depending on what you will be working on, you might need to install more or less projects. However, you will probably need `cg`:

```bash
cd /path/to/my/projects
git clone https://github.com/Clinical-Genomics/cg
source activate develop
pip install --editable ./cg
```

This should install install all dependencies automatically. However, for some of the in-house developed projects you might need to clone/install the latest updates from the `master` branch on GitHub, for example:

```bash
source activate develop

pip install git+https://github.com/Clinical-Genomics/trailblazer
# or
cd /path/to/my/projects
git clone https://github.com/Clinical-Genomics/trailblazer
pip install --editable ./trailblazer
```

### Accessing databases

We run two database servers in production: MySQL and MongoDB. You will most likely need a GUI to inspect them as you develop. There are some options listed under [_Tools_](#tools). The database servers are running on `clinical-db` but they can be accessed from other servers such as `rasta`.

To connect to them you should open an SSH tunnel from you local machine by running something like:

```bash
ssh -fN -L 3308:localhost:3308 rasta
```

This command will open an SSH tunnel that will allow you to securely access port 3308 on `rasta` by connecting to `localhost:3308`.

### Start scripts for servers

I have written Bash-scripts for each server that details all commands I use for running a particular web service. This typically involves some environment variables, sourcing some virtual environment and perhaps opening an SSH tunnel to a remote server.

This is how my start script looks when I edit the server (REST API) in the `cg` package:

```bash
#!/usr/bin/env bash

# kill any open ssh connections that are running in the background
pkill -f "ssh -fN"
# open a ssh tunnel cluster <-> local computer to access the MySQL database
ssh -fN -L 3308:localhost:3308 rasta
# source the correct conda/virtual environment
source activate develop

# start up the server with the relevant environment variables
CG_SQL_DATABASE_URI="mysql+pymysql://*****:*****@localhost:3308/stage-cg" \
LIMS_HOST="https://clinical-lims-stage.scilifelab.se" \
LIMS_USERNAME="*****" \
LIMS_PASSWORD="*****" \
GOOGLE_OAUTH_CLIENT_ID="*****" \
GOOGLE_OAUTH_CLIENT_SECRET="*****" \
OAUTHLIB_INSECURE_TRANSPORT=1 \
OAUTHLIB_RELAX_TOKEN_SCOPE=1 \
FLASK_DEBUG=1 \
FLASK_APP=cg.server.auto \
flask run
```

I like to keep everything included to start the server in one script instead of splitting it into an activation script that prepares the environment + a script that spins up the server. This way I just need to worry less about which virtual env is active etc.

[autoenv]: https://github.com/kennethreitz/autoenv
[miniconda]: https://conda.io/miniconda.html
