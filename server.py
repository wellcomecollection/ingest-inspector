# -*- encoding: utf-8

import collections
import datetime as dt
import os

from flask import Flask, request, render_template, jsonify
from wellcome_storage_service import IngestNotFound

from storage_service import lookup_ingest_by_id


app = Flask(__name__)

# Strip the whitespace in the Jinja2 templates before rendering.  This reduces
# the amount of data we need to spend to the client.
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True


@app.route("/")
def index():
    return render_template("index.html", title="Look up an ingest")


@app.template_filter("s3_url")
def s3_url(source_location):
    bucket = source_location["bucket"]
    key = source_location["path"]

    return (
        f"https://s3.console.aws.amazon.com/s3/buckets/{bucket}"
        f"/{os.path.dirname(key)}/?tab=overview&prefixSearch={os.path.basename(key)}"
        f"&region=eu-west-1"
    )


@app.template_filter("display_s3_url")
def display_s3_url(source_location):
    bucket = source_location["bucket"]
    key = source_location["path"]

    # The key to an Archivematica source is usually some hideous long path
    # of the form:
    #
    #     born-digital/2199/f389/66f5/4077/bcf7/c14b/0fdc/66cd/SAWTC={uuid}.tar.gz
    #
    # Displaying the whole thing is completely unhelpful, so truncate it
    # to a shorter URL for display purposes.
    #
    if "archivematica-ingests" in bucket:
        top_level, *_, filename = key.split("/")
        key = f"{top_level}/.../{filename}"

    return f"s3://{bucket}/{key}"


@app.template_filter("last_update")
def last_update(ingest):
    try:
        last_event = max(ingest["events"], key=lambda ev: ev["createdDate"])
    except ValueError:
        return ""

    return last_event["createdDate"]


def _parse_date(date_string):
    try:
        return dt.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return dt.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")


@app.template_filter("format_date")
def format_date(date_string):
    if not date_string:
        return ""

    d = _parse_date(date_string)

    if d.date() == dt.datetime.now().date():
        return d.strftime("today @ %H:%M")
    elif d.date() == (dt.datetime.now() - dt.timedelta(days=1)).date():
        return d.strftime("yesterday @ %H:%M")
    else:
        return d.strftime("%Y-%m-%d @ %H:%M")


@app.template_filter("kibana_url")
def kibana_url(event, api):
    namespace = {
        "production": "prod",
        "staging": "staging",
    }[api]

    try:
        ecs_service_name = {
            "Aggregating replicas": "replica_aggregator",
            "Replicating to Amazon Glacier": "bag-replicator_glacier",
            "Replicating to Azure": "bag-replicator_azure",
            "Replicating to primary location": "bag-replicator_primary",
            "Register": "bag_register",
        }[event["description"]]
    except KeyError:
        # Handle the case where the verification message includes some extra
        # detail for the user (e.g. a list of failed files.)
        if event["description"].startswith("Verification (Azure)"):
            ecs_service_name = "bag-verifier_azure"
        elif event["description"].startswith("Verification (Amazon Glacier)"):
            ecs_service_name = "bag-verifier_glacier"
        elif event["description"].startswith("Verification (primary location)"):
            ecs_service_name = "bag-verifier_primary"
        elif event["description"].startswith("Assigning bag version"):
            ecs_service_name = "bag-versioner"
        elif event["description"].startswith("Register"):
            ecs_service_name = "bag_register"

        # Normally the unpacker should include a message explaining why
        # unpacking failed; if it doesn't then we should go find out. why.
        elif event["description"] == "Unpacking failed":
            ecs_service_name = "bag-unpacker"

        # Otherwise, we don't know what logs to redirect to.
        else:
            return ""

    service_name = f"storage-{namespace}-{ecs_service_name}"

    event_time = _parse_date(event["createdDate"])

    # Slop to account for timezone weirdness.  Although Kibana stores timestamps
    # in UTC, searches happen in your local timezone.  For Wellcome devs this
    # will always be BST, so this is "good enough" for now.
    #
    # Actually localising this properly is a faff.
    search_start = (event_time - dt.timedelta(minutes=85)).strftime("%Y-%m-%dT%H:%M")
    search_end = (event_time + dt.timedelta(minutes=65)).strftime("%Y-%m-%dT%H:%M")

    firelens_index_pattern = "94746ad0-81c5-11eb-b41a-c9fd641654c0"

    return (
        "https://logging.wellcomecollection.org/app/kibana#/discover?_g="
        f"(refreshInterval:(pause:!t,value:0),time:(from:'{search_start}',to:'{search_end}'))&"
        f"_a=(columns:!(log),"
        # These are very chatty apps and probably not what we wanted -- errors in
        # these apps don't get surfaced in the ingest inspector.
        f"filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'{firelens_index_pattern}',key:service_name,params:(query:{service_name}),type:phrase),query:(match_phrase:(service_name:{service_name})))),"
        f"index:'{firelens_index_pattern}',interval:auto,sort:!(!('@timestamp',desc)))"
    )


@app.template_filter("tally_event_descriptions")
def tally_event_descriptions(events):
    """
    Iterates over a list of events, as received from the /ingests API.

    Adds a "_count" field to each description, so we can see if/when the
    same event occurred twice.  Also adds an "_is_repeated" field.
    """
    running_counter = collections.Counter()
    all_descriptions = collections.Counter(ev["description"] for ev in events)

    for ev in events:
        running_counter[ev["description"]] += 1
        ev["_count"] = running_counter[ev["description"]]

        ev["_repeated"] = all_descriptions[ev["description"]] > 1

    return events


@app.template_filter("ordinal")
def ordinal(n):
    """
    Returns the ordinal value of n, e.g. 1st, 2nd, 3rd

    From https://leancrew.com/all-this/2020/06/ordinals-in-python/
    """
    suffix = ("th", "st", "nd", "rd") + ("th",) * 10
    v = n % 100
    if v > 13:
        return f"{n}{suffix[v % 10]}"
    else:
        return f"{n}{suffix[v]}"


@app.route("/ingests/<ingest_id>")
def lookup_ingest(ingest_id):
    try:
        api, ingest = lookup_ingest_by_id(ingest_id)
        return render_template(
            "ingest.html",
            title="Ingest %s" % ingest_id,
            ingest=ingest,
            api=api
        )
    except IngestNotFound:
        return render_template(
            "not_found.html",
            title="Could not find %s" % ingest_id,
            ingest_id=ingest_id
        )
    except Exception as err:
        print("Error looking up %s: %s" % (ingest_id, err))
        display_err = err if app.config["DEBUG"] else None
        return render_template(
            "error.html",
            title="Error looking up %s" % ingest_id,
            ingest_id=ingest_id,
            display_err=display_err
        )


if __name__ == "__main__":
    app.run(debug=True)
