# ERDDAP Timeseries Explorer

Idea is to make a simple, interactive ERDDAP time series viewer in a notebook using Jupyter widgets

- do a query to find the lon,lat points of all time series stations that contain a specified `standard_name` variable
- put station markers on a map 
- click a station and get a time series plot from the last two weeks of data 
- select a different `standard_name` variable from a drop down menu

Notebook in regular mode:
[![Binder](http://mybinder.org/badge.svg)](https://mybinder.org/v2/gh/reproducible-notebooks/ERDDAP_timeseries_explorer/master?filepath=ERDDAP_timeseries_explorer.ipynb)

Notebook in app-mode:
[![Binder](http://mybinder.org/badge.svg)](https://mybinder.org/v2/gh/reproducible-notebooks/app-mode?urlpath=%2Fapps%2fERDDAP_timeseries_explorer.ipynb)
