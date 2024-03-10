var ssebop_image_file = require('users/franciscopuig/SSEBop/:ssebop_image');
var ssebop_image = ssebop_image_file.make_ssebop_image()


// -=-=-=-=-=-=-=-=-=-= INPUT PARAMS -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
var debug = true // IF TRUE THE MODEL RETURNS ALL THE BANDS, IF FALSE ONLY ET FRACTION AND ETo

// -=-=-=-=-=-=-=-=-=-=-=-= CALCULATE ET AND ET FRACTION =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
// "LANDSAT/LC09/C02/T1_L2",
// "LANDSAT/LC08/C02/T1_L2",
// "LANDSAT/LE07/C02/T1_L2", // NOTE: This collectios has a strike problem. It is better if we don't use it
// "LANDSAT/LT05/C02/T1_L2",
var image = ee.Image("LANDSAT/LC08/C02/T1_L2/LC08_041036_20220506")
var study_region = image.geometry()
var ssebop = ssebop_image(
    image,
    debug
)

var ssebop_image = ssebop[0]
var precip_feature_collection  = ssebop[1]


if (debug) {
    print("ssebop_image = ", ssebop_image)
    print("precip_feature_collection = ", precip_feature_collection)
    
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

Map.addLayer(ssebop_image.select("et_fraction"), { min: 0, max: 1, palette: etPalette }, "ET-fraction")
Map.addLayer(ssebop_image.select("et"), { min: 0, max: 10, palette: etPalette }, "ET")

if (debug) {
    Map.addLayer(ssebop_image, {}, "all_bands", false)
}