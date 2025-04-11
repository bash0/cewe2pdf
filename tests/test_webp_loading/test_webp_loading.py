import sys
import os

def test_webp_loading():
    #if this fails, then there is a problem with the pillow install.
    #know problem in 2019 for pillow from Anaconda conda 4.7.12
    #see readme
    from PIL import Image
    filename = "tests/test_webp_loading/test.webp"
    with Image.open(filename) as img:
        width, height = img.size
    #check if image has correct dimensions
    assert width == 47
    assert height == 23

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_webp_loading()