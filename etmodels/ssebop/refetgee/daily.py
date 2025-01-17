import math
import datetime

import ee
import pandas as pd

try:
    from . import calcs
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__)))
    import calcs


def lazy_property(fn):
    """Decorator that makes a property lazy-evaluated

    https://stevenloria.com/lazy-properties/
    """
    attr_name = "_lazy_" + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    return _lazy_property


class Daily:
    """"""

    def __init__(
        self,
        tmax,
        tmin,
        ea,
        rs,
        uz,
        zw,
        elev,
        lat,
        doy,
        method="asce",
        rso_type=None,
        rso=None,
    ):
        """ASCE Daily Standardized Reference Evapotranspiration (ET)

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

        """

        if method.lower() not in ["asce", "refet"]:
            raise ValueError('method must be "asce" or "refet"')

        if rso_type is None:
            pass
        elif rso_type.lower() not in ["simple", "full", "array"]:
            raise ValueError('rso_type must be None, "simple", "full", or "array')
        elif rso_type.lower() in "array":
            # Check that rso is an ee.Image or ee.Number?
            pass

        # Get time_start from tmin
        # Should time_start be set in init?
        self.time_start = ee.Image(tmin).get("system:time_start")
        self.date = ee.Date(self.time_start)

        # Do these all need to be set onto self?
        self.tmax = tmax
        self.tmin = tmin
        self.ea = ea
        self.rs = rs
        self.uz = uz
        self.zw = zw
        self.elev = elev
        self.lat = lat
        self.doy = doy

        # Convert latitude to radians
        self.lat = self.lat.multiply(math.pi / 180)

        # To match standardized form, pair is calculated from elevation
        self.pair = calcs._air_pressure(self.elev, method)

        # Psychrometric constant (Eq. 4)
        self.psy = self.pair.multiply(0.000665)

        self.tmean = self.tmax.add(self.tmin).multiply(0.5)
        self.es_slope = calcs._es_slope(self.tmean, method)

        # Saturated vapor pressure
        self.es = (
            calcs._sat_vapor_pressure(self.tmax)
            .add(calcs._sat_vapor_pressure(self.tmin))
            .multiply(0.5)
        )

        # Vapor pressure deficit
        self.vpd = calcs._vpd(es=self.es, ea=self.ea)

        # Extraterrestrial radiation
        self.ra = calcs._ra_daily(lat=self.lat, doy=self.doy, method=method)

        # Clear sky solar radiation
        # If rso_type is not set, use the method
        # If rso_type is set, use rso_type directly
        if rso_type is None:
            if method.lower() == "asce":
                self.rso = calcs._rso_simple(ra=self.ra, elev=self.elev)
            elif method.lower() == "refet":
                self.rso = calcs._rso_daily(
                    ea=self.ea, ra=self.ra, pair=self.pair, doy=self.doy, lat=self.lat
                )
        elif rso_type.lower() == "simple":
            self.rso = calcs._rso_simple(ra=self.ra, elev=self.elev)
        elif rso_type.lower() == "full":
            self.rso = calcs._rso_daily(
                ea=self.ea, ra=self.ra, pair=self.pair, doy=self.doy, lat=self.lat
            )
        elif rso_type.lower() == "array":
            # Use rso array passed to function
            self.rso = rso

        # Cloudiness fraction
        self.fcd = calcs._fcd_daily(rs=self.rs, rso=self.rso)

        # Net long-wave radiation
        self.rnl = calcs._rnl_daily(
            tmax=self.tmax, tmin=self.tmin, ea=self.ea, fcd=self.fcd
        )

        # Net radiation
        self.rn = calcs._rn(self.rs, self.rnl)

        # Wind speed
        self.u2 = calcs._wind_height_adjust(uz=self.uz, zw=self.zw)

    def etsz(self, surface):
        """Standardized reference ET

        Parameters
        ----------
        surface : {'alfalfa', 'etr', 'tall', 'grass', 'eto', 'short'}
            Reference surface type.

        Returns
        -------
        ee.Image

        """
        if surface.lower() in ["alfalfa", "etr", "tall"]:
            return self.etr
        elif surface.lower() in ["grass", "eto", "short"]:
            return self.eto
        else:
            raise ValueError("unsupported surface type: {}".format(surface))

    @lazy_property
    def eto(self):
        """Short (grass) reference surface"""
        self.cn = 900
        self.cd = 0.34
        return ee.Image(
            self._etsz().rename(["et0"]).set("system:time_start", self.time_start)
        )

    @lazy_property
    def etr(self):
        """Tall (alfalfa) reference surface"""
        self.cn = 1600
        self.cd = 0.38
        return ee.Image(
            self._etsz().rename(["etr"]).set("system:time_start", self.time_start)
        )

    def _etsz(self):
        """Daily reference ET (Eq. 1)

        Returns
        -------
        etsz : ee.Image
            Standardized reference ET [mm].

        """
        return (
            self.tmean.add(273)
            .pow(-1)
            .multiply(self.u2)
            .multiply(self.vpd)
            .multiply(self.cn)
            .multiply(self.psy)
            .add(self.es_slope.multiply(self.rn).multiply(0.408))
            .divide(
                self.u2.multiply(self.cd).add(1).multiply(self.psy).add(self.es_slope)
            )
        )

        # return self.tmin.expression(
        #     '(0.408 * es_slope * rn + (psy * cn * u2 * vpd / (tmean + 273))) / '
        #     '(es_slope + psy * (cd * u2 + 1))',
        #     {'cd': self.cd, 'cn': self.cn, 'es_slope': self.es_slope,
        #      'psy': self.psy, 'rn': self.rn, 'tmean': self.tmean,
        #      'u2': self.u2, 'vpd': self.vpd})

    @lazy_property
    def etw(self):
        """Priestley-Taylor evaporation (alpha = 1.26)

        Returns
        -------
        etw : ee.Image
            Priestley-Taylor ET [mm].

        References
        ----------
        https://wetlandscapes.github.io/blog/blog/penman-monteith-and-priestley-taylor/

        """
        return (
            self.es_slope.expression(
                "(alpha * es_slope * rn * 1000 / (2453 * (es_slope + psy)))",
                {
                    "es_slope": self.es_slope,
                    "rn": self.rn,
                    "psy": self.psy,
                    "alpha": 1.26,
                },
            )
            .rename(["etw"])
            .set("system:time_start", self.time_start)
        )
        # return self.es_slope.multiply(self.rn)\
        #     .divide((self.es_slope.add(self.psy)).multiply(2453))\
        #     .multiply(1.26).multiply(1000)\
        #     .rename(['etw'])\
        #     .set('system:time_start', self.time_start)

    @lazy_property
    def eto_fs1(self):
        """UF-IFAS Extension FS1 Radiation Term (ETrad)

        Returns
        -------
        eto_fs1 : ee.Image
            FS1 ETrad [mm].

        References
        ----------
        https://edis.ifas.ufl.edu/pdffiles/ae/ae45900.pdf

        """
        return (
            self.u2.expression(
                "(delta / (delta + psy * (1 + 0.34 * u2))) * (0.408 * rn)",
                {"delta": self.es_slope, "psy": self.psy, "u2": self.u2, "rn": self.rn},
            )
            .rename(["eto_fs1"])
            .set("system:time_start", self.time_start)
        )

        # return self.es_slope\
        #       .divide(self.es_slope.add(self.psy.multiply(self.u2.multiply(0.34).add(1))))\
        #       .multiply(self.rn.multiply(0.408))

    @lazy_property
    def eto_fs2(self):
        """UF-IFAS Extension FS2 Wind Term (ETwind)

        Returns
        -------
        eto_fs2 : ee.Image
            FS2 ETwind [mm].

        References
        ----------
        https://edis.ifas.ufl.edu/pdffiles/ae/ae45900.pdf

        """
        # Temperature Term (Eq. 14)
        TT = self.u2.expression(
            "(900 / (t + 273)) * u2", {"t": self.tmean, "u2": self.u2}
        )
        # Psi Term (Eq. 13)
        PT = self.u2.expression(
            "psy / (slope + psy * (1 + 0.34 * u2))",
            {"slope": self.es_slope, "psy": self.psy, "u2": self.u2},
        )

        return (
            self.u2.expression(
                "PT * TT * (es-ea)", {"PT": PT, "TT": TT, "es": self.es, "ea": self.ea}
            )
            .rename(["eto_fs2"])
            .set("system:time_start", self.time_start)
        )

        # return self.PT.multiply(self.TT)\
        #     .multiply(self.es.subtract(self.ea))\
        #     .rename(['eto_fs2'])\
        #     .set('system:time_start', self.time_start)

    @lazy_property
    def pet_hargreaves(self):
        """Hargreaves potential ET

        Returns
        -------
        hargreaves_pet : ee.Image
            Hargreaves ET [mm].

        References
        ----------

        """
        return (
            self.tmax.expression(
                "0.0023 * (tmean + 17.8) * ((tmax - tmin) ** 0.5) * 0.408 * ra",
                {
                    "tmean": self.tmean,
                    "tmax": self.tmax,
                    "tmin": self.tmin,
                    "ra": self.ra,
                },
            )
            .rename(["pet_hargreaves"])
            .set("system:time_start", self.time_start)
        )
        # return self.ra\
        #     .multiply(self.tmean.add(17.8))\
        #     .multiply(self.tmax.subtract(self.tmin).pow(0.5))\
        #     .multiply(0.0023 * 0.408)\
        #     .rename(['pet_hargreaves'])\
        #     .set('system:time_start', self.time_start)

    @classmethod
    def gridmet(
        cls, input_img, zw=None, elev=None, lat=None, method="asce", rso_type=None
    ):
        """Initialize daily RefET from a GRIDMET image

        Parameters
        ----------
        input_img : ee.Image
            GRIDMET image from the collection IDAHO_EPSCOR/GRIDMET.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The standard GRIDMET elevation image
            (projects/climate-engine/gridmet/elevtion) will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The latitude will be computed
            dynamically using ee.Image.pixelLonLat() if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Temperatures are converted from K to C.
        Solar radiation is converted from W m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from specific humidity (GRIDMET sph)
            and air pressure (from elevation).

        """
        image_date = ee.Date(input_img.get("system:time_start"))

        # gridmet_transform = [0.041666666666666664, 0, -124.78749996666667,
        #                      0, -0.041666666666666664, 49.42083333333334]

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            elev = ee.Image(
                "projects/earthengine-legacy/assets/"
                "projects/climate-engine/gridmet/elevation"
            ).rename(["elevation"])
            # elev = ee.Image('CGIAR/SRTM90_V4')\
            #     .reproject('EPSG:4326', gridmet_transform)
        if lat is None:
            lat = (
                ee.Image(
                    "projects/earthengine-legacy/assets/"
                    "projects/climate-engine/gridmet/elevation"
                )
                .multiply(0)
                .add(ee.Image.pixelLonLat().select("latitude"))
                .rename(["latitude"])
            )
            # lat = ee.Image.pixelLonLat().select('latitude')\
            #     .reproject('EPSG:4326', gridmet_transform)
            # lat = input_img.select([0]).multiply(0)\
            #     .add(ee.Image.pixelLonLat().select('latitude'))

        return cls(
            tmax=input_img.select(["tmmx"]).subtract(273.15),
            tmin=input_img.select(["tmmn"]).subtract(273.15),
            ea=calcs._actual_vapor_pressure(
                q=input_img.select(["sph"]), pair=calcs._air_pressure(elev, method)
            ),
            rs=input_img.select(["srad"]).multiply(0.0864),
            uz=input_img.select(["vs"]),
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(image_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def maca(
        cls, input_img, zw=None, elev=None, lat=None, method="asce", rso_type=None
    ):
        """Initialize daily RefET from a MACA image

        Parameters
        ----------
        input_img : ee.Image
            MACA image from the collection IDAHO_EPSCOR/MACAv2_METDATA.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The standard GRIDMET elevation image
            (projects/climate-engine/gridmet/elevtion) will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The latitude will be computed
            dynamically using ee.Image.pixelLonLat() if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Temperatures are converted from K to C.
        Solar radiation is converted from W m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from specific humidity (MACA huss)
            and air pressure (from elevation).
        Windspeed from east and north vector components m s-1.

        """
        image_date = ee.Date(input_img.get("system:time_start"))

        # CHECK MACA transform (Why the difference?)
        # maca_transform = [0.04163593073593073, 0, -124.7722,
        #                       0, 0.04159470085470086, 25.0631]
        # gridmet_transform = [0.041666666666666664, 0, -124.78749996666667,
        #                      0, -0.041666666666666664, 49.42083333333334]

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            # should we use gridmet elev? maca grid is shifted
            elev = ee.Image(
                "projects/earthengine-legacy/assets/"
                "projects/climate-engine/gridmet/elevation"
            )
            # elev = ee.Image('CGIAR/SRTM90_V4') \
            #     .reproject('EPSG:4326', gridmet_transform)
        if lat is None:
            lat = (
                ee.Image(
                    "projects/earthengine-legacy/assets/"
                    "projects/climate-engine/gridmet/elevation"
                )
                .multiply(0)
                .add(ee.Image.pixelLonLat().select("latitude"))
            )
            # lat = ee.Image.pixelLonLat().select('latitude') \
            #     .reproject('EPSG:4326', gridmet_transform)
            # lat = input_img.select([0]).multiply(0) \
            #     .add(ee.Image.pixelLonLat().select('latitude'))

        def wind_magnitude(input_img):
            """Compute daily wind magnitude from vectors"""
            return (
                ee.Image(input_img.select(["uas"]))
                .pow(2)
                .add(ee.Image(input_img.select(["vas"])).pow(2))
                .sqrt()
                .rename(["uz"])
            )

        wind_img = ee.Image(wind_magnitude(input_img))

        return cls(
            tmax=input_img.select(["tasmax"]).subtract(273.15),
            tmin=input_img.select(["tasmin"]).subtract(273.15),
            ea=calcs._actual_vapor_pressure(
                pair=calcs._air_pressure(elev, method), q=input_img.select(["huss"])
            ),
            rs=input_img.select(["rsds"]).multiply(0.0864),
            uz=wind_img.select(["uz"]),
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(image_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def nldas(
        cls,
        input_collection,
        zw=None,
        elev=None,
        lat=None,
        method="asce",
        rso_type=None,
    ):
        """Initialize daily RefET from a hourly NLDAS image collection

        Parameters
        ----------
        input_collection : ee.ImageCollection
            Collection of NLDAS hourly images for a single day from the
            collection NASA/NLDAS/FORA0125_H002.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  A custom NLDAS elevation image
            (projects/eddi-noaa/nldas/elevation) will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The latitude will be computed
            dynamically using ee.Image.pixelLonLat() if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Solar radiation is converted from W m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from specific humidity and air
            pressure (from elevation).

        """
        input_collection = ee.ImageCollection(input_collection)
        image_date = ee.Date(
            ee.Image(input_collection.first()).get("system:time_start")
        )

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            elev = ee.Image(
                "projects/openet/assets/meteorology/nldas/ancillary/elevation"
            )
            # elev = ee.Image('CGIAR/SRTM90_V4')\
            #     .reproject('EPSG:4326', [0.125, 0, -125, 0, -0.125, 53])
        if lat is None:
            lat = ee.Image(
                "projects/openet/assets/meteorology/nldas/ancillary/latitude"
            )
            # lat = ee.Image('projects/earthengine-legacy/assets/'
            #                'projects/eddi-noaa/nldas/elevation')\
            #     .multiply(0).add(ee.Image.pixelLonLat().select('latitude'))\
            #     .rename(['latitude'])
            # lat = ee.Image.pixelLonLat().select('latitude')\
            #     .reproject('EPSG:4326', [0.125, 0, -125, 0, -0.125, 53])
            # lat = input_collection.first().select([0]).multiply(0)\
            #     .add(ee.Image.pixelLonLat().select('latitude'))

        def wind_magnitude(input_img):
            """Compute hourly wind magnitude from vectors"""
            return (
                ee.Image(input_img.select(["wind_u"]))
                .pow(2)
                .add(ee.Image(input_img.select(["wind_v"])).pow(2))
                .sqrt()
                .rename(["uz"])
            )

        wind_img = ee.Image(
            ee.ImageCollection(input_collection.map(wind_magnitude)).mean()
        )

        ea_img = calcs._actual_vapor_pressure(
            pair=calcs._air_pressure(elev, method),
            q=input_collection.select(["specific_humidity"]).mean(),
        )

        return cls(
            tmax=input_collection.select(["temperature"]).max(),
            tmin=input_collection.select(["temperature"]).min(),
            ea=ea_img,
            rs=input_collection.select(["shortwave_radiation"]).sum().multiply(0.0036),
            uz=wind_img,
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(image_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def cfsv2(
        cls,
        input_collection,
        zw=None,
        elev=None,
        lat=None,
        method="asce",
        rso_type=None,
    ):
        """Initialize daily RefET from a 6-hourly CFSv2 image collection

        Parameters
        ----------
        input_collection : ee.ImageCollection
            Collection of CFSv2 6 hourly images for a single day from the
            collection NOAA/CFSV2/FOR6H.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The SRTM elevation image (CGIAR/SRTM90_V4)
            will be reprojected to the CFSv2 grid if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The latitude will be computed
            dynamically using ee.Image.pixelLonLat() if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Temperatures are converted from K to C.
        Solar radiation is converted from W m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from specific humidity and air
            pressure (from elevation).

        """
        input_collection = ee.ImageCollection(input_collection)
        image_date = ee.Date(
            ee.Image(input_collection.first()).get("system:time_start")
        )

        cfsv2_crs = "EPSG:4326"
        # Transform for 2011 to Present
        cfsv2_transform = [
            0.20454520376789903,
            0.0,
            -180,
            0.0,
            -0.20442210122586923,
            90,
        ]
        # Transform for 1979 to 2010
        # cfsv2_transform = [0.3124995757764987, 0, -180,
        #                    0, -0.31221217943274454, 90]

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            # TODO: Build a CFSv2 elevation asset
            elev = ee.Image("CGIAR/SRTM90_V4").reproject(cfsv2_crs, cfsv2_transform)
        if lat is None:
            lat = (
                ee.Image.pixelLonLat()
                .select("latitude")
                .reproject(cfsv2_crs, cfsv2_transform)
            )
            # lat = input_collection.first().select([0]).multiply(0)\
            #     .add(ee.Image.pixelLonLat().select('latitude'))

        def wind_magnitude(input_img):
            """Compute hourly wind magnitude from vectors"""
            u_img = ee.Image(input_img).select(
                ["u-component_of_wind_height_above_ground"]
            )
            v_img = ee.Image(input_img).select(
                ["v-component_of_wind_height_above_ground"]
            )
            return u_img.pow(2).add(v_img.pow(2)).sqrt()

        wind_img = ee.Image(
            ee.ImageCollection(input_collection.map(wind_magnitude)).mean()
        )

        ea_img = calcs._actual_vapor_pressure(
            pair=calcs._air_pressure(elev, method),
            # pair=input_collection.select(['Pressure_surface']).mean()
            q=input_collection.select(["Specific_humidity_height_above_ground"]).mean(),
        )

        return cls(
            tmax=input_collection.select(
                ["Maximum_temperature_height_above_ground_6_Hour_Interval"]
            )
            .max()
            .subtract(273.15),
            tmin=input_collection.select(
                ["Minimum_temperature_height_above_ground_6_Hour_Interval"]
            )
            .min()
            .subtract(273.15),
            ea=ea_img,
            # TODO: Check the conversion on solar
            rs=input_collection.select(
                ["Downward_Short-Wave_Radiation_Flux_surface_6_Hour_Average"]
            )
            .mean()
            .multiply(0.0864),
            uz=wind_img,
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(image_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def rtma(
        cls,
        input_collection,
        rs=None,
        zw=None,
        elev=None,
        lat=None,
        method="asce",
        rso_type=None,
    ):
        """Initialize daily RefET from a hourly RTMA image collection

        Parameters
        ----------
        input_collection : ee.ImageCollection
            Collection of RTMA hourly images for a single day from the
            collection NOAA/NWS/RTMA.
        rs : ee.Image, str, optional
            Incoming solar radiation [MJ m-2 day-1].  The GRIDMET image for the
            concurrent day will be used if not set.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The RTMA elevation image
            (projects/climate-engine/rtma/elevation) will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The latitude will be computed
            dynamically using ee.Image.pixelLonLat() if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Solar radiation is converted from W m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from specific humidity and air
            pressure (from elevation).

        """
        input_collection = ee.ImageCollection(input_collection)
        start_date = ee.Date(
            ee.Image(input_collection.first()).get("system:time_start")
        )

        # Parse the solar radiation input
        if isinstance(rs, ee.Image):
            pass
        elif isinstance(rs, ee.Number) or isinstance(rs, float) or isinstance(rs, int):
            rs = ee.Image.constant(rs)
        elif rs is None or rs.upper() == "GRIDMET":
            rs_coll = (
                ee.ImageCollection("IDAHO_EPSCOR/GRIDMET")
                .filterDate(start_date, start_date.advance(1, "day"))
                .select(["srad"])
            )
            rs = ee.Image(rs_coll.first()).multiply(0.0864)
        elif rs.upper() == "NLDAS":
            rs_coll = (
                ee.ImageCollection("NASA/NLDAS/FORA0125_H002")
                .filterDate(start_date, start_date.advance(1, "day"))
                .select(["shortwave_radiation"])
            )
            # TODO: Check this unit conversion
            rs = ee.Image(rs_coll.sum()).multiply(0.0036)
        else:
            raise ValueError("Unsupported Rs input")
        # CGM - For now I don't think it makes sense to support image collections
        # elif isinstance(rs, ee.ImageCollection):
        #     rs = ee.Image(rs.sum())
        #     # rs = ee.Image(rs.mean())

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            elev = ee.Image(
                "projects/earthengine-legacy/assets/"
                "projects/climate-engine/rtma/elevation"
            ).rename(["elevation"])
        if lat is None:
            lat = (
                ee.Image(
                    "projects/earthengine-legacy/assets/"
                    "projects/climate-engine/rtma/elevation"
                )
                .multiply(0)
                .add(ee.Image.pixelLonLat().select("latitude"))
                .rename(["latitude"])
            )

        # DEADBEEF - Don't compute wind speed from the components since
        #   a wind speed band is provided
        # def wind_magnitude(input_img):
        #     """Compute hourly wind magnitude from vectors"""
        #     return ee.Image(input_img.select(['UGRD'])).pow(2)\
        #         .add(ee.Image(input_img.select(['VGRD'])).pow(2))\
        #         .sqrt().rename(['WIND'])
        # wind_img = ee.Image(
        #     ee.ImageCollection(input_collection.map(wind_magnitude)).mean())

        ea_img = calcs._actual_vapor_pressure(
            pair=calcs._air_pressure(elev, method),
            q=input_collection.select(["SPFH"]).mean(),
        )

        return cls(
            tmax=input_collection.select(["TMP"]).max(),
            tmin=input_collection.select(["TMP"]).min(),
            ea=ea_img,
            rs=rs,
            uz=input_collection.select(["WIND"]).mean(),
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(start_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def era5(
        cls,
        input_collection,
        zw=None,
        elev=None,
        lat=None,
        method="asce",
        rso_type=None,
    ):
        """Initialize daily RefET from an hourly ERA5 image collection

        Parameters
        ----------
        input_collection : ee.ImageCollection
            Collection of ERA5 hourly images for a single day from the
            collection ECMWF/ERA5/HOURLY.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The OpenET ERA5 elevation image
            (projects/openet/assets/meteorology/era5/ancillary/elevation)
            will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The OpenET ERA5 latitude image
            (projects/openet/assets/meteorology/era5/ancillary/latitude)
            will be used if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Temperatures are converted from K to C.
        Solar radiation is summed and converted from J m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from dew point temperature.

        """
        input_collection = ee.ImageCollection(input_collection)
        start_date = ee.Date(
            ee.Image(input_collection.first()).get("system:time_start")
        )

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            elev = ee.Image(
                "projects/openet/assets/meteorology/era5/ancillary/elevation"
            )
        if lat is None:
            lat = ee.Image(
                "projects/openet/assets/meteorology/era5/ancillary/latitude"
            )  # lat = ee.Image('projects/openet/assets/meteorology/era5/ancillary/elevation')\
            #     .multiply(0).add(ee.Image.pixelLonLat().select('latitude'))\
            #     .rename(['latitude'])

        def wind_magnitude(input_img):
            """Compute hourly wind magnitude from vectors"""
            return (
                ee.Image(input_img.select(["u_component_of_wind_10m"]))
                .pow(2)
                .add(ee.Image(input_img.select(["v_component_of_wind_10m"])).pow(2))
                .sqrt()
                .rename(["wind_10m"])
            )

        wind_img = ee.Image(
            ee.ImageCollection(input_collection.map(wind_magnitude)).mean()
        )

        return cls(
            tmax=input_collection.select(["temperature_2m"]).max().subtract(273.15),
            tmin=input_collection.select(["temperature_2m"]).min().subtract(273.15),
            ea=calcs._sat_vapor_pressure(
                input_collection.select(["dewpoint_temperature_2m"])
                .mean()
                .subtract(273.15)
            ),
            rs=input_collection.select(["surface_solar_radiation_downwards"])
            .sum()
            .divide(1000000),
            uz=wind_img,
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(start_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def era5_land(
        cls,
        input_collection,
        zw=None,
        elev=None,
        lat=None,
        method="asce",
        rso_type=None,
    ):
        """Initialize daily RefET from an hourly ERA5-Land image collection

        Parameters
        ----------
        input_collection : ee.ImageCollection
            Collection of ERA5-Land hourly images for a single day from the
            collection ECMWF/ERA5_LAND/HOURLY.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The OpenET ERA5-Land elevation image
            (projects/openet/assets/meteorology/era5land/ancillary/elevation)
            will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The OpenET ERA5-Land latitude image
            (projects/openet/assets/meteorology/era5land/ancillary/latitude)
            will be used if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Temperatures are converted from K to C.
        Solar radiation is summed and converted from J m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from dew point temperature.

        """
        input_collection = ee.ImageCollection(input_collection)
        start_date = ee.Date(
            ee.Image(input_collection.first()).get("system:time_start")
        )

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            elev = ee.Image(
                "projects/openet/assets/meteorology/era5land/ancillary/elevation"
            )
        if lat is None:
            lat = ee.Image(
                "projects/openet/assets/meteorology/era5land/ancillary/latitude"
            )  # lat = ee.Image('projects/openet/assets/meteorology/era5land/ancillary/elevation')\
            #     .multiply(0).add(ee.Image.pixelLonLat().select('latitude'))\
            #     .rename(['latitude'])

        def wind_magnitude(input_img):
            """Compute hourly wind magnitude from vectors"""
            return (
                ee.Image(input_img.select(["u_component_of_wind_10m"]))
                .pow(2)
                .add(ee.Image(input_img.select(["v_component_of_wind_10m"])).pow(2))
                .sqrt()
                .rename(["wind_10m"])
            )

        wind_img = ee.Image(
            ee.ImageCollection(input_collection.map(wind_magnitude)).mean()
        )

        return cls(
            tmax=input_collection.select(["temperature_2m"]).max().subtract(273.15),
            tmin=input_collection.select(["temperature_2m"]).min().subtract(273.15),
            ea=calcs._sat_vapor_pressure(
                input_collection.select(["dewpoint_temperature_2m"])
                .mean()
                .subtract(273.15)
            ),
            rs=input_collection.select(["surface_solar_radiation_downwards_hourly"])
            .sum()
            .divide(1000000),
            uz=wind_img,
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(start_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

    @classmethod
    def era5_land_daily(
        cls,
        input_collection,
        zw=None,
        elev=None,
        lat=None,
        method="asce",
        rso_type=None,
    ):
        """Initialize daily RefET from an hourly ERA5-Land image collection

        Parameters
        ----------
        input_collection : ee.ImageCollection
            Collection of ERA5-Land hourly images for a single day from the
            collection ECMWF/ERA5_LAND/HOURLY.
        zw : ee.Number, optional
            Wind speed height [m] (the default is 10).
        elev : ee.Image or ee.Number, optional
            Elevation image [m].  The OpenET ERA5-Land elevation image
            (projects/openet/assets/meteorology/era5land/ancillary/elevation)
            will be used if not set.
        lat : ee.Image or ee.Number
            Latitude image [degrees].  The OpenET ERA5-Land latitude image
            (projects/openet/assets/meteorology/era5land/ancillary/latitude)
            will be used if not set.
        method : {'asce' (default), 'refet'}, optional
            Specifies which calculation method to use.
            * 'asce' -- Calculations will follow ASCE-EWRI 2005.
            * 'refet' -- Calculations will follow RefET software.
        rso_type : {None (default), 'full' , 'simple'}, optional
            Specifies which clear sky solar radiation (Rso) model to use.
            * None -- Rso type will be determined from "method" parameter
            * 'full' -- Full clear sky solar formulation
            * 'simple' -- Simplified clear sky solar formulation

        Notes
        -----
        Temperatures are converted from K to C.
        Solar radiation is summed and converted from J m-2 to MJ m-2 day-1.
        Actual vapor pressure is computed from dew point temperature.

        """
        input_collection = ee.ImageCollection(input_collection)
        start_date = ee.Date(
            ee.Image(input_collection.first()).get("system:time_start")
        )

        if zw is None:
            zw = ee.Number(10)
        if elev is None:
            elev = ee.Image(
                "projects/openet/assets/meteorology/era5land/ancillary/elevation"
            )
        if lat is None:
            lat = ee.Image(
                "projects/openet/assets/meteorology/era5land/ancillary/latitude"
            )  # lat = ee.Image('projects/openet/assets/meteorology/era5land/ancillary/elevation')\
            #     .multiply(0).add(ee.Image.pixelLonLat().select('latitude'))\
            #     .rename(['latitude'])

        def wind_magnitude(input_img):
            """Compute hourly wind magnitude from vectors"""
            return (
                ee.Image(input_img.select(["u_component_of_wind_10m"]))
                .pow(2)
                .add(ee.Image(input_img.select(["v_component_of_wind_10m"])).pow(2))
                .sqrt()
                .rename(["wind_10m"])
            )

        wind_img = ee.Image(
            ee.ImageCollection(input_collection.map(wind_magnitude)).mean()
        )

        return cls(
            tmax=input_collection.select(["temperature_2m"]).max().subtract(273.15),
            tmin=input_collection.select(["temperature_2m"]).min().subtract(273.15),
            ea=calcs._sat_vapor_pressure(
                input_collection.select(["dewpoint_temperature_2m"])
                .mean()
                .subtract(273.15)
            ),
            rs=input_collection.select(["surface_solar_radiation_downwards_sum"])
            .sum()
            .divide(1000000),
            uz=wind_img,
            zw=zw,
            elev=elev,
            lat=lat,
            doy=ee.Number(start_date.getRelative("day", "year")).add(1).double(),
            method=method,
            rso_type=rso_type,
        )

        # add values to pandas
        return


class Calculate_ET0:
    """
    NASA Global Land Data Assimilation System Version 2 (GLDAS-2) has three components: GLDAS-2.0, GLDAS-2.1, and GLDAS-2.2. GLDAS-2.0 is forced entirely with the Princeton meteorological forcing input data and provides a temporally consistent series from 1948 through 2014. GLDAS-2.1 is forced with a combination of model and observation data from 2000 to present. GLDAS-2.2 product suites use data assimilation (DA), whereas the GLDAS-2.0 and GLDAS-2.1 products are "open-loop" (i.e., no data assimilation). The choice of forcing data, as well as DA observation source, variable, and scheme, vary for different GLDAS-2.2 products.GLDAS-2.1 is one of two components of the GLDAS Version 2 (GLDAS-2) dataset, the second being GLDAS-2.0. GLDAS-2.1 is analogous to GLDAS-1 product stream, with upgraded models forced by a combination of GDAS, disaggregated GPCP, and AGRMET radiation data sets.

    The GLDAS-2.1 simulation started on January 1, 2000 using the conditions from the GLDAS-2.0 simulation. This simulation was forced with National Oceanic and Atmospheric Administration (NOAA)/Global Data Assimilation System (GDAS) atmospheric analysis fields (Derber et al., 1991), the disaggregated Global Precipitation Climatology Project (GPCP) precipitation fields (Adler et al., 2003), and the Air Force Weather Agency's AGRicultural METeorological modeling system (AGRMET) radiation fields which became available for March 1, 2001 onwards.


    """

    def __init__(
        self,
        study_region,
        start_date,
        end_date,
        method="asce",
        rso_type=None,
        scale=10,
        debug=False,
        landsat_cs=30,
        model="NASA",  # NASA, GFS, ECMWF
    ):
        self.study_region = study_region
        self.start_date = ee.Date(start_date)
        self.end_date = ee.Date(end_date)
        self.method = method
        self.scale = scale
        self.debug = debug
        self.rso_type = rso_type
        self.landsat_cs = landsat_cs
        self.model = model

        # Initialize the GFS dataset
        if model == "NASA":
            self.collection_name = "NASA/GLDAS/V021/NOAH/G025/T3H"
        elif model == "GFS":
            self.collection_name = "NOAA/GFS0P25"
        elif model == "ECMWF":
            self.collection_name = "ECMWF/ERA5_LAND/HOURLY"
        else:
            raise ValueError("Unsupported model input, please use NASA or GFS")
        self.input_collection = (
            ee.ImageCollection(self.collection_name)
            .filterBounds(self.study_region)
            .filterDate(self.start_date, self.end_date)
        )

    def calculate_eto_daily(self, zw=None, elev=None, lat=None, add_weather_data=False):
        ## COSTANT VALUES
        if zw is None:
            zw = ee.Number(2)
        if elev is None:
            elev = ee.Image(
                "projects/openet/assets/meteorology/era5land/ancillary/elevation"
            )
        if lat is None:
            lat = ee.Image(
                "projects/openet/assets/meteorology/era5land/ancillary/latitude"
            )

        

        def etDayNasa(dayOffset):
            start = self.start_date.advance(dayOffset, "days")
            end = start.advance(1, "days")

            tmax = (
                self.input_collection.select(["Tair_f_inst"])
                .filterDate(start, end)
                .max()
                .subtract(273.15)
            )
            tmin = (
                self.input_collection.select(["Tair_f_inst"])
                .filterDate(start, end)
                .min()
                .subtract(273.15)
            )
            mean_values = (
                self.input_collection.select(
                    ["Qair_f_inst", "Swnet_tavg", "Wind_f_inst"]
                )
                .filterDate(start, end)
                .mean()
            )
            actual_vapor_pressure = calcs._actual_vapor_pressure(
                pair=calcs._air_pressure(elev, self.method),
                q=mean_values.select(["Qair_f_inst"]),
            )
            solar_radiation = mean_values.select(["Swnet_tavg"]).multiply(0.0864)
            wind_speed = mean_values.select(["Wind_f_inst"])
            rain = (
                self.input_collection.select(["Rainf_f_tavg"])
                .filterDate(start, end)
                .sum()
            )
            doy = ee.Number(start.getRelative("day", "year")).add(1).double()
            et_daily = Daily(
                tmax=tmax,
                tmin=tmin,
                ea=actual_vapor_pressure,
                rs=solar_radiation,
                uz=wind_speed,
                zw=zw,
                elev=elev,
                lat=lat,
                doy=doy,
                method=self.method,
                rso_type=self.rso_type,
            )

            et_daily_image = et_daily.eto
            # add etr
            et_daily_image = et_daily_image.addBands(et_daily.etr)
            if add_weather_data:
                # add tmax
                et_daily_image = et_daily_image.addBands(tmax.rename("tmax"))
                # add tmin
                et_daily_image = et_daily_image.addBands(tmin.rename("tmin"))
                # add ea
                et_daily_image = et_daily_image.addBands(
                    actual_vapor_pressure.rename("actual_vapor_pressure")
                )
                # add rs
                et_daily_image = et_daily_image.addBands(
                    solar_radiation.rename("solar_radiation")
                )
                # add uz
                et_daily_image = et_daily_image.addBands(
                    wind_speed.rename("wind_speed")
                )
                # precipitation
                et_daily_image = et_daily_image.addBands(rain.rename("rain"))

            # add date
            et_daily_image = et_daily_image.set("system:time_start", start.millis())

            return et_daily_image

        def etDayGFS(dayOffset):
            start = self.start_date.advance(dayOffset, "days")
            end = start.advance(1, "days")

            tmax = (
                self.input_collection.select(["temperature_2m_above_ground"])
                .filterDate(start, end)
                .max()
                .subtract(273.15)
            )
            tmin = (
                self.input_collection.select(["temperature_2m_above_ground"])
                .filterDate(start, end)
                .min()
                .subtract(273.15)
            )
            mean_values = (
                self.input_collection.select(
                    [
                        "specific_humidity_2m_above_ground",
                        "v_component_of_wind_10m_above_ground",
                        "u_component_of_wind_10m_above_ground",
                        "downward_shortwave_radiation_flux",
                    ]
                )
                .filterDate(start, end)
                .mean()
            )
            actual_vapor_pressure = calcs._actual_vapor_pressure(
                pair=calcs._air_pressure(elev, self.method),
                q=mean_values.select(["specific_humidity_2m_above_ground"]),
            )
            solar_radiation = mean_values.select(
                [
                    "downward_shortwave_radiation_flux",
                    "v_component_of_wind_10m_above_ground",
                ]
            ).multiply(0.0864)
            wind_speed = (
                mean_values.select(
                    [
                        "u_component_of_wind_10m_above_ground",
                        "v_component_of_wind_10m_above_ground",
                    ]
                )
                .map(lambda img: wind_magnitude(img))
                .mean()
            )
            # TODO: I am not sure if this is the correct way to calculate rain
            # check https://developers.google.com/earth-engine/datasets/catalog/NOAA_GFS0P25#bands
            #
            # total_precipitation_surface is the Cumulative precipitation at surface for the previous 1-6 hours, depending on the value of the "forecast_hours" property according to the formula ((F - 1) % 6) + 1.
            # As a consequence, to calculate the total precipitation by hour X, double-counting should be avoid by only summing the values for forecast_hours that are multiples of 6 plus any remainder to reach X. It also means that to determine the precipitation for just hour X, one must subtract the value for the preceding hour unless X is the first hour in a 6-hour window.
            rain = (
                self.input_collection.select(["total_precipitation_surface"])
                .filterDate(start, end)
                .sum()
            )
            doy = ee.Number(start.getRelative("day", "year")).add(1).double()
            et_daily = Daily(
                tmax=tmax,
                tmin=tmin,
                ea=actual_vapor_pressure,
                rs=solar_radiation,
                uz=wind_speed,
                zw=zw,
                elev=elev,
                lat=lat,
                doy=doy,
                method=self.method,
                rso_type=self.rso_type,
            )

            et_daily_image = et_daily.eto
            # add etr
            et_daily_image = et_daily_image.addBands(et_daily.etr)
            if add_weather_data:
                # add tmax with the name tempmax
                et_daily_image = et_daily_image.addBands(tmax.rename("tmax"))
                # add tmin
                et_daily_image = et_daily_image.addBands(tmin.rename("tmin"))
                # add ea
                et_daily_image = et_daily_image.addBands(
                    actual_vapor_pressure.rename("actual_vapor_pressure")
                )
                # add rs
                et_daily_image = et_daily_image.addBands(
                    solar_radiation.rename("solar_radiation")
                )
                # add uz
                et_daily_image = et_daily_image.addBands(
                    wind_speed.rename("wind_speed")
                )

                # precipitation
                et_daily_image = et_daily_image.addBands(rain.rename("rain"))

            # add date
            et_daily_image = et_daily_image.set("system:time_start", start.millis())

            return et_daily_image

        def etDayECMWF(dayOffset):
            start = self.start_date.advance(dayOffset, "days")
            end = start.advance(1, "days")
            zw = ee.Number(10)

            tmax = (
                self.input_collection.select(["temperature_2m"])
                .filterDate(start, end)
                .max()
                .subtract(273.15)
            )
            tmin = (
                self.input_collection.select(["temperature_2m"])
                .filterDate(start, end)
                .min()
                .subtract(273.15)
            )
            mean_values = (
                self.input_collection.select(
                    [
                        "dewpoint_temperature_2m",
                        "surface_solar_radiation_downwards",
                        "u_component_of_wind_10m",
                        "v_component_of_wind_10m"
                    ]
                )
                .filterDate(start, end)
                .mean()
            )
            def wind_magnitude(input_img):
                """Compute hourly wind magnitude from vectors"""
                return (
                    ee.Image(input_img.select(["u_component_of_wind_10m"]))
                    .pow(2)
                    .add(
                        ee.Image(
                            input_img.select(["v_component_of_wind_10m"])
                        ).pow(2)
                    )
                    .sqrt()
                    .rename(["uz"])
                )
            actual_vapor_pressure = calcs._sat_vapor_pressure(
                mean_values.select(["dewpoint_temperature_2m"]).subtract(273.15)
            )
            solar_radiation = mean_values.select(
                ["surface_solar_radiation_downwards"]
            ).divide(1000000)
            
            wind_speed = wind_magnitude(mean_values)
            # wind_speed = ee.ImageCollection(self.input_collection.map(wind_magnitude)).mean()

            rain = (
                self.input_collection.select(["total_precipitation_hourly"])
                .filterDate(start, end)
                .sum()
            )

            doy = ee.Number(start.getRelative("day", "year")).add(1).double()
            et_daily = Daily(
                tmax=tmax,
                tmin=tmin,
                ea=actual_vapor_pressure,
                rs=solar_radiation,
                uz=wind_speed,
                zw=zw,
                elev=elev,
                lat=lat,
                doy=doy,
                method=self.method,
                rso_type=self.rso_type,
            )

            et_daily_image = et_daily.eto
            # add etr
            et_daily_image = et_daily_image.addBands(et_daily.etr)
            if add_weather_data:
                # add tmax with the name tempmax
                et_daily_image = et_daily_image.addBands(tmax.rename("tmax"))
                # add tmin
                et_daily_image = et_daily_image.addBands(tmin.rename("tmin"))
                # add ea
                et_daily_image = et_daily_image.addBands(
                    actual_vapor_pressure.rename("actual_vapor_pressure")
                )
                # add rs
                et_daily_image = et_daily_image.addBands(
                    solar_radiation.rename("solar_radiation")
                )
                # add uz
                et_daily_image = et_daily_image.addBands(
                    wind_speed.rename("wind_speed")
                )

                # precipitation
                et_daily_image = et_daily_image.addBands(rain.rename("rain"))

            # add date
            et_daily_image = et_daily_image.set("system:time_start", start.millis())

            return et_daily_image

        numberOfDays = self.end_date.difference(self.start_date, "days")

        if self.model == "NASA":
            daily = ee.ImageCollection(
                ee.List.sequence(0, numberOfDays.subtract(1)).map(etDayNasa)
            )
        elif self.model == "GFS":
            daily = ee.ImageCollection(
                ee.List.sequence(0, numberOfDays.subtract(1)).map(etDayGFS)
            )
        elif self.model == "ECMWF":
            daily = ee.ImageCollection(
                ee.List.sequence(0, numberOfDays.subtract(1)).map(etDayECMWF)
            )
        else:
            raise ValueError("Unsupported model input, please use NASA or GFS")

        return daily
