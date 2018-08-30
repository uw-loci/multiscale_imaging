import matplotlib.pyplot as plt
import SimpleITK as sitk
import mp_img_manip.itk.process as proc
import numpy as np


class RegistrationPlot:
    def __init__(self, start_metric_value, moving_image, fixed_image, transform):
        self.metric_values = [start_metric_value]
        self.idx_resolution_switch = [1]
        self.fig, self.ax_img, self.ax_cost = plt.subplots(1, 2)

        self.ax_img.axis('off')

        self.ax_cost.set_xlabel('Iteration Number', fontsize=12)
        self.ax_cost.set_ylabel('Metric Value', fontsize=12, rotation='90')

        moving_transformed = sitk.Resample(moving_image, fixed_image, transform,
                                           sitk.sitkLinear, 0.0,
                                           moving_image.GetPixelIDValue())
        combined_array = proc.overlay_images(fixed_image, moving_transformed)

        self.img = self.ax_img.imshow(combined_array)

        self.plot = self.ax_cost.plot(self.metric_values, 'r')
        self.plot_multires = self.ax_cost.plot(self.idx_resolution_switch,
                                               [self.metric_values[index] for index in self.idx_resolution_switch],
                                               'b*')

    def update_plot(self, new_metric_value, fixed_image, moving_image, transform):
        """Event: Update and plot new registration values"""

        self.metric_values = self.metric_values.append(new_metric_value)
        self.plot.set_data(self.metric_values)

        moving_transformed = sitk.Resample(moving_image, fixed_image, transform,
                                           sitk.sitkLinear, 0.0,
                                           moving_image.GetPixelIDValue())

        # Blend the registered and fixed images
        combined_array = proc.overlay_images(fixed_image, moving_transformed)
        self.img.set_data(combined_array)

        asp = np.diff(self.ax_cost.get_xlim())[0] / np.diff(self.ax_cost.get_ylim())[0]
        self.ax_cost.set_aspect(asp)

        self.fig.draw()

    def update_idx_resolution_switch(self):
        new_idx = len(self.metric_values)
        self.idx_resolution_switch = self.idx_resolution_switch.append(new_idx)



