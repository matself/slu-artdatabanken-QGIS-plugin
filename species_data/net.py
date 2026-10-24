"""Network access through QGIS, so proxy and authentication settings apply."""
import json
from urllib.parse import urlencode

from qgis.core import QgsBlockingNetworkRequest, QgsFeedback
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from .counting import CancelledError, Probe
from .query import Query
from .wfs import WFS_URL, request_params


class NetworkError(RuntimeError):
    pass


def feature_probe(query: Query, is_cancelled=lambda: False, feedback: QgsFeedback = None) -> Probe:
    """A probe asking the WFS for one feature at a start index.

    ``is_cancelled`` is checked before each request and ``feedback`` can abort one that
    is running, so a count can be stopped when the user changes the search.
    """

    def exists(index: int) -> bool:
        if is_cancelled():
            raise CancelledError()
        url = f"{WFS_URL}?{urlencode(request_params(query, start_index=index))}"
        request = QNetworkRequest(QUrl.fromEncoded(url.encode("ascii")))
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
