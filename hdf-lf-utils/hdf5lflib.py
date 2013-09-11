# This is a collection of useful functions used across our Python tools
# working with HDF5 lightfield files.

import numpy
import math

def compute_maxu(imageGroup):
    """
    Determine the maximum slope for looking through a lens, commonly
    referred to as `maxu`. Takes imageGroup (the HDF5 node carrying
    required .attrs[]) as a parameter, returns a tuple of
    (maxu, maxu_explicit).
    """
    maxu_explicit = False
    if 'op_maxu' in imageGroup.attrs:
        maxu = float(imageGroup.attrs['op_maxu'])
        maxu_explicit = True
    elif 'op_flen' in imageGroup.attrs:
        imagena = float(imageGroup.attrs['op_na']) / float(imageGroup.attrs['op_mag'])
        if imagena < 1.0:
            ulenslope = 1.0 * float(imageGroup.attrs['op_pitch']) / float(imageGroup.attrs['op_flen'])
            naslope = imagena / (1.0-imagena*imagena)**0.5
            maxu = float(naslope / ulenslope)
            if verboseMode:
                print "Using image-specific maxu of " + str(maxu)
        else:
            print "!!! Ignoring inconsistent optical parameters in the HDF5 file"
    else:
        maxu = 0.4667937556007068 #calculated from only optics data available at the time, serves as default
    return (maxu, maxu_explicit)


def lenslets_offset2corner(ar, corner):
    """
    Walk from the lenslets offset point to the point of the grid
    nearest to the top left corner.
    """
    changed = True
    while changed:
        changed = False
        if corner[1] > corner[0] and corner[0] > ar._v_attrs['down_dy'] and corner[1] > ar._v_attrs['down_dx']:
            corner[0] -= ar._v_attrs['down_dy']
            corner[1] -= ar._v_attrs['down_dx']
            changed = True
        if corner[0] > ar._v_attrs['right_dy'] and corner[1] > ar._v_attrs['right_dx']:
            corner[0] -= ar._v_attrs['right_dy']
            corner[1] -= ar._v_attrs['right_dx']
            changed = True
        if corner[1] > corner[0] and corner[0] > ar._v_attrs['down_dy'] and corner[1] > ar._v_attrs['down_dx']:
            corner[0] -= ar._v_attrs['down_dy']
            corner[1] -= ar._v_attrs['down_dx']
            changed = True
    # FIXME: Note that we might get stuck at a point where we e.g. still have
    # some room to go many steps up at the cost of going one step right.

    return corner


def compute_uvframe(node, ar, cw, ofs_U = 0., ofs_V = 0.):
    """
    Generate a view of the sample from a particular (U,V) viewpoint
    from the lightsheet data (as stored in HDF5 @node). The view
    is returned as a numpy 2D array.
    """

    # We also rotate the image by 90\deg during the processing to maintain
    # compatibility with other parts of our toolchain.

    imgdata = node.read()
    # scipy.misc.imsave('rawimage.png', imgdata)

    (right_dx, right_dy) = ar._v_attrs['right_dx'], ar._v_attrs['right_dy']
    (down_dx, down_dy) = ar._v_attrs['down_dx'], ar._v_attrs['down_dy']
    corner = [ar._v_attrs['y_offset'], ar._v_attrs['x_offset']]
    if cw is not None:
        (x0, y0, x1, y1) = (cw._v_attrs[j] for j in ('x0', 'y0', 'x1', 'y1'))
        imgdata = imgdata[y0:y1 , x0:x1]
        corner = [corner[0] - x0, corner[1] - y0]

    # Before we interpret autorectification, we need to transpose the image
    imgdata = numpy.swapaxes(imgdata, 0, 1)

    corner = lenslets_offset2corner(ar, corner)
    gridsize = (int(math.floor(imgdata.shape[0] / ar._v_attrs['down_dy'])), int(math.floor(imgdata.shape[1] / ar._v_attrs['right_dx'])))

    uvframe = numpy.zeros(shape=(gridsize[0], gridsize[1]), dtype='short')

    for y in range(int(gridsize[0])):
        for x in range(int(gridsize[1])):
            cx = int(round(corner[1] + x * right_dx + y * down_dx + ofs_U))
            cy = int(round(corner[0] + x * right_dy + y * down_dy + ofs_V))
            try:
                uvframe[gridsize[0]-1 - y][x] = imgdata[cy][cx]
                #print cx, cy, gridsize[1]-1 - x, y, int(uvframe[gridsize[1]-1 - x][y])
            except IndexError:
                #print cx, cy, gridsize[1]-1 - x, y, '---'
                pass

    return uvframe
