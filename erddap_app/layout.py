import re
from urllib.parse import quote

import bqplot as bq
import ipyleaflet as ipyl
import ipywidgets as ipyw
import numpy as np
import pandas as pd
import pendulum
from erddapy import ERDDAP
from erddapy.url_handling import urlopen
from IPython.display import display
from requests import HTTPError

from erddap_app.config import servers


def get_dsinfo(e, stdname, cdm_data_type, min_time, max_time, skip_datasets): 
    """This function finds all the datasets with a given standard_name in
    the specified time period, and return GeoJSON"""

    search_url = e.get_search_url(response="csv",
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

    dfsd = get_dsinfo(e,
                      stdname,
                      cdm_data_type,
                      min_time,
                      max_time,
                      skip_datasets,
                      )

    if not dfsd.empty:
        dfad = get_dslocation(e,
                              cdm_data_type, 
                              min_time, 
                              max_time,
                             )
        df = dfad[dfad["datasetID"].isin(dfsd["Dataset ID"])]
        
    else:
        df = pd.DataFrame()

    return df 


def get_timeseries(e, dataset=None, stdname=None, constraints=None):
    """This function returns the specified dataset time series values as a Pandas dataframe"""

    var = e.get_var_by_attr(dataset_id=dataset,
                            standard_name=lambda v: str(v).lower() == stdname.lower(),
                           )
    if var:
        var = var[0]
    else:
        raise ValueError(f"Cannot get data for {stdname}.")
        # We should filter out only valid standard_names for each dataset!
        # df = pd.read_csv(e.get_info_url(response="csv"))
        # df.loc[df["Attribute Name"] == "standard_name"]["Value"].values

    download_url = e.get_download_url(dataset_id=dataset,
                                      constraints=constraints,
                                      variables=["time", var],
                                      response="csv",
                                     )

    df = pd.read_csv(urlopen(download_url),
                     index_col="time",
                    )
    
    # getting the units for y-axis label
    unit = df.iloc[0,0]

    # dropping the line with the unit
    df=df.drop(labels=df.index[0])

    # adjusting the data types
    df.index = pd.to_datetime(df.index, utc=True) # df.time = df.time.astype('datetime64[ns]')
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
