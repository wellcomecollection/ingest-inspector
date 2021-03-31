import functools
import os


from wellcome_storage_service import IngestNotFound, RequestsOAuthStorageServiceClient, prod_client, staging_client


def _client_from_environment(api_url):
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]

    return RequestsOAuthStorageServiceClient(
        api_url=api_url,
        client_id=client_id,
        client_secret=client_secret,
        token_url="https://auth.wellcomecollection.org/oauth2/token"
    )


@functools.lru_cache()
def get_prod_client():
    try:
        return _client_from_environment(
            api_url="https://api.wellcomecollection.org/storage/v1"
        )
    except KeyError:
        return prod_client()


@functools.lru_cache()
def get_staging_client():
    try:
        return _client_from_environment(
            api_url="https://api-stage.wellcomecollection.org/storage/v1"
        )
    except KeyError:
        return staging_client()


def lookup_ingest_by_id(ingest_id):
    prod_api = get_prod_client()
    staging_api = get_staging_client()

    try:
        ingest = prod_api.get_ingest(ingest_id=ingest_id)
        return ("production", ingest)
    except IngestNotFound:
        ingest = staging_api.get_ingest(ingest_id=ingest_id)
        return ("staging", ingest)
