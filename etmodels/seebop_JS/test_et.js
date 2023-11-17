var et_daily_file = require('users/franciscopuig/SSEBop/:et_daily');

var study_region = geometry.bounds(1, "EPSG:4326")
var start_date = "2023-01-03"
var end_date = "2023-01-05"
var method = "asce"
var rso_type = undefined
var debug = false
var model = "ECMWF"
var need_to_clip = true // if true, the output will be clipped to the study region
var add_weather_date = true
var et_daily = et_daily_file.make_calculate_et0(
    study_region,
    start_date,
    end_date,
    method,
    rso_type,
    debug,
    model,
    need_to_clip,
    add_weather_date
);

var et0_collection = et_daily.calculate_daily_et0()

print("et0_collection = ", et0_collection)


// heat palette
var heatPalette = [
    'FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718', '74A901',
    '66A000', '529400', '3E8601', '207401', '056201', '004C00', '023B01',
    '012E01', '011D01', '011301'
];
// show in map band et0 and etr
Map.centerObject(study_region, 12)
// add heat palette
Map.addLayer(et0_collection.select("et0"), { min: 0, max: 10, palette: heatPalette }, "et0")
Map.addLayer(et0_collection.select("etr"), { min: 0, max: 10, palette: heatPalette }, "etr")





