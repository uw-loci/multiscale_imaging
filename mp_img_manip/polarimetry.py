import mp_img_manip.tiling as til
import mp_img_manip.bulk_img_processing as blk
import mp_img_manip.itk.metadata as meta
import mp_img_manip.utility_functions as util

import scipy.stats as st
import numpy as np
import SimpleITK as sitk
import os


def calculate_retardance_over_area(retardance, orientation):
    """Calculate the average retardance in an neighborhood
    
    Retardance has a directional component, so it has to be weighted by
    the slow-axis orientation.  This function performs that weighting by
    doubling the orientation angle, and then turning it into a complex
    number which holds both magnitude and angle
    
    Inputs:
    Equally sized retardance and orientation neighborhoods holding
    corresponding pixels.
    
    Both units are degrees.  
    """
    # Orientation doubled to calculate alignment.
    circular_orientation = (2*np.pi/180)*orientation
    complex_orientation = np.exp(1j*circular_orientation)
    
    retardance_weighted_by_orientation = retardance*complex_orientation
    
    num_pixels = np.size(retardance)
    
    average_retardance = np.sum(retardance_weighted_by_orientation)/num_pixels
    
    ret_mag = np.absolute(average_retardance)
    ret_base_angle = np.angle(average_retardance, deg=True)
    
    if ret_base_angle < 0:
        ret_base_angle += 360
        
    ret_angle = ret_base_angle/2

    # bug: ret_angle does not give right value.
    
    return ret_mag, ret_angle


def calculate_circular_variance(ret_tile, orient_tile, ret_threshold):

    mask = ret_tile > ret_threshold
    circular_variance = st.circvar(orient_tile[mask])

    return circular_variance


def write_orientation_to_excel(orient_img_path, output_dir, tile_number, orient_pixel):
    return


def convert_intensity_to_retardance(itk_image, 
                                    ret_ceiling=35, wavelength=549,
                                    nm_input=True, deg_output=True):
    """Convert retardance intensities that are scaled to the image input 
    (e.g., 16 bit int) into to actual retardance values.  
    
    Input: 
    itk_image -- The image being converted, as an ITK _image object
    ret_ceiling -- The retardance value corresponding to max intensity
    wavelength -- The wavelength of light used to image, for converting 
    between degrees and retardance.  Defaults to 546 for the LOCI
    PolScope wavelength
    nm_input -- The input ret_ceiling is in nm if true, degrees if false
    deg_output -- The output is in degrees if true, nm if false
        
    Output:
    A new ITK image with retardance values either in degrees (default)
    or in nm (if deg_output is set to False)
    
    """
    
    input_array = sitk.GetArrayFromImage(itk_image)
    
    # todo: implement a check for pixel type
    
    pixel_type_factor = ret_ceiling/65535
    
    if nm_input and deg_output:
        wavelength_factor = 360/wavelength
    elif nm_input is False and deg_output is False:
        wavelength_factor = wavelength/360
    else:
        wavelength_factor = 1
        
    output_array = input_array*pixel_type_factor*wavelength_factor

    output_image = sitk.GetImageFromArray(output_array)
    output_image = sitk.Cast(output_image, sitk.sitkFloat32)
    
    return output_image
    

def bulk_intensity_to_retardance(input_dir, output_dir, output_suffix,
                                 skip_existing_images=False):
    
    path_list = util.list_filetype_in_dir(input_dir, '.tif')
    
    for i in range(len(path_list)):
        output_path = blk.create_new_image_path(
                path_list[i], output_dir, output_suffix)
        if output_path.exists and skip_existing_images:
            continue
        
        int_image = meta.setup_image(path_list[i])
        ret_image = convert_intensity_to_retardance(int_image)
        
        sitk.WriteImage(ret_image, str(output_path))

        meta.write_image_parameters(output_path, 
                                    int_image.GetSpacing(),
                                    int_image.GetOrigin())
    

def downsample_retardance_image(ret_image_path, orient_image_path, 
                                scale_pixel_factor,
                                simulated_resolution_factor=None,
                                write_excel=False,
                                write_image=False,
                                return_image=False,
                                output_dir=None):

    if not simulated_resolution_factor:
        simulated_resolution_factor = scale_pixel_factor

    ret_image = sitk.ReadImage(ret_image_path)
    orient_image = sitk.ReadImage(orient_image_path)

    ret_array = sitk.GetArrayFromImage(ret_image)
    orient_array = sitk.GetArrayFromImage(orient_image)
    
    array_size = np.shape(ret_array)
    
    pixel_num, offset = til.calculate_number_of_tiles(array_size, scale_pixel_factor, simulated_resolution_factor)

    if write_image:
        down_ret_array = np.zeros(pixel_num)
        down_orient_array = np.zeros(pixel_num)
      
    for start, end, tile_number in til.generate_tile_start_end_index(
            pixel_num, scale_pixel_factor, tile_offset=offset, 
            tile_separation=simulated_resolution_factor):

            ret_neighborhood = ret_array[range(start[0], end[0]),
                                         range(start[1], end[1])]
            
            orient_neighborhood = orient_array[range(start[0], end[0]),
                                               range(start[1], end[1])]
            
            ret_pixel, orient_pixel = calculate_retardance_over_area(
                    ret_neighborhood, orient_neighborhood)

            if write_excel:
                write_orientation_to_excel(orient_image_path, output_dir, tile_number, orient_pixel)

            if write_image:
                down_ret_array[tile_number[0], tile_number[1]] = ret_pixel
                down_orient_array[tile_number[0], tile_number[1]] = orient_pixel

    if write_image:
        down_ret_image = sitk.GetImageFromArray(down_ret_array)
        down_ret_image = sitk.Cast(down_ret_image, ret_image.GetPixelID())
    
        down_orient_image = sitk.GetImageFromArray(down_orient_array)
        down_orient_image = sitk.Cast(down_orient_image, orient_image.GetPixelID())

    if return_image:
        return down_ret_image, down_orient_image


def batch_downsample_retardance(ret_dir, orient_dir, output_dir,
                                scale_factor,
                                simulated_resolution_factor = None):
    
    output_suffix = 'DownSample-' + str(scale_factor) + 'x'

    if (simulated_resolution_factor 
        and simulated_resolution_factor != scale_factor):
        
        output_suffix = (output_suffix + '_SimRes-' 
                         + str(simulated_resolution_factor) + 'x')

    (ret_image_path_list, orient_image_path_list) = blk.find_shared_images(
            ret_dir, orient_dir)
    
    for i in range(0, np.size(ret_image_path_list)):
        (down_ret_image, down_orient_image) = downsample_retardance_image(
                ret_image_path_list[i], orient_image_path_list[i],
                scale_factor, simulated_resolution_factor)
        
        down_ret_dir = os.path.join(output_dir, output_suffix, '_ret',)
        down_orient_dir = os.path.join(output_dir, output_suffix, 'SlowAxis',)
        
        down_ret_path = blk.create_new_image_path(ret_image_path_list[i],
                                                  down_ret_dir,
                                                  '__ret_' + output_suffix )
        
        down_orient_path = blk.create_new_image_path(
                orient_image_path_list[i],
                down_orient_dir,
                '_SlowAxis_' + output_suffix)
      
        sitk.Write_image(down_ret_image, down_ret_path)
        meta.write_image_parameters(down_ret_path,
                                    down_ret_image.GetSpacing(),
                                    down_ret_image.GetOrigin())
        
        sitk.Write_image(down_orient_image, down_orient_path)
        meta.write_image_parameters(down_orient_path,
                                    down_orient_image.GetSpacing(),
                                    down_orient_image.GetOrigin())
