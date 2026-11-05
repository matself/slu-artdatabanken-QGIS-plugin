"""Network access through QGIS, so proxy and authentication settings apply."""
import json
from urllib.parse import urlencode

from qgis.core import QgsBlockingNetworkRequest, QgsFeedback
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from . import provenance
from .counting import CancelledError, Probe
from .query import BOTH, Query
from .wfs import WFS_URL, request_params

# The value of ``taxonCategory`` for genus level taxa, spelled as the service does.
GENUS_CATEGORY = "Släkte"
SPECIES_CATEGORY = "Art"


# Identifies the client to the service, as SLU Artdatabanken asks API users to do.
REQUESTING_SYSTEM = f"QGIS plugin Species Data (SLU Artdatabanken) {provenance.plugin_version()}".encode("ascii")


class NetworkError(RuntimeError):
    pass


def new_request(url: str) -> QNetworkRequest:
    """A GET request for ``url`` that identifies this plugin."""
    request = QNetworkRequest(QUrl.fromEncoded(url.encode("ascii")))
    request.setRawHeader(b"X-Requesting-System", REQUESTING_SYSTEM)
    return request


def feature_probe(query: Query, is_cancelled=lambda: False, feedback: QgsFeedback = None) -> Probe:
    """A probe asking the WFS for one feature at a start index.

    ``is_cancelled`` is checked before each request and ``feedback`` can abort one that
    is running, so a count can be stopped when the user changes the search.
    """

    def exists(index: int) -> bool:
        if is_cancelled():
            raise CancelledError()
        url = f"{WFS_URL}?{urlencode(request_params(query, start_index=index))}"
        request = new_request(url)
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request, False, feedback)
        if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
            if is_cancelled():
                raise CancelledError()
            raise NetworkError(blocking.errorMessage())
        try:
            payload = json.loads(bytes(blocking.reply().content()).decode("utf-8"))
        except ValueError as exc:
            raise NetworkError("The service did not return GeoJSON") from exc
        return bool(payload.get("features"))

    return exists


def genus_for_swedish_name(name: str, organism_group, is_cancelled=lambda: False, feedback=None):
    """The scientific genus when ``name`` is the Swedish name of a genus (for example
    "sippor" gives "Anemone"), else None.

    The service has no taxonomy, so this looks for observations identified only to genus
    level, which carry the Swedish name of the genus. A genus without such observations
    cannot be resolved here.
    """
    return _scientific_for_swedish_name(name, organism_group, GENUS_CATEGORY, is_cancelled, feedback)


def species_for_swedish_name(name: str, organism_group, is_cancelled=lambda: False, feedback=None):
    """The scientific name when ``name`` is the Swedish name of a species (for example
    "backsippa" gives "Pulsatilla vulgaris"), else None.

    The subspecies of a species have Swedish names of their own ("vanlig backsippa"), so a
    Swedish name alone would miss them. The scientific name also finds them.
    """
    return _scientific_for_swedish_name(name, organism_group, SPECIES_CATEGORY, is_cancelled, feedback)


def _scientific_for_swedish_name(name, organism_group, category, is_cancelled, feedback):
    probe = Query(organism_group=organism_group, names=(name,), occurrence=BOTH)
    names = ("scientificName", "vernacularName", "taxonCategory")
    params = request_params(probe, max_features=20, fields=names)
    url = f"{WFS_URL}?{urlencode(params)}"
    request = new_request(url)
    blocking = QgsBlockingNetworkRequest()
    if is_cancelled():
        raise CancelledError()
    error = blocking.get(request, False, feedback)
    if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
        if is_cancelled():
            raise CancelledError()
        raise NetworkError(blocking.errorMessage())
    try:
        features = json.loads(bytes(blocking.reply().content()).decode("utf-8")).get("features", [])
    except ValueError as exc:
        raise NetworkError("The service did not return GeoJSON") from exc
    for feature in features:
        props = feature.get("properties", {})
        same_name = (props.get("vernacularName") or "").lower() == name.lower()
        if props.get("taxonCategory") == category and same_name:
            return props.get("scientificName")
    return None
