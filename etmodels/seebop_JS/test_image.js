var image = ee.Image("LANDSAT/LC08/C02/T1_L2/LC08_041035_20220506")

var study_region = image.geometry()
Map.centerObject(study_region, 12)

print("image = ", image)
// show all bands
Map.addLayer(image, {}, "all_bands", false)
// show only the bands we want
