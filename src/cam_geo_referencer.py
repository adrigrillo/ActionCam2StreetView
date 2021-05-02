# This is a sample Python script.
import datetime
import os
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
from loguru import logger
from mapillary_tools.exif_write import ExifEdit
from mapillary_tools.gps_parser import get_lat_lon_time_from_gpx
from tqdm import tqdm

NEW_FRAME_EXTRACTED_STR = 'New frame extracted: {}.'

VIDEO_TIME_FORMAT = '%Y_%m%d_%H%M%S_%f'


class ActionCamGeoReferencer:

    def __init__(self, video_path: str, gpx_path: str, time_lapse: int = 1, output_path: str = None):
        self.video_path = Path(video_path)
        if not self.video_path.is_file():
            raise FileNotFoundError(f'The video could not be found. Search path: {video_path}.')

        self.gpx_path = Path(gpx_path)
        if not self.gpx_path.is_file():
            raise FileNotFoundError(f'The gpx file could not be found. Search path: {gpx_path}.')
        self.gpx_data = self.parse_gpx()

        self.time_lapse = time_lapse

        if not output_path:
            self.output_path = Path(self.video_path.parent, f'output_{self.video_path.stem}')
        else:
            self.output_path = Path(output_path, f'output-{self.video_path.stem}')

        logger.info('The results of the processing will be located in: {}', self.output_path)
        if not self.output_path.exists():
            os.makedirs(self.output_path)

    @staticmethod
    def save_image(path: str, image: np.ndarray, jpg_quality: int = 100) -> None:
        """ Saves the image allowing to adjust the quality of the saving.

        :param path: path where the image will be saved.
        :param image: image data.
        :param jpg_quality: int between 0 and 100 where higher means better. Default is 95.
        """
        logger.trace('Saving image in `{}`', path)
        if 0 <= jpg_quality <= 100:
            cv2.imwrite(path, image, [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])
        else:
            cv2.imwrite(path, image)

    def parse_gpx(self) -> List[Tuple[datetime.datetime, float, float, float]]:
        return get_lat_lon_time_from_gpx(self.gpx_path)

    def get_matching_gpx_point(self, timestamp: datetime.datetime) -> Optional[Tuple[datetime.datetime,
                                                                                     float, float, float]]:
        index, best_index = 0, None
        time_diff = datetime.timedelta(seconds=1)
        diff_reduced = True
        while diff_reduced and index < len(self.gpx_data):
            gpx_timestamp = self.gpx_data[index][0]

            # Always the later time minus the earlier one
            check_next = False
            if timestamp <= gpx_timestamp:
                diff = gpx_timestamp - timestamp
            else:
                diff = timestamp - gpx_timestamp
                check_next = True

            logger.trace('Difference between timestamps: {}.{} seconds.', diff.seconds, diff.microseconds)

            if time_diff >= diff:
                logger.debug('Reduced time difference between frame and gpx. New time: {} seconds.', diff.seconds)
                time_diff = diff
                diff_reduced = True
                best_index = index
            elif not check_next:
                logger.trace('Time difference not reduced. Exiting from while.')
                diff_reduced = False

            index += 1

        if best_index is not None:
            # Remove elements before the taken point
            for i in range(best_index):
                self.gpx_data.pop(i)

            logger.debug('Suitable GPX point found.')
            return self.gpx_data.pop(best_index)
        else:
            logger.debug('No suitable GPX point found.')
            return None

    def geo_reference(self, sync_error: float = 0, discard_start_frames: int = 0, discard_gpx_points: int = 0) -> None:
        """ Read the video from the action cam frame by frame adding the GPS information.

        The GPS data is retrieved by matching the point from the GPX file with the lowest
        time difference with respect the frame timestamp.

        The frame timestamp is inferred using the initial timestamp of the video and the
        frame number multiplied by the specified time between frames in the constructor.

        Additionally, the timestamp can be synced with the GPX timestamp indicating the
        seconds that the video should be moved backwards in time, negative number as
        `sync_error`, or it should be moved forward, positive number as `sync_error`.

        Furthermore, a given number of video frames or GPX points can be discarded by
        indicating the desired value in `discard_start_frames` and `discard_gpx_points`
        respectively.

        :param sync_error: modifies video timestamp in seconds by the number specified.
         It could be a negative number.
        :param discard_start_frames: number of frames to discard from the video.
        :param discard_gpx_points: number of GPX points to discard from the file.
        """
        # Get the start time from the video file name
        video_creation_time = datetime.datetime.strptime(self.video_path.stem, VIDEO_TIME_FORMAT)
        if sync_error != 0:
            video_creation_time += datetime.timedelta(seconds=sync_error)

        # Remove the gpx points desired
        if discard_gpx_points > 0:
            self.gpx_data = self.gpx_data[discard_gpx_points:]

        # Go through the video using matching timestamp for frame and gpx
        frame_num = 0
        cap = cv2.VideoCapture(str(self.video_path))
        if discard_start_frames > 0:
            frame_num = discard_start_frames - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

        pbar = tqdm(total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) + 1), unit='frames')
        success, image = cap.read()
        while success:
            # 1. Calculate frame timestamp
            frame_timestamp = video_creation_time + datetime.timedelta(seconds=self.time_lapse * frame_num)

            # 2. Match with gpx and add data
            gpx_point = self.get_matching_gpx_point(frame_timestamp)
            if not gpx_point:
                success, image = cap.read()
                logger.debug(NEW_FRAME_EXTRACTED_STR, success)
                frame_num += 1
                continue

            # 3. Save image and add exif data
            image_path = Path(self.output_path, f'{frame_timestamp.strftime(VIDEO_TIME_FORMAT)}.jpg')
            self.save_image(str(image_path), image)

            image_exif = ExifEdit(str(image_path))
            image_exif.add_date_time_original(frame_timestamp)
            image_exif.add_lat_lon(gpx_point[1], gpx_point[2])
            image_exif.add_altitude(gpx_point[3])
            image_exif.add_orientation(1)
            image_exif.add_camera_make_model("apeman", "a80")
            image_exif.write()

            success, image = cap.read()
            logger.debug(NEW_FRAME_EXTRACTED_STR, success)
            frame_num += 1
            pbar.update(1)

        pbar.close()

    def extract_n_frames(self, num_frames: int, discard_start_frames: int = 0) -> None:
        video_creation_time = datetime.datetime.strptime(self.video_path.stem, VIDEO_TIME_FORMAT)
        # Go through the video
        frame_num = 0
        cap = cv2.VideoCapture(str(self.video_path))
        if discard_start_frames > 0:
            frame_num = discard_start_frames - 1
            num_frames += discard_start_frames - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        success, image = cap.read()
        while success and frame_num < num_frames:
            frame_timestamp = video_creation_time + datetime.timedelta(seconds=self.time_lapse * frame_num)

            # 3. Save image and add exif data
            image_path = Path(self.output_path, f'{frame_timestamp.strftime(VIDEO_TIME_FORMAT)}.jpg')
            self.save_image(str(image_path), image)

            success, image = cap.read()
            logger.debug(NEW_FRAME_EXTRACTED_STR, success)
            frame_num += 1
