# Press the green button in the gutter to run the script.
import sys

from loguru import logger

from src.cam_geo_referencer import ActionCamGeoReferencer

if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    converter = ActionCamGeoReferencer('/home/adrigrillo/Videos/Coche/video/2021_0506_193319_013.MP4',
                                       '/home/adrigrillo/Videos/Coche/gps/2021-05-06_19-32_Thu.gpx')
    extract = False
    # extract = True
    if not extract:
        converter.geo_reference(
            sync_error=-25,
            discard_start_frames=5,
            discard_gpx_points=0
        )
    else:
        converter.extract_n_frames(50, 50)
