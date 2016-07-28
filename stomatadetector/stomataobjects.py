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
    # TODO make sure uint scale is right one


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
    ls = [l[:, 0:10].flatten(), l[:, -10:].flatten(), l[0:10, :].flatten(), l[-10:, :].flatten()]
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




def get_stomata(max_proj_image, max_obj_size=1000, min_obj_size=200):
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

def get_pore(img, margin=10):
    """Extracts darkest region from subimage - in context presumed to be the pore. Inverts the image and finds the brightest region.
    returns binary image in which pixels with value 1 are within margin percent of the image max. All other pixel
    values are 0.

    :param img: input image section
    :type img: numpy.ndarray
    :param margin:  the percent of the inverted image maximum pixel value to take as the minimum pixel value for the pore
    :type margin: int
    :return: binary numpy.ndaarray
    """

    inv = img.max() - img
    min_val = inv.max() - ((inv.max() / 100.0) * margin)
    p = np.copy(inv)
    p[p<min_val] = 0
    p = ndimage.binary_fill_holes(p).astype('uint16')
    return p


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



class GetStomataObjects(object):
    """Gets list of LeafImage objects from a list of flex file names. Each file name provided returns a
    different LeafImage object. Each LeafImage object has an attribute `stomata_objects` that contains stomata information

    >>> analysed_flex_files = sd.GetStomataObjects(flex_file_names, image_options=[])

    """

    def __init__(self, flex_file_name_list, max_obj_size = 1000, min_obj_size = 200, image_options=[]):
        self.flex_files = flex_file_name_list
        self.opts = image_options
        self.processed_images = self.process_images( max_obj_size, min_obj_size, image_options )

    def process_images(self, max_obj_size, min_obj_size, image_options):
        return [LeafImage(flex_file, max_obj_size, min_obj_size, image_options) for flex_file in self.flex_files]

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

    def __init__(self, flex_file, max_obj_size = 1000, min_obj_size = 200, image_options=[]):

        #if len(image_options) == 0:
        #    image_options = [('clip', (50,100))]
        self.flex_file = flex_file
        self.mp = maximum_project_flex(self.flex_file)
        self.stomata_positions = []
        self.binary_obj_img = np.zeros((10,10))
        self.stomata_labels = np.zeros((10,10))
        self.stomata_objects = []
        self.metadata = None

        if flex_file.endswith('flex'):
            self.metadata = FlexMetaData(flex_file)

        for func, val in image_options:
            if func == 'gamma':
                self.mp = gamma_transform(self.mp, val)
            elif func == 'gaussian':
                self.mp = gaussian(self.mp, val)
            elif func == 'sharpen':
                self.mp == sharpen(self.mp, val)
            elif func == 'median':
                self.mp == median_denoise(self.mp,val)
            elif func == 'log':
                self.mp == log_transform(self.mp,val)
            elif func == 'adaptive':
                self.mp = equalize_adapthist(self.mp, val)
            elif func == 'rescale':
                self.mp = rescale_intensity(self.mp, val )
            elif func == 'clip':
                self.mp = clip(self.mp, val)

        self.is_dark = is_dark_image(self.mp)

        #if not self.is_dark:
        stomata_data = get_stomata(self.mp, max_obj_size, min_obj_size)
        self.stomata_positions = stomata_data[0]
        self.binary_obj_img = stomata_data[1]
        self.stomata_labels = stomata_data[2]
            #self.border_objects = edge_objects(self.stomata_labels)
        stomata_props = measure.regionprops(self.stomata_labels, intensity_image=self.mp)
            #on_border = [x in self.border_objects for x in range(1, self.stomata_labels.max() + 1 )]
        self.stomata_objects = [StomataObject(self.mp[stomata_pos[0]], stomata_pos[0], stomata_pos[1], self.binary_obj_img, stomata_pos[2] ) for stomata_pos in zip(self.stomata_positions, stomata_props, range(1, self.stomata_labels.max() + 1) )]

    def object_count(self):
        return len(self.stomata_objects)



    # TODO make flex metadata exportable.

class StomataObject(object):
    """represents a single object, presumed to be a stomate from the segmented flex file

    :ivar detected_stomate: binary image of stomate
    :ivar intensity_image: normal image of stomate
    :ivar props: properties of stomata - calculated by skimage.measure.regionprops in original mp image
    :ivar position_in_image: Python slice object describing the position in the original image
    :ivar pore_binary_image: binary image of pore region
    :ivar pore_props: properties of pore region - calculated by skimage.measure.regionprops - only first property list is returned if multiple objects are found.

    """

    def __init__(self, max_proj_img_slice, stomata_pos, stomata_props, binary_obj_img,  label):
        self.detected_stomate = binary_obj_img[stomata_pos].astype('uint16')
        self.intensity_image = max_proj_img_slice
        self.props = stomata_props
        self.label = label
        self.position_in_image = stomata_pos
        self.pore_binary_image = get_pore(max_proj_img_slice)
        self.pore_props = measure.regionprops(self.pore_binary_image)[0]

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