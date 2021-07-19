import ipywidgets as ipyw
from __main__ import server_name
from IPython.display import display

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


def point(dataset, lon, lat, nchar):
    """This function puts lon,lat and datasetID into a GeoJSON feature"""
    geojsonFeature = {
        "type": "Feature",
        "properties": {"datasetID": dataset, "short_dataset_name": dataset[:nchar]},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }
    geojsonFeature["properties"]["style"] = {"color": "Grey"}
    return geojsonFeature


def search_datasets(e, standard_name, cdm_data_type, min_time, max_time, skip_datasets):
    """This function finds all the datasets with a given standard_name in
    the specified time period, and return GeoJSON"""

    search_url = e.get_search_url(
        response="csv",
        cdm_data_type=cdm_data_type.lower(),
        items_per_page=100000,
        standard_name=standard_name,
        min_time=min_time,
        max_time=max_time,
    )
    try:
        df = pd.read_csv(urlopen(search_url))

        for skip_dataset in skip_datasets:
            try:
                row = df.loc[df["Dataset ID"] == skip_dataset].index[0]
                df.drop(row, inplace=True)
            except IndexError:  # this error arises when the stdname doesn't have any datasets to be skipped.
                pass

    except HTTPError:
        df = pd.DataFrame([])

    return df


def all_datasets_locations(e, cdm_data_type, min_time, max_time):
    """This function returns the lon,lat values from all datasets"""
    url_dset = (
        f"{e.server}"
        "/tabledap/allDatasets.csv?"
        "datasetID,minLongitude,minLatitude&"
        f'cdm_data_type="{cdm_data_type}"'
        f"&minTime<={max_time.to_datetime_string()}"
        f"&maxTime>={min_time.to_datetime_string()}"
    )

    url_dataset = quote(url_dset, safe=":/?&= ")
    del url_dset
    df = pd.read_csv(urlopen(url_dataset), skiprows=[1])
    return df


def stdname2geojson(e, standard_name, cdm_data_type, min_time, max_time, skip_datasets):
    """This function returns GeoJSON containing lon, lat and dataset ID
    for all matching stations"""

    dfsd = search_datasets(
        e,
        standard_name,
        cdm_data_type,
        min_time,
        max_time,
        skip_datasets,
    )
    if not dfsd.empty:
        datasets = dfsd["Dataset ID"].values

        dfad = all_datasets_locations(e, cdm_data_type, min_time, max_time)
        df = dfad[dfad["datasetID"].isin(dfsd["Dataset ID"])]
        geojson = {
            "features": [point(row[1], row[2], row[3], 3) for row in df.itertuples()],
        }
    else:
        geojson = {"features": []}
        datasets = []
    return geojson, datasets


def update_timeseries_plot(
    e=None,
    dataset=None,
    standard_name=None,
    constraints=None,
    title_len=18,
):
    """This function updates the time series plot when the Update Search
    or the Update TimeSeries button is selected."""
    from erddap_app.layout import figure

    df, var = get_timeseries(
        e,
        dataset=dataset,
        standard_name=standard_name,
        constraints=constraints,
    )
    figure.marks[0].x = df.index
    figure.marks[0].y = df[var]
    figure.title = f"{dataset[:title_len]} - {var}"


def get_timeseries(e, dataset=None, standard_name=None, constraints=None):
    """This function returns the specified dataset time series values as a Pandas dataframe"""

    var = e.get_var_by_attr(
        dataset_id=dataset,
        standard_name=lambda v: str(v).lower() == standard_name.lower(),
    )
    if var:
        var = var[0]
    else:
        raise ValueError(f"Cannot get data for {standard_name}.")
        # We should filter out only valid standard_names for each dataset!
        # df = pd.read_csv(e.get_info_url(response="csv"))
        # df.loc[df["Attribute Name"] == "standard_name"]["Value"].values

    download_url = e.get_download_url(
        dataset_id=dataset,
        constraints=constraints,
        variables=["time", var],
        response="csv",
    )

    df = pd.read_csv(
        urlopen(download_url),
        index_col="time",
        parse_dates=True,
        skiprows=[1],
    )
    return df, var


def remove_qcstdnames(standard_names):
    """This cell specifies the standard names to be skipped, such as
    quality control-related and time-invariant variables"""

    qc = re.compile("^.*(qc)$|^.*(data_quality)$|^.*(flag)$")
    qc_stdnames = list(filter(qc.search, standard_names))
    del qc

    skip_stdnames = [
        "depth",
        "latitude",
        "longitude",
        "platform",
        "station_name",
        "time",
        "offset_time",
        "altitude",
        "battery_voltage",
        "panel_temperature",
        "webcam",
    ]

    skip_stdnames.extend(qc_stdnames)
    del qc_stdnames

    for skip_stdname in skip_stdnames:
        try:
            standard_names.remove(skip_stdname)
        except ValueError:
            pass
    del skip_stdname

    return standard_names


def get_valid_stdnames(server_name):
    """Find all the `standard_name` attributes that exist on
    this ERDDAP endpoint, using [ERDDAP's "categorize" service]
    (http://www.neracoos.org/erddap/categorize/index.html)"""

    server = servers[server_name]
    server_url = server.get("url")

    # global e
    e = ERDDAP(server=server_url, protocol="tabledap")

    url_standard_names = f"{server_url}/categorize/standard_name/index.csv"
    df = pd.read_csv(urlopen(url_standard_names), skiprows=[1, 2])
    standard_names = list(df["Category"].values)

    standard_names = remove_qcstdnames(standard_names)

    valid_standard_names = []
    count = 0

    print(
        "Checking the variables available for this server. This might take up to a couple of minutes...\n",
    )

    for standard_name in standard_names:

        count += 1

        if count == np.floor(len(standard_names) / 2):
            print("Halfway there...\n")
        elif count == np.floor((len(standard_names) / 4) * 3):
            print("Almost done...\n")
        elif count == (len(standard_names)):
            print("Done!")

        features, datasets = stdname2geojson(
            e,
            standard_name,
            server.get("cdm_data_type"),
            server.get("min_time"),
            server.get("max_time"),
            server.get("skip_datasets"),
        )

        if len(datasets) > 0:  # if there is at least one dataset with this data

            var = e.get_var_by_attr(
                dataset_id=datasets[0],
                standard_name=lambda v: str(v).lower() == standard_name.lower(),
            )

            if var != []:
                valid_standard_names.append(standard_name)

        del features, datasets

    return valid_standard_names, server, e


def plot_datasets(server, e):
    """This defines the initial ipyleaflet map"""

    map = ipyl.Map(
        center=server.get("center"),
        zoom=server.get("zoom"),
        layout=dict(width="750px", height="350px"),
    )

    features, datasets = stdname2geojson(
        e,
        server.get("standard_name"),
        server.get("cdm_data_type"),
        server.get("min_time"),
        server.get("max_time"),
        server.get("skip_datasets"),
    )

    feature_layer = ipyl.GeoJSON(data=features)

    # feature_layer.on_click(map_click_handler(e=e))
    map.layers = [map.layers[0], feature_layer]
    return map, feature_layer, datasets


def plot_timeseries(server, e, dataset_id):
    """This defines the initial bqplot time series plot"""
    dt_x = bq.DateScale()
    sc_y = bq.LinearScale()

    constraints = {"time>=": server.get("min_time"), "time<=": server.get("max_time")}

    df, var = get_timeseries(
        e=e,
        dataset=dataset_id,
        standard_name=server.get("standard_name"),
        constraints=constraints,
    )
    def_tt = bq.Tooltip(fields=["y"], formats=[".2f"], labels=["value"])
    time_series = bq.Lines(
        x=df.index,
        y=df[var],
        scales={"x": dt_x, "y": sc_y},
        tooltip=def_tt,
    )
    ax_x = bq.Axis(scale=dt_x, label="Time")
    ax_y = bq.Axis(scale=sc_y, orientation="vertical")
    figure = bq.Figure(marks=[time_series], axes=[ax_x, ax_y])
    figure.title = f"{dataset_id[:18]} - {var}"
    figure.layout.height = "300px"
    figure.layout.width = "800px"
    return figure


def space():
    ispace = ipyw.HTML(
        value='<style>  .space {margin-bottom: 6.5cm;}</style><p class="space"> </p>',
        placeholder="",
        description="",
    )
    return ispace


def widget_replot_button_handler(change):
    """The widget_replot_button_handler function updates the time series plot when the
    Update TimeSeries button is selected"""
    from erddap_app.layout import (
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
    from erddap_app.layout import (
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
