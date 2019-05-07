from __future__ import absolute_import, division, print_function

import numpy as np

from qtpy import compat
from glue.config import viewer_tool
from glue.viewers.common.tool import Tool

from glue_plotly import PLOTLY_LOGO

from plotly.offline import plot
import plotly.graph_objs as go


@viewer_tool
class PlotlyScatter2DStaticExport(Tool):

    icon = PLOTLY_LOGO
    tool_id = 'save:plotly2d'
    action_text = 'Save Plotly HTML page'
    tool_tip = 'Save Plotly HTML page'

    def activate(self):

        filename, _ = compat.getsavefilename(parent=self.viewer, basedir="plot.html")
        
        width, height= np.array(self.viewer.figure.get_size_inches()*self.viewer.figure.dpi)[0], np.array(self.viewer.figure.get_size_inches()*self.viewer.figure.dpi)[1]
        
        layout = go.Layout(
            margin=dict(r=50, l=50, b=50, t=50),  
            width=1200,
            height=1200*height/width, #scale axis correctly
            xaxis=dict(
                title=self.viewer.axes.get_xlabel(),
                titlefont=dict(
                    family='Arial, sans-serif',
                    size=self.viewer.axes.xaxis.get_label().get_size(),
                    color='black'
                ),
                showticklabels=True,
                tickfont=dict(
                    family='Arial, sans-serif',
                    size=self.viewer.axes.xaxis.get_ticklabels()[0].get_fontsize(),
                    color='black'),
                range=[self.viewer.state.x_min,self.viewer.state.x_max]),
            yaxis=dict(
                title=self.viewer.axes.get_xlabel(),
                titlefont=dict(
                    family='Arial, sans-serif',
                    size=self.viewer.axes.yaxis.get_label().get_size(),
                    color='black'),
                range=[self.viewer.state.y_min,self.viewer.state.y_max],
                showticklabels=True,
                tickfont=dict(
                    family='Old Standard TT, serif',
                    size=self.viewer.axes.yaxis.get_ticklabels()[0].get_fontsize(),
                    color='black'),
            )
        )

        fig = go.Figure(layout=layout)

        for layer_state in self.viewer.state.layers:
        
            if layer_state.visible==True:

                marker = {}

                x = layer_state.layer[self.viewer.state.x_att]
                y = layer_state.layer[self.viewer.state.y_att]

                if layer_state.cmap_mode == 'Fixed':
                    if layer_state.color!='0.35':
                        marker['color'] = layer_state.color
                    else:
                        marker['color'] =   'gray'
                else:
                    marker['color'] = layer_state.layer[layer_state.cmap_att].copy()
                    marker['cmin'] = layer_state.cmap_vmin
                    marker['cmax'] = layer_state.cmap_vmin
                    marker['colorscale'] = layer_state.cmap.name.upper()
                    marker['color'][np.isnan(marker['color'])] = -np.inf


                if layer_state.size_mode == 'Fixed':
                    marker['size'] = layer_state.size
                else:
                    marker['size'] = 20 * (layer_state.layer[layer_state.size_att] - layer_state.size_vmin) / (layer_state.size_vmax - layer_state.size_vmin)
                    marker['sizemin'] = 1
                    marker['size'][np.isnan(marker['size'])] = 0
                    marker['size'][marker['size'] < 0] = 0

                marker['opacity'] = layer_state.alpha

                fig.add_scatter(x=x, y=y,
                                mode='markers',
                                marker=marker,
                                name=layer_state.layer.label)
                            
        plot(fig, filename=filename, auto_open=False)
        
