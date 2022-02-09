# ERDDAP Timeseries Explorer

Idea is to make a simple, interactive ERDDAP time series viewer in a notebook using Jupyter widgets

- do a query to find the lon,lat points of all time series stations that contain a specified `standard_name` variable
- put station markers on a map
- click a station and get a time series plot from the last two weeks of data
- select a different `standard_name` variable from a drop down menu

### Run Notebook on binder:
[![Open In SageMaker Studio Lab](https://studiolab.sagemaker.aws/studiolab.svg)](https://studiolab.sagemaker.aws/import/github/https://github.com/reproducible-notebooks/ERDDAP_timeseries_explorer/blob/master/ERDDAP_timeseries_explorer.ipynb)
