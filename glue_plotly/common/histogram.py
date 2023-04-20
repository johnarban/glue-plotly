from uuid import uuid4

from glue.core import BaseData
from plotly.graph_objs import Bar

from glue_plotly.common import base_layout_config, fixed_color, rectilinear_axis
from glue_plotly.utils import ticks_values


def axis(viewer, ax):
    a = rectilinear_axis(viewer, ax)
    vals, text = ticks_values(viewer.axes, ax)
    if vals and text:
        a.update(tickmode='array', tickvals=vals, ticktext=text)
    return a


def layout_config(viewer):
    config = base_layout_config(viewer, barmode="overlay", bargap=0)
    x_axis = axis(viewer, 'x')
    y_axis = axis(viewer, 'y')
    config.update(xaxis=x_axis, yaxis=y_axis)
    return config


def traces_for_layer(viewer, layer, add_data_label=True):
    traces = []
    layer_state = layer.state
    legend_group = uuid4().hex

    # The x values should be at the midpoints between successive pairs of edge values
    edges, y = layer_state.histogram
    x = [0.5 * (edges[i] + edges[i + 1]) for i in range(len(edges) - 1)]

    # set the opacity and remove bar borders
    # set all bars to be the same color
    marker = dict(opacity=layer_state.alpha,
                  line=dict(width=0),
                  color=fixed_color(layer))

    name = layer.layer.label
    if add_data_label and not isinstance(layer.layer, BaseData):
        name += " ({0})".format(layer.layer.data.label)

    hist_info = dict(hoverinfo="skip", marker=marker, name=name)
    if viewer.state.x_log:
        for i in range(len(x)):
            hist_info.update(
                legendgroup=legend_group,
                showlegend=i == 0,
                x=[x[i]],
                y=[y[i]],
                width=edges[i + 1] - edges[i],
            )
            traces.append(Bar(**hist_info))
    else:
        hist_info.update(
            x=x,
            y=y,
            width=edges[1] - edges[0],
        )
        traces.append(Bar(**hist_info))

    return traces
