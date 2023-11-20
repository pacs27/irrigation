
var et_daily_file = require('users/franciscopuig/SSEBop/:et_daily');
var ssebop_model_file = require('users/franciscopuig/SSEBop/:ssebop_model');
var landsat_utils_file = require('users/franciscopuig/SSEBop/:landsat_utils');

var landsat_utils = landsat_utils_file.make_landsat_utils();
var ssebop_model = ssebop_model_file.make_ssebop_model();
function filter_collection_list(start_date, end_date, collections) {
    function filter(collections, collection_to_remove) {

        for (var i = 0; i < collections.length; i++) {
            if (collections[i] == collection_to_remove) {
                collections.splice(i, 1);
            }
        }
        return collections
    }
    // check if end date is less than 1984-01-01
    if (end_date <= "1984-01-01") {
        // exclude LT05
        collections = filter(collections, "LANDSAT/LT05/C02/T1_L2")
    }
    if (start_date >= "2012-01-01") {

        collections = filter(collections, "LANDSAT/LT05/C02/T1_L2")

    }
    if (end_date <= "1999-01-01") {
        collections = filter(collections, "LANDSAT/LE07/C02/T1_L2")
    }
    if (start_date >= "2022-01-01") {
        collections = filter(collections, "LANDSAT/LE07/C02/T1_L2")
    }
    if (end_date <= "2013-01-01") {
        collections = filter(collections, "LANDSAT/LC08/C02/T1_L2")
    }
    if (end_date <= "2022-01-01") {
        collections = filter(collections, "LANDSAT/LC09/C02/T1_L2")
    }
    return collections
}

function ssebop_collection(
    study_region,
    start_date,
    end_date
) {

    // -=-=-=-=-=-=-=-=-=-WEATHER DATA AND  ET0-=-=-=-=-=-=-=-=-=-=-=-=-=
    var method = "asce"
    var rso_type = undefined
    var debug = false
    var model = "ECMWF"
    var need_to_clip = true
    var add_weather_date = true
    var cloud_cover_max = 30

    var reference_et_weather_daily = et_daily_file.make_calculate_et0(study_region,
        start_date,
        end_date,
        method,
        rso_type,
        debug,
        model,
        need_to_clip
    );

    var et0_weather_collection = reference_et_weather_daily.calculate_daily_et0()
    var elev = et0_weather_collection.select("elev")
    var tmax = et0_weather_collection.select("tmax")
    var tmin = et0_weather_collection.select("tmin")
    var actual_vapor_pressure = et0_weather_collection.select("actual_vapor_pressure")
    var solar_radiation = et0_weather_collection.select("solar_radiation")
    var wind_speed = et0_weather_collection.select("wind_speed")
    var rain = et0_weather_collection.select("rain")
    var et0 = et0_weather_collection.select("et0")
    var etr = et0_weather_collection.select("etr")

    // -=-=-=-=-=-=-=-=-=-=-=-=-=IMAGE COLLECTION-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= 

    function search_all_collections(collections) {
        var all_collections;
        for (var i = 0; i < collections.length; i++) {
            var input_collection = ee.ImageCollection(collections[i])
                .filterBounds(study_region)
                .filterDate(start_date, end_date)
                .filterMetadata('CLOUD_COVER_LAND', 'less_than',
                    cloud_cover_max)
                .filterMetadata('CLOUD_COVER_LAND', 'greater_than', -0.5)

            // check for bad images
            // if LT05 in collection[i]
            if (collections[i] == "LANDSAT/LT05/C02/T1_L2") {
                input_collection = input_collection.filter(ee.Filter.lt(
                    'system:time_start', ee.Date('2011-12-31').millis()))
            } else if (collections[i] == "LANDSAT/LE07/C02/T1_L2") {
                input_collection = input_collection.filter(ee.Filter.lt(
                    'system:time_start', ee.Date('2022-01-01').millis()))
            } else if (collections[i] == "LANDSAT/LC08/C02/T1_L2") {
                input_collection = input_collection.filter(ee.Filter.gt(
                    'system:time_start', ee.Date('2013-04-01').millis()))
            } else if (collections[i] == "LANDSAT/LC09/C02/T1_L2") {
                input_collection = input_collection.filter(ee.Filter.gt(
                    'system:time_start', ee.Date('2022-01-01').millis()))
            }
            if (all_collections == undefined) {
                all_collections = input_collection
            } else {
                all_collections = all_collections.merge(input_collection)
            }

        }
        return all_collections
    }

    var collections_list = [
        "LANDSAT/LC09/C02/T1_L2",
        "LANDSAT/LC08/C02/T1_L2",
        "LANDSAT/LE07/C02/T1_L2",
        "LANDSAT/LT05/C02/T1_L2",
    ]

    var collections = filter_collection_list(start_date, end_date, collections_list)

    function calculate() {

        var input_collection = search_all_collections(collections)
        print("input_collection = ", input_collection)

        var input_collection_prepared = input_collection.map(
            function (image) {
                return landsat_utils.prepare_landsat_c2_sr(image, false)
            })
        print("input_collection_prepared = ", input_collection_prepared)
        var ssebop_collection_value = ee.ImageCollection(
            input_collection_prepared.map(function (image) {
                return compute_ssebop_image(
                    image,
                    elev,
                    tmax,
                    tmin,
                    actual_vapor_pressure,
                    solar_radiation,
                    wind_speed,
                    rain,
                    et0,
                    etr
                )
            }))
        return ssebop_collection_value
    }

    return calculate()
}


function compute_ssebop_image(
    image,
    elev,
    tmax,
    tmin,
    actual_vapor_pressure,
    solar_radiation,
    wind_speed,
    rain,
    et0,
    etr
) {
    var _id = image.get("system:id")
    var _index = image.get("system:index")
    var _time_start = image.get("system:time_start")
    var properties = {
        "system:id": _id,
        "system:index": _index,
        "system:time_start": _time_start
    }
    var crs = image.projection().crs()

    var _date = ee.Date(_time_start)
    var _doy = ee.Number(_date.getRelative('day', 'year')).add(1).int()
    var _lat = ee.Number(image.get("pixelLonLat").get("latitude")) // TODO: CHECK this
    // 1. Get image bands
    var lst = image.select("lst")
    var ndvi = image.select("ndvi")
    var ndwi = image.select("ndwi")
    var qa_water_mask = image.select("qa_water")

    // 2. Calculate dt_value
    var dt_value = calculate_dt(
        tmax,
        tmin,
        elev,
        _doy,
        _lat,
        solar_radiation,
        actual_vapor_pressure
    )

    // 3. Calculate tcorr
    var tcorr = calculate_tcorr(
        lst,
        ndvi,
        tmax,
        dt_value,
        ndwi,
        qa_water_mask,
        crs
    )

    // 4. Calculate et_fraction
    var et_fraction = calculate_et_fraction(
        lst,
        tmax,
        tcorr,
        dt_value
    )

    // 5. Calculate actual_et
    var actual_et = calculate_actual_et(
        et_fraction,
        et0,
        properties
    )

    var all_bands = ee.Image(
        [
            lst,
            ndvi,
            ndwi,
            qa_water_mask,
            dt_value,
            tcorr,
            et_fraction,
            actual_et
        ]
    )

    return all_bands


}

function calculate_actual_et(
    et_fraction,
    et0,
    default_properties
) {
    var actual_et = et_fraction.multiply(et0).rename(["et"])
        .set(default_properties)

    return actual_et
}

function calculate_et_fraction(lst, tmax, tcorr, dta) {
    var et_fraction = ssebop_model.et_fraction(lst, tmax, tcorr, dta)
    return et_fraction
}


// TODO: This is not necessary
function calculate_dt(
    tmax,
    tmin,
    elev,
    doy,
    lat,
    rs,
    ea
) {
    /*
    Temperature difference between hot/dry ground and cold/wet canopy
    */
    var dta_value = ssebop_model.dt_calculate(tmax, tmin, elev, doy, lat, rs, ea)


    return dta_value.rename("dt")
}


function tcorr_FANO_calculate(
    lst,
    ndvi,
    tmax,
    dt,
    ndwi,
    qa_water_mask,
    crs
) {
    /*
    Compute the scene wide Tcorr for the current image adjusting tcorr
            temps based on NDVI thresholds to simulate true cold cfactor
 
    FANO: Forcing And Normalizing Operation
 
    */
    var coarse_transform = [5000, 0, 15, 0, -5000, 15]
    var coarse_transform100 = [100000, 0, 15, 0, -100000, 15]
    var dt_coeff = 0.125
    var ndwi_threshold = -0.15
    var high_ndvi_threshold = 0.9
    var water_pct = 10
    // max pixels argument for .reduceResolution()
    var m_pixels = 65535

    lst = ee.Image(lst)
    ndvi = ee.Image(ndvi).clamp(-1.0, 1.0)
    tmax = ee.Image(tmax)
    dt = ee.Image(dt)
    ndwi = ee.Image(ndwi)
    qa_water_mask = ee.Image(qa_water_mask)

    //  setting NDVI to negative values where Landsat QA Pixel detects water.
    ndvi = ndvi.where(qa_water_mask.eq(1).And(ndvi.gt(0)), ndvi.multiply(-1))

    var watermask = ndwi.lt(ndwi_threshold)
    //  combining NDWI mask with QA Pixel watermask.
    watermask = watermask.multiply(qa_water_mask.eq(0))
    //  returns qa_water_mask layer masked by combined watermask to get a count of valid pixels
    var watermask_for_coarse = qa_water_mask.updateMask(watermask)

    var watermask_coarse_count = watermask_for_coarse.reduceResolution(ee.Reducer.count(), False, m_pixels)
        .reproject(crs, coarse_transform)
        .updateMask(1)
        .select([0], ["count"])

    var total_pixels_count = ndvi.reduceResolution(ee.Reducer.count(), False, m_pixels)
        .reproject(crs, coarse_transform)
        .updateMask(1)
        .select([0], ["count"])


    //  Doing a layering mosaic check to fill any remaining Null watermask coarse pixels with valid mask data.
    //  This can happen if the reduceResolution count contained exclusively water pixels from 30 meters.
    watermask_coarse_count = ee.Image(
        [watermask_coarse_count, total_pixels_count.multiply(0).add(1)]
    ).reduce(ee.Reducer.firstNonNull())

    var percentage_bad = watermask_coarse_count.divide(total_pixels_count)
    var pct_value = 1 - (water_pct / 100)
    var wet_region_mask_5km = percentage_bad.lte(pct_value)

    var ndvi_avg_masked = ndvi.updateMask(watermask)
        .reduceResolution(ee.Reducer.mean(), False, m_pixels)
        .reproject(self.crs, coarse_transform)

    var ndvi_avg_masked100 = ndvi.updateMask(watermask)
        .reduceResolution(ee.Reducer.mean(), True, m_pixels)
        .reproject(self.crs, coarse_transform100)

    var ndvi_avg_unmasked = ndvi.reduceResolution(ee.Reducer.mean(), False, m_pixels)
        .reproject(self.crs, coarse_transform)
        .updateMask(1)

    var lst_avg_masked = lst.updateMask(watermask)
        .reduceResolution(ee.Reducer.mean(), False, m_pixels)
        .reproject(self.crs, coarse_transform)

    var lst_avg_masked100 = lst.updateMask(watermask)
        .reduceResolution(ee.Reducer.mean(), True, m_pixels)
        .reproject(self.crs, coarse_transform100)

    var lst_avg_unmasked = lst.reduceResolution(ee.Reducer.mean(), False, m_pixels)
        .reproject(self.crs, coarse_transform)
        .updateMask(1)


    // Here we don't need the reproject.reduce.reproject sandwich bc these are coarse data-sets
    var dt_avg = dt.reproject(self.crs, coarse_transform)
    var dt_avg100 = dt.reproject(self.crs, coarse_transform100).updateMask(1)
    var tmax_avg = tmax.reproject(self.crs, coarse_transform)

    // FANO expression as a function of dT, calculated at the coarse resolution(s)
    var Tc_warm = lst_avg_masked.expression("(lst - (dt_coeff * dt * (ndvi_threshold - ndvi) * 10))",
        {
            "dt_coeff": dt_coeff,
            "ndvi_threshold": high_ndvi_threshold,
            "ndvi": ndvi_avg_masked,
            "dt": dt_avg,
            "lst": lst_avg_masked
        }
    )

    var Tc_warm100 = lst_avg_masked100.expression(
        "(lst - (dt_coeff * dt * (ndvi_threshold - ndvi) * 10))",
        {
            "dt_coeff": dt_coeff,
            "ndvi_threshold": high_ndvi_threshold,
            "ndvi": ndvi_avg_masked100,
            "dt": dt_avg100,
            "lst": lst_avg_masked100
        }
    )

    //  In places where NDVI is really high, use the masked original lst at those places.
    //  In places where NDVI is really low (water) use the unmasked original lst.
    //  Everywhere else, use the FANO adjusted Tc_warm, ignoring masked water pixels.
    //  In places where there is too much land covered by water 10% or greater,
    //    use a FANO adjusted Tc_warm from a coarser resolution (100km) that ignored masked water pixels.
    var Tc_cold = lst_avg_unmasked.where(
        (ndvi_avg_masked.gte(0).And(ndvi_avg_masked.lte(high_ndvi_threshold))),
        Tc_warm
    )
        .where(ndvi_avg_masked.gt(high_ndvi_threshold), lst_avg_masked)
        .where(wet_region_mask_5km, Tc_warm100)
        .where(ndvi_avg_unmasked.lt(0), lst_avg_unmasked)


    var c_factor = Tc_cold.divide(tmax_avg)

    // bilinearly smooth the gridded c factor
    var c_factor_bilinear = c_factor.resample("bilinear")

    return c_factor_bilinear.rename(["tcorr"]).set(
        {
            "system:index": self._index,
            "system:time_start": self._time_start,
            "tmax_source": tmax.get("tmax_source"),
            "tmax_version": tmax.get("tmax_version")
        }
    )

}

function calculate_tcorr(
    lst,
    ndvi,
    tmax,
    dt_value,
    ndwi,
    qa_water_mask,
    crs
) {
    /*Get Tcorr from pre-computed assets for each Tmax source
 
    Returns
    -------
 
 
    Raises
    ------
    ValueError
        If `self._tcorr_source` is not supported.
 
    Notes
    -----
    Tcorr Index values indicate which level of Tcorr was used
      0 - Gridded blended cold/hot Tcorr (*)
      1 - Gridded cold Tcorr
      2 - Continuous cold tcorr based on an NDVI function.
      3 - Scene specific Tcorr
      4 - Mean monthly Tcorr per WRS2 tile
      5 - Mean seasonal Tcorr per WRS2 tile (*)
      6 - Mean annual Tcorr per WRS2 tile
      7 - Default Tcorr
      8 - User defined Tcorr
      9 - No data
 
    */
    var tcorr_FANO = tcorr_FANO_calculate(
        lst,
        ndvi,
        tmax,
        dt_value,
        ndwi,
        qa_water_mask,
        crs
    )
    var tcorr_img = ee.Image(tcorr_FANO).select(["tcorr"])

    return tcorr_img.rename(["tcorr"])

}



exports.make_ssebop_collection = function () {
    return ssebop_collection
}