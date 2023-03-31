def setup():

    from glue.config import exporters
    from glue_plotly.web.export_plotly import (can_save_plotly, DISPATCH,
                                               export_scatter, export_histogram)
    from glue_plotly.web.qt.exporter import save_plotly

    from glue.viewers.scatter.qt import ScatterViewer
    from glue.viewers.histogram.qt import HistogramViewer

    DISPATCH[ScatterViewer] = export_scatter
    DISPATCH[HistogramViewer] = export_histogram

    exporters.add('Plotly', save_plotly, can_save_plotly)
