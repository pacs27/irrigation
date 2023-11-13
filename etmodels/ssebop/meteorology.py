import ee

def retrievePrecip(metadate, location, window_days=10, scale=None):
    startDate = ee.Date(metadate).advance(-window_days, 'day')
    endDate = ee.Date(metadate).advance(-1, 'day')

    collection = ee.ImageCollection("NOAA/CFSV2/FOR6H")
    
    # print("Target scale = ", ee.Image(collection.first()).select('Precipitation_rate_surface_6_Hour_Average').projection().nominalScale().getInfo())
    # print("Image id = ", ee.Image(collection.first()).select('Precipitation_rate_surface_6_Hour_Average').getInfo()['id'])
    # function to sum the values by day
    def sumPrecip(dayOffset, start_):
        start = start_.advance(dayOffset, 'days')
        end = start.advance(1, 'days')
        return collection.select('Precipitation_rate_surface_6_Hour_Average') \
                      .filterDate(start, end) \
                      .sum() \
                      .set('system:time_start', start.millis())

    # function to extract the precipitation values
    def extractPrecip(image):
        # convert from kg/m^2/s to mm/s over 6 hours
        precip_conversion_factor = ee.Number(6 * 60 * 60) # num hours in sample * num mins * num secs

        # target_scale = scale if scale else image.projection().nominalScale()
        

        precip_value = image.select('Precipitation_rate_surface_6_Hour_Average').reduceRegion(
          reducer=ee.Reducer.first(),
          geometry=location.c
          entroid(),
          scale=22264,
        ).get('Precipitation_rate_surface_6_Hour_Average')
        precip_value = ee.Number(precip_value)

        return ee.Feature(None, {
          'precip_value': precip_value.multiply(precip_conversion_factor),
          'date': image.date().format('yyyy-MM-dd'),
          'system:time_start': image.date().millis()
        })

    # create a list of dates to use to extract precip values
    numberOfDays = endDate.difference(startDate, 'days')
    daily = ee.ImageCollection(
                        ee.List.sequence(0, numberOfDays) \
                            .map(lambda x: sumPrecip(x, startDate))
                    )

    # calculate the total precipitation for each of prior X days
    # extract as features
    precip_ts = ee.FeatureCollection(daily.map(extractPrecip)) \
                  .sort('date', opt_ascending=False)

    return precip_ts.aggregate_array('precip_value')