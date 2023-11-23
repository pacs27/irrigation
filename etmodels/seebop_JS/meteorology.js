function retrieve_precipitation_last_days(reference_day, location, window_days) {
    /*
    Retrieve precipitation for the last X days

    Parameters:
        :param reference_day: ee.Date 'YYYY-MM-dd'

        :param location: ee.Geometry.Point
            
        :param window_days: int

        :param scale: int
    
    Returns:
        ee.FeatureCollection with precipitation values for the last X days
    
    */
    if (window_days == undefined) {
        window_days = 10
    }

    var startDate = ee.Date(reference_day).advance(-window_days, 'day')
    var endDate = ee.Date(reference_day).advance(-1, 'day')

    var collection = ee.ImageCollection("NOAA/CFSV2/FOR6H")
    var collection_scale = collection.first().projection().nominalScale()

    function sumPrecip(dayOffset, start_) {
        var _start = start_.advance(dayOffset, 'days')
        var _end = _start.advance(1, 'days')
        return collection.select('Precipitation_rate_surface_6_Hour_Average')
            .filterDate(_start, _end)
            .sum()
            .set('system:time_start', _start.millis())
    }

    function extractPrecip(image) {
        // convert from kg/m^2/s to mm/s over 6 hours
        var precip_conversion_factor = ee.Number(6 * 60 * 60) // num hours in sample * num mins * num secs

        var precip_value = image.select('Precipitation_rate_surface_6_Hour_Average').reduceRegion(
            ee.Reducer.first(),
            location.centroid({'maxError': 1}),
            collection_scale
        ).get('Precipitation_rate_surface_6_Hour_Average')

        precip_value = ee.Number(precip_value)

        var precipitation_feature = ee.Feature(null, {
            'precip_value': precip_value.multiply(precip_conversion_factor),
            'date': image.date().format('yyyy-MM-dd'),
            'system:time_start': image.date().millis()
        })

        return precipitation_feature
    }


    // create a list of dates to use to extract precip values
    var numberOfDays = endDate.difference(startDate, 'days')
    var daily = ee.ImageCollection(
        ee.List.sequence(0, numberOfDays)
            .map(function (x) {
                return sumPrecip(x, startDate)
            }
            )
    )

    // calculate the total precipitation for each of prior X days
    // extract as features
    var precip_ts = ee.FeatureCollection(daily.map(extractPrecip))
        .sort('date',  false)

    precip_ts = precip_ts.aggregate_array('precip_value')


    return precip_ts
}


exports.make_meteorology = function () {
    return {
        "retrieve_precipitation_last_days": retrieve_precipitation_last_days,
    }
}