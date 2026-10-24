"""Example Processing algorithm: copies the features of a layer to a new layer."""
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)
from qgis.PyQt.QtCore import QCoreApplication

from ..compat import FAST_INSERT, VECTOR_ANY_GEOMETRY


class ExampleAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    @staticmethod
    def tr(message):
        return QCoreApplication.translate("ExampleAlgorithm", message)

    def name(self):
        return "copy_features"

    def displayName(self):  # noqa: N802
        return self.tr("Copy features")

    def group(self):
        return self.tr("Examples")

    def groupId(self):  # noqa: N802
        return "examples"

    def shortHelpString(self):  # noqa: N802
        return self.tr("Copies all features of the input layer to a new layer.")

    def createInstance(self):  # noqa: N802
        return ExampleAlgorithm()

    def initAlgorithm(self, config=None):  # noqa: N802
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, self.tr("Input layer"), [VECTOR_ANY_GEOMETRY]
            )
        )
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Output layer")))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context, source.fields(), source.wkbType(), source.sourceCrs()
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        total = 100.0 / source.featureCount() if source.featureCount() else 0
        for i, feature in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            sink.addFeature(feature, FAST_INSERT)
            feedback.setProgress(int(i * total))

        return {self.OUTPUT: dest_id}
