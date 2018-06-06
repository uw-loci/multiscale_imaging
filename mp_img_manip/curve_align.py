# -*- coding: utf-8 -*-
"""
Created on Wed Jun  6 10:19:59 2018

@author: mpinkert
"""

import mp_img_manip.bulk_img_processing as blk
import mp_img_manip.tiling as til
import mp_img_manip.utility_functions as util

import SimpleITK as sitk
import pandas as pd
import os
import numpy as np
import scipy.io as sio
from pathlib import Path
import datetime


def create_rois_from_tile(tile, roi_size):

    date = str(datetime.date.today())
    t = datetime.datetime.now()
    time = str(t.hour) + ':' + str(t.minute) + ':' + str(t.second)
    roi_shape = 1

    tile_dim = np.shape(tile)

    num_rois, roi_offset = til.calculate_number_of_tiles(tile_dim, roi_size, roi_size)

    separate_rois = {}

    for start, end, roi_number in til.generate_tile_start_end_index(num_rois, roi_size,
                                                                    roi_offset):

        roi_def = [start[0], start[1], roi_size[0], roi_size[1]]
        enclosing_rect = [start[0], start[1], end[0], end[1]]
        ym = start[1] + roi_size[1]/2
        xm = start[0] + roi_size[0]/2
        boundary = np.array((1,), dtype=np.object)
        boundary_object = np.array([[start[0], start[1]],
                    [start[0], end[1]],
                    [start[1], end[1]],
                    [start[1], end[0]],
                    [start[0], end[0]]], dtype=np.object)
        boundary[0] = boundary_object
    
        roi = {
            'date': date,
            'time': time,
            'shape': roi_shape,
            'roi': roi_def,
            'enclosing_rect': enclosing_rect,
            'ym': ym,
            'xm': xm,
            'boundary': boundary
        }

        roi_name = 'ROI' + str(roi_number[0]) + 'x' + str(roi_number[1]) + 'y'

        separate_rois[roi_name] = roi

    return separate_rois


def save_rois(image_path, output_dir, output_suffix, tile_number, separate_rois):

    roi_suffix = output_suffix + '_' + str(tile_number[0]) + 'x-' +str(tile_number[1]) + 'y' \
                  + _'ROIs'

    roi_dir = Path(output_dir, 'ROI_management')
    os.makedirs(roi_dir, exist_ok=True)

    rois_path = blk.create_new_image_path(image_path, roi_dir, roi_suffix)

    sio.savemat(rois_path, separate_rois)

    return


def process_image_to_rois(image_path, output_dir, output_suffix='Tile',
                          tile_size=520, tile_separation=512,
                          roi_size=64,
                          intensity_threshold=1, number_threshold=10,
                          skip_existing_images=True):

    image = sitk.ReadImage(image_path)
    image_array = sitk.GetArrayFromImage(image)
    max_value = np.max(image_array)

    for tile, tile_number in til.generate_tile(image, tile_size, tile_separation=tile_separation):

        if til.tile_passes_threshold(tile, intensity_threshold, number_threshold, max_value):

            separate_rois = {'separate_rois': create_rois_from_tile(tile, roi_size)}
            save_rois(image_path, output_dir, output_suffix,
                      tile_number, separate_rois)
            til.write_tile(tile, image_path, output_dir, output_suffix,
                           tile_number[0], tile_number[1],
                           skip_existing_images=skip_existing_images)


def process_folder_to_jobs(image_path, tile_dir, output_dir,
                           batch_size,
                           skip_existing_images=True):
    return


def create_batches_for_chtc(input_dir, output_dir,
                            tile_size=520, tile_separation=512,
                            roi_size=64,
                            intensity_threshold=1,
                            number_threshold=10,
                            batch_size=10,
                            skip_existing_images=True):

    image_path_list = util.list_filetype_in_subdirs(input_dir, '.tif')

    # want to split on sample name...

    for path in image_path_list:

        tile_dir = Path(output_dir, blk.get_core_file_name(path))
        os.makedirs(tile_dir, exist_ok=True)

        process_image_to_rois(path, tile_dir,
                              tile_size, tile_separation,
                              roi_size,
                              intensity_threshold, number_threshold,
                              skip_existing_images)

        process_folder_to_jobs(path, tile_dir, output_dir,
                               batch_size,
                               skip_existing_images)

    return