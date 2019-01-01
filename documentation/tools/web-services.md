# Web services

We run all our web services on a single server and manage them in very similar ways. The setup is built around a few key components:

- [Supervisor][supervisor]: monitors and controls long-runnning processes like web services and database servers.
- [NGINX][nginx]: production web server that handles HTTPS and restricts traffic based on IP-addresses.

## Example setup (Python)

We run a lot of Python web services, preferrably written in Flask. We run them in production using [Gunicorn][gunicorn]. _Gunicorn_ is able to parallelize and load balance multiple _Flask_ processes so the interface is responsive even under load or if one process hangs.

A call to start a _Flask_ web service can look something like:

```bash
/path/to/gunicorn
    --workers=4                 # for production, 2 for staging
    --bind=":8080"              # port to listen on localhost
    --access-logfile=-          # redirect access log to STDOUT
    --error-logfile=-           # redirect errors to STDOUT
    my_program.server.auto:app
```

The web service is run on `http://localhost:8080`. We let _NGINX_ handle the specifics of which domain the web service is available on as well as encypting traffic over SSL/HTTPS.

## NGINX

To make life easy for users we proxy each sevice behind _NGINX_ so we can use pretty URLs such as `scout.scilifelab.se`.

- everything is behind `https://` managed by _NGINX_ with SLL certificates that SciLifeLab IT provides, requests on port 80 are automatically forwarded to port 443
- IP-based access rules are setup for each web service individually in the _NGINX_ configuration
- for each subdomain we have a separate config file under `clinical-db:/etc/nginx/conf.d/{SUBDOMAIN}.conf`

Each subdomain config contains the following (abbreviated) setup:

```ini
server {
    server_name {SUBDOMAIN}.scilifelab.se

    location / {
        proxy_pass http://localhost:{PORT};  # port where the server runs
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Web service run on `http://localhost:XXXX`. _NGINX_ will handle forwarding requests and setting the correct headers to make it all work. Since _NGINX_ also handles the `https` part - individual web services don't need to worry about that!

Whenever you update access rules or other settings you need to restart _NGINX_ for the changes to take effect. To restart _NGINX_, run:

```bash
sudo /sbin/service nginx restart
```

## Supervisor

Supervisor is a handy tool for monitoring and manage long running processes. We use it for databases and web services.

The `supervisord` deamon process is started automatically by a crontab whenever the server reboots. It reads a config file which tells it which processes to manage. For each of the services we tell it to start it automatically and if a process for some reason goes down - _Supervisor_ will restart it automatically!

Using the `supervisorctl`, we can interact with processes.

```bash
supervisorctl restart scout  # force a restart of the "scout" process
supervisorctl status         # list all the monitored processses and their status
```

For more information, read the [documentation][supervisor].

> `supervisorctl` is an alias which points to the relevant config.

## Port mapping

This is a summary of the setup for production web services:

| service            | subdomain       | port |
|--------------------|-----------------|------|
| cgweb              | clinical        | 8080 |
| cg (REST)          | clinical-api    | 8081 |
| NIPT               | nipt            | 8082 |
| Scout              | scout           | 8083 |
| Scout (Archive)    | scout-archive   | 8084 |
| Trailblazer        | trailblazer     | 8085 |
| Trailblazer (REST) | trailblazer-api | 8086 |
| Genotype           | genotype        | 8087 |
| Microbial          | microbial       | 8088 |

And for stage web services:

| service            | subdomain             | port |
|--------------------|-----------------------|------|
| cgweb              | clinical-stage        | 7070 |
| cg (REST)          | clinical-api-stage    | 7071 |
| NIPT               | nipt-stage            | 7073 |
| scout              | scout-stage           | 7073 |
| Trailblazer        | trailblazer-stage     | 7075 |
| Trailblazer (REST) | trailblazer-api-stage | 7076 |

### Updating services

We have scripts to update different web services/apps on `clinical-db`:

- cg: `bash ~/servers/resources/update-cg.sh`
- cgweb: `bash ~/servers/resources/update-cgweb.sh`
- Scout: `bash ~/servers/resources/update-scout.sh`
- Trailblazer: `bash ~/servers/update-trailblazer.sh`

[supervisor]: http://supervisord.org/
[nginx]: https://www.nginx.com/
[gunicorn]: http://gunicorn.org/
