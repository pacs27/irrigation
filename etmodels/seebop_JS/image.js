
var et_daily_file = require('users/franciscopuig/SSEBop/:et_daily');
var seebop_model_file = require('users/franciscopuig/SSEBop/:seebop_model');


function seebop_image(
    image,

) {
    var _id = image.get("system:id")
    var _index = image.get("system:index")
    var _time_start = image.get("system:time_start")
    var properties = {
        "system:id": _id,
        "system:index": _index,
        "system:time_start": _time_start
    }

}

function et_fraction(lst, tmax, tcorr, dta) {
    var et_fraction = seebop_model_file.et_fraction(lst, tmax, tcorr, dta)
    return et_fraction
}

function dta(dt_source, doy) {
    /*
    Temperature difference between hot/dry ground and cold/wet canopy
    */
    //  Assumes a string source is an image collection ID (not an image ID),\
    //    MF: and currently only supports a climatology 'DOY-based' dataset filter
    var dt_coll = ee.ImageCollection(dt_source).filter(
        ee.Filter.calendarRange(doy, doy, "day_of_year")
    )
    //  MF: scale factor property only applied for string ID dT collections, and
    //   no clamping used for string ID dT collections.
    var dt_img = ee.Image(dt_coll.first())
    var dt_scale_factor = ee.Dictionary(
        { "scale_factor": dt_img.get("scale_factor") }
    ).combine({ "scale_factor": "1.0" }, overwrite = False)
    dt_img = dt_img.multiply(ee.Number.parse(dt_scale_factor.get("scale_factor")))

    return dt_img.rename("dt")
}

function tcorr_FANO_calculate(
    lst,
    ndvi,
    tmax,
    dt,
    ndwi,
    qa_water_mask,
    crs,
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
            "lst": lst_avg_masked,
        },
    )

    var Tc_warm100 = lst_avg_masked100.expression(
        "(lst - (dt_coeff * dt * (ndvi_threshold - ndvi) * 10))",
        {
            "dt_coeff": dt_coeff,
            "ndvi_threshold": high_ndvi_threshold,
            "ndvi": ndvi_avg_masked100,
            "dt": dt_avg100,
            "lst": lst_avg_masked100,
        },
    )

    //  In places where NDVI is really high, use the masked original lst at those places.
    //  In places where NDVI is really low (water) use the unmasked original lst.
    //  Everywhere else, use the FANO adjusted Tc_warm, ignoring masked water pixels.
    //  In places where there is too much land covered by water 10% or greater,
    //    use a FANO adjusted Tc_warm from a coarser resolution (100km) that ignored masked water pixels.
    var Tc_cold = lst_avg_unmasked.where(
        (ndvi_avg_masked.gte(0).And(ndvi_avg_masked.lte(high_ndvi_threshold))),
        Tc_warm,
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
            "tmax_version": tmax.get("tmax_version"),
        }
    )

}

function tcorr(
    lst,
    ndvi,
    tmax,
    dt_value,
    ndwi,
    qa_water_mask,
    crs,
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
        crs,
    )
    var tcorr_img = ee.Image(tcorr_FANO).select(["tcorr"])

    return tcorr_img.rename(["tcorr"])

}



/**
 * Calculates daily ET0 (reference evapotranspiration) and weather data for a given study region and time period.
 * @param {string} study_region - The study region for which to calculate ET0 and weather data.
 * @param {Date} start_date - The start date of the time period for which to calculate ET0 and weather data.
 * @param {Date} end_date - The end date of the time period for which to calculate ET0 and weather data.
 * @param {string} method - The method to use for calculating ET0.
 * @param {string} rso_type - The type of RSO (reference station) to use for calculating ET0.
 * @param {boolean} debug - Whether or not to output debug information.
 * @param {string} model - The ET model to use for calculating ET0.
 * @param {boolean} need_to_clip - Whether or not to clip the output to the study region.
 * @returns {ee.Collection} - An object containing the daily ET0 and weather data for the specified time period.
 */
function calculate_et_and_weather(study_region,
    start_date,
    end_date,
    method,
    rso_type,
    debug,
    model,
    need_to_clip) {

    var et_daily = t_daily_file.make_calculate_et0(study_region,
        start_date,
        end_date,
        method,
        rso_type,
        debug,
        model,
        need_to_clip
    );

    var et0_collection = et_daily.calculate_daily_et0()
    return et0_collection
}