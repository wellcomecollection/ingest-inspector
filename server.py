# -*- encoding: utf-8

import datetime as dt
import os

from flask import Flask, request, render_template, jsonify
from wellcome_storage_service import IngestNotFound, StorageServiceClient

app = Flask(__name__)

prod_api = StorageServiceClient(
    api_url="https://api.wellcomecollection.org/storage/v1",
    client_id=os.environ["CLIENT_ID"],
    client_secret=os.environ["CLIENT_SECRET"],
    token_url="https://auth.wellcomecollection.org/oauth2/token"
)

staging_api = StorageServiceClient(
    api_url="https://api-stage.wellcomecollection.org/storage/v1",
    client_id=os.environ["CLIENT_ID"],
    client_secret=os.environ["CLIENT_SECRET"],
    token_url="https://auth.wellcomecollection.org/oauth2/token"
)


@app.route("/")
def index_page():
    return render_template("index.html", title="Look up an ingest")


@app.template_filter("last_update")
def last_update(ingest):
    try:
        last_event = max(ingest["events"], key=lambda ev: ev["createdDate"])
    except IndexError:
        return ""

    last_event_date = last_event["createdDate"]

    delta = dt.datetime.utcnow() - dt.datetime.strptime(
        last_event_date, "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    last_event_date_string = format_date(last_event_date)

    if delta.seconds < 5:
        return "%s (just now)" % last_event_date_string
    elif delta.seconds < 60:
        return "%s (%d seconds ago)" % (last_event_date_string, delta.seconds)
    elif 60 <= delta.seconds < 120:
        return "%s (1 minute ago)" % last_event_date_string
    elif delta.seconds < 60 * 60:
        return "%s (%d minutes ago)" % (last_event_date_string, int(delta.seconds / 60))
    else:
        return last_event_date_string


@app.template_filter("format_date")
def format_date(date_string):
    if not date_string:
        return ""

    d = dt.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")

    if d.date() == dt.datetime.now().date():
        return d.strftime("today @ %H:%M")
    elif d.date() == (dt.datetime.now() - dt.timedelta(days=1)).date():
        return d.strftime("yesterday @ %H:%M")
    else:
        return d.strftime("%Y-%m-%d @ %H:%M")


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

    except Exception:
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
