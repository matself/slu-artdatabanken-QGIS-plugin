"""Network access through QGIS, so proxy and authentication settings apply."""
import json
from urllib.parse import urlencode

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from .counting import Probe
from .query import Query
from .wfs import WFS_URL, request_params


class NetworkError(RuntimeError):
    pass


def feature_probe(query: Query) -> Probe:
    """A probe asking the WFS for one feature at a start index."""

    def exists(index: int) -> bool:
        url = f"{WFS_URL}?{urlencode(request_params(query, start_index=index))}"
        request = QNetworkRequest(QUrl.fromEncoded(url.encode("ascii")))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)
        if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise NetworkError(blocking.errorMessage())
        try:
            payload = json.loads(bytes(blocking.reply().content()).decode("utf-8"))
        except ValueError as exc:
            raise NetworkError("The service did not return GeoJSON") from exc
        return bool(payload.get("features"))

    return exists
