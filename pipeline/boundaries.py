import ee
import geemap
# https://developers.google.com/earth-engine/datasets/catalog/USDOS_LSIB_SIMPLE_2017#table-schema
# continents
#     oceania not included due to number of polygons required
africa = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('wld_rgn', 'equals', 'Africa').set('aoi_label', 'africa')
europe = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('wld_rgn', 'equals', 'Europe').set('aoi_label', 'europe')
northAmerica = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('wld_rgn', 'equals', 'North America').set('aoi_label', 'north_america')
southAmerica = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('wld_rgn', 'equals', 'South America').set('aoi_label', 'south_america')

# specific countries of interest
argentina = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'AR').set('aoi_label', 'argentina')
australia = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'AS').set('aoi_label', 'australia')
brazil = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'BR').set('aoi_label', 'brazil')
chile = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'CI').set('aoi_label', 'chile')
new_zealand = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'NZ').set('aoi_label', 'new_zealand')
united_states = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'US').set('aoi_label', 'usa')
ne_usa = ee.FeatureCollection(united_states.toList(10).slice(2,3,1)).set('aoi_label', 'ne_usa')
se_usa = ee.FeatureCollection(united_states.toList(10).slice(1,2,1)).set('aoi_label', 'se_usa')
nw_usa = ee.FeatureCollection(united_states.toList(10).slice(4,5,1)).set('aoi_label', 'nw_usa')
sw_usa = ee.FeatureCollection(united_states.toList(10).slice(5,6,1)).set('aoi_label', 'sw_usa')
spain = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filterMetadata('country_co', 'equals', 'SP').set('aoi_label', 'spain')

# specific areas of interest
#!wget https://eric.clst.org/assets/wiki/uploads/Stuff/gz_2010_us_040_00_20m.json
california = geemap.geojson_to_ee('gz_2010_us_040_00_20m.json') \
                    .filterMetadata('NAME', 'equals', 'California') \
                    .set('aoi_label', 'california')

# these are custom-files made by copying geometries created on https://code.earthengine.google.com and printed to the console
central_ca = ee.FeatureCollection(central_california.central_valley_california_g)\
                .set('aoi_label', 'central_valley_california')

az_rainfed = ee.FeatureCollection(az_rainfed_g)\
                .set('aoi_label', 'az_rainfed')

or_rainfed = ee.FeatureCollection(or_rainfed_g)\
                .set('aoi_label', 'or_rainfed')

ca_rainfed = ee.FeatureCollection(miscellaneous_aois.ca_rainfed_g)\
                .set('aoi_label', 'ca_rainfed')

bakersfield = ee.FeatureCollection(miscellaneous_aois.bakersfield_g)\
                .set('aoi_label', 'bakersfield')

southern_idaho = ee.FeatureCollection(miscellaneous_aois.southern_idaho_g)\
                .set('aoi_label', 'southern_idaho')

central_kansas = ee.FeatureCollection(miscellaneous_aois.central_kansas_g)\
                .set('aoi_label', 'central_kansas')

central_valley_california_g = ee.Geometry({
  "type": "Polygon",
  "coordinates": [
    [
      [
        -122.2286422366599,
        40.28233810975918
      ],
      [
        -122.38310075342639,
        39.842682484273325
      ],
      [
        -122.3824508304099,
        39.11587403235935
      ],
      [
        -121.8331344241599,
        38.12017202382117
      ],
      [
        -121.6024215335349,
        37.704124178806325
      ],
      [
        -119.4930465335349,
        35.21273370921282
      ],
      [
        -119.25906417616741,
        35.01075684633611
      ],
      [
        -118.8393600100974,
        34.94300718912039
      ],
      [
        -118.70477749056614,
        35.23741399555778
      ],
      [
        -119.0535934085349,
        36.335797909177614
      ],
      [
        -120.3499801272849,
        37.49521901385896
      ],
      [
        -120.91302944369114,
        38.13529595072468
      ],
      [
        -121.3717086429099,
        39.16274032694631
      ],
      [
        -121.76373799407064,
        39.774008125791156
      ],
      [
        -122.2286422366599,
        40.28233810975918
      ]
    ]
  ]
})

az_rainfed_g = ee.Geometry({
  "type": "MultiPoint",
  "coordinates": [
    [
      -111.19993057460678,
      32.400588652140044
    ],
    [
      -111.15632858486069,
      32.382904539677845
    ],
    [
      -111.35408249111069,
      32.42203686080392
    ],
    [
      -111.37187578377437,
      32.50689475802398
    ],
    [
      -111.4226875513525,
      32.550024863870355
    ],
    [
      -111.41032793221187,
      32.574909323443336
    ],
    [
      -111.58851244148921,
      32.578959628689596
    ],
    [
      -111.64722063240718,
      32.58214188303631
    ],
    [
      -111.36706926521968,
      32.60875267780486
    ],
    [
      -111.71210863289546,
      32.754104467948416
    ],
    [
      -111.54525377449703,
      32.795961131467166
    ],
    [
      -111.71033601605731,
      32.91328213208168
    ],
    [
      -111.5537863710461,
      33.16370172031747
    ],
    [
      -111.50022802143673,
      32.99800359795222
    ],
    [
      -112.61303089470763,
      33.386074575669035
    ],
    [
      -112.27382801384826,
      33.34593176721804
    ],
    [
      -113.5025915642504,
      32.98262301830211
    ],
    [
      -112.94022889335196,
      33.03559752629318
    ],
    [
      -112.74110169608633,
      32.931345673039026
    ],
    [
      -112.89216370780508,
      32.88868793123279
    ],
    [
      -113.29591126639883,
      32.99702141323495
    ],
    [
      -114.28611581244525,
      32.71370999908829
    ],
    [
      -114.34516732611712,
      32.75818417680268
    ],
    [
      -113.96819894232806,
      32.720642499484434
    ],
    [
      -113.38193634344267,
      32.785998626989176
    ],
    [
      -113.43429306341338,
      32.80042901026511
    ],
    [
      -111.81572975866226,
      33.52185144290009
    ]
  ]
})

or_rainfed_g = ee.Geometry({
  "type": "MultiPoint",
  "coordinates": [
    [
      -123.22304775146787,
      44.179085061502484
    ],
    [
      -123.11936427978819,
      44.22387990484195
    ],
    [
      -123.02186061767881,
      44.26864068887215
    ],
    [
      -123.06786586670225,
      44.32761382632347
    ],
    [
      -123.19283534912412,
      44.41105771032327
    ],
    [
      -123.295832175296,
      44.23421233960921
    ],
    [
      -123.13378383545225,
      44.27699881778173
    ],
    [
      -123.04520656494444,
      44.31287609483352
    ],
    [
      -122.95868923096006,
      44.37720364372508
    ],
    [
      -123.120050925296,
      44.38211124367837
    ],
    [
      -123.20725490478819,
      44.33645468826441
    ],
    [
      -123.30750514892881,
      44.35560531713149
    ],
    [
      -123.3452706518585,
      44.37916673306828
    ],
    [
      -123.14339687256162,
      44.26913237641892
    ],
    [
      -123.08983852295225,
      44.17169802642608
    ],
    [
      -122.922297019046,
      44.3664054758834
    ],
    [
      -123.04266992307417,
      44.535266453136686
    ],
    [
      -122.99254480100386,
      44.56682767159939
    ],
    [
      -123.16901269651167,
      44.5159298150841
    ],
    [
      -122.99391809201948,
      44.48703528793659
    ],
    [
      -122.9619890759062,
      44.549458886070546
    ],
    [
      -118.92733687999475,
      43.23106666710689
    ],
    [
      -118.8663970911764,
      43.2144298178783
    ],
    [
      -118.82107848766077,
      43.19966550423123
    ],
    [
      -118.86365050914515,
      43.19991577660667
    ],
    [
      -118.66280669810999,
      43.259201375587175
    ],
    [
      -118.61096496227015,
      43.25595091773198
    ],
    [
      -118.66040343883265,
      43.276200942919196
    ],
    [
      -118.59427534975791,
      43.32559439547066
    ],
    [
      -118.5664662066915,
      43.35281167121602
    ],
    [
      -118.60800825991416,
      43.358053964825594
    ],
    [
      -118.55856978335166,
      43.248620923513585
    ],
    [
      -118.60354506411338,
      43.28412079460944
    ],
    [
      -118.73503767885947,
      43.268873386528135
    ],
    [
      -118.85348402895713,
      43.27812227025973
    ],
    [
      -118.84867751040244,
      43.252621943924375
    ],
    [
      -118.8847263995626,
      43.277122458702856
    ],
    [
      -119.12586987442673,
      43.36862067136755
    ],
    [
      -118.95832837052048,
      43.41028600556181
    ],
    [
      -118.72496649917981,
      43.61863442773782
    ],
    [
      -118.89222782713381,
      43.59216125792663
    ],
    [
      -119.01342075926271,
      43.56181745014319
    ],
    [
      -118.98870152098146,
      43.53295177966151
    ],
    [
      -119.03505009275881,
      43.5533582546386
    ],
    [
      -119.045349775376,
      43.519867973149275
    ],
    [
      -119.06388920408693,
      43.496710663610074
    ],
    [
      -119.06938236814943,
      43.52111273812029
    ],
    [
      -119.04603642088381,
      43.487245980413576
    ],
    [
      -119.01067417723146,
      43.50617386353212
    ],
    [
      -118.87952488523928,
      43.53716790378691
    ],
    [
      -118.01103974591204,
      45.4144501190926
    ],
    [
      -117.89087678204486,
      45.34355065130437
    ],
    [
      -117.9698410154433,
      45.389862415845144
    ],
    [
      -118.07215119610736,
      45.36719368519729
    ],
    [
      -117.98563386212298,
      45.422161703222365
    ],
    [
      -117.83525849591204,
      45.3372763516564
    ],
    [
      -117.91284943829486,
      45.2967179619491
    ],
    [
      -117.8929367185683,
      45.406255406970246
    ],
    [
      -117.20240631982533,
      45.356910897780594
    ],
    [
      -117.27896729394642,
      45.36028828148647
    ],
    [
      -117.23330536767689,
      45.40393487704498
    ],
    [
      -117.16944733545033,
      45.38681785317658
    ],
    [
      -117.30025330468861,
      45.37572518264261
    ],
    [
      -117.34110871240345,
      45.41502201210444
    ],
    [
      -117.18009034082142,
      45.36969564453642
    ],
    [
      -117.20171967431752,
      45.414540008008395
    ],
    [
      -117.31844941064564,
      45.385853359526024
    ]
  ]
})

ca_rainfed_g = ee.Geometry({
  "type": "MultiPoint",
  "coordinates": [
    [
      -119.00282659540157,
      35.81903363428792
    ],
    [
      -119.01795198728976,
      35.77116736394321
    ],
    [
      -119.07633209419613,
      35.700635788783984
    ],
    [
      -119.47840430063361,
      35.66364220381159
    ],
    [
      -119.6005089826193,
      35.69249866065749
    ],
    [
      -119.4122352339576,
      35.46423418631675
    ],
    [
      -119.24748509684503,
      35.34222754226795
    ],
    [
      -118.99739317345315,
      35.436315469657465
    ],
    [
      -119.17111280898605,
      35.30429869821853
    ],
    [
      -118.89027863643477,
      35.37235075960683
    ],
    [
      -119.10577151923472,
      35.021434816524874
    ],
    [
      -119.47570429121959,
      36.0661584287997
    ],
    [
      -119.57552781165874,
      36.160965921960376
    ],
    [
      -120.04869671756387,
      36.00367427294754
    ],
    [
      -120.28523980984829,
      36.216347967220514
    ],
    [
      -120.0950458879926,
      36.238505161771286
    ],
    [
      -120.23348941054027,
      36.900093742015905
    ],
    [
      -120.82265896780416,
      36.80011935367169
    ],
    [
      -119.97121853811666,
      37.093158703472945
    ],
    [
      -120.52272485737255,
      37.19362038373315
    ],
    [
      -120.45303734283583,
      37.18185708369741
    ],
    [
      -120.6655541275038,
      37.207838206668754
    ],
    [
      -120.73078545074598,
      37.21822815223648
    ],
    [
      -120.81489952545301,
      37.197446830388124
    ],
    [
      -120.23331078033583,
      37.26469196653896
    ],
    [
      -120.16486084148534,
      37.177541168123994
    ],
    [
      -120.45358897661386,
      37.44870897166161
    ],
    [
      -120.44583046359215,
      37.355206926802786
    ],
    [
      -120.45596097003312,
      37.35807064914209
    ],
    [
      -120.4387948323378,
      37.38999235479201
    ],
    [
      -120.51624846119552,
      37.393790212421166
    ],
    [
      -120.7243339696076,
      37.2833965920519
    ],
    [
      -120.73085710193182,
      37.295005184573434
    ],
    [
      -120.74544831897283,
      37.24705695513707
    ],
    [
      -120.60824047200973,
      37.48078819624136
    ],
    [
      -120.52956066569263,
      37.5454212448496
    ],
    [
      -120.47215734841588,
      37.57619059778019
    ],
    [
      -121.36669171961225,
      37.621215634859674
    ],
    [
      -120.99093115594135,
      37.98162813745391
    ],
    [
      -120.92844641473042,
      37.96187096446961
    ],
    [
      -121.66583628454758,
      38.43418498150221
    ],
    [
      -121.7580670684489,
      38.379607524839614
    ],
    [
      -121.9729779566232,
      38.46461907451309
    ],
    [
      -121.94684251198208,
      38.458167127227334
    ],
    [
      -121.01517718668266,
      38.11944284398314
    ],
    [
      -121.00195926065727,
      38.08945550122624
    ],
    [
      -121.05483390463526,
      38.26467404542954
    ],
    [
      -121.77023436580609,
      38.13576092199049
    ],
    [
      -119.5114431732439,
      36.504734738300414
    ],
    [
      -119.48073943574141,
      36.39659090156782
    ],
    [
      -119.22186099154555,
      36.516487456932985
    ],
    [
      -119.09477380305638,
      36.293118762878706
    ],
    [
      -119.06561724976919,
      36.261972629173655
    ],
    [
      -118.93482099182852,
      36.23178122726982
    ],
    [
      -118.9655525652453,
      36.1304038230241
    ],
    [
      -118.97533541488244,
      35.907893415071236
    ],
    [
      -119.07494347441464,
      35.57461643069523
    ]
  ]
})

bakersfield_g = ee.Geometry({
  "type": "Polygon",
  "coordinates": [
    [
      [
        -119.44268257679244,
        35.42757659340908
      ],
      [
        -119.03893501819869,
        35.42757659340908
      ],
      [
        -119.03893501819869,
        35.5382838100466
      ],
      [
        -119.44268257679244,
        35.5382838100466
      ],
      [
        -119.44268257679244,
        35.42757659340908
      ]
    ]
  ]
})

central_kansas_g = ee.Geometry({
  "type": "Polygon",
  "coordinates": [
    [
      [
        -101.39418477864311,
        37.13889997760407
      ],
      [
        -100.12526388020561,
        37.13889997760407
      ],
      [
        -100.12526388020561,
        38.36043236071481
      ],
      [
        -101.39418477864311,
        38.36043236071481
      ],
      [
        -101.39418477864311,
        37.13889997760407
      ]
    ]
  ]
})

southern_idaho_g = ee.Geometry({
  "type": "Polygon",
  "coordinates": [
    [
      [
        -115.1437807047337,
        42.064591353386916
      ],
      [
        -113.1662416422337,
        42.064591353386916
      ],
      [
        -113.1662416422337,
        43.099984199862824
      ],
      [
        -115.1437807047337,
        43.099984199862824
      ],
      [
        -115.1437807047337,
        42.064591353386916
      ]
    ]
  ]
})
