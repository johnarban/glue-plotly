from __future__ import absolute_import, division, print_function

import numpy as np
import matplotlib.colors as colors
from matplotlib.colors import Normalize

from qtpy import compat
from glue.config import viewer_tool, settings, colormaps

from glue.core import DataCollection, Data
from glue.utils import ensure_numerical

try:
    from glue.viewers.common.qt.tool import Tool
except ImportError:
    from glue.viewers.common.tool import Tool

from glue_plotly import PLOTLY_LOGO
from .. import save_hover

from plotly.offline import plot
import plotly.graph_objs as go
from glue.core.qt.dialogs import warn

DEFAULT_FONT = 'Arial, sans-serif'


@viewer_tool
class PlotlyScatter3DStaticExport(Tool):
    icon = PLOTLY_LOGO
    tool_id = 'save:plotly3d'
    action_text = 'Save Plotly HTML page'
    tool_tip = 'Save Plotly HTML page'

    def activate(self):

        # grab hover info
        dc_hover = DataCollection()

        for layer in self.viewer.layers:
            layer_state = layer.state
            if layer_state.visible and layer.enabled:
                data = Data(label=layer_state.layer.label)
                for component in layer_state.layer.components:
                    data[component.label] = np.ones(10)
                dc_hover.append(data)

        checked_dictionary = {}

        # figure out which hover info user wants to display
        for layer in self.viewer.layers:
            layer_state = layer.state
            if layer_state.visible and layer.enabled:
                checked_dictionary[layer_state.layer.label] = np.zeros((len(layer_state.layer.components))).astype(bool)

        dialog = save_hover.SaveHoverDialog(data_collection=dc_hover, checked_dictionary=checked_dictionary)
        proceed = warn('Scatter 3d plotly may look different',
                       'Plotly and Matlotlib graphics differ and your graph may look different when exported. Do you '
                       'want to proceed?',
                       default='Cancel', setting='SHOW_WARN_PROFILE_DUPLICATE')
        if not proceed:
            return
        dialog.exec_()

        # query filename
        filename, _ = compat.getsavefilename(
            parent=self.viewer, basedir="plot.html")

        # when vispy viewer is in "native aspect ratio" mode, scale axes size by data
        if self.viewer.state.native_aspect:
            width = self.viewer.state.x_max - self.viewer.state.x_min
            height = self.viewer.state.y_max - self.viewer.state.y_min
            depth = self.viewer.state.z_max - self.viewer.state.z_min

        # otherwise, set all axes to be equal size
        else:
            width = 1200  # this 1200 size is arbitrary, could change to any width; just need to scale rest accordingly
            height = 1200
            depth = 1200

        # check which projection we want to use
        projection_type = "perspective" if self.viewer.state.perspective_view else "orthographic"

        # set the aspect ratio of the axes, the tick label size, the axis label sizes, and the axes limits
        layout = go.Layout(
            margin=dict(r=50, l=50, b=50, t=50),  # noqa
            width=1200,
            paper_bgcolor=settings.BACKGROUND_COLOR,
            scene=dict(
                xaxis=dict(
                    title=self.viewer.state.x_att.label,
                    titlefont=dict(
                        family=DEFAULT_FONT,
                        size=20,
                        color=settings.FOREGROUND_COLOR
                    ),
                    showspikes=False,
                    showgrid=False,
                    zeroline=False,
                    backgroundcolor=settings.BACKGROUND_COLOR,
                    showticklabels=True,
                    tickfont=dict(
                        family=DEFAULT_FONT,
                        size=12,
                        color=settings.FOREGROUND_COLOR),
                    mirror=True,
                    ticks='outside',
                    showline=True,
                    linecolor=settings.FOREGROUND_COLOR,
                    tickcolor=settings.FOREGROUND_COLOR,
                    range=[self.viewer.state.x_min, self.viewer.state.x_max]),
                yaxis=dict(
                    title=self.viewer.state.y_att.label,
                    titlefont=dict(
                        family=DEFAULT_FONT,
                        size=20,
                        color=settings.FOREGROUND_COLOR),
                    showspikes=False,
                    showgrid=False,
                    zeroline=False,
                    backgroundcolor=settings.BACKGROUND_COLOR,
                    range=[self.viewer.state.y_min, self.viewer.state.y_max],
                    showticklabels=True,
                    tickfont=dict(
                        family=DEFAULT_FONT,
                        size=12,
                        color=settings.FOREGROUND_COLOR),
                    mirror=True,
                    ticks='outside',
                    showline=True,
                    linecolor=settings.FOREGROUND_COLOR,
                    tickcolor=settings.FOREGROUND_COLOR
                ),
                zaxis=dict(
                    title=self.viewer.state.z_att.label,
                    titlefont=dict(
                        family=DEFAULT_FONT,
                        size=20,
                        color=settings.FOREGROUND_COLOR),
                    showspikes=False,
                    showgrid=False,
                    zeroline=False,
                    backgroundcolor=settings.BACKGROUND_COLOR,
                    range=[self.viewer.state.z_min, self.viewer.state.z_max],
                    showticklabels=True,
                    tickfont=dict(
                        family=DEFAULT_FONT,
                        size=12,
                        color=settings.FOREGROUND_COLOR),
                    mirror=True,
                    ticks='outside',
                    showline=True,
                    linecolor=settings.FOREGROUND_COLOR,
                    tickcolor=settings.FOREGROUND_COLOR
                ),
                camera=dict(
                    projection=dict(
                        type=projection_type
                    )
                ),
                aspectratio=dict(x=1 * self.viewer.state.x_stretch,
                                 y=height / width * self.viewer.state.y_stretch,
                                 z=depth / width * self.viewer.state.z_stretch),
                                 aspectmode='manual'),
        )

        fig = go.Figure(layout=layout)

        for layer in self.viewer.layers:

            layer_state = layer.state

            if layer_state.visible and layer.enabled:

                x = layer_state.layer[self.viewer.state.x_att]
                y = layer_state.layer[self.viewer.state.y_att]
                z = layer_state.layer[self.viewer.state.z_att]

                marker = {}

                # set all points to be the same color
                if layer_state.color_mode == 'Fixed':
                    if layer_state.color != '0.35':
                        marker['color'] = layer_state.color
                    else:
                        marker['color'] = 'gray'

                # color by some attribute
                else:
                    if layer_state.cmap_vmin > layer_state.cmap_vmax:
                        cmap = layer_state.cmap.reversed()
                        norm = Normalize(
                            vmin=layer_state.cmap_vmax, vmax=layer_state.cmap_vmin)
                    else:
                        cmap = layer_state.cmap
                        norm = Normalize(
                            vmin=layer_state.cmap_vmin, vmax=layer_state.cmap_vmax)

                    # most matplotlib colormaps aren't recognized by plotly, so we convert manually to a hex code
                    rgba_list = [cmap(
                        norm(point)) for point in layer_state.layer[layer_state.cmap_attribute].copy()]
                    rgb_str = [r'{}'.format(colors.rgb2hex(
                        (rgba[0], rgba[1], rgba[2]))) for rgba in rgba_list]
                    marker['color'] = rgb_str

                # set all points to be the same size, with set scaling
                if layer_state.size_mode == 'Fixed':
                    marker['size'] = layer_state.size_scaling * layer_state.size

                # scale size of points by set size scaling
                else:
                    s = ensure_numerical(layer_state.layer[layer_state.size_attribute].ravel())
                    s = ((s - layer_state.size_vmin) /
                         (layer_state.size_vmax - layer_state.size_vmin))
                    # The following ensures that the sizes are in the
                    # range 3 to 30 before the final size scaling.
                    np.clip(s, 0, 1, out=s)
                    s *= 0.95
                    s += 0.05
                    s *= (30 * layer_state.size_scaling)
                    marker['size'] = s

                # set the opacity
                marker['opacity'] = layer_state.alpha
                marker['line'] = dict(width=0)

                if layer_state.vector_visible:
                    proceed = warn('Arrows may look different',
                                   'Plotly and Matlotlib vector graphics differ and your graph may look different '
                                   'when exported. Do you want to proceed?',
                                   default='Cancel', setting='SHOW_WARN_PROFILE_DUPLICATE')
                    if not proceed:
                        return
                    vx = layer_state.layer[layer_state.vx_attribute]
                    vy = layer_state.layer[layer_state.vy_attribute]
                    vz = layer_state.layer[layer_state.vz_attribute]
                    # convert anchor names from glue values to plotly values
                    anchor_dict = {'middle': 'center', 'tip': 'tip', 'tail': 'tail'}
                    anchor = anchor_dict[layer_state.vector_origin]
                    if layer_state.color_mode == 'Fixed':
                        # get the singular color in rgb format
                        c = 'rgb{}'.format(tuple(int(
                            marker['color'][i:i + 2], 16) for i in (1, 3, 5)))
                        fig.add_cone(x=x, y=y, z=z, u=vx, v=vy, w=vz,
                                     anchor=anchor, colorscale=[[0, c], [1, c]],
                                     hoverinfo='skip', showscale=False,
                                     showlegend=False)
                    else:
                        rgb_colors = list((int(rgba[0] * 256), int(rgba[1] * 256), int(rgba[2] * 256))
                                          for rgba in rgba_list)
                        for i in range(len(marker['color'])):
                            fig.add_cone(x=[x[i]], y=[y[i]], z=[z[i]],
                                         u=[vx[i]], v=[vy[i]], w=[vz[i]], anchor=anchor,
                                         colorscale=[[0, 'rgb{}'.format(rgb_colors[i])],
                                                     [1, 'rgb{}'.format(rgb_colors[i])]],
                                         hoverinfo='skip',
                                         showscale=False, showlegend=False, sizeref=0.3)
                    fig.update_layout(layout)

                # add error bars
                xerr = {}
                if layer_state.xerr_visible:
                    xerr['type'] = 'data'
                    xerr['array'] = np.absolute(ensure_numerical(
                        layer_state.layer[layer_state.xerr_attribute].ravel()))
                    xerr['visible'] = True

                yerr = {}
                if layer_state.yerr_visible:
                    yerr['type'] = 'data'
                    yerr['array'] = np.absolute(ensure_numerical(
                        layer_state.layer[layer_state.yerr_attribute].ravel()))
                    yerr['visible'] = True

                zerr = {}
                if layer_state.zerr_visible:
                    zerr['type'] = 'data'
                    zerr['array'] = np.absolute(ensure_numerical(
                        layer_state.layer[layer_state.zerr_attribute].ravel()))
                    zerr['visible'] = True

                # add hover info to layer
                if np.sum(dialog.checked_dictionary[layer_state.layer.label]) == 0:
                    hoverinfo = 'skip'
                    hovertext = None
                else:
                    hoverinfo = 'text'
                    hovertext = ["" for i in range((layer_state.layer.shape[0]))]
                    for i in range(0, len(layer_state.layer.components)):
                        if dialog.checked_dictionary[layer_state.layer.label][i]:
                            hover_data = layer_state.layer[layer_state.layer.components[i].label]
                            for k in range(0, len(hover_data)):
                                hovertext[k] = (hovertext[k] + "{}: {} <br>"
                                                .format(layer_state.layer.components[i].label,
                                                        hover_data[k]))

                # add layer to axes
                fig.add_scatter3d(x=x, y=y, z=z,
                                  error_x=xerr,
                                  error_y=yerr,
                                  error_z=zerr,
                                  mode='markers',
                                  marker=marker,
                                  hoverinfo=hoverinfo,
                                  hovertext=hovertext,
                                  name=layer_state.layer.label)

        plot(fig, filename=filename, auto_open=False)
