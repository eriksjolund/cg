"""Set data in the status database and LIMS"""
import datetime
import getpass

import click
from cg.apps.lims import LimsAPI
from cg.constants import FAMILY_ACTIONS, PRIORITY_OPTIONS, FLOWCELL_STATUS
from cg.store import Store

CONFIRM = "Continue?"


@click.group("set")
@click.pass_context
def set_cmd(context):
    """Update information in the database."""
    context.obj["status"] = Store(context.obj["database"])
    context.obj["lims"] = LimsAPI(context.obj)


@set_cmd.command()
@click.option("-a", "--action", type=click.Choice(FAMILY_ACTIONS), help="update family action")
@click.option("-p", "--priority", type=click.Choice(PRIORITY_OPTIONS), help="update priority")
@click.option("-g", "--panel", "panels", multiple=True, help="update gene panels")
@click.argument("family_id")
@click.pass_context
def family(context, action, priority, panels, family_id):
    """Update information about a family."""
    family_obj = context.obj["status"].family(family_id)
    if family_obj is None:
        click.echo(click.style(f"Can't find family {family_id}", fg="red"))
        context.abort()
    if not (action or priority or panels):
        click.echo(click.style(f"Nothing to change", fg="yellow"))
        context.abort()
    if action:
        click.echo(
            click.style(f"Update action: {family_obj.action or 'NA'} -> {action}", fg="green")
        )
        family_obj.action = action
    if priority:
        message = f"update priority: {family_obj.priority_human} -> {priority}"
        click.echo(click.style(message, fg="blue"))
        family_obj.priority_human = priority
    if panels:
        for panel_id in panels:
            panel_obj = context.obj["status"].panel(panel_id)
            if panel_obj is None:
                click.echo(click.style(f"unknown gene panel: {panel_id}", fg="red"))
                context.abort()
        message = f"update panels: {', '.join(family_obj.panels)} -> {', '.join(panels)}"
        click.echo(click.style(message, fg="blue"))
        family_obj.panels = panels
    context.obj["status"].commit()


@set_cmd.command()
@click.option(
    "-id",
    "--identifier",
    "identifiers",
    nargs=2,
    type=click.Tuple([str, str]),
    multiple=True,
    help="Give an identifier on sample and the value to use it with, e.g. -id name Prov52",
)
@click.option(
    "-kv",
    "--key-value",
    "kwargs",
    nargs=2,
    type=click.Tuple([str, str]),
    multiple=True,
    help="Give a property on sample and the value to set it to, e.g. -kv name Prov52",
)
@click.option("--skip-lims", is_flag=True, help="Skip setting value in LIMS")
@click.option("-y", "--yes", is_flag=True, help="Answer yes on all confirmations")
@click.pass_context
def samples(context, identifiers, kwargs, skip_lims, yes):

    identifier_args = {}
    for identifier_name, identifier_value in identifiers:
        identifier_args[identifier_name] = identifier_value

    samples_objs = context.obj["status"].samples_by_ids(**identifier_args)

    click.echo("Would alter samples:")

    for sample_obj in samples_objs:
        click.echo(f"{sample_obj}")

    if not (yes or click.confirm(CONFIRM)):
        context.abort()

    for sample_obj in samples_objs:
        context.invoke(
            sample, sample_id=sample_obj.internal_id, kwargs=kwargs, yes=yes, skip_lims=skip_lims
        )


@set_cmd.command()
@click.argument("sample_id")
@click.option(
    "-kv",
    "--key-value",
    "kwargs",
    nargs=2,
    type=click.Tuple([str, str]),
    multiple=True,
    help="Give a property on sample and the value to set it to, e.g. -kv name Prov52",
)
@click.option("--skip-lims", is_flag=True, help="Skip setting value in LIMS")
@click.option("-y", "--yes", is_flag=True, help="Answer yes on all confirmations")
@click.pass_context
def sample(context, sample_id, kwargs, skip_lims, yes):

    sample_obj = context.obj["status"].sample(internal_id=sample_id)

    if sample_obj is None:
        click.echo(click.style(f"Can't find sample {sample_id}", fg="red"))
        context.abort()

    for key, _ in kwargs:

        if key in ["id", "internal_id"]:
            click.echo(click.style(f"{key} not a changeable attribute", fg="red"))
            context.abort()

    for key, value in kwargs:

        new_value = None
        if not hasattr(sample_obj, key):
            click.echo(click.style(f"{key} is not a property of sample", fg="yellow"))
            continue
        if key in ["customer", "application_version"]:
            if key == "customer":
                new_value = context.obj["status"].customer(value)
            elif key == "application_version":
                new_value = context.obj["status"].current_application_version(value)

            if not new_value:
                click.echo(click.style(f"{key} {value} not found, aborting", fg="red"))
                context.abort()
        else:
            new_value = value

        old_value = getattr(sample_obj, key)

        click.echo(f"Would change from {key}={old_value} to {key}={new_value} on {sample_obj}")

        if not (yes or click.confirm(CONFIRM)):
            context.abort()

        setattr(sample_obj, key, new_value)
        _update_comment(_generate_comment(key, old_value, new_value), sample_obj)
        context.obj["status"].commit()

    if not skip_lims:

        for key, value in kwargs:
            click.echo(f"Would set {key} to {value} for {sample_obj.internal_id} in LIMS")

            if not (yes or click.confirm(CONFIRM)):
                context.abort()

            context.obj["lims"].update_sample(lims_id=sample_id, **{key: value})
            click.echo(click.style(f"Set LIMS/{key} to {value}", fg="blue"))


def _generate_comment(what, old_value, new_value):
    return f"\n{what} changed from " f"{str(old_value)} to " f"{str(new_value)}."


def _update_comment(comment, obj):
    """Appends the comment on obj including a timestamp"""
    if comment:
        timestamp = str(datetime.datetime.now())[:-10]
        if obj.comment is None:
            obj.comment = f"{timestamp}-{getpass.getuser()}: {comment}"
        else:
            obj.comment = f"{timestamp}-{getpass.getuser()}: {comment}" + "\n" + obj.comment


@set_cmd.command()
@click.option("-s", "--status", type=click.Choice(FLOWCELL_STATUS))
@click.argument("flowcell_name")
@click.pass_context
def flowcell(context, flowcell_name, status):
    """Update information about a flowcell"""
    flowcell_obj = context.obj["status"].flowcell(flowcell_name)

    if flowcell_obj is None:
        click.echo(click.style(f"flowcell not found: {flowcell_name}", fg="yellow"))
        context.abort()
    prev_status = flowcell_obj.status
    flowcell_obj.status = status

    context.obj["status"].commit()
    click.echo(click.style(f"{flowcell_name} set: {prev_status} -> {status}", fg="green"))


@set_cmd.command("microbial-order")
@click.option(
    "-a",
    "--application-tag",
    "apptag",
    help="sets application tag on all samples in " "order.",
    type=str,
)
@click.option("-p", "--priority", type=click.Choice(PRIORITY_OPTIONS), help="update priority")
@click.option("-t", "--ticket", "ticket", help="sets ticket number.", type=str)
@click.option("-n", "--name", "name", help="sets name both in status-db and LIMS.", type=str)
@click.argument("order_id")
@click.argument("user_signature")
@click.pass_context
def microbial_order(context, apptag, priority, ticket, name, order_id, user_signature):
    """Update information on all samples on a microbial order"""

    if not apptag and not priority and not ticket and not name:
        click.echo(click.style(f"No option specified: {order_id}", fg="yellow"))
        context.abort()

    microbial_order_obj = context.obj["status"].microbial_order(internal_id=order_id)
    if not microbial_order_obj:
        click.echo(click.style(f"order not found: {order_id}", fg="yellow"))
        context.abort()

    if apptag or priority:
        for sample_obj in microbial_order_obj.microbial_samples:
            context.invoke(
                microbial_sample,
                sample_id=sample_obj.internal_id,
                user_signature=user_signature,
                apptag=apptag,
                priority=priority,
            )

    echo_msg = ""

    if ticket:
        if microbial_order_obj.ticket_number == ticket:
            click.echo(
                click.style(
                    f"Order {microbial_order_obj.internal_id} already has the " f"ticket {ticket}",
                    fg="yellow",
                )
            )
            return

        comment = (
            f"Ticket changed from"
            f" {microbial_order_obj.ticket_number} to "
            f"{ticket} by {user_signature}"
        )
        microbial_order_obj.ticket_number = ticket

        echo_msg += click.style(
            f"\nTicket for {microbial_order_obj.internal_id} set to "
            f"{str(microbial_order_obj.ticket_number)}.",
            fg="green",
        )

        _update_comment(comment, microbial_order_obj)
        echo_msg += click.style(
            f"\nComment added to order {microbial_order_obj.internal_id}", fg="green"
        )

    if name:
        if microbial_order_obj.name == name:
            click.echo(
                click.style(
                    f"Order {microbial_order_obj.internal_id} already has the " f"name {name}",
                    fg="yellow",
                )
            )
            return

        comment = (
            f"Name changed from" f" {microbial_order_obj.name} to " f"{name} by {user_signature}"
        )
        microbial_order_obj.name = name
        echo_msg += click.style(
            f"\nName for {microbial_order_obj.internal_id} set to "
            f"{str(microbial_order_obj.name)}.",
            fg="green",
        )

        _update_comment(comment, microbial_order_obj)
        echo_msg += click.style(
            f"\nComment added to order {microbial_order_obj.internal_id}", fg="green"
        )

        lims_name = f"{name} ({microbial_order_obj.internal_id})"
        context.obj["lims"].update_project(microbial_order_obj.internal_id, name=lims_name)
        click.echo(click.style(f"updated LIMS/Project-name to {lims_name}", fg="blue"))

    context.obj["status"].commit()
    click.echo(echo_msg)


@set_cmd.command("microbial-sample")
@click.option("-a", "--application-tag", "apptag", help="sets application tag.", type=str)
@click.option("-p", "--priority", type=click.Choice(PRIORITY_OPTIONS), help="update priority")
@click.argument("sample_id")
@click.argument("user_signature")
@click.pass_context
def microbial_sample(context, apptag, priority, sample_id, user_signature):
    """Update information on one sample"""

    sample_obj = context.obj["status"].microbial_sample(internal_id=sample_id)

    if not sample_obj:
        click.echo(click.style(f"Sample not found: {sample_id}", fg="yellow"))
        context.abort()

    if not apptag and not priority:
        click.echo(click.style(f"No option specified: {sample_id}", fg="yellow"))
        context.abort()

    if apptag:
        apptags = [app.tag for app in context.obj["status"].applications()]
        if apptag not in apptags:
            click.echo(click.style(f"Application tag {apptag} does not exist.", fg="red"))
            context.abort()

        application_version = context.obj["status"].current_application_version(apptag)
        if application_version is None:
            click.echo(click.style(f"No valid current application version found!", fg="red"))
            context.abort()

        application_version_id = application_version.id

        if sample_obj.application_version_id == application_version_id:
            click.echo(
                click.style(
                    f"Sample {sample_obj.internal_id} already has the "
                    f"apptag {str(application_version)}",
                    fg="yellow",
                )
            )
            return

        comment = (
            f"Application tag changed from"
            f" {sample_obj.application_version.application} to "
            f"{str(application_version)} by {user_signature}"
        )
        sample_obj.application_version_id = application_version_id
        click.echo(
            click.style(
                f"Application tag for sample {sample_obj.internal_id} set to "
                f"{str(application_version)}.",
                fg="green",
            )
        )

        timestamp = str(datetime.datetime.now())[:-10]
        if sample_obj.comment is None:
            sample_obj.comment = f"{timestamp}: {comment}"
        else:
            sample_obj.comment += "\n" + f"{timestamp}: {comment}"
        click.echo(click.style(f"Comment added to sample {sample_obj.internal_id}", fg="green"))
        context.obj["status"].commit()

        context.obj["lims"].update_sample(sample_id, application=apptag)
        click.echo(click.style("updated LIMS/application", fg="blue"))

    if priority:
        comment = (
            f"Priority changed from"
            f" {sample_obj.priority_human} to "
            f"{str(priority)} by {user_signature}"
        )
        sample_obj.priority_human = priority
        click.echo(
            click.style(
                f"priority for sample {sample_obj.internal_id} set to " f"{str(priority)}.",
                fg="green",
            )
        )

        timestamp = str(datetime.datetime.now())[:-10]
        if sample_obj.comment is None:
            sample_obj.comment = f"{timestamp}: {comment}"
        else:
            sample_obj.comment += "\n" + f"{timestamp}: {comment}"
        click.echo(click.style(f"Comment added to sample {sample_obj.internal_id}", fg="green"))

        context.obj["status"].commit()

        context.obj["lims"].update_sample(sample_id, priority=priority)
        click.echo(click.style("updated LIMS/priority", fg="blue"))
