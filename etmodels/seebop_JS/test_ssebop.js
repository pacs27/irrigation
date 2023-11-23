var ssebop_collection_file = require('users/franciscopuig/SSEBop/:ssebop_collection');
var ssebop_collection = ssebop_collection_file.make_ssebop_collection()

// -=-=-=-=-=-=-=-=-=-= INPUT PARAMS -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
var study_region = geometry.bounds(1, "EPSG:4326")
var start_date = "2023-01-01"
var end_date = "2023-10-28"
var debug = true // IF TRUE THE MODEL RETURNS ALL THE BANDS, IF FALSE ONLY ET FRACTION AND ETo

// -=-=-=-=-=-=-=-=-=-=-=-= CALCULATE ET AND ET FRACTION =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
var ssebop_coll = ssebop_collection(
    study_region,
    start_date,
    end_date,
    debug
)

if (debug) {
    print("ssebop_collection = ", ssebop_coll)

}

// -=-=-=-=-=-=-=-=-=-=-=-= DISPLAY THE COLLECTION =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
var etPalette = [
    "DEC29B",
    "E6CDA1",
    "EDD9A6",
    "F5E4A9",
    "FFF4AD",
    "C3E683",
    "6BCC5C",
    "3BB369",
    "20998F",
    "1C8691",
    "16678A",
    "114982",
    "0B2C7A",
]
Map.centerObject(study_region, 12)

Map.addLayer(ssebop_coll.select("et_fraction"), { min: 0, max: 1, palette: etPalette }, "ET-fraction")
Map.addLayer(ssebop_coll.select("et"), { min: 0, max: 10, palette: etPalette }, "ET")

if (debug) {
    Map.addLayer(ssebop_coll, {}, "all_bands", false)
}





