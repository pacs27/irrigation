class Constants:

    # LANDSAT COLLECTIONS
    LANDSAT_COLLECTION_9 = "LANDSAT/LC09/C02/T1_L2"
    LANDSAT_COLLECTION_8 = "LANDSAT/LC08/C02/T1_L2"
    LANDSAT_COLLECTION_7 = "LANDSAT/LE07/C02/T1_L2"
    LANDSAT_COLLECTION_5 = "LANDSAT/LT05/C02/T1_L2"
    
    LANDSAT_9_BANDS = {
        "OFFICIAL": ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7", "ST_B10"],
        "CUSTOM": ["UB", "B", "GR", "R", "NIR", "SWIR_1", "SWIR_2", "T_LST"],
    }
    
    LANDSAT_8_BANDS = {
        "OFFICIAL": ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7", "ST_B10"],
        "CUSTOM": ["UB", "B", "GR", "R", "NIR", "SWIR_1", "SWIR_2", "T_LST"],
    }
    
    LANDSAT_5_7_BANDS = {
        "OFFICIAL": ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7", "ST_B6"],
        "CUSTOM": ["B", "GR", "R", "NIR", "SWIR_1", "SWIR_2", "T_LST"],
    }
    
    
    
    SRTM_ELEVATION_COLLECTION = "USGS/SRTMGL1_003"
    WEATHER_COLLECTION = "ECMWF/ERA5_LAND/HOURLY"
    WEATHER_NASA_GLDAS_V021_NOAH_G025_T3H= "NASA/GLDAS/V021/NOAH/G025/T3H"
    NOAA_CFSV2_6H = "NOAA/CFSV2/FOR6H"
    
    #SURFACE WATER VAPOUR VARIABLE FROM NCEP
    #NOTE THAT EACH OBSERVATION DURING DAY
    #IS A COLLECTION THERE ARE 4 OBSERVATION PER DAY
    SURFACE_WATER_VAPOUR_COLLECTION = "NCEP_RE/surface_wv"
    
    MODIS_MCD12Q1_COLLECTION = 'MODIS/006/MCD12Q1'
    
    REDUCER_SCALE = 30
    REDUCER_MAX_PIXELS = 9e9
    REDUCER_WP_SCALE = 1000 # FOR SURFACE_WATER_VAPOUR_COLLECTION