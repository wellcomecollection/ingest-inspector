import functools
import json
import os


from wellcome_storage_service import IngestNotFound, StorageServiceClient


def _get_secret(name):
    try:
        return os.environ[name.upper()]
    except KeyError:
        creds_path = os.path.join(
            os.environ["HOME"], ".wellcome-storage", "oauth-credentials.json"
        )
        oauth_creds = json.load(open(creds_path))
        return oauth_creds[name.lower()]


@functools.lru_cache()
def get_client(api_url):
    return  StorageServiceClient(
        api_url=api_url,
        client_id=_get_secret("client_id"),
        client_secret=_get_secret("client_secret"),
        token_url="https://auth.wellcomecollection.org/oauth2/token"
    )


def lookup_ingest_by_id(ingest_id):
    prod_api = get_client(api_url="https://api.wellcomecollection.org/storage/v1")
    staging_api = get_client(api_url="https://api-stage.wellcomecollection.org/storage/v1")

    try:
        ingest = prod_api.get_ingest(ingest_id=ingest_id)
        return ("production", ingest)
    except IngestNotFound:
        ingest = staging_api.get_ingest(ingest_id=ingest_id)
        return ("staging", ingest)
