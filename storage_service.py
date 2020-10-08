import json
import os


from wellcome_storage_service import StorageServiceClient


def _get_secret(name):
    try:
        return os.environ[name.upper()]
    except KeyError:
        creds_path = os.path.join(
            os.environ["HOME"], ".wellcome-storage", "oauth-credentials.json"
        )
        oauth_creds = json.load(open(creds_path))
        return oauth_creds[name.lower()]


def get_client(api_url):
    return StorageServiceClient(
        api_url=api_url,
        client_id=_get_secret("client_id"),
        client_secret=_get_secret("client_secret"),
        token_url="https://auth.wellcomecollection.org/oauth2/token",
    )
