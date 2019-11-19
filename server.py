# -*- encoding: utf-8

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
        return max(ingest["events"], key=lambda ev: ev["createdDate"])["createdDate"]
    except IndexError:
        return ""


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
                title=f"Could not find {ingest_id}",
                ingest_id=ingest_id
            )
        except Exception as err:
            print(f"Looking up {ingest_id}: {err}")
            return render_template(
                "error.html",
                title=f"Error looking up {ingest_id}",
                ingest_id=ingest_id
            )
        else:
            return render_template(
                "ingest.html",
                title=f"Ingest {ingest_id}",
                ingest=ingest,
                api="staging"
            )

    except Exception:
        print(f"Looking up {ingest_id}: {err}")
        return render_template(
            "error.html",
            title=f"Error looking up {ingest_id}",
            ingest_id=ingest_id
        )

    else:
        return render_template(
            "ingest.html",
            title=f"Ingest {ingest_id}",
            ingest=ingest,
            api="production"
        )


if __name__ == "__main__":
    app.run(debug=True)
