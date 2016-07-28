"""
Module for dealing with Multi-TIFF metadata in Perkin ELmer .flex files.
"""


import xmltodict
import tifffile as tf

#flex_file = '/Users/macleand/Desktop/stomata_detector/Test images and output/Ok/002002002/002002002.flex'

def count_planes_in_stack(flxml_arr):
    return len(flxml_arr)

class FlexMetaData(object):

    """
    Implements an `xmltodict` object that contains .flex metadata

    :param: filename
    :return: xmltodict object - nested structure with data

    >>> flex_file = '/Users/user/test/002002002/002002002.flex'
    >>> a = parse_flex_metadata(flex_file)
    >>> metadata = a[0]
    >>> print(metadata['Root']['Arrays']['Array'][0])
    >>>
    >>> OrderedDict([('@Type', 'Image'), ('@Name', 'Exp1Cam2'), ('@Width', '688'), ('@Height', '512'), ('@BitsPerPixel', '16'), ('@CompressionType', ''), ('@CompressionRate', ''), ('@Factor', '1.000000')])

    """

    def __init__(self, flex_filepath):
        self.metadata = self._parse_flex_metadata(flex_filepath)
        self.planes_in_stack = count_planes_in_stack(self.metadata)


    def _parse_flex_metadata(self, flex_filepath):
        """returns list of xmltodict objects of xml portion of a flex file.
        Appends None if no xml found for a given image in the flex"""
        with tf.TiffFile(flex_filepath) as flex:
            xmls = []
            for image in flex:
                try:
                    xmls.append(xmltodict.parse(image.tags.get('flex_xml').value ))
                except:
                    xmls.append(None)
            return xmls



