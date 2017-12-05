
# coding: utf-8

# # Explore ERDDAP timeseries data using Jupyter Widgets
# Inspired by [Jason Grout's excellent ESIP Tech Dive talk on "Jupyter Widgets"](https://youtu.be/CVcrTRQkTxo?t=2596), this notebook uses the `ipyleaflet` and `bqplot` widgets
# to interactively explore the last two weeks of time series data from an ERDDAP Server. Select a `standard_name` from the list, then click a station to see the time series.  

# NOTE: To access a protected ERDDAP endpoint is protected, you can add a `~/.netrc` file like this:
# ```
# machine cgoms.coas.oregonstate.edu
# login <username>
# password <password>
# ```

# In[ ]:

import numpy as np
import pandas as pd
import requests
from io import StringIO


# `pendulum` is a drop-in replacement for `datetime`, with more useful functions

# In[ ]:

import pendulum


# `ipyleaflet` and `bqplot` are both Jupyter widgets, so can interact with Python like any other widget.  Since we want to click on a map in a notebook and get an interactive time series plot, they are perfect tools to use here. 

# In[ ]:

import ipyleaflet as ipyl
import bqplot as bq
import ipywidgets as ipyw


# To make working with ERDDAP simpler, we use `erddapy`, a high-level python interface to ERDDAP's RESTful API

# In[ ]:

from erddapy import ERDDAP


# This code should work with minor modifications on any ERDDAP (v1.64+) endpoint that has `cdm_data_type=timeseries` or `cdm_data_type=point` datasets.  Change the values for other ERDDAP endpoints or regions of interest

# In[ ]:

endpoint = 'http://www.neracoos.org/erddap'

initial_standard_name = 'significant_height_of_wind_and_swell_waves'

nchar = 3 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [42.5, -68]
zoom = 6

now = pendulum.utcnow()
max_time = now
min_time = now.subtract(weeks=2)


# In[ ]:

endpoint = 'https://cgoms.coas.oregonstate.edu/erddap'

initial_standard_name = 'air_temperature'

nchar = 3 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [44, -124]
zoom = 6

now = pendulum.utcnow()
max_time = now
min_time = now.subtract(weeks=2) 


# In[ ]:

e = ERDDAP(server_url=endpoint)


# Find all the `standard_name` attributes that exist on this ERDDAP endpoint, using [ERDDAP's "categorize" service](http://www.neracoos.org/erddap/categorize/index.html)

# In[ ]:

url='{}/categorize/standard_name/index.csv'.format(endpoint)

r1 = requests.get(url, verify=True)

df = pd.read_csv(StringIO(r1.text), skiprows=[1, 2])
vars = df['Category'].values


# Create a dropdown menu widget with all the `standard_name` values found

# In[ ]:

dpdown = ipyw.Dropdown(options=vars, value=initial_standard_name)


# This function convert an ERDDAP timeseries CSV response to a Pandas dataframe

# In[ ]:

def download_csv(url):
    r = requests.get(url, verify=True)
    return pd.read_csv(StringIO(r.text), index_col='time', parse_dates=True, skiprows=[1])


# This function puts lon,lat and datasetID into a GeoJSON feature

# In[ ]:

def point(dataset, lon, lat, nchar):
    geojsonFeature = {
        "type": "Feature",
        "properties": {
            "datasetID": dataset,
            "short_dataset_name": dataset[:nchar]
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        }
    };
    geojsonFeature['properties']['style'] = {'color': 'Grey'}
    return geojsonFeature


# This function finds all the datasets with a given standard_name in the specified time period, and return GeoJSON

# In[ ]:

def adv_search(e, standard_name, cdm_data_type, min_time, max_time):
    try:
        search_url = e.get_search_url(response='csv', cdm_data_type=cdm_data_type.lower(), items_per_page=100000,
                                  standard_name=standard_name, min_time=min_time, max_time=max_time)
        r = requests.get(search_url, verify=True)
        df = pd.read_csv(StringIO(r.text))
    except:
        df = []
        if len(var)>14:
            v = '{}...'.format(standard_name[:15])
        else:
            v = standard_name
        figure.title = 'No {} found in this time range. Pick another variable.'.format(v)
        figure.marks[0].y = 0.0 * figure.marks[0].y
    return df


# This function returns the lon,lat vlaues from allDatasets

# In[ ]:

def alllonlat(e, cdm_data_type, min_time, max_time):
    url='{}/tabledap/allDatasets.csv?datasetID%2CminLongitude%2CminLatitude&cdm_data_type=%22{}%22&minTime%3C={}&maxTime%3E={}'.format(e.server_url,cdm_data_type,max_time,min_time)
    r = requests.get(url, verify=True)
    df = pd.read_csv(StringIO(r.text), skiprows=[1])
    return df


# In[ ]:

def stdname2geojson(e, standard_name, min_time, max_time, nchar):
    '''return geojson containing lon, lat and datasetID for all matching stations'''
    # find matching datsets using Advanced Search
    dfa = adv_search(e, standard_name, cdm_data_type, min_time, max_time)
    if isinstance(dfa, pd.DataFrame):
        datasets = dfa['Dataset ID'].values
        # find lon,lat values from allDatasets 
        dfll = alllonlat(e, cdm_data_type, min_time, max_time)
        # extract lon,lat values of matching datasets from allDatasets dataframe
        dfr = dfll[dfll['datasetID'].isin(dfa['Dataset ID'])]
        # contruct the GeoJSON using fast itertuples
        geojson = {'features':[point(row[1],row[2],row[3],nchar) for row in dfr.itertuples()]}
    else:
        geojson = {'features':[]}
        datasets = []
    return geojson, datasets


# This function updates the time series plot when a station marker is clicked

# In[ ]:

def click_handler(event=None, id=None, properties=None):
    datasetID = properties['datasetID']
    kwargs = {'time%3E=': min_time, 'time%3C=': max_time}
    df, var = get_data(datasetID, dpdown.value, kwargs)
    figure.marks[0].x = df.index
    figure.marks[0].y = df[var]
    figure.title = '{} - {}'.format(properties['short_dataset_name'], var)


# This function updates the map when a new variable is selected

# In[ ]:

def update_dpdown(change):
    standard_name = change['new']
    data, datasets = stdname2geojson(e, standard_name, min_time, max_time, nchar)
    feature_layer = ipyl.GeoJSON(data=data)
    feature_layer.on_click(click_handler)
    map.layers = [map.layers[0], feature_layer]


# This specifies which function to use when a variable is selected from the dropdown list

# In[ ]:

dpdown.observe(update_dpdown, names=['value'])


# This function returns the specified dataset time series values as a Pandas dataframe

# In[ ]:

def get_data(dataset, standard_name, kwargs):
    var = e.get_var_by_attr(dataset_id=dataset, 
                    standard_name=lambda v: str(v).lower() == standard_name)[0]
    download_url = e.get_download_url(dataset_id=dataset, 
                                  variables=['time',var], response='csv', **kwargs)
    df = download_csv(download_url)
    return df, var


# This defines the initial `ipyleaflet` map 

# In[ ]:

map = ipyl.Map(center=center, zoom=zoom, layout=ipyl.Layout(width='650px', height='350px'))
data, datasets = stdname2geojson(e, initial_standard_name, min_time, max_time, nchar)
feature_layer = ipyl.GeoJSON(data=data)
feature_layer.on_click(click_handler)
map.layers = [map.layers[0], feature_layer]


# This defines the intitial `bqplot` time series plot

# In[ ]:

dt_x = bq.DateScale()
sc_y = bq.LinearScale()

initial_dataset = datasets[0]
kwargs = {'time%3E=': min_time, 'time%3C=': max_time}
df, var = get_data(initial_dataset, initial_standard_name, kwargs)
time_series = bq.Lines(x=df.index, y=df[var], scales={'x': dt_x, 'y': sc_y})
ax_x = bq.Axis(scale=dt_x, label='Time')
ax_y = bq.Axis(scale=sc_y, orientation='vertical')
figure = bq.Figure(marks=[time_series], axes=[ax_x, ax_y])
figure.title = '{} - {}'.format(initial_dataset[:nchar], var)
figure.layout.height = '300px'
figure.layout.width = '800px'


# This specifies the widget layout

# In[ ]:

ipyw.VBox([dpdown, map, figure])


# In[ ]:



