import numpy as np
import SimpleITK as sitk
import os
import mp_img_manip.utility_functions as util
import mp_img_manip.bulk_img_processing as blk
from pathlib import Path

def get_tile_start_end_index(tile_number, tile_size,
                             tile_offset = None, tile_separation = None):
    """Calculate the starting and ending index along a single dimension"""

    #todo: implement tests

    if not tile_separation:
        tile_separation = tile_size
        
    if not tile_offset:
        tile_offset = 0
            
    start_index = (tile_number*tile_separation)+tile_offset
    end_index = start_index + tile_size
    
    return (start_index, end_index)


def calculate_number_of_tiles(size_of_image_dimension, tile_size,
                              tile_separation = None):
    """Calculate the number of tiles that fit along an image dimension,
     given a certain tile size, and step size."""
    
    border = 0
    
    if not tile_separation:
        tile_separation = tile_size
            
    if tile_size > tile_separation:
        border = (tile_size - tile_separation)

    idx_range = size_of_image_dimension-2*border

    number_of_tiles = np.fix(idx_range/tile_separation)
    remainder = np.remainder(idx_range,tile_separation)  
    offset = np.fix(remainder/2) + border

    return int(number_of_tiles), int(offset)


def tile_passes_threshold(tile, val_threshold, num_threshold):
    """Given a np array, check if it has enough entries larger than a value"""
    
    #broken
    thresholded_tile = np.ma.masked_less_equal(tile, val_threshold)
        
    num_values = np.ma.count(thresholded_tile)
        
    if num_values > num_threshold:
        return True
    else:
        return False
    
    
def query_tile_size_and_separation(diff_separation = False):
    message_tile_size = 'How many pixels should the tile width/height be? >>>'
    tile_size = util.query_int(message_tile_size)


    if diff_separation:       
        message_separation = 'What is the separation between tiles?'
        separation = util.query_int(message_separation)
    else:
        separation = tile_size

    
    return tile_size, separation


def query_tile_thresholds():
    message_intensity = 'What percentage intensity is the value threshold? >>>'
    message_number = 'What percentage of pixels above the threshold? >>>'
    
    intensity_threshold = util.query_int(message_intensity)
    number_threshold = util.query_int(message_number)
    
    return intensity_threshold, number_threshold


#def calculate_tile_start_indexes(image_dimens, tile_size, separation = None):
#    
#    num_tiles = [calculate_number_of_tiles(image_dimens[i], tile_size) for
#                 i in range(len(image_dimens))]
#    
#    start_idx_list = [get_tile_start_index(num_tiles[i], tile_size) for
#                  i in range(len(image_dimens))]
#    
#    return start_index_list


def extract_image_tiles(image_path, output_dir, output_suffix,
                        diff_separation = False,
                        tile_size = None, separation = None,
                        intensity_threshold = None,
                        number_threshold = None):
    

    basename = os.path.basename(image_path)
    print('Extracting tiles from {0}'.format(basename))
    
    if not tile_size or ((not separation) and diff_separation):
        tile_size, separation = query_tile_size_and_separation(diff_separation)
        
    if not intensity_threshold or not number_threshold:
        intensity_threshold, number_threshold = query_tile_thresholds()
    
    
    input_image = sitk.ReadImage(image_path)
    input_array = sitk.GetArrayFromImage(input_image)
    
    image_dimens = np.shape(input_array)

    num_x, offset_x = calculate_number_of_tiles(image_dimens[0], tile_size)
    num_y, offset_y = calculate_number_of_tiles(image_dimens[1], tile_size)

    tile_number = 0
    
    # still need to do csv saving and
    
    for x in range(num_x):
        for y in range(num_y):
            start_x, end_x = get_tile_start_end_index(
                    tile_number, tile_size, 
                    tile_offset = offset_x, tile_separation = separation)

            start_y, end_y = get_tile_start_end_index(
                    tile_number, tile_size, 
                    tile_offset = offset_y, tile_separation = separation)
            
            tile = input_array[start_x:end_x, start_y:end_y]
            if tile_passes_threshold(tile, 
                                     intensity_threshold, 
                                     number_threshold):
            
                tile_image = sitk.GetImageFromArray(tile)
                
                tile_suffix = output_suffix + '-' + str(tile_number)
                tile_path = blk.create_new_image_path(image_path, output_dir,
                                                      tile_suffix)
                sitk.WriteImage(tile_image, tile_path)
            
            tile_number += 1
            
            
def bulk_extract_image_tiles(input_dir, output_dir, output_suffix,
                             diff_separation = False,
                             tile_size = None, separation = None,
                             intensity_threshold = None,
                             number_threshold = None):
    
    if not tile_size:
        tile_size, separation = query_tile_size_and_separation(diff_separation)
        
    if not separation:
        separation = tile_size
        
    if not intensity_threshold or not number_threshold:
        intensity_threshold, number_threshold = query_tile_thresholds()
        
    image_path_list = util.list_filetype_in_dir(input_dir, '.tif')
    
    for path in image_path_list:
        
        stem_name = Path(path).stem
        
        output_dir_sub = os.path.join(output_dir, stem_name)
        os.makedirs(output_dir_sub, exist_ok = True)
        
        extract_image_tiles(path, output_dir_sub, output_suffix,
                            diff_separation, tile_size, separation,
                            intensity_threshold, number_threshold)
            
        