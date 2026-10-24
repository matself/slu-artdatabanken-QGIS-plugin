"""Background download of a snapshot, shown with progress in the QGIS task manager."""
from urllib.parse import urlencode

from qgis.core import QgsBlockingNetworkRequest, QgsFeedback, QgsTask
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from . import counting, snapshot
from .net import NetworkError, feature_probe
from .query import BOTH, Query
from .wfs import WFS_URL, request_params


class SnapshotTask(QgsTask):
    """Fetch all matching observations page by page. Cancel stops between requests."""

    def __init__(self, query: Query, fields: tuple, total: int, on_done, on_error):
        super().__init__("Species Data: fetching observations", QgsTask.Flag.CanCancel)
        self.query = query
        self.fields = fields
        self.total = total
        self._on_done = on_done
        self._on_error = on_error
        self._feedback = QgsFeedback()
        self._rows = []
        self._error = None

    def cancel(self):
        self._feedback.cancel()
        super().cancel()

    def run(self):
        try:
            self._rows = snapshot.collect(
                self._fetch_page,
                self.total,
                is_cancelled=self.isCanceled,
                on_progress=lambda done, total: self.setProgress(100 * done / total),
            )
        except counting.CancelledError:
            return False
        except Exception as exc:  # reported to the user in finished()
            self._error = str(exc)
            return False
        return True

    def finished(self, ok):
        if ok:
            self._on_done(self._rows)
        elif self._error:
            self._on_error(self._error)

    def _fetch_page(self, start, size):
        names = tuple(name for name, _ in self.fields)
        params = request_params(self.query, start_index=start, max_features=size, fields=names)
        url = f"{WFS_URL}?{urlencode(params)}"
        request = QNetworkRequest(QUrl.fromEncoded(url.encode("ascii")))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request, False, self._feedback)
        if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
            if self.isCanceled():
                raise counting.CancelledError()
            raise NetworkError(blocking.errorMessage())
        try:
            return snapshot.parse_page(
                bytes(blocking.reply().content()).decode("utf-8"), tuple(n for n, _ in self.fields)
            )
        except (ValueError, KeyError) as exc:
            raise NetworkError("The service did not return GeoJSON") from exc


class CountTask(QgsTask):
    """Count the matches in the background. Cancelling stops the request series."""

    def __init__(self, query: Query, on_done, on_error):
        super().__init__("Species Data: counting observations", QgsTask.Flag.CanCancel)
        self.query = query
        self._on_done = on_done
        self._on_error = on_error
        self._feedback = QgsFeedback()
        self._result = None
        self._unknown = ()
        self._error = None

    def cancel(self):
        self._feedback.cancel()
        super().cancel()

    def _name_exists(self, name):
        """Is the name in the data at all, ignoring area, period and the other filters?"""
        any_obs = Query(organism_group=self.query.organism_group, names=(name,), occurrence=BOTH)
        return feature_probe(any_obs, self.isCanceled, self._feedback)(0)

    def run(self):
        try:
            probe = feature_probe(self.query, self.isCanceled, self._feedback)
            self._result = counting.count(probe)
            self._unknown = counting.unknown_names(self.query.names, self._name_exists)
        except counting.CancelledError:
            return False
        except Exception as exc:  # reported to the user in finished()
            self._error = str(exc)
            return False
        return True

    def finished(self, ok):
        if ok:
            self._on_done(self._result, self._unknown)
        elif self._error:
            self._on_error(self._error)


__all__ = ["CountTask", "SnapshotTask"]
