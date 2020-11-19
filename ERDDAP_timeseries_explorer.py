
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

# In[1]:


import numpy as np
import pandas as pd


# In[2]:


import pendulum


# `ipyleaflet` and `bqplot` are both Jupyter widgets, so can interact with Python like any other widget.  Since we want to click on a map in a notebook and get an interactive time series plot, they are perfect tools to use here. 

# In[3]:


import ipyleaflet as ipyl
import bqplot as bq
import ipywidgets as ipyw


# To make working with ERDDAP simpler, we use `erddapy`, a high-level python interface to ERDDAP's RESTful API

# In[4]:


from erddapy import ERDDAP
from erddapy.url_handling import urlopen


# This code should work with minor modifications on any ERDDAP (v1.64+) endpoint that has `cdm_data_type=timeseries` or `cdm_data_type=point` datasets.  Change the values for other ERDDAP endpoints or regions of interest

# In[5]:


endpoint = 'http://erddap.sensors.ioos.us/erddap'

initial_standard_name = 'sea_surface_wave_significant_height'

nchar = 9 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [35, -100]
zoom = 3

min_time = pendulum.parse('2017-11-01T00:00:00Z')
max_time = pendulum.parse('2017-11-11T00:00:00Z')


# In[6]:


endpoint = 'https://gamone.whoi.edu/erddap'

initial_standard_name = 'sea_water_temperature'

nchar = 9 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [35, -100]
zoom = 3

min_time = pendulum.parse('2011-05-05T00:00:00Z')
max_time = pendulum.parse('2011-05-15T00:00:00Z')


# In[7]:


endpoint = 'https://erddap-uncabled.oceanobservatories.org/uncabled/erddap'

initial_standard_name = 'sea_water_temperature'

nchar = 8 # number of characters for short dataset name
cdm_data_type = 'Point'
center = [35, -100]
zoom = 1

min_time = pendulum.parse('2017-08-01T00:00:00Z')
max_time = pendulum.parse('2017-08-03T00:00:00Z')


# In[8]:


endpoint = 'https://cgoms.coas.oregonstate.edu/erddap'

initial_standard_name = 'air_temperature'

nchar = 8 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [44, -124]
zoom = 6

now = pendulum.now(tz='utc')
max_time = now
min_time = now.subtract(days=3)


# In[9]:


endpoint = 'http://ooivm1.whoi.net/erddap'

initial_standard_name = 'solar_panel_1_voltage'

nchar = 8 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [41.0, -70.]
zoom = 7

now = pendulum.now(tz='utc')
max_time = now
min_time = now.subtract(days=3)


# In[10]:


server = 'http://www.neracoos.org/erddap'

standard_name = 'significant_height_of_wind_and_swell_waves'
#standard_name = 'sea_water_temperature'

nchar = 3 # number of characters for short dataset name
cdm_data_type = 'TimeSeries'
center = [42.5, -68]
zoom = 6

now = pendulum.now(tz='utc')
search_max_time = now
search_min_time = now.subtract(weeks=2)


# In[11]:


e = ERDDAP(server=server, protocol='tabledap')


# Find all the `standard_name` attributes that exist on this ERDDAP endpoint, using [ERDDAP's "categorize" service](http://www.neracoos.org/erddap/categorize/index.html)

# In[12]:


url='{}/categorize/standard_name/index.csv'.format(server)
df = pd.read_csv(urlopen(url), skiprows=[1, 2])
standard_names = df['Category'].values


# Create a dropdown menu widget with all the `standard_name` values found

# In[13]:


widget_std_names = ipyw.Dropdown(options=standard_names, value=standard_name)


# Create a text widget to enter the search minimum time

# In[14]:


widget_search_min_time = ipyw.Text(
    value=search_min_time.to_datetime_string(),
    description='Search Min',
    disabled=False
)


# In[15]:


widget_search_max_time = ipyw.Text(
    value=search_max_time.to_datetime_string(),
    description='Search Max',
    disabled=False
)


# This function puts lon,lat and datasetID into a GeoJSON feature

# In[16]:


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

# In[17]:


def adv_search(e, standard_name, cdm_data_type, min_time, max_time):
    try:
        search_url = e.get_search_url(response='csv', cdm_data_type=cdm_data_type.lower(), items_per_page=100000,
                                  standard_name=standard_name, min_time=min_time, max_time=max_time)
        df = pd.read_csv(urlopen(search_url))
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

# In[18]:


def alllonlat(e, cdm_data_type, min_time, max_time):
    url='{}/tabledap/allDatasets.csv?datasetID%2CminLongitude%2CminLatitude&cdm_data_type=%22{}%22&minTime%3C={}&maxTime%3E={}'.format(e.server,
                        cdm_data_type,max_time.to_datetime_string(),min_time.to_datetime_string())
    df = pd.read_csv(urlopen(url), skiprows=[1])
    return df


# In[19]:


def stdname2geojson(e, standard_name, cdm_data_type, search_min_time, search_max_time):
    '''return geojson containing lon, lat and datasetID for all matching stations'''
    # find matching datsets using Advanced Search
    dfa = adv_search(e, standard_name, cdm_data_type, search_min_time, search_max_time)
    if isinstance(dfa, pd.DataFrame):
        datasets = dfa['Dataset ID'].values

        # find lon,lat values from allDatasets 
        dfll = alllonlat(e, cdm_data_type, search_min_time, search_max_time)
        # extract lon,lat values of matching datasets from allDatasets dataframe
        dfr = dfll[dfll['datasetID'].isin(dfa['Dataset ID'])]
        # contruct the GeoJSON using fast itertuples
        geojson = {'features':[point(row[1],row[2],row[3],3) for row in dfr.itertuples()]}
    else:
        geojson = {'features':[]}
        datasets = []
    return geojson, datasets


# The `map_click_handler` function updates the time series plot when a station marker is clicked

# In[20]:


def map_click_handler(event=None, id=None, properties=None):
    global dataset_id, standard_name
    print('map clicked')
    dataset_id = properties['datasetID']
    # get standard_name from dropdown widget
    standard_name = widget_std_names.value
    print(dataset_id, standard_name, constraints)
    widget_dsnames.value = dataset_id
    update_timeseries_plot(dataset=dataset_id, standard_name=standard_name, constraints=constraints)


# The `search_button_handler` function updates the map when the `Search` button is selected 

# In[21]:


def widget_replot_button_handler(change):
    global dataset_id, constraints
    plot_start_time = pendulum.parse(widget_plot_start_time.value)
    plot_stop_time = pendulum.parse(widget_plot_stop_time.value)

    constraints = {
    'time>=': plot_start_time,
    'time<=': plot_stop_time
    }
    dataset_id = widget_dsnames.value
    update_timeseries_plot(dataset=dataset_id, standard_name=standard_name, constraints=constraints)


# In[22]:


def widget_search_button_handler(change):
    global features, datasets, standard_name, dataset_id, constraints
    search_min_time = pendulum.parse(widget_search_min_time.value)
    search_max_time = pendulum.parse(widget_search_max_time.value)

    # get standard_name from dropdown widget
    standard_name = widget_std_names.value

    # get updated datsets and map features
    features, datasets = stdname2geojson(e, standard_name, cdm_data_type, search_min_time, search_max_time)
    # update map
    feature_layer = ipyl.GeoJSON(data=features)
    feature_layer.on_click(map_click_handler)
    map.layers = [map.layers[0], feature_layer]
    
   # widget_plot_start_time.value = widget_search_min_time.value
   # widget_plot_stop_time.value = widget_search_max_time.value

    # populate datasets widget with new info
    dataset_id = datasets[0]
    widget_dsnames.options = datasets
    widget_dsnames.value = dataset_id
    
    constraints = {
    'time>=': search_min_time,
    'time<=': search_max_time
    }
    print(dataset_id, standard_name, constraints)
    update_timeseries_plot(dataset=dataset_id, standard_name=standard_name, constraints=constraints)


# In[23]:


def update_timeseries_plot(dataset=None, standard_name=None, constraints=None, title_len=18):
    df, var = get_data(dataset=dataset, standard_name=standard_name, constraints=constraints)
    figure.marks[0].x = df.index
    figure.marks[0].y = df[var]
    figure.title = '{} - {}'.format(dataset[:title_len], var)


# In[24]:


widget_search_button = ipyw.Button(
    value=False,
    description='Update search',
    disabled=False,
    button_style='')


# In[25]:


widget_replot_button = ipyw.Button(
    value=False,
    description='Update TimeSeries',
    disabled=False,
    button_style='')


# In[26]:


widget_replot_button.on_click(widget_replot_button_handler)


# In[27]:


widget_search_button.on_click(widget_search_button_handler)


# In[28]:


widget_plot_start_time = ipyw.Text(
    value=search_min_time.to_datetime_string(),
    description='Plot Min',
    disabled=False
)


# In[29]:


widget_plot_stop_time = ipyw.Text(
    value=search_max_time.to_datetime_string(),
    description='Plot Max',
    disabled=False
)


# This function returns the specified dataset time series values as a Pandas dataframe

# In[30]:


def get_data(dataset=None, standard_name=None, constraints=None):
    print(dataset_id, standard_name, constraints)
    var = e.get_var_by_attr(dataset_id=dataset, 
                    standard_name=lambda v: str(v).lower() == standard_name.lower())[0]
    download_url = e.get_download_url(dataset_id=dataset, constraints=constraints,
                                  variables=['time',var], response='csv')
    df = pd.read_csv(urlopen(download_url), index_col='time', parse_dates=True, skiprows=[1])
    return df, var


# This defines the initial `ipyleaflet` map 

# In[31]:


map = ipyl.Map(center=center, zoom=zoom, layout=dict(width='750px', height='350px'))
features, datasets = stdname2geojson(e, standard_name, cdm_data_type, search_min_time, search_max_time)
dataset_id = datasets[0]
feature_layer = ipyl.GeoJSON(data=features)
feature_layer.on_click(map_click_handler)
map.layers = [map.layers[0], feature_layer]


# In[32]:


widget_dsnames = ipyw.Dropdown(options=datasets, value=dataset_id)


# This defines the intitial `bqplot` time series plot

# In[33]:


dt_x = bq.DateScale()
sc_y = bq.LinearScale()

constraints = {
    'time>=': search_min_time,
    'time<=': search_max_time
}

df, var = get_data(dataset=dataset_id, standard_name=standard_name, constraints=constraints)
def_tt = bq.Tooltip(fields=['y'], formats=['.2f'], labels=['value'])
time_series = bq.Lines(x=df.index, y=df[var], 
                       scales={'x': dt_x, 'y': sc_y}, tooltip=def_tt)
ax_x = bq.Axis(scale=dt_x, label='Time')
ax_y = bq.Axis(scale=sc_y, orientation='vertical')
figure = bq.Figure(marks=[time_series], axes=[ax_x, ax_y])
figure.title = '{} - {}'.format(dataset_id[:18], var)
figure.layout.height = '300px'
figure.layout.width = '800px'


# In[34]:


#Not currently using this (cell below setting "observe" to this function is commented out)
def widget_dsnames_handler(change):
    dataset_id = widget_dsnames.value
    constraints = {
    'time>=': search_min_time,
    'time<=': search_max_time
    }
    update_timeseries_plot(dataset=dataset_id, standard_name=standard_name, constraints=constraints)


# In[35]:


#widget_dsnames.observe(widget_replot_button_handler)


# In[36]:


#all this widget does it take up 7 cm of vertical space 
ispace = ipyw.HTML(
    value='<style>  .space {margin-bottom: 6.5cm;}</style><p class="space"> </p>',
    placeholder='',
    description='',
)


# This specifies the widget layout

# In[37]:


form_item_layout = ipyw.Layout(display='flex', flex_flow='column', justify_content='space-between')

col1 = ipyw.Box([map, figure], layout=form_item_layout)
col2 = ipyw.Box([widget_std_names, widget_search_min_time, widget_search_max_time, widget_search_button,
                ispace, widget_dsnames, widget_plot_start_time, widget_plot_stop_time, widget_replot_button], layout=form_item_layout)

form_items = [col1, col2]

form = ipyw.Box(form_items, layout=ipyw.Layout(display='flex', flex_flow='row', border='solid 2px',
    align_items='flex-start', width='100%'))

form

