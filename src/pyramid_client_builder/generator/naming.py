"""Naming conventions for generated client code."""

import logging
import re

import nltk
from nltk.corpus import wordnet

logger = logging.getLogger(__name__)

_wordnet_ready = False


def _ensure_wordnet():
    """Download WordNet corpus if not already available."""
    global _wordnet_ready
    if _wordnet_ready:
        return
    try:
        wordnet.synsets("test")
    except LookupError:
        nltk.download("wordnet", quiet=True)
    _wordnet_ready = True


_ROUTE_NAME_SEPS = re.compile(r"[-_]+")
_DUPLICATE_UNDERSCORES = re.compile(r"_+")
_PATH_PARAM = re.compile(r"\{[^}]+\}")
_VERSION_RE = re.compile(r"v(\d+)")

_ROLE_SUFFIXES = (
    "RequestSchema",
    "ResponseSchema",
    "QuerySchema",
    "BodySchema",
    "PathSchema",
    "ErrorSchema",
)

_SCHEMA_ROLE_MAP = {
    "request": "RequestSchema",
    "querystring": "QuerySchema",
    "response": "ResponseSchema",
}


def to_class_name(name: str) -> str:
    """Convert a client name to a PascalCase class name.

    Examples:
        "payments" -> "PaymentsClient"
        "legal_entity" -> "LegalEntityClient"
        "my-service" -> "MyServiceClient"
    """
    parts = _ROUTE_NAME_SEPS.split(name)
    pascal = "".join(part.capitalize() for part in parts if part)
    return f"{pascal}Client"


def to_package_name(name: str) -> str:
    """Convert a client name to a Python package name.

    Examples:
        "payments" -> "payments_client"
        "legal-entity" -> "legal_entity_client"
    """
    return f"{name.replace('-', '_')}_client"


def to_request_attr(name: str) -> str:
    """Convert a client name to a request attribute name.

    Examples:
        "payments" -> "payments_client"
        "legal-entity" -> "legal_entity_client"
    """
    return f"{name.replace('-', '_')}_client"


def to_schema_name(path: str, role: str) -> str | None:
    """Derive a schema name from an endpoint path and its usage role.

    Uses path segments (stripping API prefixes and path params) joined in
    PascalCase, plus a role suffix.

    Returns None if the path has no meaningful segments.

    Examples:
        ("/api/v1/charges", "request")          -> "ChargesRequestSchema"
        ("/api/v1/charges/{id}", "response")     -> "ChargesResponseSchema"
        ("/api/v1/charges/{id}/refund", "request")
            -> "ChargesRefundRequestSchema"
        ("/api/v1/split_accounts", "querystring")
            -> "SplitAccountsQuerySchema"
    """
    segments = _path_segments(path)
    if not segments:
        return None
    pascal = "".join(_to_pascal(seg) for seg in segments)
    suffix = _SCHEMA_ROLE_MAP.get(role)
    if suffix is None:
        return None
    return f"{pascal}{suffix}"


def needs_schema_rename(name: str) -> bool:
    """Check whether a schema name needs role-based renaming.

    Returns True if the name does NOT already end with a recognized role
    suffix like ``RequestSchema``, ``ResponseSchema``, etc.
    """
    return not any(name.endswith(suffix) for suffix in _ROLE_SUFFIXES)


def extract_version(path: str) -> str | None:
    """Extract an API version string from a URL path.

    Looks for segments matching ``v<digits>`` (e.g. ``v1``, ``v2``).

    Examples:
        "/api/v1/charges"       -> "v1"
        "/api/v2/invoices/{id}" -> "v2"
        "/health"               -> None
        "/"                     -> None
    """
    for seg in path.strip("/").split("/"):
        if _VERSION_RE.fullmatch(seg):
            return seg
    return None


def _to_pascal(segment: str) -> str:
    """Convert a snake_case or plain segment to PascalCase."""
    return "".join(word.capitalize() for word in segment.split("_"))


def to_method_name(route_name: str, method: str, path: str = "") -> str:
    """Convert a route name + HTTP method + path to a Python method name.

    Strategy:
    1. If the path ends with a verb after a resource (e.g. /charges/{id}/cancel),
       use the verb as prefix: cancel_charge.
    2. For API-style paths (2+ segments), use path-aware naming:
       - GET collection  -> list_charges
       - GET detail      -> get_charge
       - POST collection -> create_charge
       - DELETE detail   -> delete_charge
    3. For short/root paths (/, /health), fall back to route name:
       - get_home, get_health.

    Examples:
        ("charge_cancel", "POST", "/api/v1/charges/{charge_id}/cancel")
            -> "cancel_charge"
        ("charges", "GET", "/api/v1/charges")
            -> "list_charges"
        ("charge_detail", "GET", "/api/v1/charges/{charge_id}")
            -> "get_charge"
        ("charges", "POST", "/api/v1/charges")
            -> "create_charge"
        ("home", "GET", "/")
            -> "get_home"
    """
    segments = _path_segments(path) if path else []

    if len(segments) >= 2 and _is_verb(segments[-1]):
        verb = segments[-1]
        resource = _find_resource_before_verb(segments)
        return f"{verb}_{resource}"

    if _is_api_path(path) and segments:
        return _method_prefix_name_from_path(segments, method, path)

    return _route_name_fallback(route_name, method)


_API_PREFIXES = {"api", "v1", "v2", "v3", "v4"}


def _is_api_path(path: str) -> bool:
    """Check if a path looks like a REST API path (starts with /api/ or similar)."""
    stripped = path.strip("/").lower()
    return stripped.startswith("api/") or stripped.startswith("v1/") or "/" in stripped


def _path_segments(path: str) -> list[str]:
    """Extract meaningful segments from a URL path, dropping params and prefixes.

    "/api/v1/charges/{charge_id}/cancel" -> ["charges", "cancel"]
    "/" -> []
    "/health" -> ["health"]
    """
    raw = path.strip("/").split("/")
    segments = []
    for seg in raw:
        if not seg:
            continue
        if _PATH_PARAM.fullmatch(seg):
            continue
        if seg.lower() in _API_PREFIXES:
            continue
        segments.append(seg.replace("-", "_"))
    return segments


def _find_resource_before_verb(segments: list[str]) -> str:
    """Find the resource noun that precedes the trailing verb.

    ["charges", "cancel"] -> "charge" (singularized)
    ["charges", "conciliate"] -> "charge"
    """
    for seg in reversed(segments[:-1]):
        if not _PATH_PARAM.fullmatch(seg):
            return _singularize(seg)
    return segments[0]


def _singularize(word: str) -> str:
    """Naive singularization for common English resource names."""
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("ses") or word.endswith("xes") or word.endswith("zes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _is_verb(word: str) -> bool:
    """Check if a word is an English verb using NLTK WordNet."""
    _ensure_wordnet()
    synsets = wordnet.synsets(word, pos=wordnet.VERB)
    return len(synsets) > 0


def _method_prefix_name_from_path(segments: list[str], method: str, path: str) -> str:
    """Generate a method name from path segments + HTTP method.

    GET /charges              -> list_charges
    GET /charges/{id}         -> get_charge
    GET /charges/{id}/html    -> get_charge_html
    POST /charges             -> create_charge
    DELETE /charges/{id}      -> delete_charge
    """
    is_detail = _ends_with_param(path) or _has_path_params(path)
    resource = "_".join(segments)
    resource = _DUPLICATE_UNDERSCORES.sub("_", resource)

    if method.upper() == "GET" and not is_detail:
        return f"list_{resource}"

    resource = _singularize(resource)
    prefix = _HTTP_PREFIX.get(method.upper(), method.lower())
    return f"{prefix}_{resource}"


def _route_name_fallback(route_name: str, method: str) -> str:
    """Fallback: use the Pyramid route name for short/root paths."""
    clean = _clean_route_name(route_name)
    prefix = _HTTP_PREFIX.get(method.upper(), method.lower())
    return f"{prefix}_{clean}"


_HTTP_PREFIX = {
    "GET": "get",
    "POST": "create",
    "PUT": "update",
    "DELETE": "delete",
    "PATCH": "patch",
}


def _ends_with_param(path: str) -> bool:
    """Check if the path ends with a path parameter like /{id}."""
    last_segment = path.rstrip("/").rsplit("/", 1)[-1]
    return bool(_PATH_PARAM.fullmatch(last_segment))


def _has_path_params(path: str) -> bool:
    """Check if the path contains any path parameter like /{id}/."""
    return bool(_PATH_PARAM.search(path))


def _clean_route_name(route_name: str) -> str:
    """Clean a route name into a valid Python identifier fragment."""
    clean = _ROUTE_NAME_SEPS.sub("_", route_name).strip("_")
    return _DUPLICATE_UNDERSCORES.sub("_", clean)
