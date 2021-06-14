import pendulum

now = pendulum.now(tz="utc")

servers = {
    "ioos": {
        "url": "http://erddap.sensors.ioos.us/erddap",
        "standard_name": "sea_surface_wave_significant_height",
        "nchar": 9,
        "cdm_data_type": "TimeSeries",
        "center": [35, -100],
        "zoom": 3,
        "max_time": pendulum.parse("2017-11-11T00:00:00Z"),
        "min_time": pendulum.parse("2017-11-01T00:00:00Z"),
        "skip_datasets": [],
    },
    "whoi": {
        "url": "https://gamone.whoi.edu/erddap",
        "standard_name": "sea_water_temperature",
        "nchar": 9,
        "cdm_data_type": "TimeSeries",
        "center": [35, -100],
        "zoom": 3,
        "max_time": pendulum.parse("2011-05-15T00:00:00Z"),
        "min_time": pendulum.parse("2011-05-05T00:00:00Z"),
        "skip_datasets": [],
    },
    "ooi": {
        "url": "https://erddap-uncabled.oceanobservatories.org/uncabled/erddap",
        "standard_name": "sea_water_temperature",
        "nchar": 8,
        "cdm_data_type": "Point",
        "center": [35, -100],
        "zoom": 1,
        "max_time": pendulum.parse("2017-08-03T00:00:00Z"),
        "min_time": pendulum.parse("2017-08-01T00:00:00Z"),
        "skip_datasets": [],
    },
    "neracoos": {
        "url": "http://www.neracoos.org/erddap",
        "standard_name": "significant_height_of_wind_and_swell_waves",
        "nchar": 3,
        "cdm_data_type": "TimeSeries",
        "center": [42.5, -68],
        "zoom": 6,
        "max_time": now,
        "min_time": now.subtract(weeks=2),
        "skip_datasets": ["cwwcNDBCMet", "UNH_CML"],
    },
}
