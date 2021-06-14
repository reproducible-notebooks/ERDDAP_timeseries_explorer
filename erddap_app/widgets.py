import ipyleaflet as ipyl
import ipywidgets as ipyw
import pendulum

from erddap_app.plots import stdname2geojson, update_timeseries_plot

# from requests import HTTPError


# def map_click_handler(event=None, id=None, properties=None, feature=None):
#     """The map_click_handler function updates the time series plot when a station marker is clicked"""

#     dataset_id = properties["datasetID"]

#     min_time = pendulum.parse(widget_search_min_time.value)
#     max_time = pendulum.parse(widget_search_max_time.value)
#     constraints = {"time>=": min_time, "time<=": max_time}

#     standard_name = widget_std_names.value
#     widget_dsnames.value = dataset_id

#     try:
#         update_timeseries_plot(
#             e,
#             dataset=dataset_id,
#             standard_name=standard_name,
#             constraints=constraints,
#         )
#     except HTTPError:
#         print(
#             "No",
#             standard_name,
#             "data for this station. Please choose another station.",
#         )


def widget_replot_button_handler(change):
    """The widget_replot_button_handler function updates the time series plot when the
    Update TimeSeries button is selected"""
    from __main__ import (
        e,
        widget_dsnames,
        widget_plot_start_time,
        widget_plot_stop_time,
        widget_std_names,
    )

    plot_start_time = pendulum.parse(widget_plot_start_time.value)
    plot_stop_time = pendulum.parse(widget_plot_stop_time.value)

    constraints = {"time>=": plot_start_time, "time<=": plot_stop_time}
    dataset_id = widget_dsnames.value
    update_timeseries_plot(
        e,
        dataset=dataset_id,
        standard_name=widget_std_names.value,
        constraints=constraints,
    )


def widget_search_button_handler(change):
    """The widget_search_button_handler function updates the map when the
    Update Search button is selected"""
    from __main__ import (
        e,
        map,
        server,
        widget_dsnames,
        widget_search_max_time,
        widget_search_min_time,
        widget_std_names,
    )

    min_time = pendulum.parse(widget_search_min_time.value)
    max_time = pendulum.parse(widget_search_max_time.value)

    standard_name = widget_std_names.value

    features, datasets = stdname2geojson(
        e,
        standard_name,
        server.get("cdm_data_type"),
        min_time,
        max_time,
        server.get("skip_datasets"),
    )

    feature_layer = ipyl.GeoJSON(data=features)
    constraints = {"time>=": min_time, "time<=": max_time}
    # feature_layer.on_click(map_click_handler)
    map.layers = [map.layers[0], feature_layer]

    dataset_id = datasets[0]
    widget_dsnames.options = datasets
    widget_dsnames.value = dataset_id

    update_timeseries_plot(
        e,
        dataset=dataset_id,
        standard_name=standard_name,
        constraints=constraints,
    )


def f_widget_dsnames(datasets):
    """Create a dropdown menu widget with all the datasets names found"""
    dataset_id = datasets[0]
    widget_dsnames = ipyw.Dropdown(options=datasets, value=dataset_id)
    return widget_dsnames


def f_widget_std_names(server, valid_standard_names):
    """Create a dropdown menu widget with all the valid standard_name values found"""
    widget_std_names = ipyw.Dropdown(
        options=valid_standard_names,
        value=server.get("standard_name"),
    )
    return widget_std_names


def f_widget_search_min_time(server):
    """Create a text widget to enter the search minimum time for the datasets search"""
    widget_search_min_time = ipyw.Text(
        value=server.get("min_time").to_datetime_string(),
        description="Search Min",
        disabled=False,
    )
    return widget_search_min_time


def f_widget_search_max_time(server):
    """Create a text widget to enter the search maximum time for the datasets search"""
    widget_search_max_time = ipyw.Text(
        value=server.get("max_time").to_datetime_string(),
        description="Search Max",
        disabled=False,
    )
    return widget_search_max_time


# Create the Update Search button
widget_search_button = ipyw.Button(
    value=False,
    description="Update Search",
    disabled=False,
    button_style="",
)


def f_widget_plot_start_time(server):
    """Create a text widget to enter the search minimum time for the time series plot"""
    widget_plot_start_time = ipyw.Text(
        value=server.get("min_time").to_datetime_string(),
        description="Plot Min",
        disabled=False,
    )
    return widget_plot_start_time


def f_widget_plot_stop_time(server):
    """Create a text widget to enter the search maximum time for the time series plot"""
    widget_plot_stop_time = ipyw.Text(
        value=server.get("max_time").to_datetime_string(),
        description="Plot Max",
        disabled=False,
    )
    return widget_plot_stop_time


# Create the Update TimeSeries button
widget_replot_button = ipyw.Button(
    value=False,
    description="Update TimeSeries",
    disabled=False,
    button_style="",
)
