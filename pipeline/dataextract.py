import ee
from etbrasil.geesebal import TimeSeries_bcj
from tqdm import tqdm

def exportETdata(etFC, lbl, loc, folder='irrigation'):
    filename = 'et_TS_' + lbl + '_' + loc
    task = ee.batch.Export.table.toDrive(
      collection = etFC,
      description = filename,
      folder = folder,
    )
    task.start()

def extractData(aoi, aoi_label,
                start_yr=2015, start_mo=6, start_dy=1,
                end_yr=2021, end_mo=8, end_dy=31,
                max_cloud_cover=30,
                buffer_range=50,
                calc_ET_region=False):

    # buffer_range is in meters, max 7000 for GEE limits.
    # must be set tight around sample locations to limit zone from
    # which data is retrievedfor the sample location itself.

    # region size for ET_24_R calculation is handled with
    # buffersize parameter below

    out = []
    max_points = 10000 # set arbitrarily high to capture all values
    num_sample_years = end_yr - start_yr

    # ensure there is a defined buffer zone around each location
    locs_list = aoi.toList(max_points)
    locations_buffered = ee.FeatureCollection(locs_list) \
                            .geometry() \
                            .coordinates() \
                            .map(lambda p: ee.Geometry.Point(p) \
                                             .buffer(buffer_range))

    num_locations = locations_buffered.size().getInfo()
    print('Number of locations to extract =', num_locations)

    cnt = 0
    for yr_inc in tqdm(range(num_sample_years)):
        for idx in tqdm(range(num_locations), leave=False):
            location = locations_buffered.get(idx)
            single_location = ee.Geometry(location)

            loc_type = ee.Feature(locs_list.get(idx)).get('POINT_TYPE')

            # use buffersize=5000 and calcRegionalET=True for ET_24h_R regionalization calculations
            buffsize = 50
            if calc_ET_region:
                buffsize = 5000

            sebalTS = TimeSeries_bcj(start_yr+yr_inc, start_mo, start_dy,
                                        start_yr+yr_inc, end_mo, end_dy,
                                        max_cloud_cover, single_location,
                                        buffersize=buffsize,
                                        calcRegionalET=calc_ET_region
                                     )

            sebalTS.ETandMeteo = sebalTS.ETandMeteo \
                                    .map(lambda x: x.set('loc_type', loc_type))

            exportETdata(etFC=sebalTS.ETandMeteo,
                         lbl=aoi_label,
                         loc=str(idx)+'_'+str(start_yr+yr_inc))
            out.append(sebalTS.ETandMeteo)
            cnt+=1

    print('Number of tasks launched =', cnt)
    return out