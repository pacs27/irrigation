#----------------------------------------------------------------------------------------#
#---------------------------------------//GEESEBAL//-------------------------------------#
#GEESEBAL - GOOGLE EARTH ENGINE APP FOR SURFACE ENERGY BALANCE ALGORITHM FOR LAND (SEBAL)
#CREATE BY: LEONARDO LAIPELT, RAFAEL KAYSER, ANDERSON RUHOFF AND AYAN FLEISCHMANN
#PROJECT - ET BRASIL https://etbrasil.org/
#LAB - HIDROLOGIA DE GRANDE ESCALA [HGE] website: https://www.ufrgs.br/hge/author/hge/
#UNIVERSITY - UNIVERSIDADE FEDERAL DO RIO GRANDE DO SUL - UFRGS
#RIO GRANDE DO SUL, BRAZIL

#DOI
#VERSION 0.1.1
#CONTACT US: leonardo.laipelt@ufrgs.br

#----------------------------------------------------------------------------------------#
#
# Customized by bjonesneu@berkeley.edu, bjonesneu@gmail.com in February 2022
#   - Added additional output variables
#   - Converted to run all code on GEE Server instead of Client
#
#----------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------#

#PYTHON PACKAGES
#Call EE
import ee
ee.Initialize()
from datetime import date
import datetime

import sys

#FOLDERS
from .landsatcollection import fexp_landsat_5Coordinate, fexp_landsat_7Coordinate, fexp_landsat_8Coordinate, fexp_landsat_9Coordinate
from .masks import (f_albedoL5L7,f_albedoL8_9)
from .meteorology import get_meteorology, retrievePrecip, verifyMeteoAvail
from .tools import (fexp_spec_ind, fexp_radlong_up, LST_DEM_correction,
fexp_radshort_down, fexp_radlong_down, fexp_radbalance, fexp_soil_heat,fexp_sensible_heat_flux_ver_server)
from .endmembers import fexp_cold_pixel, fexp_hot_pixel
from .evapotranspiration import fexp_et
from .constants import Constants
from .landsat_utils import prepSrLandsat5and7, prepSrLandsat8and9


    
#TIMESRIES FUNCTION
class TimeSeries():

    #ENDMEMBERS DEFAULT
    #ALLEN ET AL. (2013)
    def __init__(self,
                 year_i,
                 month_i,
                 day_i,
                 year_e,
                 month_e,
                 day_e,
                 cloud_cover,
                 coordinate,
                 buffersize=90,
                 NDVI_cold=5,
                 Ts_cold=20,
                 NDVI_hot=10,
                 Ts_hot=20,
                 calcRegionalET=False,
                 debug=False,
                 scale=Constants.REDUCER_SCALE
        ):

        #output variable
        self.ETandMeteo = None

        #INFORMATIONS
        self.coordinate=coordinate
        self.cloud_cover=cloud_cover
        self.start_date = ee.Date.fromYMD(year_i,month_i,day_i)
        self.i_date = ee.Date.fromYMD(year_i,month_i,day_i)
        self.end_date = ee.Date.fromYMD(year_e,month_e,day_e)

        #COLLECTIONS
        self.collection_l5=fexp_landsat_5Coordinate(self.start_date, self.end_date, self.coordinate, self.cloud_cover)
        self.collection_l7=fexp_landsat_7Coordinate(self.start_date, self.end_date, self.coordinate, self.cloud_cover)
        self.collection_l8=fexp_landsat_8Coordinate(self.start_date, self.end_date, self.coordinate, self.cloud_cover)
        self.collection_l9=fexp_landsat_9Coordinate(self.start_date, self.end_date, self.coordinate, self.cloud_cover)

        #FOR EACH IMAGE IN THE COLLECTION
        #ESTIMATE ET DAILY IMAGE AND EXTRACT
        #ET VALUE AT THE COORDINATE

        def retrieveETandMeteo(image, debug=False):
            image=ee.Image(image) # just used to ensure correct type casting
            
            #GET INFORMATIONS FROM IMAGE
            _index=image.get('system:index')
            cloud_cover=image.get('CLOUD_COVER')
            LANDSAT_ID=image.get('L1_LANDSAT_PRODUCT_ID')
            landsat_version=ee.String(image.get('SPACECRAFT_ID'))
            zenith_angle=image.get('SOLAR_ZENITH_ANGLE')
            sun_elevation = image.get("SUN_ELEVATION")
            azimuth_angle=image.get('SUN_AZIMUTH')
            time_start=image.get('system:time_start')
            _date=ee.Date(time_start)
            _year=ee.Number(_date.get('year'))
            _month=ee.Number(_date.get('month'))
            _day=ee.Number(_date.get('month'))
            _hour=ee.Number(_date.get('hour'))
            _minutes = ee.Number(_date.get('minutes'))
            crs = image.projection().crs()
            transform = ee.List(ee.Dictionary(ee.Algorithms.Describe(image.projection())).get('transform'))
            date_string=_date.format('YYYY-MM-dd')

            #ENDMEMBERS
            p_top_NDVI=ee.Number(NDVI_cold)
            p_coldest_Ts=ee.Number(Ts_cold)
            p_lowest_NDVI=ee.Number(NDVI_hot)
            p_hottest_Ts=ee.Number(Ts_hot)

            etFeature = ee.Feature(self.coordinate.centroid(), {
              'date': date_string,
              'version': landsat_version,
              'status': 'no status',
                'ET_24h': None,
                'ET_R_min': None,
                'ET_R_max': None,
                'NDVI': None,
                'AirT_G': None,
                'LandT_G': None,
                'ux': None,
                'UR': None,
                'z_alt': None,
                'slope': None,
                'precip': None
                
            })
            errmsg = None
            
            #TO AVOID ERRORS DURING THE PROCESS
            try:
                #GEOMETRY
                geometryReducer=image.geometry().bounds()

                #AIR TEMPERATURE [C]
                T_air = image.select('AirT_G')
                
                #WIND SPEED [M S-1]
                ux= image.select('ux_G')

                #RELATIVE HUMIDITY (%)
                UR = image.select('RH_G')
                #return ee.Feature(None, {'msg': UR})
               
                #NET RADIATION 24H [W M-2]
                Rn24hobs = image.select('Rn24h_G')

                #SRTM DATA ELEVATION
                srtm = ee.Image(Constants.SRTM_ELEVATION_COLLECTION).clip(geometryReducer)
                z_alt = srtm.select('elevation')
                slope = ee.Terrain.slope(z_alt)

                #SPECTRAL IMAGES (NDVI, EVI, SAVI, LAI, T_LST, e_0, e_NB, long, lat)
                image=fexp_spec_ind(image)
                
                #LAND SURFACE TEMPERATURE
                # TODO: IS THIS CORRECTION NECESSARY? Answer: No, because it uses the brightness temperature
                image=LST_DEM_correction(image, z_alt, T_air, UR,sun_elevation,_hour,_minutes)
                T_land = image.select('T_LST_DEM').rename('LandT_G')
                
                
                
                #COLD PIXEL
                d_cold_pixel=fexp_cold_pixel(image, geometryReducer, p_top_NDVI, p_coldest_Ts)

                #COLD PIXEL NUMBER
                n_Ts_cold = ee.Number(d_cold_pixel.get('temp'))
                
                #INSTANTANEOUS OUTGOING LONG-WAVE RADIATION [W M-2]
                image=fexp_radlong_up(image)
                
                #INSTANTANEOUS INCOMING SHORT-WAVE RADIATION [W M-2]
                image=fexp_radshort_down(image,z_alt,T_air,UR, sun_elevation)
                
                #INSTANTANEOUS INCOMING LONGWAVE RADIATION [W M-2]
                image=fexp_radlong_down(image, n_Ts_cold)

                #INSTANTANEOUS NET RADIATON BALANCE [W M-2]
                image=fexp_radbalance(image)

                #SOIL HEAT FLUX (G) [W M-2]
                image=fexp_soil_heat(image)
                
                #HOT PIXEL
                d_hot_pixel=fexp_hot_pixel(image, geometryReducer,p_lowest_NDVI, p_hottest_Ts)
                
                #SENSIBLE HEAT FLUX (H) [W M-2]
                image=fexp_sensible_heat_flux_ver_server(image, ux, UR,Rn24hobs,n_Ts_cold,
                                            d_hot_pixel, date_string, geometryReducer, scale=scale)

                #DAILY EVAPOTRANSPIRATION (ET_24H) [MM DAY-1]
                image=fexp_et(image,Rn24hobs)
                
                NAME_FINAL=ee.String(LANDSAT_ID).slice(0,5).cat(ee.String(LANDSAT_ID).slice(10,17)).cat(ee.String(LANDSAT_ID).slice(17,25))

                #EXTRACT VALUES
                def extractValue(var):
                    return var.reduceRegion(
                        reducer=ee.Reducer.first(),
                        geometry=self.coordinate,
                        scale=Constants.REDUCER_SCALE,
                        maxPixels=Constants.REDUCER_MAX_PIXELS)

                def extractMinValue(var):
                    return var.reduceRegion(
                        reducer=ee.Reducer.min(),
                        geometry=self.coordinate,
                        scale=Constants.REDUCER_SCALE,
                        maxPixels=Constants.REDUCER_MAX_PIXELS)
                def extractMinAndMaxValue(var):
                    return var.reduceRegion(
                        reducer=ee.Reducer.minMax(),
                        geometry=self.coordinate,
                        scale=Constants.REDUCER_SCALE,
                        maxPixels=Constants.REDUCER_MAX_PIXELS)

                def extractMaxValue(var):
                    return var.reduceRegion(
                        reducer=ee.Reducer.max(),
                        geometry=self.coordinate,
                        scale=Constants.REDUCER_SCALE,
                        maxPixels=Constants.REDUCER_MAX_PIXELS)
                
                ET_daily=image.select(['ET_24h'],[NAME_FINAL])
                ET_point = extractValue(ET_daily)

                if calcRegionalET:
                    
                    ET = image.select(['ET_24h'],[NAME_FINAL])
                    ET_MinMax_Daily = extractMinAndMaxValue(ET)
                    ET_min_daily= ET_MinMax_Daily.get('ET_24h_min')
                    ET_max_daily= ET_MinMax_Daily.get('ET_24h_max')
                    
                    

                NDVI_daily=image.select(['NDVI'],[NAME_FINAL])
                NDVI_point = extractValue(NDVI_daily)

                T_air_daily=T_air.select(['AirT_G'],[NAME_FINAL])
                T_air_point = extractValue(T_air_daily)

                T_land_daily=T_land.select(['LandT_G'],[NAME_FINAL])
                T_land_point = extractValue(T_land_daily)

                ux_daily=ux.select(['ux_G'],[NAME_FINAL])
                ux_point = extractValue(ux_daily)
                

                UR_daily=UR.select(['RH_G'],[NAME_FINAL])
                UR_point = extractValue(UR_daily)

                z_alt_daily=srtm.select(['elevation'],[NAME_FINAL])
                z_alt_point = extractValue(z_alt_daily)

                slope_daily=slope.select(['slope'],[NAME_FINAL])
                slope_point = extractValue(slope_daily)

                #GET DATE AND DAILY ET
                ET_point_get = ee.Number(ET_point.get(NAME_FINAL))
               
                if calcRegionalET:
                    ET_min_point_get = ee.Number(ET_min_point.get(NAME_FINAL))
                    ET_max_point_get = ee.Number(ET_max_point.get(NAME_FINAL))
                else: # this will effectively cause any downstream ET_R calculations to return the ET_24h value
                    ET_min_point_get = ee.Number(0.0)
                    ET_max_point_get = ee.Number(1.0)

                NDVI_point_get = ee.Number(NDVI_point.get(NAME_FINAL))
                T_air_point_get = ee.Number(T_air_point.get(NAME_FINAL))
                T_land_point_get = ee.Number(T_land_point.get(NAME_FINAL))#.subtract(ee.Number(273.15))
                                  # conversion from Kelvin to Celsius causes crash when LandT_G is None
                                    # so this conversion was moved to client code
                ux_point_get = ee.Number(ux_point.get(NAME_FINAL))
                UR_point_get = ee.Number(UR_point.get(NAME_FINAL))
                z_alt_point_get = ee.Number(z_alt_point.get(NAME_FINAL))
                slope_point_get = ee.Number(slope_point.get(NAME_FINAL))

                precip = retrievePrecip(date_string, self.coordinate, scale=None)

                etFeature = ee.Feature(self.coordinate.centroid(), {
                    'date': date_string,
                    'version': landsat_version,
                    'status': 'ok',
                    'ET_24h': ET_point_get,
                    'ET_R_min': ET_min_point_get,
                    'ET_R_max':     ET_max_point_get,
                    'NDVI': NDVI_point_get,
                    'AirT_G': T_air_point_get,
                    'LandT_G': T_land_point_get,
                    'ux': ux_point_get,
                    'UR': UR_point_get,
                    'z_alt': z_alt_point_get,
                    'slope': slope_point_get,
                    'precip': precip,
                })

            except:
                # ERRORS CAN OCCUR WHEN:
                # - THERE IS NO METEOROLOGICAL INFORMATION.
                # - ET RETURN NULL IF AT THE POINT WAS APPLIED MASK CLOUD.
                # - CONNECTION ISSUES.
                # - SEBAL DOESN'T FIND A REASONABLE LINEAR RELATIONSHIP (dT).
                raise Exception(sys.exc_info()[0])
                # etFeature = ee.Feature(self.coordinate.centroid(), {
                #     'date': date_string,
                #     'version': landsat_version,
                #     'status': 'failed',
                #     'ET_24h': None,
                #     'ET_R_min': None,
                #     'ET_R_max': None,
                #     'NDVI': None,
                #     'AirT_G': None,
                #     'LandT_G': None,
                #     'ux': None,
                #     'UR': None,
                #     'z_alt': None,
                #     'slope': None,
                #     'precip': None
                # })

            
            if(debug):
                image_bands_max = image.reduceRegion(
                reducer=ee.Reducer.max(),
                geometry=self.coordinate,
                scale=Constants.REDUCER_SCALE,
                maxPixels=Constants.REDUCER_MAX_PIXELS
                )
                
                image_band_features = ee.Feature(None, {
                    "id": LANDSAT_ID,
                    'date': time_start,
                    'version': landsat_version,
                    'status': 'ok',
                    'image_bands_max': image_bands_max
                })
                # return etFeature variable and image
                return ee.Feature(None, {'msg': etFeature, 'image': image_band_features})
            
            return etFeature
        
        if(debug):
            def print_image_id(image):
                image=ee.Image(image)
                return image.get('system:index')
            
            try:
                collention_l5 = (self.collection_l5.map(f_albedoL5L7)
                            .map(verifyMeteoAvail)
                            .filter(ee.Filter.gt('meteo_count', 0)).map(print_image_id))
                
                
                number_of_l5_images = collention_l5.size().getInfo()
                
                print("Number of L5 images = ", number_of_l5_images)
            except:
                number_of_l5_images = 0
                print("No L5 images")
            try:
                collection_l7 = (self.collection_l7.map(f_albedoL5L7)
                            .map(verifyMeteoAvail)
                            .filter(ee.Filter.gt('meteo_count', 0)).map(print_image_id))
                
                number_of_l7_images = collection_l7.size().getInfo()
            
            
        
                print("Number of L7 images = ", number_of_l7_images)
            except:
                number_of_l7_images = 0
                print("No L7 images")
                
            try:
            
                collection_l8 = (self.collection_l8.map(f_albedoL8_9)
                            .map(verifyMeteoAvail)
                            .filter(ee.Filter.gt('meteo_count', 0)).map(print_image_id))
                number_of_l8_images = collection_l8.size().getInfo()
                
                print("Number of L8 images = ", number_of_l8_images)
            except:
                number_of_l8_images = 0
                print("No L8 images")
                
            try:
                collection_l9 = (self.collection_l9.map(f_albedoL8_9)
                            .map(verifyMeteoAvail)
                            .filter(ee.Filter.gt('meteo_count', 0)).map(print_image_id))
                
                number_of_l9_images = collection_l9.size().getInfo()
                
                print("Number of L9 images = ", number_of_l9_images)
            
            except:
                number_of_l9_images = 0
                print("No L9 images")
                
        fc5 = (self.collection_l5
                    .map(f_albedoL5L7)
                    .map(verifyMeteoAvail)
                    .filter(ee.Filter.gt('meteo_count', 0)) 
                    .map(lambda image: get_meteorology(image))
                    # .aside(print)
                    .map(lambda image: retrieveETandMeteo(image, debug=debug))
        )
        self.ETandMeteo = fc5
           
        fc7 = (self.collection_l7
                    .map(f_albedoL5L7)
                    .map(verifyMeteoAvail)
                    .filter(ee.Filter.gt('meteo_count', 0))
                    .map(lambda image: get_meteorology(image))
                    .map(lambda image: retrieveETandMeteo(image, debug=debug))
        )
        self.ETandMeteo = self.ETandMeteo.merge(fc7)
        
        fc8 = (self.collection_l8
                    .map(f_albedoL8_9)
                    .map(verifyMeteoAvail)
                    .filter(ee.Filter.gt('meteo_count', 0))
                    .map(lambda image: get_meteorology(image))
                    .map(lambda image: retrieveETandMeteo(image, debug=debug))
        )
        self.ETandMeteo = self.ETandMeteo.merge(fc8)

        fc9 = (self.collection_l9
                    .map(f_albedoL8_9)
                    .map(verifyMeteoAvail)
                    .filter(ee.Filter.gt('meteo_count', 0))
                    .map(lambda image: get_meteorology(image))
                    .map(lambda image: retrieveETandMeteo(image, debug=debug))
        )
        self.ETandMeteo = self.ETandMeteo.merge(fc9)
