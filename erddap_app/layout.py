import numpy as np
import pandas as pd
import datetime

import re
from urllib.parse import quote
from requests import HTTPError

import hvplot.pandas
import bokeh
from bokeh.models import HoverTool
import holoviews as hv
import panel as pn
from holoviews.element.tiles import OSM

from erddapy import ERDDAP
from erddapy.url_handling import urlopen

from erddap_app.config import servers

from IPython.display import display

from bokeh.models.formatters import DatetimeTickFormatter
formatter = DatetimeTickFormatter(days="%d/%m/%y")
utcnow = datetime.datetime.utcnow() 

hv.extension("bokeh")
pn.extension()

pd.set_option('mode.chained_assignment',None) # silence some stupid warning from pandas

hover1 = HoverTool(
    tooltips=[
        ( 'latitude', '@latitude'),
        ( 'longitude', '@longitude'),
        ( 'dataset', '@datasetID'),
   ],
    formatters={
        'latitude' : 'numeral',
        'longitude' : 'numeral',
    },
)


def create_dyndsmap():
    trange = np.arange(datetime.datetime(2011,1,1), 
                   utcnow, 
                   datetime.timedelta(days=1)
                   )
    # says that the function above has to do with a dynamic map, and each map will be calculated 
    # for each different stdname and each timerange
    dyndsmap = hv.DynamicMap(plot_dsmap, kdims=['Stdnames','TimeRange'])
    dyndsmap = dyndsmap.redim.values(Stdnames=valid_stdnames, TimeRange=trange)

    # pn.bind declares that the function load_stdnames should be re-run when the stdname and/or timerange argument
    # changes, due to changes in the stdnames_menu / dsname_date widget value.
    # function, its arguments and which widgets will have the values for the arguments
    dyndsmap = hv.DynamicMap(pn.bind(plot_dsmap, 
                                     stdname=wstdname_menu, 
                                     timerange=wstdname_date,
                                    )
                             )
#                             , streams=create_stream()) 
    
    return dyndsmap


def f_wstdname_menu(valid_stdnames):
    wstdname_menu = pn.widgets.Select(name='Choose a variable',
                                      options=valid_stdnames, 
                                      value=server.get("standard_name")
                                 )
    return wstdname_menu


def f_wds_menu():
    global dsnames # create_dynplot needs it
    df = get_datasets(e,
                  server.get("standard_name"),
                  server.get("cdm_data_type"),
                  wstdname_date.value_start, 
                  wstdname_date.value_end, 
                  server.get("skip_datasets")
                  )
    dsnames = list(df.datasetID.values)

    # this widget depends on the wstdname_menu.value pra poder achar os valores disponíveis como opções
    wds_menu = pn.widgets.Select(name='Choose a dataset',
                                 options=dsnames,        
                                 ) 
    return wds_menu


def plot_tseries(dataset,timerange,stdname):    
    
    constraints = {"time>=": timerange[0], "time<=": timerange[1]}
    
    df_tseries, var_tseries, unit_tseries = get_timeseries(e=e,
                                                        dataset=dataset,            # from dswidgets
                                                        stdname=wstdname_menu.value,# from stdwidgets
                                                        constraints=constraints,    # from dswidgets
                                                        )
    
    # determine ylabel
    ylabel = df_tseries.columns[0] 
    ylabel.replace("_", " ")
    
    # determine title
    dsname = dataset.replace("_", " ") 
    varname = df_tseries.columns[0].replace("_", " ")

    # plot
    tseries = df_tseries.hvplot(kind='line',
                                ylabel=unit_tseries,
                                title=f"{dsname}   -   {varname}",
                                grid=True,
                                xticks=8,
                                xformatter=formatter,
                                )
    return tseries


def update_wds_menu(event):
        df = get_datasets(e,
                          wstdname_menu.value, 
                          server.get("cdm_data_type"), # what's this for, again?
                          wstdname_date.value_start, 
                          wstdname_date.value_end, 
                          server.get("skip_datasets")
                         )
        dsnames = list(df.datasetID.values)
        wds_menu.options = dsnames


def update_wds_date(event):
        wds_date.value = wstdname_date.value


def get_dsinfo(e, stdname, cdm_data_type, min_time, max_time, skip_datasets):
    """This function finds all the datasets with a given standard_name in
    the specified time period, and return GeoJSON"""

    search_url = e.get_search_url(
        response="csv",
        cdm_data_type=cdm_data_type.lower(),
        items_per_page=100000,
        standard_name=stdname,
        min_time=min_time,
        max_time=max_time,
    )
    try:
        df = pd.read_csv(urlopen(search_url))

        for skip_dataset in skip_datasets:
            try:
                row = df.loc[df["Dataset ID"] == skip_dataset].index[0]
                df.drop(row, inplace=True)
            except IndexError:
                pass

    except HTTPError:
        df = pd.DataFrame([])

    return df


def get_dslocation(e, cdm_data_type, min_time, max_time):
    """This function returns the lon,lat values from all datasets"""
    max_time_str = max_time.strftime("%Y-%m-%d %H:%M:%S")
    min_time_str = min_time.strftime("%Y-%m-%d %H:%M:%S")

    url_dset = (
        f"{e.server}"
        "/tabledap/allDatasets.csv?"
        "datasetID,minLongitude,minLatitude&"
        f'cdm_data_type="{cdm_data_type}"'
        f"&minTime<={max_time_str}"
        f"&maxTime>={min_time_str}"
    )

    url_dataset = quote(url_dset, safe=":/?&= ")
    del url_dset
    df = pd.read_csv(urlopen(url_dataset), skiprows=[1])

    return df


def get_datasets(e, stdname, cdm_data_type, min_time, max_time, skip_datasets):
    """This function returns GeoJSON containing lon, lat and dataset ID
    for all matching stations"""

    dfsd = get_dsinfo(
        e,
        stdname,
        cdm_data_type,
        min_time,
        max_time,
        skip_datasets,
    )

    if not dfsd.empty:
        dfad = get_dslocation(
            e,
            cdm_data_type,
            min_time,
            max_time,
        )
        df = dfad[dfad["datasetID"].isin(dfsd["Dataset ID"])]
        df.rename({'minLongitude':'longitude','minLatitude':'latitude'},axis='columns', inplace=True)
    else:
        df = pd.DataFrame()

    return df


def get_timeseries(e, dataset=None, stdname=None, constraints=None):
    """This function returns the specified dataset time series values as a Pandas dataframe"""

    var = e.get_var_by_attr(
        dataset_id=dataset,
        standard_name=lambda v: str(v).lower() == stdname.lower(),
    )
    if var:
        var = var[0]
    else:
        raise ValueError(f"Cannot get data for {stdname}.")
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
    )

    # getting the units for y-axis label
    unit = df.iloc[0, 0]

    # dropping the line with the unit
    df = df.drop(labels=df.index[0])

    # adjusting the data types
    df.index = pd.to_datetime(
        df.index,
        utc=True,
    )  # df.time = df.time.astype('datetime64[ns]')
    df[var] = df[var].astype(float)

    return df, var, unit


def remove_qcstdnames(stdnames):
    """This cell specifies the standard names to be skipped, such as
    quality control-related and time-invariant variables"""

    qc = re.compile("^.*(qc)$|^.*(data_quality)$|^.*(flag)$")
    qc_stdnames = list(filter(qc.search, stdnames))
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
            stdnames.remove(skip_stdname)
        except ValueError:
            pass
    del skip_stdname

    return stdnames


def get_valid_stdnames(server_name):
    """Find all the `standard_name` attributes that exist on
    this ERDDAP endpoint, using [ERDDAP's "categorize" service]
    (http://www.neracoos.org/erddap/categorize/index.html)"""

    server = servers[server_name]
    server_url = server.get("url")

    e = ERDDAP(server=server_url, protocol="tabledap")

    url_stdnames = f"{server_url}/categorize/standard_name/index.csv"
    df = pd.read_csv(urlopen(url_stdnames), skiprows=[1, 2])
    stdnames = list(df["Category"].values)

    stdnames = remove_qcstdnames(stdnames)

    valid_stdnames = []
    count = 0

    display(pn.Column(pn.panel(progressbar.name), progressbar))

    for stdname in stdnames:

        count += 1

        progressbar.value = int(count / (len(stdnames)) * 100)

        df_stdname = get_datasets(
            e,
            stdname,
            server.get("cdm_data_type"),
            server.get("min_time"),
            server.get("max_time"),
            server.get("skip_datasets"),
        )

        if not df_stdname.empty:

            var = e.get_var_by_attr(
                dataset_id=df_stdname.datasetID.values[0],
                standard_name=lambda v: str(v).lower() == stdname.lower(),
            )

            if var != []:
                valid_stdnames.append(stdname)

    return valid_stdnames, server, e


def plot_dsmap(stdname, timerange):

    df_dsmap = get_datasets(
        e,
        stdname,
        server.get("cdm_data_type"),
        timerange[0],
        timerange[1],
        server.get("skip_datasets"),
    )

    easting, northing = hv.util.transform.lon_lat_to_easting_northing(
        df_dsmap.minLongitude,
        df_dsmap.minLatitude,
    )
    df_dsmap.loc[:, "easting"] = easting
    df_dsmap["northing"] = northing

    dsmap = hv.Points(df_dsmap,kdims=['easting','northing'],
                              ).opts(size=5,
                                     color='black',
                                     tools=['tap',hover1],
                                     alpha=0.4,
                                     )

    return dsmap


progressbar = pn.indicators.Progress(
    name="Checking the variables available for this server",
    bar_color="info",
    value=0,
    width=200,
)


wstdname_date = pn.widgets.DateRangeSlider(
    start=datetime.datetime(2011, 1, 1),
    end=datetime.datetime.today(),
    value=(
        datetime.datetime.today() - datetime.timedelta(days=14),
        datetime.datetime.today(),
    ),
)


wds_date = pn.widgets.DateRangeSlider(
    name="Limits for the timeseries plot",
    start=datetime.datetime(2011, 1, 1),
    end=datetime.datetime.today(),
    value=(wstdname_date.value_start, wstdname_date.value_end),
)
