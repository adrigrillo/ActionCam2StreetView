# Press the green button in the gutter to run the script.
import sys

from loguru import logger

from src.cam_geo_referencer import ActionCamGeoReferencer

if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stderr, level="ERROR")
    converter = ActionCamGeoReferencer('/home/adrigrillo/Videos/Coche/2021_0416_171609_003.MP4',
                                       '/home/adrigrillo/Videos/Coche/2021-04-16_17-16_Fri.gpx')
    converter.geo_reference(
        sync_error=11,
        discard_start_frames=7,
        discard_gpx_points=0
    )
    # converter.extract_n_frames(5, 7)
