import PIL


def autorot(im):
    # some cameras return JPEG in MPO container format. Just use the first image.
    if im.format not in ('JPEG', 'MPO'):
        return im
    ExifRotationTag = 274
    exifdict = im.getexif()
    if exifdict is not None and ExifRotationTag in list(exifdict.keys()):
        orientation = exifdict[ExifRotationTag]
        # The PIL.Image values must be dynamic in some way so disable pylint no-member
        if orientation == 2:
            im = im.transpose(PIL.Image.FLIP_LEFT_RIGHT) # pylint: disable=no-member
        elif orientation == 3:
            im = im.transpose(PIL.Image.ROTATE_180) # pylint: disable=no-member
        elif orientation == 4:
            im = im.transpose(PIL.Image.FLIP_TOP_BOTTOM) # pylint: disable=no-member
        elif orientation == 5:
            im = im.transpose(PIL.Image.FLIP_TOP_BOTTOM) # pylint: disable=no-member
            im = im.transpose(PIL.Image.ROTATE_90) # pylint: disable=no-member
        elif orientation == 6:
            im = im.transpose(PIL.Image.ROTATE_270) # pylint: disable=no-member
        elif orientation == 7:
            im = im.transpose(PIL.Image.FLIP_LEFT_RIGHT) # pylint: disable=no-member
            im = im.transpose(PIL.Image.ROTATE_90) # pylint: disable=no-member
        elif orientation == 8:
            im = im.transpose(PIL.Image.ROTATE_90) # pylint: disable=no-member
    return im
