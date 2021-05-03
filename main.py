# Press the green button in the gutter to run the script.
import sys

from loguru import logger

from src.cam_geo_referencer import ActionCamGeoReferencer

if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    converter = ActionCamGeoReferencer('/home/adrigrillo/Videos/Coche/2021_0503_123013_011.MP4',
                                       '/home/adrigrillo/Videos/Coche/2021-05-03_11-48_Mon.gpx')
    converter.geo_reference(
        sync_error=-16,
        discard_start_frames=0,
        discard_gpx_points=0
    )
    # converter.extract_n_frames(100, 0)
