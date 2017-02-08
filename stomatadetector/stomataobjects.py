"""Module for segmenting stomata sub-images and related measurements from a .flex file

"""

import numpy as np
from skimage import io
from skimage import exposure
import matplotlib.pyplot as plt
from skimage.morphology import reconstruction, dilation
from scipy import ndimage
from skimage import measure
import math
from .flexmetadata import *

def max_proj(img_list):
    """ maximum projection from a list of numpy ndarrays

    :param img_list: list of numpy ndarrays to merge
    :type img_list: list
    :returns: ndarray -- the maximum projection of the list
    """
    return np.maximum.reduce(img_list)

def rescale(img):
    """sets input image to type 'uint16'

    :param img: image
     :type img: numpy.ndarray
    :returns: numpy.ndarray -- with type 'uint16'
    """
    return exposure.rescale_intensity(img, in_range='uint16')



def maximum_project_flex(flex_file):
    """ maximum projection and rescaling of a flex_file for skimage.

    :param flex_file: the flex file to maximum project and rescale
    :return: numpy.ndarray maximum projection of all planes in the Flex file into one plane in 'uint16' type.
    """
    flex =  io.imread(flex_file, conserve_memory=True, dtype=None)
    flex = max_proj(flex)
    return rescale(flex)

def imshow(image, title="No Title",cmap='hot', width=36,height=36, **kwargs):
    """render image as a graphic

    :param image: image to show
    :type image: numpy.ndarray

    """
    fig, ax = plt.subplots(figsize=(width,height))
    ax.imshow(image, cmap=cmap, **kwargs)
    ax.axis('off')
    ax.set_title(title)
    plt.show()

def imhist(flex,  bins=20, width=36,height=36, **kwargs):
    plt.hist(flex.mp.ravel(), bins=bins, **kwargs)
    plt.show()

def is_dark_image(img,min_bright=100, prop=0.1):
    """work out if too few pixels pass a brightness threshold
    Default is < 10% of pixels with brightness of 100

    :param img:
    :type img: numpy.ndarray
    :param min_bright: the threshold value for bright pixels
    :type min_bright: int
    :param prop: the proportion of image pixels that must pass the threshold
    :type prop: float

    :return bool:
    """
    count = (img <= min_bright).sum()
    target = img.shape[0] * img.shape[1] * prop
    if count >= target:
        return False
    else:
        return True


def object_filter(leaf_image_obj, filter):
    for prop, value in filter:
        if prop == 'delete_border_objects' and value:
            delete_border_objects(leaf_image_obj)
        elif prop == 'roundness':
            delete_not_round_objects(leaf_image_obj, value)
        elif prop == 'width_length':
            delete_long_objects(leaf_image_obj, value)
        elif prop == 'size_range':
            delete_by_size(leaf_image_obj, value)

def custom_filter(leaf_image_obj):
    """implements the Robatzek lab object filtering system"""
    delete_border_objects(leaf_image_obj)
    delete_not_round_objects(leaf_image_obj)
    delete_long_objects(leaf_image_obj)

def edge_objects(l, margin=3):
    """finds objects overlapping  margin pixels at edge of image

    :param l: label image
    :param margin: thickness of border to search
    :type l: numpy.ndarray
    :type margin: int

    :return: list

    """
    ls = [l[:, 0:margin].flatten(), l[:, -margin:].flatten(), l[0:margin, :].flatten(), l[-margin:, :].flatten()]
    return list(set([item for sublist in ls for item in sublist]))

def long_objects(leaf_image_obj, ratio=3):
    """returns list of objects with self.width_length_ration >= ratio"""
    return [x.label for x in leaf_image_obj.stomata_objects if x.width_length_ratio() >= ratio ]


def not_round_objects(leaf_image_obj, roundness=0.65):
    """"""
    return [x.label for x in leaf_image_obj.stomata_objects if x.roundness() < roundness]

def delete_not_round_objects(leaf_image_obj, roundness=0.65):
    not_round_obj = not_round_objects(leaf_image_obj, roundness)
    delete_objects(leaf_image_obj, not_round_obj)

def delete_long_objects(leaf_image_obj, ratio=3):
    """Given a LeafImage object, uses long_objects()  attribute to long objects. uses delete_objects() to delete """
    long_obj = long_objects(leaf_image_obj, ratio)
    delete_objects(leaf_image_obj,long_obj)

def delete_objects(leaf_image_obj, delete_list):
    """Given a LeafImageObject and a list of labels, deletes the objects in the labels list from the object list and removes the object from the binary and label image"""
    leaf_image_obj.stomata_objects = [s for s in leaf_image_obj.stomata_objects if not s.label in delete_list]

    for o in delete_list:
        leaf_image_obj.stomata_labels[leaf_image_obj.stomata_labels == o] = 0

    tmp = np.copy(leaf_image_obj.stomata_labels)
    tmp[tmp > 0] = 1
    leaf_image_obj.binary_obj_img = tmp

def delete_border_objects(leaf_image_obj,margin=3):
    """Given a LeafImage object, uses border_objects()  attribute to find border objects. uses delete_objects() to delete

    :param leaf_image_obj: a LeafImage object
    :param margin: the number of pixels at the edge to consider the border
    :type margin: int

    """
    border_obj = edge_objects(leaf_image_obj.stomata_labels,margin)
    delete_objects(leaf_image_obj, border_obj)


def get_stomata(max_proj_image, min_obj_size=200, max_obj_size=1000):
    """Performs image segmentation from a max_proj_image.
     Disposes of objects in range min_obj_size to
    max_obj_size

    :param max_proj_image: the maximum projection image
    :type max_proj_image: numpy.ndarray, uint16
    :param min_obj_size: minimum size of object to keep
    :type min_obj_size: int
    :param max_obj_size: maximum size of object to keep
    :type max_obj_size: int
    :returns: list of [ [coordinates of kept objects - list of slice objects],
                        binary object image - numpy.ndarray,
                        labelled object image - numpy.ndarray
                     ]

    """

    # pore_margin = 10
    # max_obj_size = 1000
    # min_obj_size = 200
    # for prop, value in segment_options:
    #     if prop == 'pore_margin':
    #         pore_margin = value
    #     if prop == 'max_obj_size':
    #         max_obj_size = value
    #     if prop == 'min_obj_size':
    #         min_obj_size = value
    #
    # print(pore_margin)
    # print(max_obj_size)
    # print(min_obj_size)

    #rescale_min = 50
    #rescale_max= 100
    #rescaled = exposure.rescale_intensity(max_proj_image, in_range=(rescale_min,rescale_max))
    rescaled = max_proj_image
    seed = np.copy(rescaled)
    seed[1:-1, 1:-1] = rescaled.max()
    #mask = rescaled
    #if gamma != None:
    #    rescaled = exposure.adjust_gamma(max_proj_image, gamma)
    #filled = reconstruction(seed, mask, method='erosion')
    closed = dilation(rescaled)
    seed = np.copy(closed)
    seed[1:-1, 1:-1] = closed.max()
    mask = closed


    filled = reconstruction(seed, mask, method='erosion')
    label_objects, nb_labels = ndimage.label(filled)
    sizes = np.bincount(label_objects.ravel())
    mask_sizes = sizes
    mask_sizes = (sizes > min_obj_size) & (sizes < max_obj_size)
    #mask_sizes = (sizes > 200) & (sizes < 1000)
    mask_sizes[0] = 0
    big_objs = mask_sizes[label_objects]
    stomata, _ = ndimage.label(big_objs)
    obj_slices = ndimage.find_objects(stomata)
    return [obj_slices, big_objs, stomata]

def get_pore(img, percentile=75,edge_object_margin=1):
    """Extracts largest, non-border, darkest region from subimage - in context presumed to be the pore. Works out the
    values are 0.

    :param img: input image (section of full intensity leaf image with just stomate in it)
    :type img: numpy.ndarray
    :param percentile: the percentile of the intensity histogram below which values will be taken to be dark.
    :type percentile: int
    :param edge_object_margin: the width of border in which objects must lie to be removed as border objects, default = 1
    :return: binary numpy.ndaarray
    """
    dark_level = np.percentile(img, percentile )
    #imshow(img)
    cp = np.copy(img)
    cp[img > dark_level] = 0
    cp[img <= dark_level] = 1
    label_objects, nb_labels = ndimage.label(cp)
    removed = np.copy(label_objects)
    for o in edge_objects(label_objects, margin=edge_object_margin):
        removed[removed == o] = 0
    new_label_objects, new_nb_labels = ndimage.label(removed)
    props = measure.regionprops(new_label_objects, intensity_image=img)
    if len(props) > 0:
        area = max([i.area for i in props])
        biggest = [i for i, j in enumerate(props) if j.area == area]

        index_of_obj_to_keep = biggest[0]
        label_of_obj_to_keep = np.arange(1, new_nb_labels + 1)[index_of_obj_to_keep]
        new_label_objects[new_label_objects != label_of_obj_to_keep] = 0
        final_label_objects, final_nb_labels = ndimage.label(new_label_objects)
        return(final_label_objects)
    else: #no pore
        return(None)

def get_stomata_info(stomata):
    l = ndimage.find_objects(stomata)

def gaussian(img, sigma=1):
    return ndimage.gaussian_filter(img, sigma)

def sharpen(img, alpha=30):
    filter_blurred = ndimage.gaussian_filter(img, 1)
    return  img + alpha * (img - filter_blurred)

def median_denoise(img, sigma=1):
    return ndimage.median_filter(img, sigma)

def gamma_transform(img, gamma=0.75):
    return exposure.adjust_gamma(img, gamma)

def log_transform(img, gain=1):
    return exposure.adjust_log(img, gain)

def sigmoid_transform(img, cutoff=0.5):
    return exposure.adjust_sigmoid(img, cutoff)

def equalize_adapthist(img, val=None):
    return exposure.equalize_adapthist(img)

def rescale_intensity(img, val=None):
    return exposure.rescale_intensity(img)

def clip(img, range):
    return exposure.rescale_intensity(img, in_range=range)

def report_header():
    return ",".join(["Treatment", "PlateRow","PlateColumn","TimeStamp","XUnits", "XUnitsPerPixel", "YUnits", "YUnitsPerPixel","Stack","CameraBinningX", "CameraBinningY", "ObjectCount", "ImageStomateIndex", "StomateArea","StomateRoundness", "StomateLength", "StomateWidth", "PoreLength", "PoreWidth"])

def custom_report(flex, stomata):

    props = [str(x) for x in flex.sample_info()] + [str(flex.object_count()) ] + [str(x) for x in stomata.stoma_info() ]
    return ",".join(props)

class GetStomataObjects(object):
    """Gets list of LeafImage objects from a list of flex file names. Each file name provided returns a
    different LeafImage object. Each LeafImage object has an attribute `stomata_objects` that contains stomata information

    >>> analysed_flex_files = sd.GetStomataObjects(flex_file_names, image_options=[], segment_options = [] )

    """

    def __init__(self, flex_file_name_list, image_options=[], segment_options = [] ):


        self.flex_files = flex_file_name_list
        self.image_opts = Qopts(image_options)
        self.segment_opts = Qopts(segment_options)



        self.processed_images = self.process_images()

    def process_images(self):
        return [LeafImage(flex_file, image_options = self.image_opts, segment_options = self.segment_opts ) for flex_file in self.flex_files]

    def __iter__(self):
        return iter(self.processed_images)

    def __getitem__(self,idx):
        return self.processed_images[idx]

class LeafImage(object):
    """represents the leaf image and the objects found in it from a single flex file

    :ivar flex_file: the flex file represented
    :ivar mp: the maximum projection of the flex file
    :ivar stomata_positions: the python Slice objects describing the sub images of the maximum projection containing detected stomata
    :ivar binary_obj_img: a binary image of the objects
    :ivar stomata_labels: a numpy label image of the stomata found
    :ivar stomata_objects: list of StomataObject's - one per detected stomate
    """

    def __init__(self, flex_file, image_options=[], segment_options = [] ):

        #if len(image_options) == 0:
        #    image_options = [('clip', (50,100))]
        self.flex_file = flex_file
        self.mp = maximum_project_flex(self.flex_file)
        self.stomata_positions = []
        self.binary_obj_img = np.zeros((10,10))
        self.stomata_labels = np.zeros((10,10))
        self.stomata_objects = []
        self.metadata = None
        self.treatment = None
        self.well_coordinate = None
        self.imaging_time = None
        self.x_units = None
        self.y_units = None
        self.x_perpixel = None
        self.y_perpixel = None
        self.camerabinning_x = None
        self.camerabinning_y = None


        if flex_file.endswith('flex'):
            self.metadata = FlexMetaData(flex_file)
            self.treatment = self.metadata.metadata[0]['Root']['FLEX']['Well']['AreaName']
            self.plate_row = self.metadata.metadata[0]['Root']['FLEX']['Well']['WellCoordinate']['@Row']
            self.plate_column = self.metadata.metadata[0]['Root']['FLEX']['Well']['WellCoordinate']['@Col']
            self.imaging_time = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['DateTime']['#text']
            self.x_units = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['ImageResolutionX']['@Unit']
            self.x_perpixel = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['ImageResolutionX']['#text']
            self.y_units = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['ImageResolutionY']['@Unit']
            self.y_perpixel = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['ImageResolutionY']['#text']
            self.stack = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['Sublayout']['#text']
            self.camerabinning_x = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['CameraBinningX']['#text']
            self.camerabinning_y = self.metadata.metadata[0]['Root']['FLEX']['Well']['Images']['Image'][0]['CameraBinningY']['#text']

        for func, val in image_options:
            if func == 'gamma':
                self.mp = gamma_transform(self.mp, val)
            elif func == 'gaussian':
                self.mp = gaussian(self.mp, val)
            elif func == 'sharpen':
                self.mp = sharpen(self.mp, val)
            elif func == 'median':
                self.mp = median_denoise(self.mp,val)
            elif func == 'log':
                self.mp = log_transform(self.mp,val)
            elif func == 'adaptive':
                self.mp = equalize_adapthist(self.mp, val)
            elif func == 'rescale':
                self.mp = rescale_intensity(self.mp, val )
            elif func == 'clip':
                self.mp = clip(self.mp, val)

        self.is_dark = is_dark_image(self.mp)

        stomata_data = get_stomata(self.mp, min_obj_size=segment_options.stomate_min_obj_size, max_obj_size=segment_options.stomate_max_obj_size)
        self.stomata_positions = stomata_data[0]
        self.binary_obj_img = stomata_data[1]
        self.stomata_labels = stomata_data[2]
        stomata_props = measure.regionprops(self.stomata_labels, intensity_image=self.mp)
        self.stomata_objects = [StomataObject(self.mp[stomata_pos[0]], stomata_pos[0], stomata_pos[1], self.binary_obj_img, stomata_pos[2], segment_options ) for stomata_pos in zip(self.stomata_positions, stomata_props, range(1, self.stomata_labels.max() + 1) )]

    def object_count(self):
        return len(self.stomata_objects)

    def sample_info(self):
        return [self.treatment, self.plate_row, self.plate_column,  self.imaging_time, self.x_units, self.x_perpixel, self.y_units, self.y_perpixel, self.stack, self.camerabinning_x, self.camerabinning_y]




class StomataObject(object):
    """represents a single object, presumed to be a stomate from the segmented flex file

    :ivar detected_stomate: binary image of stomate
    :ivar intensity_image: normal image of stomate
    :ivar props: properties of stomata - calculated by skimage.measure.regionprops in original mp image
    :ivar position_in_image: Python slice object describing the position in the original image
    :ivar pore_binary_image: binary image of pore region
    :ivar pore_props: properties of pore region - calculated by skimage.measure.regionprops - only first property list is returned if multiple objects are found.

    """

    def __init__(self, max_proj_img_slice, stomata_pos, stomata_props, binary_obj_img,  label, segment_options):

        self.detected_stomate = binary_obj_img[stomata_pos].astype('uint16')
        self.intensity_image = max_proj_img_slice
        self.props = stomata_props
        self.label = label
        self.position_in_image = stomata_pos
        self.pore_binary_image = get_pore(self.intensity_image, segment_options.pore_percentile, segment_options.pore_edge_object_margin)
        if self.pore_binary_image is not None:
            self.pore_props = measure.regionprops(self.pore_binary_image)[0] #should only be one object in the list
        else:
            self.pore_props = None

    def roundness(self):
        return 4 * math.pi * (self.props.area / (self.props.perimeter ** 2))

    def width_length_ratio(self):
        return self.props.major_axis_length / self.props.minor_axis_length

    def original_width_length_ratio(self):
        """strange function for width to length found in original Ji Zhou, Opera version of this procedure.
        """
        return (self.props.area / (self.props.major_axis_length / 2) / self.props.major_axis_length)

    def ramanujan_perimeter(self):
        a = self.props.major_axis_length
        b = self.props.minor_axis_length
        h = ((a - b)**2)/((a + b)**2)
        c = 1 + ((3*h) / (10 + math.sqrt(4 + (3 * h) ) ) )
        return (math.pi * (a+b) * c)

    def stoma_info(self):
        pore_width = None
        pore_length = None
        if self.pore_props is not None:
            pore_width = self.pore_props.minor_axis_length
            pore_length = self.pore_props.major_axis_length

        return [self.label, self.props.area, self.roundness(), self.props.major_axis_length, self.props.minor_axis_length, str(pore_length), str(pore_width) ]


class Qopts(object):
    def __init__(self, itt):
        for k,v in itt:
            setattr(self,k,v)

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value

