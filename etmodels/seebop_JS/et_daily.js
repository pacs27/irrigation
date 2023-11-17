var calcs_file = require('users/franciscopuig/SSEBop/:et_calcs');

var calcs = calcs_file.make_calcs();


function _daily_et(
    tmax,
    tmin,
    ea,
    rs,
    uz,
    zw,
    elev,
    lat,
    doy,
    method,
    rso_type,
    rso
) {
    /*
    ASCE Daily Standardized Reference Evapotranspiration (ET)

    Arguments
    ---------
    tmax : ee.Image
        Maximum daily temperature [C].
    tmin : ee.Image
        Minimum daily temperature [C].
    ea : ee.Image
        Actual vapor pressure [kPa].
    rs : ee.Image
        Incoming shortwave solar radiation [MJ m-2 day-1].
    uz : ee.Image
        Wind speed [m s-1].
    zw : ee.Number
        Wind speed height [m].
    elev : ee.Image or ee.Number
        Elevation [m].
    lat : ee.Image or ee.Number
        Latitude [degrees].
    doy : ee.Number
        Day of year.
    method : {'asce' (default), 'refet'}, optional
        Specifies which calculation method to use.
        * 'asce' -- Calculations will follow ASCE-EWRI 2005 [1].
        * 'refet' -- Calculations will follow RefET software.
    rso_type : {None (default), 'full' , 'simple', 'array'}, optional
        Specifies which clear sky solar radiation (Rso) model to use.
        * None -- Rso type will be determined from "method" parameter
        * 'full' -- Full clear sky solar formulation
        * 'simple' -- Simplified clear sky solar formulation
        * 'array' -- Read Rso values from "rso" function parameter
    rso : ee.Image, ee.Number, or None, optional
        Clear sky solar radiation [MJ m-2 day-1] (the default is None).
        Only used if rso_type == 'array'.

    Raises
    ------
    ValueError
        If 'method' or 'rso_type' parameter is invalid.

    Notes
    -----
    Latitude units are degress, not radians.

    References
    ----------
    .. [1] ASCE-EWRI (2005). The ASCE standardized reference evapotranspiration
        equation. ASCE-EWRI Standardization of Reference Evapotranspiration
        Task Committee Rep., ASCE Reston, Va.

    */
    if (method == undefined) {
        method = "asce"
    }




    if (rso_type === undefined) {
        // do nothing
    } else if (
        rso_type.toLowerCase() !== "simple" &&
        rso_type.toLowerCase() !== "full" &&
        rso_type.toLowerCase() !== "array"
    ) {

    } else if (rso_type.toLowerCase() === "array") {
        // Check that rso is an ee.Image or ee.Number?
        // pass
    }

    // Get time_start from tmin
    // Should time_start be set in init?
    var time_start = ee.Image(tmin).get("system:time_start");


    // Convert latitude to radians
    lat = lat.multiply(Math.PI / 180);

    // To match standardized form, pair is calculated from elevation
    var pair = calcs.air_pressure(elev, method);

    // Psychrometric constant (Eq. 4)
    var psy = pair.multiply(0.000665);


    var tmean = tmax.add(tmin).multiply(0.5);
    var es_slope = calcs.es_slope(tmean, method);


    // Saturated vapor pressure
    var es = calcs.sat_vapor_pressure(tmax)
        .add(calcs.sat_vapor_pressure(tmin))
        .multiply(0.5)


    // Vapor pressure deficit
    var vpd = calcs.vpd(es, ea);

    // Extraterrestrial radiation
    var ra = calcs.ra_daily(lat, doy, method);

    // Clear sky solar radiation
    // If rso_type is not set, use the method
    // If rso_type is set, use rso_type directly
    if (rso_type === undefined) {
        if (method.toLowerCase() === "asce") {
            rso = calcs.rso_simple(ra, elev);
        } else if (method.toLowerCase() === "refet") {
            rso = calcs.rso_daily(ea,
                ra,
                pair,
                doy,
                lat
            );
        }
    } else if (rso_type.toLowerCase() === "simple") {
        rso = calcs.rso_simple(ra, elev);
    } else if (rso_type.toLowerCase() === "full") {
        rso = calcs.rso_daily(ea,
            ra,
            pair,
            doy,
            lat
        );
    } else if (rso_type.toLowerCase() === "array") {
        // Use rso array passed to function
        rso = rso;
    }

    // Cloudiness fraction
    var fcd = calcs.fcd_daily(rs, rso);


    // Net long-wave radiation
    var rnl = calcs.rnl_daily(tmax,
        tmin,
        ea,
        fcd
    );

    // Net radiation
    var rn = calcs.rn(rs, rnl);

    // Wind speed
    var u2 = calcs.wind_height_adjust(uz, zw);

    return {
        "et0": function () { return _eto(time_start, tmean, u2, vpd, psy, es_slope, rn) },
        "etr": function () { return _etr(time_start, tmean, u2, vpd, psy, es_slope, rn) },
        "etw": function () { return _etw(es_slope, rn, psy, time_start) },
        "eto_fs1": function () { return _eto_fs1(es_slope, psy, u2, rn, time_start) },
        "eto_fs2": function () { return _eto_fs2(es_slope, psy, u2, es, ea, time_start, tmean) },
        "pet_hargreaves": function () { return _pet_hargreaves(tmean, tmax, tmin, ra, time_start) },

    }


}

// function __etsz(surface, etr) {
//     /*
//      Standardized reference ET

//         Parameters
//         ----------
//         surface : {'alfalfa', 'etr', 'tall', 'grass', 'eto', 'short'}
//             Reference surface type.

//         Returns
//         -------
//         ee.Image

//     */



function _eto(time_start,
    tmean,
    u2,
    vpd,
    psy,
    es_slope,
    rn
) {
    var cn = 900
    var cd = 0.34
    var et0 = ee.Image(
        _etsz(
            tmean,
            u2,
            vpd,
            cn,
            psy,
            es_slope,
            rn,
            cd

        ).rename(["et0"]).set("system:time_start", time_start)
    );
    return et0
}


function _etr(time_start, tmean,
    u2,
    vpd,
    psy,
    es_slope,
    rn
) {
    /* Tall (alfalfa) reference surface */
    var cn = 1600
    var cd = 0.38
    var etr = ee.Image(_etsz(
        tmean,
        u2,
        vpd,
        cn,
        psy,
        es_slope,
        rn,
        cd
    ).rename(["etr"]).set("system:time_start", time_start)
    );
    return etr
}

function _etsz(
    tmean,
    u2,
    vpd,
    cn,
    psy,
    es_slope,
    rn,
    cd

) {
    /*
     Daily reference ET (Eq. 1)

        Returns
        -------
        etsz : ee.Image
            Standardized reference ET [mm].

    */
    var _etsz = tmean.add(273)
        .pow(-1)
        .multiply(u2)
        .multiply(vpd)
        .multiply(cn)
        .multiply(psy)
        .add(es_slope.multiply(rn).multiply(0.408))
        .divide(
            u2.multiply(cd).add(1).multiply(psy).add(es_slope)
        )
    return _etsz
}

function _etw(
    es_slope,
    rn,
    psy,
    time_start
) {
    /* Priestley-Taylor evaporation (alpha = 1.26) */
    var etw = es_slope.expression(
        "(alpha * es_slope * rn * 1000 / (2453 * (es_slope + psy)))",
        {
            es_slope: es_slope,
            rn: rn,
            psy: psy,
            alpha: 1.26,
        }
    )
        .rename(["etw"])
        .set("system:time_start", time_start)
    return etw
}

function _eto_fs1(
    es_slope,
    psy,
    u2,
    rn,
    time_start
) {
    /* UF-IFAS Extension FS1 Radiation Term (ETrad)

    Returns
    -------
    eto_fs1 : ee.Image
            FS1 ETrad [mm].

    References
    ----------
    https://edis.ifas.ufl.edu/pdffiles/ae/ae45900.pdf

    */
    var eto_fs1 = u2.expression(
        "(delta / (delta + psy * (1 + 0.34 * u2))) * (0.408 * rn)",
        {
            delta: es_slope,
            psy: psy,
            u2: u2,
            rn: rn,
        }
    )
        .rename(["etr"])
        .set("system:time_start", time_start)

    return eto_fs1
}

function _eto_fs2(
    es_slope,
    psy,
    u2,
    es,
    ea,
    time_start,
    tmean
) {
    /* UF-IFAS Extension FS2 Wind Term (ETwind)

    Returns
    -------
    eto_fs2 : ee.Image
        FS2 ETwind [mm].

    References
    ----------
    https://edis.ifas.ufl.edu/pdffiles/ae/ae45900.pdf

    */
    // Temperature Term (Eq. 14)
    var TT = u2.expression(
        "(900 / (t + 273)) * u2", { "t": tmean, "u2": u2 }
    );
    // Psi Term (Eq. 13)
    var PT = u2.expression(
        "psy / (slope + psy * (1 + 0.34 * u2))",
        { "slope": es_slope, "psy": psy, "u2": u2 }
    );

    var eto_fs2 = u2.expression(
        "PT * TT * (es-ea)", { "PT": PT, "TT": TT, "es": es, "ea": ea }
    )
        .rename(["eto_fs2"])
        .set("system:time_start", time_start)


    return eto_fs2
}

function _pet_hargreaves(
    tmean,
    tmax,
    tmin,
    ra,
    time_start
) {
    /* Hargreaves potential ET

    Returns
    -------
    hargreaves_pet : ee.Image
            Hargreaves ET [mm].

    References
    ----------

    */
    var pet_hargreaves = tmax.expression(
        "0.0023 * (tmean + 17.8) * ((tmax - tmin) ** 0.5) * 0.408 * ra",
        {
            tmean: tmean,
            tmax: tmax,
            tmin: tmin,
            ra: ra,
        }
    )
        .rename(["pet_hargreaves"])
        .set("system:time_start", time_start)

    return pet_hargreaves;
}


exports.make_calculate_et0 = function (
    study_region,
    start_date,
    end_date,
    method,
    rso_type,
    debug,
    model,
    need_to_clip, // TODO: I have calculated that for the ECMWF model and approximately for more than 300 points, it is better if we dontnot clip
    add_weather_data
) {
    if (method == "undefined") {
        method = "asce"
    }

    if (debug == "undefined") {
        debug = False
    }
    if (add_weather_data == "undefined") {
        add_weather_data = true
    }

    var rso = undefined // TODO: ??


    if (model == "undefined") {
        model = "NASA" // NASA, GFS, ECMWF
    }

    var start_date = ee.Date(start_date)
    var end_date = ee.Date(end_date)

    // Initialize the GFS dataset
    if (model == "NASA") {
        var collection_name = "NASA/GLDAS/V021/NOAH/G025/T3H"
    }
    else if (model == "GFS") {
        var collection_name = collection_name = "NOAA/GFS0P25"
    }
    else if (model == "ECMWF") {
        var collection_name = collection_name = "ECMWF/ERA5_LAND/HOURLY"
    }

    if (need_to_clip) {
        var input_collection = (
            ee.ImageCollection(collection_name)
                .filterBounds(study_region) // TODO: I think this is redundant
                .filterDate(start_date, end_date)
                .map(function (image) {
                    return image.clip(study_region)
                })
        )
    }
    else {
        var input_collection = (
            ee.ImageCollection(collection_name)
                .filterBounds(study_region) // TODO: I think this is redundant
                .filterDate(start_date, end_date)
        )
    }


    var elev = ee.Image("projects/openet/assets/meteorology/era5land/ancillary/elevation")

    var lat = ee.Image(
        "projects/openet/assets/meteorology/era5land/ancillary/latitude"
    )

    function _calculate_daily_et0(

    ) {

        function _nasa_weather_data(
            start,
            end,
            start_date,
            input_collection
        ) {


            var tmax = input_collection.select(["Tair_f_inst"])
                .filterDate(start, end)
                .max()
                .subtract(273.15)
            var tmin = input_collection.select(["Tair_f_inst"])
                .filterDate(start, end)
                .min()
                .subtract(273.15)

            var mean_values = input_collection.select(
                ["Qair_f_inst", "Swnet_tavg", "Wind_f_inst"]
            )
                .filterDate(start, end)
                .mean()

            var actual_vapor_pressure = calcs.actual_vapor_pressure(
                pair = calcs.air_pressure(elev, method),
                q = mean_values.select(["Qair_f_inst"])
            )
            var solar_radiation = mean_values.select(["Swnet_tavg"]).multiply(0.0864)

            var wind_speed = mean_values.select(["Wind_f_inst"])
            var rain = input_collection.select(["Rainf_f_tavg"]).filterDate(start, end).sum()
            var doy = ee.Number(start_date.getRelative("day", "year")).add(1).double()


            return {
                "tmax": tmax,
                "tmin": tmin,
                "actual_vapor_pressure": actual_vapor_pressure,
                "solar_radiation": solar_radiation,
                "wind_speed": wind_speed,
                "rain": rain,
                "doy": doy,
            }
        }


        function _gfs_weather_data(
            start,
            end,
            start_date,
            input_collection
        ) {


            var tmax = input_collection.select(["temperature_2m_above_ground"])
                .filterDate(start, end)
                .max()
                .subtract(273.15)
            var tmin = input_collection.select(["temperature_2m_above_ground"])
                .filterDate(start, end)
                .min()
                .subtract(273.15)

            var mean_values = input_collection.select(
                ["specific_humidity_2m_above_ground",
                    "v_component_of_wind_10m_above_ground",
                    "u_component_of_wind_10m_above_ground",
                    "downward_shortwave_radiation_flux",]
            )
                .filterDate(start, end)
                .mean()

            var actual_vapor_pressure = calcs.actual_vapor_pressure(
                pair = calcs.air_pressure(elev, method),
                q = mean_values.select(["specific_humidity_2m_above_ground"])
            )
            var solar_radiation = mean_values.select(["dswrf_surface"]).multiply(0.0864)
            var wind_speed = mean_values.select(["wind_speed_gust_surface"])
            var rain = input_collection.select(["total_precipitation_surface"]).filterDate(start, end).sum()
            var doy = ee.Number(start_date.getRelative("day", "year")).add(1).double()

            return {
                "tmax": tmax,
                "tmin": tmin,
                "actual_vapor_pressure": actual_vapor_pressure,
                "solar_radiation": solar_radiation,
                "wind_speed": wind_speed,
                "rain": rain,
                "doy": doy,
            }
        }

        function _ecmwf_weather_data(
            start,
            end,
            start_date,
            input_collection
        ) {


            var tmax = input_collection.select(["temperature_2m"])
                .filterDate(start, end)
                .max()
                .subtract(273.15)
            var tmin = input_collection.select(["temperature_2m"])
                .filterDate(start, end)
                .min()
                .subtract(273.15)


            var mean_values = input_collection.select(
                ["dewpoint_temperature_2m",
                    "surface_solar_radiation_downwards",
                    "u_component_of_wind_10m",
                    "v_component_of_wind_10m",]
            )
                .filterDate(start, end)
                .mean()
            var actual_vapor_pressure = calcs.sat_vapor_pressure(
                mean_values.select(["dewpoint_temperature_2m"]).subtract(273.15)
            )

            var solar_radiation = mean_values.select(
                ["surface_solar_radiation_downwards"]
            ).divide(1000000)



            function wind_magnitude(input_img) {
                // Compute hourly wind magnitude from vectors
                return ee.Image(input_img.select(["u_component_of_wind_10m"]))
                    .pow(2)
                    .add(
                        ee.Image(
                            input_img.select(["v_component_of_wind_10m"])
                        ).pow(2)
                    )
                    .sqrt()
                    .rename(["uz"])
            }
            var wind_speed = wind_magnitude(mean_values)
            var rain = input_collection.select(["total_precipitation_hourly"]).filterDate(start, end).sum()
            var doy = ee.Number(start_date.getRelative("day", "year")).add(1).double()

            return {
                "tmax": tmax,
                "tmin": tmin,
                "actual_vapor_pressure": actual_vapor_pressure,
                "solar_radiation": solar_radiation,
                "wind_speed": wind_speed,
                "rain": rain,
                "doy": doy,
            }
        }


        function _calculate_et0(
            day_off_set
        ) {
            var start = start_date.advance(day_off_set, "days")
            var end = start.advance(1, "days")
            var weather_data;
            if (model == "NASA") {
                weather_data = _nasa_weather_data(
                    start,
                    end,
                    start_date,
                    input_collection,
                    method
                )
                var zw = ee.Number(2)
            }
            else if (model == "GFS") {
                weather_data = _gfs_weather_data(
                    start,
                    end,
                    start_date,
                    input_collection,
                    method
                )
                var zw = ee.Number(10)
            }
            else if (model == "ECMWF") {
                weather_data = _ecmwf_weather_data(
                    start,
                    end,
                    start_date,
                    input_collection,
                    method
                )
                var zw = ee.Number(10)
            }

            var et_daily = _daily_et(
                weather_data.tmax,

                weather_data.tmin,

                weather_data.actual_vapor_pressure,
                weather_data.solar_radiation,
                weather_data.wind_speed,
                zw,
                elev,
                lat,
                weather_data.doy,
                method,
                rso_type,
                rso
            )
            var et0_daily = et_daily.et0()
            var etr_daily = et_daily.etr()
            var et_daily_image = et0_daily.addBands(etr_daily)
            if (add_weather_data) {
                et_daily_image = et_daily_image.addBands(
                    ee.Image([weather_data.tmax, weather_data.tmin, weather_data.actual_vapor_pressure, weather_data.solar_radiation, weather_data.wind_speed, weather_data.rain, elev])
                        .rename(["tmax", "tmin", "actual_vapor_pressure", "solar_radiation", "wind_speed", "rain", "elev"])

                )
            }
            et_daily_image = et_daily_image.set("system:time_start", start_date.millis())
            return et_daily_image

        }

        var number_of_days = end_date.difference(start_date, "days")

        // var daily_et0 = ee.ImageCollection(
        //     ee.List.sequence(0, number_of_days.subtract(1))).first()



        // return _calculate_daily_et(
        //     0,
        //     model,
        //     zw,
        //     elev,
        //     lat,
        //     method,
        //     rso
        // )

        var daily_et0 = ee.ImageCollection(
            ee.List.sequence(0, number_of_days.subtract(1))
                .map(function (day_off_set) {
                    return _calculate_et0(
                        day_off_set
                    )
                })
        )

        return daily_et0
    }

    return {
        "calculate_daily_et0": _calculate_daily_et0,
    }

}
