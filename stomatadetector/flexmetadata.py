import xmltodict
import tifffile as tf

flex_file = '/Users/macleand/Desktop/stomata_detector/Test images and output/Ok/002002002/002002002.flex'

def parse_flex_metadata(flex_filepath):
    '''returns list of xmltodict objects of xml portion of a flex file.
    Appends None if no xml found for a given image in the flex'''
    with tf.TiffFile(flex_filepath) as flex:
        xmls = []
        for image in flex:
            try:
                xmls.append(xmltodict.parse(image.tags.get('flex_xml').value ))
            except:
                xmls.append(None)
        return xmls

