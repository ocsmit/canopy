import os
from .templates import config_template
from configparser import ConfigParser


class Config:
    '''
    Object to effectively manage the configuration of CanoPy and run
    the processing functions created.

    Attributes
    ----------
    config : str
        Path for initialized configuration file.
    phyregs_layer : str
        Layer containing polygon features for all physiographic regions.
    phyregs_area_sqkm_field : str
        Field name for computed area.
    naipqq_layer : str
        Name of the NAIP QQ feature layer.
    naipqq_phyregs_field : str
        Field name to make NAIP QQ's queryable based on physiographic
        region.
    naip_path : str
        Path to NAIP directory
    spatref_wkid : int
        WKID specifies the target spatial reference for all output files.
    snaprast_path : str
        This input/output raster is used to snap NAIP tiles to a
        consistent grid system. If this file does not already exist, the
        filename part of snaprast_path must be 'r' + the filename of an
        existing original NAIP tile so that reproject_input_tiles() can
        automatically create it based on the folder structure of the
        NAIP imagery data (naip_path).
    results_path : str
        Folder which will contain all outputs.
    analysis_year : int
        Specifies which year is being analyzed.
    phyreg_ids : list
        List of phyreg ids to process.

    Methods
    -------
    gen_cfg(config_path):
        Generates a template configuration file at the specified location.
    update_config(**parameters):
        Allows CanoPy attributes to be written directly in the generated *.cfg
        file.
    regions(phyregs):
        Adds the desired regions to self.phyreg_ids
    calculate_row_column(xy, rast_ext, rast_res):
        Calculates array row and column using x, y, extent, and
        resolution.
    assign_phyregs_to_naipqq():
        Adds the phyregs field to the NAIP QQ shapefile and
        populates it with physiographic region IDs that intersect each NAIP
        tile.
    reproject_naip_tiles():
        Function reprojects and snaps the NAIP tiles that intersect
        selected physiographic regions.
    convert_afe_to_final_tiles():
        Converts AFE outputs to final TIFF files.
    clip_final_tiles():
        Clips final TIFF files.
    mosaic_clipped_final_tiles():
        Mosaics clipped final TIFF files and clips mosaicked files
        to physiographic regions.
    convert_afe_to_canopy_tif():
        A wrapper function that converts AFE outputs to the
        final canopy TIFF file by invoking convert_afe_to_final_tiles(),
        clip_final_tiles(), and mosaic_clipped_final_tiles() in the correct
        order.
    correct_inverted_canopy_tif(inverted_phyreg_ids):
        Corrects the values of mosaikced and clipped regions that
        have been inverted.
    convert_canopy_tif_to_shp():
        Converts the canopy TIFF files to shapefile.
    generate_gtpoints(phyreg_ids, min_area_sqkm, max_area_sqkm, min_points,
                      max_points):
        Generates randomized points for ground truthing.
    update_gtpoints(self, old_points, phyreg_ids)
        Copies a previous years GT points but with the new years GT values.
    add_naip_tiles_for_gt(gtpoints):
        Adds NAIP imagery where a ground truthing point is located.
    '''

    def __init__(self, config_path):
        '''
        Parameters
        ----------
            config_path : str
                Path which points to the *.cfg path which serve as the
                configuration for CanoPy. If one does not exist it will be
                automatically generated using the template configuration.
        '''

        # Add .cfg extentsion to file path if not present
        if not os.path.splitext(config_path)[1] == '.cfg':
            config_path = '%s%s' % (config_path, '.cfg')

        # Generate template configuration file if file path does not exist.
        if os.path.exists(config_path):
            self.config = config_path
        if not os.path.exists(config_path):
            self.gen_cfg(config_path)
            self.config = config_path
        self.__reload_cfg()

    def gen_cfg(self, config_path):
        '''
        Generates a template configuration file at the specified location.

        Parameters
        ----------
            config_path : str
        '''
        # Write config file template
        with open(config_path, 'w') as f:
            f.write(config_template)
            f.close()
        print("CanoPy config generated at %s" % config_path)
        return config_path

    def __reload_cfg(self):
        '''
        Reloads the configuration parameters within the Canopy object if changes
        have been made to the *.cfg file. This allows for changes to be made to
        the overall configuration with out the object or the python environment
        having to be reinitalized.
        '''
        # Open configuration file with configparser
        conf = ConfigParser()
        conf.read(self.config)

        # Get individual attributes from configuration
        self.verbosity = int(conf.get('config', 'verbosity'))
        self.phyregs_layer = str.strip(conf.get('config', 'phyregs_layer'))
        self.phyregs_area_sqkm_field = str.strip(conf.get('config',
                                                    'phyregs_area_sqkm_field'))
        self.naipqq_layer = str.strip(conf.get('config', 'naipqq_layer'))
        self.naipqq_phyregs_field = str.strip(conf.get('config',
                                                       'naipqq_phyregs_field'))
        self.naip_path = str.strip(conf.get('config', 'naip_path'))
        self.spatref_wkid = int(conf.get('config', 'spatref_wkid'))
        self.snaprast_path = str.strip(conf.get('config', 'snaprast_path'))
        self.results_path = str.strip(conf.get('config', 'results_path'))
        self.analysis_year = int(conf.get('config', 'analysis_year'))

    def update_config(self, **parameters):
        '''
        Updates the configuration parameters directly in the Canopy *.cfg file.

        Keyword Args
        ------------

        phyregs_layer: str
            This input layer contains the polygon features for all physiographic
            regions.
                Required fields:
                NAME (Text)
                PHYSIO_ID (Long)
                AREA (Float)
        naipqq_layer: str
            This input layer contains the polygon features for all NAIP tiles.
                Required field:
                FileName (Text)
        naipqq_phyregs_field: str
            This output text field will be created in the naipqq layer by
            assign_phyregs_to_naipqq().
        naip_path: str
            The structure of this input folder is defined by USDA, the original
            source of NAIP imagery. Under this folder are multiple 5-digit
            numeric folders that contain actual imagery GeoTIFF files.
            For example,
                F:/Georgia/ga/
                    34083/
                        m_3408301_ne_17_1_20090929.tif
                        m_3408301_ne_17_1_20090930.tif
                        ...
                    34084/
                        m_3408407_ne_16_1_20090930.tif
                        m_3408407_nw_16_1_20090930.tif
                        ...
                    ...
        spatref_wkid: int
            Well-Known IDs (WKIDs) are numeric identifiers for coordinate
            systems administered by Esri. This variable specifies the target
            spatial reference for output files
        project_path: str
            This variable specifies the path to the project root folder
            The default structure of the project folder is defined as follows:
            C:/.../ (project_path)
                Data/
                    Physiographic_Districts_GA.shp (added as a layer)
                        2009 Analysis/ (analysis_path)
                            Data/
                                naip_ga_2009_1m_m4b.shp (added as a layer)
                                snaprast.tif (snaprast_path)
                            Results/ (results_path)
                                Winder_Slope/ (physiographic region name)
                                    Inputs/
                                        reprojected NAIP tiles
                                    Outputs/
                                        intermediate output tiles
                                        canopy_2009_Winder_Slope.tif
                                        gtpoints_2009_Winder_Slope.tif
                        ...
        analysis_year: int
            This variable specifies the year for analysis.
        snaprast_path: str
            This input/output raster is used to snap NAIP tiles to a consistent
            grid system. If this file does not already exist, the filename part
            of snaprast_path must be 'r' + the filename of an existing original
            NAIP tile so that reproject_input_tiles() can automatically create
            it based on the folder structure of the NAIP imagery data
            (naip_path).
        '''

        # Read the configuration file
        conf = ConfigParser(inline_comment_prefixes='#')
        conf.read(self.config)

        # List of parameters which can be edited by user.
        params = ["phyregs_layer", "naipqq_layer", "naipqq_phyregs_field",
                  "naip_path", "spatref_wkid", "project_path", "analysis_year",
                  "snaprast_path"]

        # iterate over key word parameters and if present, overwrite entry in
        # config file.
        for arg in parameters:
            for p in params:
                if arg is p:
                    # Get parameters entry from key word dictonary.
                    conf.set('config', arg, f'{parameters.get(arg)}')
        # Write file
        with open(self.config, 'w') as configfile:
            conf.write(configfile)
        # Reload the configuration within the CanoPy object.
        self.__reload_cfg()

    def regions(self, phyregs):
        '''
        Adds the desired regions to be generated.

        Parameters
        ----------
            phyregs : list
                List of physiographic region id's to be processed with CanoPy.
        '''
        # Populate phyregs_ids
        self.phyreg_ids = []
        for i in range(len(phyregs)):
            self.phyreg_ids.append(phyregs[i])