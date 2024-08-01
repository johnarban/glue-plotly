from glue.config import viewer_tool

from glue_plotly.common.base_3d import layout_config
from glue_plotly.common.common import data_count, layers_to_export
from glue_plotly.common.scatter3d import traces_for_layer
from glue_plotly.jupyter_base_export_tool import JupyterBaseExportTool

import plotly.graph_objs as go
from plotly.offline import plot


@viewer_tool
class PlotlyScatter3DStaticExport(JupyterBaseExportTool):
    tool_id = 'save:jupyter_plotly3dscatter'

    def save_figure(self, filepath):

        if not filepath:
            return

        config = layout_config(self.viewer.state)
        layout = go.Layout(**config)
        fig = go.Figure(layout=layout)

        layers = layers_to_export(self.viewer)
        add_data_label = data_count(layers) > 1
        for layer in layers:
            traces = traces_for_layer(self.viewer.state, layer.state,
                                      add_data_label=add_data_label)
            for trace in traces:
                fig.add_trace(trace)

        plot(fig, filename=filepath, auto_open=False)
