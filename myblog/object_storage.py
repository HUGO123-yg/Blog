"""
S3-compatible object storage helpers.
Uploads image files after they are stored locally and returns a direct URL.
"""
import logging
import mimetypes
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None
    BotoCoreError = ClientError = Exception


def _get_config():
    return getattr(settings, 'OBJECT_STORAGE', {}) or {}


def _get_db_preference():
    try:
        from .models import StoragePreference  # local import to avoid circular deps
    except Exception:
        return None, ''
    try:
        pref = StoragePreference.get_solo()
        return pref.use_object_storage, pref.cdn_domain or ''
    except Exception:  # pragma: no cover - defensive
        return None, ''


def is_enabled():
    cfg = _get_config()
    required = ['bucket', 'endpoint', 'access_key', 'secret_key']
    env_ready = boto3 is not None and all(cfg.get(k) for k in required)
    db_flag, _ = _get_db_preference()
    # Explicit toggle from admin; default to False if missing.
    return env_ready and bool(db_flag)


def _client():
    if not boto3:
        raise RuntimeError("boto3 is not installed; install to enable object storage uploads")
    cfg = _get_config()
    session = boto3.session.Session()
    return session.client(
        's3',
        endpoint_url=cfg.get('endpoint'),
        aws_access_key_id=cfg.get('access_key'),
        aws_secret_access_key=cfg.get('secret_key'),
        region_name=cfg.get('region'),
        use_ssl=cfg.get('use_ssl', True),
    )


def build_public_url(key: str) -> str:
    cfg = _get_config()
    _, db_domain = _get_db_preference()
    domain = db_domain or cfg.get('public_domain') or cfg.get('endpoint') or ''
    bucket = cfg.get('bucket')
    domain = domain.rstrip('/')
    key = key.lstrip('/')
    return f"{domain}/{bucket}/{key}"


def upload_local_file(local_path: str, key: str) -> str | None:
    """
    Upload a local file to S3-compatible storage.
    Returns the public URL if successful, otherwise None.
    """
    if not is_enabled():
        return None

    cfg = _get_config()
    client = _client()
    content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
    extra_args = {'ContentType': content_type}
    default_acl = cfg.get('default_acl')
    if default_acl:
        extra_args['ACL'] = default_acl

    try:
        client.upload_file(local_path, cfg['bucket'], key, ExtraArgs=extra_args)
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover - network call
        logger.warning("Upload to object storage failed for %s: %s", key, exc)
        return None

    return build_public_url(key)


def upload_field_file(field_file, key_prefix: str | None = None) -> str | None:
    """
    Upload a Django FileField to object storage.
    """
    if not field_file or not getattr(field_file, 'name', None):
        return None
    name = str(field_file.name).lstrip('/')
    key = f"{key_prefix.rstrip('/')}/{name}" if key_prefix else name

    local_path = getattr(field_file, 'path', None)
    if not local_path:
        # Ensure the file is saved locally
        storage_path = field_file.storage.save(name, field_file)
        local_path = field_file.storage.path(storage_path)

    return upload_local_file(local_path, key)
