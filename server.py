# -*- encoding: utf-8

import datetime as dt
import os

from flask import Flask, request, render_template, jsonify
from wellcome_storage_service import IngestNotFound

from storage_service import get_client


app = Flask(__name__)

prod_api = get_client(api_url="https://api.wellcomecollection.org/storage/v1")
staging_api = get_client(api_url="https://api-stage.wellcomecollection.org/storage/v1")


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
    return dt.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")


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
            "Aggregating replicas failed": "replica_aggregator",
            "Assigning bag version failed": "bag-versioner",
            "Replicating to Amazon Glacier failed": "bag-replicator_glacier",
            "Replicating to Azure failed": "bag-replicator_azure",
            "Replicating to primary location failed": "bag-replicator_primary",
            "Register failed": "bag_register",
        }[event["description"]]
    except KeyError:
        # Handle the case where the verification message includes some extra
        # detail for the user (e.g. a list of failed files.)
        if event["description"].startswith("Verification (Azure) failed"):
            ecs_service_name = "bag-verifier_azure"
        elif event["description"].startswith("Verification (Amazon Glacier) failed"):
            ecs_service_name = "bag-verifier_glacier"
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

    firelens_index_pattern = "978cbc80-af0d-11ea-b454-cb894ee8b269"

    return (
        "https://logging.wellcomecollection.org/app/kibana#/discover?_g="
        f"(refreshInterval:(pause:!t,value:0),time:(from:'{search_start}',to:'{search_end}'))&"
        f"_a=(columns:!(log),"
        # These are very chatty apps and probably not what we wanted -- errors in
        # these apps don't get surfaced in the ingest inspector.
        f"filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'{firelens_index_pattern}',key:service_name,params:(query:{service_name}),type:phrase),query:(match_phrase:(service_name:{service_name})))),"
        f"index:'{firelens_index_pattern}',interval:auto,sort:!(!('@timestamp',desc)))"
    )


@app.route("/ingests/<ingest_id>")
def lookup_ingest(ingest_id):
    try:
        ingest = prod_api.get_ingest(ingest_id=ingest_id)
    except IngestNotFound:
        try:
            ingest = staging_api.get_ingest(ingest_id=ingest_id)
        except IngestNotFound:
            return render_template(
                "not_found.html",
                title="Could not find %s" % ingest_id,
                ingest_id=ingest_id
            )
        except Exception as err:
            print("Looking up %s: %s" % (ingest_id, err))
            return render_template(
                "error.html",
                title="Error looking up %s" % ingest_id,
                ingest_id=ingest_id
            )
        else:
            return render_template(
                "ingest.html",
                title="Ingest %s" % ingest_id,
                ingest=ingest,
                api="staging"
            )

    except Exception as err:
        print("Looking up %s: %s" % (ingest_id, err))
        return render_template(
            "error.html",
            title="Error looking up %s" % ingest_id,
            ingest_id=ingest_id
        )

    else:
        return render_template(
            "ingest.html",
            title="Ingest %s" % ingest_id,
            ingest=ingest,
            api="production"
        )


if __name__ == "__main__":
    app.run(debug=True)
