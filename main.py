# Press the green button in the gutter to run the script.
import argparse
import subprocess
import sys

from loguru import logger

from src.cam_geo_referencer import ActionCamGeoReferencer

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('video',
                        type=str,
                        help='path of the video to be processed')
    parser.add_argument('gpx',
                        type=str,
                        help='path of the GPX file to be processed')
    parser.add_argument('-o', '--output-path',
                        type=str, default=None,
                        help='path of the GPX file to be processed')

    # Flags
    parser.add_argument('-e', '--extract',
                        action='store_true',
                        help='only extracts the video frames')
    parser.add_argument('-u', '--upload',
                        action='store_true',
                        help='upload to Mapillary and Karta View')
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='execute in debug mode')

    # Options
    parser.add_argument('-t', '--time-lapse',
                        type=int, default=1,
                        help='time between frames in the video')
    parser.add_argument('-se', '--sync-error',
                        type=int, default=0,
                        help='synchronization error between the video and gpx file in seconds')
    parser.add_argument('-f', '--num-frames',
                        type=int, default=50,
                        help='Number of frames to extract from the video file. Only when --extract is True')
    parser.add_argument('-sf', '--skip-frames',
                        type=int, default=0,
                        help='Number of frames to skip from the video file')
    parser.add_argument('-sp', '--skip-points',
                        type=int, default=0,
                        help='Number of points to skip from the GPX file')
    parser.add_argument('--user',
                        type=str, default='adrigrillo',
                        help='Mapillary upload user')
    opt = parser.parse_args()

    if not opt.debug:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    else:
        logger.debug('Executing in debug mode.')

    converter = ActionCamGeoReferencer(video_path=opt.video,
                                       gpx_path=opt.gpx,
                                       time_lapse=opt.time_lapse,
                                       output_path=opt.output_path)

    if opt.extract:
        converter.extract_n_frames(opt.num_frames, opt.skip_frames)

    else:
        converter.geo_reference(
            sync_error=opt.sync_error,
            discard_start_frames=opt.skip_frames,
            discard_gpx_points=opt.skip_points
        )

        if opt.upload:
            logger.info('Uploading processed video `{}` to Mapillary with user {}.', converter.output_path, opt.user)
            res = subprocess.run(f'mapillary_tools process_and_upload '
                                 f'--import_path {converter.output_path} '
                                 f'--user_name {opt.user}',
                                 shell=True)

            if res.returncode == 0:
                logger.info('Successfully uploaded to Mapillary.')
            else:
                logger.error('Error uploading data to Mapillary. Check the logs.')

            logger.info('Uploading processed video `{}` to Karta View.', converter.output_path)
            res = subprocess.run(f'python upload-scripts/osc_tools.py upload '
                                 f'-p {converter.output_path}',
                                 shell=True)

            if res.returncode == 0:
                logger.info('Successfully uploaded to Karta View.')
            else:
                logger.error('Error uploading data to Karta View. Check the logs.')
