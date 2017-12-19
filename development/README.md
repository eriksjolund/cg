# Development :computer:

Should contain content moved from the [Clinical-Genomics/development](https://github.com/Clinical-Genomics/development) repo.

## Local development

Setting up projects locally should not be so different from setting them up in production. When it comes to Python projects, it's a good idea to work in a virual environment. You probably also need to come up with a smart way to organize configs for different tools to make sure you connect to staging databases etc.

There's many [solutions][autoenv] for manging development setups. What I found tho, was that just as I regularly push code updates to GitHub as a way to backup my progress - I want to organize and backup how I setup tools for development purposes.

### Start scripts for servers

I have created a Bash-script for each server that details all commands I use for running a particular web service. This typically involves some environment variables, sourcing some virtual environment and perhaps opening an SSH tunnel to a remote server.

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
