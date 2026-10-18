import PIL


_GPS_INFO_TAG = 34853
_GPS_LATITUDE_REF_TAG = 1
_GPS_LATITUDE_TAG = 2
_GPS_LONGITUDE_REF_TAG = 3
_GPS_LONGITUDE_TAG = 4
DEFAULT_GEO_LINK_URL_TEMPLATE = 'https://www.google.com/maps?q={latitude},{longitude}'


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


def getMapUrlFromExif(image, urlTemplate=DEFAULT_GEO_LINK_URL_TEMPLATE):
    """Return a configured map URL for an image with complete EXIF GPS.

    Images without location information deliberately produce no link. Six
    decimal places are about 10 cm precision, adequate for phone GPS without
    preserving needless EXIF rational-number detail.
    """
    try:
        gpsInfo = image.getexif().get_ifd(_GPS_INFO_TAG)
        latitude = _gpsDegrees(
            gpsInfo[_GPS_LATITUDE_TAG], gpsInfo[_GPS_LATITUDE_REF_TAG], 'N', 'S')
        longitude = _gpsDegrees(
            gpsInfo[_GPS_LONGITUDE_TAG], gpsInfo[_GPS_LONGITUDE_REF_TAG], 'E', 'W')
        return urlTemplate.format(
            latitude=round(latitude, 6), longitude=round(longitude, 6))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def _gpsDegrees(dms, reference, positiveReference, negativeReference):
    """Convert an EXIF degrees/minutes/seconds coordinate to decimal degrees."""
    if isinstance(reference, bytes):
        reference = reference.decode('ascii')
    if reference not in (positiveReference, negativeReference):
        raise ValueError(f'Unknown GPS coordinate reference {reference!r}')
    degrees, minutes, seconds = (float(component) for component in dms)
    decimalDegrees = degrees + minutes / 60 + seconds / 3600
    return decimalDegrees if reference == positiveReference else -decimalDegrees
