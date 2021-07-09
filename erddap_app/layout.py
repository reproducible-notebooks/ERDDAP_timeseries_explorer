import ipywidgets as ipyw
from __main__ import server_name

from erddap_app.plots import get_valid_stdnames, plot_datasets, plot_timeseries, space
from erddap_app.widgets import (
    f_widget_dsnames,
    f_widget_plot_start_time,
    f_widget_plot_stop_time,
    f_widget_search_max_time,
    f_widget_search_min_time,
    f_widget_std_names,
    widget_replot_button,
    widget_replot_button_handler,
    widget_search_button,
    widget_search_button_handler,
)

# gets standard names
valid_standard_names, server, e = get_valid_stdnames(server_name)


# Creates map and timeseries plot
map, feature_layer, datasets = plot_datasets(server, e)
figure = plot_timeseries(server, e, datasets[0])


# Creates widgets
widget_std_names = f_widget_std_names(server, valid_standard_names)
widget_search_min_time = f_widget_search_min_time(server)
widget_search_max_time = f_widget_search_max_time(server)
widget_plot_start_time = f_widget_plot_start_time(server)
widget_plot_stop_time = f_widget_plot_stop_time(server)
widget_dsnames = f_widget_dsnames(datasets)

widget_replot_button.on_click(widget_replot_button_handler)
widget_search_button.on_click(widget_search_button_handler)

# Specifies the widget layout
ispace = space()

form_item_layout = ipyw.Layout(
    display="flex",
    flex_flow="column",
    justify_content="space-between",
)

col1 = ipyw.Box([map, figure], layout=form_item_layout)
col2 = ipyw.Box(
    [
        widget_std_names,
        widget_search_min_time,
        widget_search_max_time,
        widget_search_button,
        ispace,
        widget_dsnames,
        widget_plot_start_time,
        widget_plot_stop_time,
        widget_replot_button,
    ],
    layout=form_item_layout,
)

form_items = [col1, col2]

form = ipyw.Box(
    form_items,
    layout=ipyw.Layout(
        display="flex",
        flex_flow="row",
        border="solid 2px",
        align_items="flex-start",
        width="100%",
    ),
)

display(form)
