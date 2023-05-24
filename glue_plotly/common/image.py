from uuid import uuid4

from astropy.visualization import ManualInterval, ContrastBiasStretch
from glue.viewers.image.layer_artist import PixelSubsetState
from matplotlib.colors import to_rgb
import numpy as np

from glue.config import settings
from glue.utils import ensure_numerical
from glue.viewers.image.composite_array import STRETCHES
from glue.viewers.image.state import BaseData, ImageLayerState, ImageSubsetLayerState
from glue.viewers.scatter.state import IncompatibleAttribute, ScatterLayerState

from plotly.graph_objects import Heatmap, Image, Scatter

from glue_plotly.common import base_layout_config, color_info, fixed_color, layers_to_export
from glue_plotly.common.common import DEFAULT_FONT
from glue_plotly.utils import cleaned_labels


def slice_to_bound(slc, size):
    min, max, step = slc.indices(size)
    n = (max - min - 1) // step
    max = min + step * n
    return min, max, n + 1


def background_color(viewer):
    using_colormaps = viewer.state.color_mode == 'Colormaps'
    if using_colormaps:
        return [256, 256, 256, 1]
    else:
        img = viewer.axes._composite()
        bg_color = [_ for _ in img[0][0]]
        for i in range(3):
            bg_color[i] *= 256
        return bg_color

def layout_config(viewer):
    bg_color = background_color(viewer)
    return base_layout_config(viewer,
                              plot_bgcolor='rgba{0}'.format(tuple(bg_color)),
                              showlegend=True)


def axes_data(viewer):
    axes_data = {}

    axes = viewer.axes
    xmin, xmax = axes.get_xlim()
    ymin, ymax = axes.get_ylim()

    for helper in axes.coords:
        ticks = helper.ticks
        ticklabels = helper.ticklabels
        for axis in ticklabels.get_visible_axes():
            ax = 'x' if axis in ['t', 'b'] else 'y'
            ax_idx = 0 if ax == 'x' else 1
            locations = sorted([loc[0][ax_idx] for loc in ticks.ticks_locs[axis]])
            labels = ticklabels.text[axis]
            if ax == 'y':
                labels = list(reversed(labels))
            labels = cleaned_labels(labels)
            if ax == 'x':
                axis_range = [xmin, xmax]
            else:
                axis_range = [ymin, ymax]
            axis_info = dict(
                showspikes=False,
                linecolor=settings.FOREGROUND_COLOR,
                tickcolor=settings.FOREGROUND_COLOR,
                ticks='outside',
                zeroline=False,
                showline=False,
                showgrid=False,
                range=axis_range,
                showticklabels=True,
                tickmode='array',
                tickvals=locations,
                ticktext=labels,
                tickfont=dict(
                    family=DEFAULT_FONT,
                    size=1.5 * axes.xaxis.get_ticklabels()[0].get_fontsize(),
                    color=settings.FOREGROUND_COLOR)
            )

            if axis == 'b':
                axis_info.update(
                    title=viewer.axes.get_xlabel(),
                    titlefont=dict(
                        family=DEFAULT_FONT,
                        size=2 * axes.xaxis.get_label().get_size(),
                        color=settings.FOREGROUND_COLOR
                    )
                )
                axes_data['xaxis'] = axis_info
            elif axis == 'l':
                axis_info.update(
                    title=viewer.axes.get_ylabel(),
                    titlefont=dict(
                        family=DEFAULT_FONT,
                        size=2 * axes.yaxis.get_label().get_size(),
                        color=settings.FOREGROUND_COLOR
                    )
                )
                axes_data['yaxis'] = axis_info
            elif axis == 't':
                axis_info.update(overlaying='x', side='top')
                axes_data['xaxis2'] = axis_info
            elif axis == 'r':
                axis_info.update(overlaying='y', side='right')
                axes_data['yaxis2'] = axis_info
            else:
                continue

    return axes_data


def shape(viewer):
    xy_axes = sorted([viewer.state.x_att.axis, viewer.state.y_att.axis])
    return [viewer.state.reference_data.shape[i] for i in xy_axes]


def size_info(layer):
    state = layer.state
    if state.size_mode == 'Fixed':
       return state.size
    else:
        s = ensure_numerical(state.layer[state.size_att].ravel())
        size = 25 * (s - state.size_vmin) / (
                        state.size_vmax - state.size_vmin)
        size[np.isnan(size)] = 0
        size[size< 0] = 0
        return size


def colorscale_info(layer, interval, contrast_bias):
    if layer.state.v_min > layer.state.v_max:
        cmap = layer.state.cmap.reversed()
        bounds = [layer.state.v_max, layer.state.v_min]
    else:
        cmap = layer.state.cmap
        bounds = [layer.state.v_min, layer.state.v_max]
    mapped_bounds = STRETCHES[layer.state.stretch]()(contrast_bias(interval(bounds)))
    unmapped_space = np.linspace(0, 1, 60)
    mapped_space = np.linspace(mapped_bounds[0], mapped_bounds[1], 60)
    color_space = [cmap(b)[:3] for b in mapped_space]
    color_values = [tuple(256 * v for v in p) for p in color_space]
    colorscale = [[0, 'rgb{0}'.format(color_values[0])]] + \
                 [[u, 'rgb{0}'.format(c)] for u, c in zip(unmapped_space, color_values)] + \
                 [[1, 'rgb{0}'.format(color_values[-1])]]
    return mapped_bounds, colorscale


def layers_by_type(viewer):
    layers = sorted(layers_to_export(viewer), key=lambda lyr: lyr.zorder)
    scatter_layers, image_layers, image_subset_layers = [], [], []
    for layer in layers:
        if isinstance(layer.state, ImageLayerState):
            image_layers.append(layer)
        elif isinstance(layer.state, ImageSubsetLayerState):
            image_subset_layers.append(layer)
        elif isinstance(layer.state, ScatterLayerState):
            scatter_layers.append(layer)

    return dict(scatter=scatter_layers, image=image_layers, image_subset=image_subset_layers)


def full_view_transpose(viewer):
    state = viewer.state
    full_view, _agg_func, transpose = state.numpy_slice_aggregation_transpose
    full_view[state.x_att.axis] = slice(None)
    full_view[state.y_att.axis] = slice(None)
    for i in range(state.reference_data.ndim):
        if isinstance(full_view[i], slice):
            full_view[i] = slice_to_bound(full_view[i], state.reference_data.shape[i])

    return full_view, transpose


def empty_secondary_layer(viewer, secondary_x, secondary_y):
    bg = np.ones(shape(viewer))
    secondary_info = dict(z=bg,
                          colorscale=[[0, 'rgb(0,0,0)'], [1, 'rgb(0,0,0)']],
                          hoverinfo='skip',
                          opacity=0,
                          showscale=False,
                          xaxis='x2' if secondary_x else 'x',
                          yaxis='y2' if secondary_y else 'y'
                    )
    return Heatmap(**secondary_info)


def background_heatmap_layer(viewer):
    """
    This function creates an all-white heatmap which we can use as the bottom layer
    when the viewer is using colormap, to match what we see in glue
    """
    bg = np.ones(shape(viewer))
    bottom_color = (256, 256, 256)
    bottom_colorstring = 'rgb{0}'.format(bottom_color)
    bottom_info = dict(z=bg, hoverinfo='skip', opacity=1, showscale=False,
                       colorscale=[[0, bottom_colorstring], [1, bottom_colorstring]])
    return Heatmap(**bottom_info)


def traces_for_pixel_subset_layer(viewer, layer):
    state = layer.state
    subset_state = layer.layer.subset_state
    xmin, xmax = viewer.axes.get_xlim()
    ymin, ymax = viewer.axes.get_ylim()

    try:
        x, y = subset_state.get_xy(layer.layer.data, viewer.state.x_att.axis, viewer.state.y_att.axis)
        line_data = dict(
            mode="lines",
            marker=dict(
                color=state.color
            ),
            opacity = state.alpha * 0.5,
            name = state.layer.label,
            legendgroup=uuid4().hex
        )

        x_line_data = {**line_data, 'x': [x, x], 'y': [ymin, ymax], 'showlegend': True}
        y_line_data = {**line_data, 'x': [xmin, xmax], 'y': [y, y], 'showlegend': False}
        return [Scatter(**x_line_data), Scatter(**y_line_data)]
    except IncompatibleAttribute:
        return []


def traces_for_nonpixel_subset_layer(viewer, layer, full_view, transpose):
    layer_state = layer.state
    subset_state = layer.layer.subset_state
    ref_data = viewer.state.reference_data
    color = fixed_color(layer)
    buffer = ref_data \
            .compute_fixed_resolution_buffer(full_view,
                                             target_data=ref_data,
                                             broadcast=False,
                                             subset_state=subset_state)
    if transpose:
        buffer = buffer.transpose()

    vf = np.vectorize(int)
    img = vf(buffer)
    rgb_color = to_rgb(color)

    # We use alpha = 0 for the bottom of the colorscale since we don't want
    # anything outside the subset to contribute
    colorscale = [[0, 'rgba(0,0,0,0)'], [1, 'rgb{0}'.format(tuple(256 * v for v in rgb_color))]]
    image_info = dict(
        z=img,
        colorscale=colorscale,
        hoverinfo='skip',
        xaxis='x',
        yaxis='y',
        name=layer_state.layer.label,
        opacity=layer_state.alpha * 0.5,
        showscale=False,
        showlegend=True
    )

    return [Heatmap(**image_info)]


def traces_for_scatter_layer(viewer, layer, hover_data=None, add_data_label=True):
    viewer_state = viewer.state
    layer_state = layer.state

    x = layer_state.layer[viewer_state.x_att]
    y = layer_state.layer[viewer_state.y_att]

    marker = dict(color=color_info(layer),
                  opacity = layer_state.alpha,
                  line=dict(width=0),
                  size=size_info(layer),
                  sizemin=1
            )

    if np.sum(hover_data) == 0:
        hoverinfo = 'skip'
        hovertext = None
    else:
        hoverinfo = 'text'
        hovertext = ['' for _ in range(layer_state.layer.shape[0])]
        for i in range(len(layer_state.layer.components)):
            if hover_data[i]:
                hover_values = layer_state.layer.components[i].label
                for k in range(len(hover_values)):
                    hovertext[k] = (hovertext[k] + '{}: {} <br>'
                                    .format(layer_state.layer.components[i].label,
                                            hover_values[k]))

    name = layer_state.layer.label
    if add_data_label and not isinstance(layer.layer, BaseData):
        name += " ({0})".format(layer.layer.data.label)
    scatter_info = dict(mode='markers',
                        marker=marker,
                        x=x,
                        y=y,
                        xaxis='x',
                        yaxis='y',
                        hoverinfo=hoverinfo,
                        hovertext=hovertext,
                        name=name
                    )

    return [Scatter(**scatter_info)]


def traces_for_image_layer(layer):
    layer_state = layer.state

    interval = ManualInterval(layer_state.v_min, layer_state.v_max)
    constrast_bias = ContrastBiasStretch(layer_state.contrast, layer_state.bias)
    array = layer.get_image_data
    if callable(array):
        array = array(bounds=None)
    if array is None:
        return []

    if np.isscalar(array):
        array = np.atleast_2d(array)

    img = STRETCHES[layer_state.stretch]()(constrast_bias(interval(array)))
    img[np.isnan(img)] = 0

    z_bounds, colorscale = colorscale_info(layer, interval, constrast_bias)
    image_info = dict(z=img,
                      colorscale=colorscale,
                      hoverinfo='skip',
                      xaxis='x',
                      yaxis='y',
                      zmin=z_bounds[0],
                      zmax=z_bounds[1],
                      name=layer_state.layer.label,
                      showscale=False,
                      showlegend=True,
                      opacity=layer_state.alpha
                )
    return [Heatmap(**image_info)]


def single_color_trace(viewer):
    img = viewer.axes._composite()
    img[:, :, :3] *= 256
    image_info = dict(z=img,
                      opacity=1,
                      hoverinfo='skip'
                )

    return Image(**image_info)


def traces(viewer, secondary_x=False, secondary_y=False, hover_selections=None, add_data_label=True):
    traces = []
    layers = layers_by_type(viewer)
    using_colormaps = viewer.state.color_mode == 'Colormaps'

    has_nonpixel_subset = any(not isinstance(layer.layer.subset_state, PixelSubsetState)
                              for layer in layers['image_subset'])
    if has_nonpixel_subset:
        full_view, transpose = full_view_transpose(viewer)

    if using_colormaps:
        traces.append(background_heatmap_layer(viewer))
        for layer in layers['image']:
            traces += traces_for_image_layer(layer)
    else:
        traces.append(single_color_trace(viewer))

    for layer in layers['image_subset']:
        subset_state = layer.layer.subset_state
        if isinstance(subset_state, PixelSubsetState):
            traces += traces_for_pixel_subset_layer(viewer, layer)
        else:
            traces += traces_for_nonpixel_subset_layer(viewer, layer, full_view, transpose)

    for layer in layers['scatter']:
        traces += traces_for_scatter_layer(viewer, layer,
                                           hover_data=hover_selections[layer.state.layer.label],
                                           add_data_label=add_data_label)

    if secondary_x or secondary_y:
        traces.append(empty_secondary_layer(viewer, secondary_x, secondary_y))

    return traces
