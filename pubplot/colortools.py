#!/usr/bin/env python3
#------------------------------------------------------------------------------#
# Imports
# Note colormaps are *callable*, will just deliver the corresponding color, easy.
# TODO: Still confused over some issues:
# * Note that by default extremes are stored at end of *lookup table*, not as
#   separate RGBA values (so look under cmap._lut, indexes cmap._i_over and
#   cmap._i_under). You can verify that your cmap is using most extreme values
#   by comparing high-resolution one to low-resolution one.
# * Seems by default that extremes are always a separate color; so far have
#   been using *hack* where we simply *resample the lookup table* to the number
#   of levels minus extremes, and magically extremes work out to the same color.
# * Unsure whether to (a) limit the _segmentdata in a segmented colormap to
#   the desired number with get_cmap() (which calls _resample), (b) create
#   a ListedColormap with fixed colors, or (d) simply create a discrete
#   normalizer that rounds to the nearest color in high-resolution lookup
#   table? Probably should prefer the latter?
# * Unsure of issue with contourf, DiscreteNorm, and colorbar that results in
#   weird offset ticks. Contour function seems to do weird stuff, still has
#   high-resolution LinearSegmentedColormap, but distinct contour levels. Maybe
#   you shouldn't pass a discrete normalizer since contour takes care of this
#   task itself.
# Pcolor stuff: see https://stackoverflow.com/q/48613920/4970632
#------------------------------------------------------------------------------#
# Here's some useful info on colorspaces
# https://en.wikipedia.org/wiki/HSL_and_HSV
# http://www.hclwizard.org/color-scheme/
# http://www.hsluv.org/comparison/ compares lch, hsluv (scaled lch), and hpluv (truncated lch)
# Info on the CIE conventions
# https://en.wikipedia.org/wiki/CIE_1931_color_space
# https://en.wikipedia.org/wiki/CIELUV
# https://en.wikipedia.org/wiki/CIELAB_color_space
# And some useful tools for creating colormaps and cycles
# https://nrlmry.navy.mil/TC.html
# http://help.mail.colostate.edu/tt_o365_imap.aspx
# http://schumacher.atmos.colostate.edu/resources/archivewx.php
# https://coolors.co/
# http://tristen.ca/hcl-picker/#/hlc/12/0.99/C6F67D/0B2026
# http://gka.github.io/palettes/#diverging|c0=darkred,deeppink,lightyellow|c1=lightyellow,lightgreen,teal|steps=13|bez0=1|bez1=1|coL0=1|coL1=1
# https://flowingdata.com/tag/color/
# http://tools.medialab.sciences-po.fr/iwanthue/index.php
# https://learntocodewith.me/posts/color-palette-tools/
#------------------------------------------------------------------------------#
import os
import re
import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as mcm
from matplotlib import rcParams
from cycler import cycler
from glob import glob
from . import colormath
from . import utils
# Define some new palettes
cycles = {
    # default matplotlib v2
    'default':      ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
    # copied from stylesheets; stylesheets just add color themese from every possible tool, not already present as a colormap
    'ggplot':       ['#E24A33', '#348ABD', '#988ED5', '#777777', '#FBC15E', '#8EBA42', '#FFB5B8'],
    'bmh':          ['#348ABD', '#A60628', '#7A68A6', '#467821', '#D55E00', '#CC79A7', '#56B4E9', '#009E73', '#F0E442', '#0072B2'],
    'solarized':    ['#268BD2', '#2AA198', '#859900', '#B58900', '#CB4B16', '#DC322F', '#D33682', '#6C71C4'],
    '538':          ['#008fd5', '#fc4f30', '#e5ae38', '#6d904f', '#8b8b8b', '#810f7c'],
    'seaborn':      ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974', '#64B5CD'],
    'pastel':       ['#92C6FF', '#97F0AA', '#FF9F9A', '#D0BBFF', '#FFFEA3', '#B0E0E6'],
    'colorblind':   ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#F0E442', '#56B4E9'],
    'deep':         ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974', '#64B5CD'], # similar to colorblind
    'muted':        ['#4878CF', '#6ACC65', '#D65F5F', '#B47CC7', '#C4AD66', '#77BEDB'], # similar to colorblind
    'bright':       ["#023EFF", "#1AC938", "#E8000B", "#8B2BE2", "#FFC400", "#00D7FF"], # similar to colorblind
    'colorblind10': ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC", "#CA9161", "#FBAFE4", "#949494", "#ECE133", "#56B4E9"], # versions with more colors
    'deep10':       ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"],
    'muted10':      ["#4878D0", "#EE854A", "#6ACC64", "#D65F5F", "#956CB4", "#8C613C", "#DC7EC0", "#797979", "#D5BB67", "#82C6E2"],
    'bright10':     ["#023EFF", "#FF7C00", "#1AC938", "#E8000B", "#8B2BE2", "#9F4800", "#F14CC1", "#A3A3A3", "#FFC400", "#00D7FF"],
    # created with online tools
    'cinematic1':   [(51,92,103), (255,243,176), (224,159,62), (158,42,43), (84,11,14)],
    'cinematic2':   [(1,116,152), (231,80,0), (123,65,75), (197,207,255), (241,255,47)],
    }
seaborn_cycles = ['colorblind', 'deep', 'muted', 'bright']
# Note the default listed colormaps
cmap_cycles = ['Pastel1', 'Pastel2', 'Paired',
    'Accent', 'Dark2', 'Set1', 'Set2', 'Set3',
    'tab10', 'tab20', 'tab20b', 'tab20c']
# Finally some names
cspace_names = {
    'hsv': ['hsv'],
    'hpl': ['hpl','hpluv'],
    'hsl': ['hsl','hsluv'],
    'hcl': ['hcl','lch']
    }

#------------------------------------------------------------------------------#
# More generalized utility for retrieving colors
#------------------------------------------------------------------------------#
def to_rgb(color, input='rgb'):
    """
    Generalization of mcolors.to_rgb to translate color tuple
    from any colorspace to rgb.
    Convert color of arbitrary space to RGB.
    """
    if input in cspace_names['hsv']:
        color = colormath.hsl_to_rgb(*color)
    elif input in cspace_names['hpl']:
        color = colormath.hpluv_to_rgb(*color)
    elif input in cspace_names['hsl']:
        color = colormath.hsluv_to_rgb(*color)
    elif input in cspace_names['hcl']:
        color = colormath.hcl_to_rgb(*color)
    elif type(color) is str:
        color = mcolors.to_rgb(color) # ensure is valid color
    elif utils.isiterable(color):
        if any(_>1 for _ in color):
            color = [_/255 for _ in color] # scale to within 0-1
        color = mcolors.to_rgb(color) # trim the alpha channel
    else:
        raise ValueError('Invalid RGB value.')
    return color

def to_xyz(color, input):
    """
    Inverse of above, translate to some colorspace.
    """
    if input in cspace_names['hsv']:
        color = colormath.rgb_to_hsl(*color)
    elif input in cspace_names['hpl']:
        color = colormath.rgb_to_hpluv(*color)
    elif input in cspace_names['hsl']:
        color = colormath.rgb_to_hsluv(*color)
    elif input in cspace_names['hcl']:
        color = colormath.rgb_to_hcl(*color)
    else:
        raise ValueError(f'Invalid colorspace {input}.')
    return color

#------------------------------------------------------------------------------#
# Register new colormaps; must come before registering the color cycles
# * If leave 'name' empty in register_cmap, name will be taken from the
#   Colormap instance. So do that.
# * Note that **calls to cmap instance do not interpolate values**; this is only
#   done by specifying levels in contourf call, specifying lut in get_cmap,
#   and using LinearSegmentedColormap.from_list with some N.
# * The cmap object itself only **picks colors closest to the "correct" one
#   in a "lookup table**; using lut in get_cmap interpolates lookup table.
#   See LinearSegmentedColormap doc: https://matplotlib.org/api/_as_gen/matplotlib.colors.LinearSegmentedColormap.html#matplotlib.colors.LinearSegmentedColormap
# * If you want to always disable interpolation, use ListedColormap. This type
#   of colormap instance will choose nearest-neighbors when using get_cmap, levels, etc.
#------------------------------------------------------------------------------#
def register_cmaps():
    """
    Register colormaps and cycles in the cmaps directory.
    Note all of those methods simply modify the dictionary mcm.cmap_d.
    """
    # First read from file
    for file in glob(f'{os.path.dirname(__file__)}/cmaps/*'):
        # Read table of RGB values
        if not re.search('.rgb$', file) and not re.search('.hex$', file):
            continue
        name = os.path.basename(file)[:-4]
        # Comment this out to overwrite existing ones
        # if name in mcm.cmap_d: # don't want to re-register every time
        #     continue
        if re.search('.rgb$', file):
            try: cmap = np.loadtxt(file, delimiter=',') # simple
            except:
                print(f'Failed to load {os.path.basename(file)}.')
                continue
            if (cmap>1).any():
                cmap = cmap/255
        # Read list of hex strings
        else:
            cmap = [*open(file)][0] # just a single line
            cmap = cmap.strip().split(',') # csv hex strings
            cmap = np.array([mcolors.to_rgb(c) for c in cmap]) # from list of tuples
        # Register as ListedColormap or LinearSegmentedColormap
        if 'lines' in name.lower():
            cmap   = mcolors.ListedColormap(cmap)
            cmap_r = cmap.reversed() # default name is name+'_r'
            custom_cycles[name] = cmap
        else:
            N = len(cmap) # simple as that; number of rows of colors
            cmap   = mcolors.LinearSegmentedColormap.from_list(name, cmap, N) # using static method is way easier
            cmap_r = cmap.reversed() # default name is name+'_r'
            custom_cmaps[name] = cmap
        # Register maps (this is just what register_cmap does)
        mcm.cmap_d[cmap.name]   = cmap
        mcm.cmap_d[cmap_r.name] = cmap_r
    # Next register names so that they can be invoked ***without capitalization***
    # This always bugged me! Note cannot change dictionary during iteration.
    ignorecase = {}
    for name,cmap in mcm.cmap_d.items():
        if re.search('[A-Z]',name):
            ignorecase[name.lower()] = cmap
    mcm.cmap_d.update(ignorecase)

def register_cycles():
    """
    Register cycles defined right here by dictionaries.
    """
    # Simply register them as ListedColormaps
    for name,colors in cycles.items():
        mcm.cmap_d[name]        = mcolors.ListedColormap([to_rgb(color) for color in colors])
        mcm.cmap_d[f'{name}_r'] = mcolors.ListedColormap([to_rgb(color) for color in colors[::-1]])

def register_colors(nmax=256):
    """
    Register new color names. Will only read first n of these
    colors, since XKCD library is massive (they should be sorted by popularity
    so later ones are no loss).
    """
    for file in glob(f'{os.path.dirname(__file__)}/colors/*.txt'):
        category, _ = os.path.splitext(os.path.basename(file))
        data = np.genfromtxt(file, delimiter='\t', dtype=str, comments='%', usecols=(0,1)).tolist()
        for i,(name,color) in enumerate(data): # is list of name, color tuples
            # if i>nmax:
            #     break
            mcolors._colors_full_map[name] = color
        custom_colors[category] = data

# Register stuff when this module is imported
custom_colors = {} # initialize
custom_cycles = {}
custom_cmaps  = {}
register_colors()
register_cmaps()
register_cycles()
print('Registered colors and colormaps.')

#------------------------------------------------------------------------------#
# Generalized colormap/cycle constructors
#------------------------------------------------------------------------------#
def Colormap(*args, levels=None, light=True, extend='both', **kwargs):
    """
    Convenience function for generating colormaps in a variety of ways.
    The 'extend' property will be used to resample LinearSegmentedColormap
    if we don't intend to use both out-of-bounds colors; otherwise we lose
    the strongest colors at either end of the colormap.
    You can still use extend='neither' in Colormap() call with extend='both'
    in contour or colorbar call, just means that colors at ends of the main
    region will be same as out-of-bounds colors.
    """
    if len(args)==0:
        raise ValueError('Function requires at least 1 positional arg.')
    cmaps = []
    # if type(args[-1])==1:
    for cmap in args:
        if isinstance(cmap, mcolors.Colormap):
            cmaps += [cmap]
            continue
        if not utils.isiterable(cmap):
            cmap = f'C{cmap}' # use current color cycle
        elif type(cmap) is dict:
            # Dictionary of hue/sat/luminance values or 2-tuples representing linear transition
            cmap = cspace_cmap(**cmap)
        # (len(cmap)==2 and type(cmap[0]) is str and type(cmap[1]) is dict):
        elif type(cmap) is str:
            # Map name or color for generating monochrome gradiation
            # if type(cmap) is not str:
            #     cmap, cmap_kw = cmap[0], {**cmap_kw, **cmap[1]}
            if cmap in mcm.cmap_d:
                cmap = mcm.cmap_d[cmap] # get the instance
            else:
                # Parse extra options
                cmap_kw = kwargs.copy() # may be different for each cmap in *args
                regex = '_([rlwdb]+)$'
                match = re.search(regex, cmap) # declare options with _[flags]
                cmap = re.sub(regex, '', cmap) # remove options
                options = '' if not match else match.group(1)
                if 'r' in options:
                    cmap_kw.update({'reverse':True})
                if 'w' in options or 'l' in options:
                    light = True
                    if 'w' in options:
                        cmap_kw.update({'white':'white'}) # use *actual* white
                if 'd' in options or 'b' in options:
                    light = False
                    if 'b' in options:
                        cmap_kw.update({'black':'black'}) # use *actual* black
                # Build colormap
                cmap = to_rgb(cmap) # to ensure is hex code/registered color
                if light:
                    cmap = light_cmap(cmap, **cmap_kw)
                else:
                    cmap = dark_cmap(cmap, **cmap_kw)
        else:
            # List of colors
            cmap = mcolors.ListedColormap(cmap)
        # Optionally make extremes same color as map
        offset = {'neither':-1, 'max':0, 'min':0, 'both':1}
        if extend not in offset:
            raise ValueError(f'Unknown extend option {extend}.')
        if extend!='both' and isinstance(cmap, mcolors.LinearSegmentedColormap):
            if levels is None:
                raise ValueError('You must pass levels to Colormap() function when extend!="both", so lookup table can be resampled.')
            cmap = mcm.get_cmap(cmap.name, lut=len(levels)-offset[extend])
            # cmap = mcolors.LinearSegmentedColormap.from_list(cmap(np.linspace(0,1,len(levels-1)))) # another idea
        cmaps += [cmap]
    return merge_cmaps(cmaps)

def Cycle(*args, vmin=0, vmax=1):
    """
    Convenience function to draw colors from arbitrary ListedColormap or
    LinearSegmentedColormap. Use vmin/vmax to scale your samples.
    """
    if len(args)==0:
        raise ValueError('Function requires at least 1 positional arg.')
    if len(args)==1:
        samples = 10
    else:
        args, samples = args[:-1], args[-1]
    cmap = Colormap(*args) # the cmap object itself
    if isinstance(cmap, mcolors.ListedColormap):
        # Just get the colors
        colors = cmap.colors
    elif isinstance(cmap, mcolors.LinearSegmentedColormap):
        # Employ ***more flexible*** version of get_cmap() method, which does this:
        # LinearSegmentedColormap(self.name, self._segmentdata, lutsize)
        if not utils.isiterable(samples):
            # samples = np.linspace(0, 1-1/nsample, nsample) # from 'centers'
            samples = np.linspace(0, 1, samples) # from edge to edge
        else:
            samples = np.array(samples)
        colors = cmap((samples-vmin)/(vmax-vmin))
    else:
        raise ValueError(f'Colormap returned weird object type: {type(cmap)}.')
    return colors

#------------------------------------------------------------------------------#
# Cycle helper functions
#------------------------------------------------------------------------------#
def set_cycle(cmap, samples=None, rename=False):
    """
    Set the color cycler.
    Arguments
    ---------
        cmap :
            Name of colormap or colormap instance from which we draw list of colors.
        samples :
            Array of values from 0-1 or number indicating number of evenly spaced
            samples from 0-1 from which to draw colormap colors. Will be ignored
            if the colormap is a ListedColormap (interpolation not possible).
    """
    colors = Cycle(cmap, samples)
    cyl = cycler('color', colors)
    rcParams['axes.prop_cycle'] = cyl
    rcParams['patch.facecolor'] = colors[0]
    if rename:
        rename_colors(cmap)

def rename_colors(cycle='colorblind'):
    """
    Calling this will change how shorthand codes like "b" or "g"
    are interpreted by matplotlib in subsequent plots.
    Arguments
    ---------
        cycle : {deep, muted, pastel, dark, bright, colorblind}
            Named seaborn palette to use as the source of colors.
    """
    if cycle=='reset':
        colors = [(0.0, 0.0, 1.0), (0.0, .50, 0.0), (1.0, 0.0, 0.0), (.75, .75, 0.0),
                  (.75, .75, 0.0), (0.0, .75, .75), (0.0, 0.0, 0.0)]
    elif cycle in seaborn_cycles:
        colors = cycles[cycle] + [(.1, .1, .1)]
    else:
        raise ValueError(f'Cannot set colors with color cycle {cycle}.')
    for code, color in zip('bgrmyck', colors):
        rgb = mcolors.colorConverter.to_rgb(color)
        mcolors.colorConverter.colors[code] = rgb
        mcolors.colorConverter.cache[code]  = rgb

#------------------------------------------------------------------------------#
# Colormap constructors
#------------------------------------------------------------------------------#
def merge_cmaps(cmaps, n=512, name='merged'):
    """
    Merge arbitrary colormaps.
    Arguments
    ---------
        cmaps : 
            List of colormap strings or instances for merging.
        n :
            Number of lookup table colors desired for output colormap.
        name :
            Name of output colormap.
    """
    if len(cmaps)==1:
        return cmaps[0] # needed to avoid recursion!
    samples = np.linspace(0,1,n//len(cmaps)) # from darkest to brightest color
    colors = [Colormap(cmap)(samples) for cmap in cmaps]
    colors = [color for sublist in colors for color in sublist]
    cmap = mcolors.LinearSegmentedColormap.from_list(name, colors)
    mcm.cmap_d[name] = cmap # 'register' the cmap
    return cmap

def smooth_cmap(colors, n=512, name='custom', input='rgb'):
    """
    Create colormap that smoothly blends between list of colors (in RGB
    space, so should't be too drastic).
    Input
    -----
        colors :
            List of colors.
        n :
            Number of lookup table colors desired for output colormap.
        name :
            Name of output colormap.
        input :
            If input is color tuple, indicates colorspace to which this
            color belongs (e.g. rgb, hcl).
    """
    colors = [to_rgb(color,input) for color in colors]
    cmap   = mcolors.LinearSegmentedColormap.from_list(name, colors, n)
    mcm.cmap_d[name] = cmap # 'register' the colormap
    return cmap

def cspace_cmap(n=256, h=[0.05,1], s=1.0, l=[0.2,1], c=None,
                    input='hsl', name=None, reverse=False, mask=True):
    """
    Linearly vary between one or more of the parameters in some colorspace.
    Input
    -----
        n : (int) number of colors
        h : (scalar, string) scalar hue or color-string from which we draw hue
            pass a length-2 tuple to request gradiation between two hues
        s : (scalar, string) as above, for saturation/chroma
        l : (scalar, string) as above, for lightness/luminance
    Options
    -------
        input :
            (str) colorspace from which you're creating your map, choose
            from 'hsv', 'hsl'/'hsluv', and 'hcl'/'hcluv'
        name :
            (str) name of colormap, default is same as "input"
        reverse :
            (bool) optionally reverse the map
        mask :
            (bool) whether to mask out (True) or clip (False) out-of-bounds or
            "imaginary" colors when making 'hcl' colormap
    --------------------------------------------------------------------------
    Choose from the following:
        * HSL (where L is not actually perceptually uniform)
        * HSLuv (where L is perceptually uniform but S is not always)
        * LCH (where it is uniform)
    See: http://www.hsluv.org/comparison/
    Q: Default is HSLuv. Why not HCL space?
    A: HCL space space has "dead zones" where you have impossible colors, so you
    can't just pick arbitrary numbers and draw a line (or will have to raise
    errors when we do this). Channels end up being clipped, which may cause
    strange/unexpected gradiations.
    HSLuv is just *scaled* HCL where chroma is represented as a percentage of
    the maximum possible chroma for that hue/luminance combo.
    """
    # Figure out transform function
    scale = (359, 99, 99)
    if input=='hsv':
        scale = (1, 1, 1) # hsv just scales everything within 1
    # Helper function; gets channel value from string color-name, and optionally offsets this value
    def channel(color, i):
        if type(color) is not str:
            return color
        offset = 0
        regex = '([-+]\S*)$' # user can optionally offset from color; don't filter to just numbers, want to raise our own error if user messes up
        match = re.search(regex, color)
        if match:
            try:
                offset = float(match.group(0))
            except ValueError as err:
                raise type(err)(f'Invalid channel identifier "{color}".')
            color  = color[:match.start()]
        return offset + to_xyz(to_rgb(color), input)[i]/scale[i]
    # Get length-2 tuples specifying colorspace gradations
    # Make sure we don't modify underlying vector
    # if s is not None and c is not None:
    #     raise ValueError('Can only specify either "s" or "c".')
    name = name or input # default to just naming colormap after input
    if c is not None: # by default, overwrite
        s = c
    if not utils.isiterable(h) or type(h) is str:
        h = [h, h]
    else:
        h = [*h]
    if not utils.isiterable(s) or type(s) is str:
        s = [s, s]
    else:
        s = [*s]
    if not utils.isiterable(l) or type(l) is str:
        l = [l, l]
    else:
        l = [*l]
    for i in range(2):
        h[i] = channel(h[i], 0)
        s[i] = channel(s[i], 1)
        l[i] = channel(l[i], 2)
    # Next calculate stuff
    # NOTE: Before these were all minus 1, dunno why
    hues = scale[0]*(np.linspace(h[0], h[1], n+1) % 1) # before these were all minus 1, dunno why
    sats = scale[1]*(np.linspace(s[0], s[1], n+1)) # dunnot why max has to be 99
    lums = scale[2]*(np.linspace(l[0], l[1], n+1))
    colors = [to_rgb((h,s,l),input) for h,s,l in zip(hues,sats,lums)]
    colors = clip_colors(colors, mask=mask)
    if reverse:
        colors = colors[::-1]
    return smooth_cmap(colors, name=name)

def clip_colors(colors, mask=True):
    """
    Arguments
    ---------
        colors :
            List of length-3 RGB color tuples.
        mask : (bool)
            Whether to mask out (set to some dark gray color) or clip (limit
            range of each channel to [0,1]) out-of-range RGB channels.
    """
    under = {}
    over = {}
    message = 'Invalid value for' if mask else 'Clipping'
    colors = [list(rgb) for rgb in colors] # so we can overwrite
    gray = 0.2 # RGB values for gray color
    for rgb in colors:
        for i,(c,n) in enumerate(zip(rgb,'rgb')):
            if c<0:
                if mask:
                    rgb[-1] = 0
                    for j in range(3):
                        rgb[j] = gray
                else:
                    rgb[i] = 0
                if n not in under:
                    under[n] = True
                    print(f'Warning: {message} channel {n} (<0).')
            if c>1:
                if mask:
                    rgb[-1] = 1 # full alpha
                    for j in range(3):
                        rgb[j] = gray
                else:
                    rgb[i] = 1 # keep
                if n not in over:
                    over[n] = True
                    print(f'Warning: {message} channel {n} (>1).')
    return colors

def light_cmap(color, n=512, reverse=False, input='hsl', white='#eeeeee', light=None):
    """
    Make a sequential colormap that blends from color to near-white.
    Arguments
    ---------
        color :
            Build colormap by varying the luminance of some RGB color while
            keeping its saturation and hue constant.
    Optional
    --------
        n : (512)
            Number of lookup table colors desired for output colormap.
        reverse : (False)
            Optionally reverse colormap.
        input : ('hsl')
            Colorspace in which we vary luminance.
    """
    white = light or white
    _, ws, wl = to_xyz(to_rgb(white), input)
    h, s, l = to_xyz(to_rgb(color), input)
    h, s, l, ws, wl = h/359.0, s/99.0, l/99.0, ws/99.0, wl/99.0
    ws = s # perhaps don't change the chroma by default
    index = slice(None,None,-1) if reverse else slice(None)
    return cspace_cmap(n, h, [s,ws][index], [l,wl][index], input=input)

def dark_cmap(color, n=512, reverse=False, input='hsl', black='#444444', dark=None, gray=None, grey=None):
    """
    Make a sequential colormap that blends from gray to color.
    Arguments
    ---------
        color :
            Build colormap by varying the luminance of some RGB color while
            keeping its saturation and hue constant.
    Optional
    --------
        n : (512)
            Number of lookup table colors desired for output colormap.
        reverse : (False)
            Optionally reverse colormap.
        input : ('hsl')
            Colorspace in which we vary luminance.
    """
    black = grey or gray or dark or black # alternative kwargs
    _, bs, bl = to_xyz(to_rgb(black), input)
    h, s, l = to_xyz(to_rgb(color), input)
    h, s, l, bs, bl = h/359.0, s/99.0, l/99.0, bs/99.0, bl/99.0
    index = slice(None,None,-1) if reverse else slice(None)
    return cspace_cmap(n, h, [bs,s][index], [bl,l][index], input=input)

#------------------------------------------------------------------------------
# Normalization classes for mapping data to colors (i.e. colormaps)
# WARNING: Many methods in ColorBarBase tests for class membership, crucially
# including _process_values(), which if it doesn't detect BoundaryNorm will
# end up trying to infer boundaries from inverse() method
#------------------------------------------------------------------------------
def Norm(norm, levels=None, default='discrete', **kwargs):
    """
    Return arbitrary normalizer.
    """
    if isinstance(norm, mcolors.Normalize):
        pass
    elif norm is None and levels is not None:
        kwargs.update({'levels':levels})
        norm = default # the default case when levels are provided
    elif norm is None:
        norm = mcolors.Normalize() # default is just linear from 0 to 1
    elif type(norm) is not str: # dictionary lookup
        raise ValueError(f'Unknown norm "{norm}".')
    if type(norm) is str:
        if norm not in normalizers:
            raise ValueError(f'Unknown normalizer "{norm}". Options are {", ".join(normalizers.keys())}.')
        norm = normalizers[norm](**kwargs)
    return norm

class ContinuousNorm(mcolors.Normalize):
    """
    As in BoundaryNorm case, but instead we linearly *interpolate* colors
    between the provided boundary indices. Use this e.g. if you want to
    have the gradation from 0-1 'zoomed in' and gradation from 0-10 'zoomed out'.
    In this case, can control number of colors by setting the *lookup table*
    when declaring colormap.
    """
    def __init__(self, levels=None, midpoint=None, clip=False, ncolors=None, **kwargs):
        # Very simple
        levels = np.atleast_1d(levels)
        if np.any((levels[1:]-levels[:-1])<=0):
            raise ValueError(f'Levels passed to ContinuousNorm must be monotonically increasing.')
        super().__init__(np.nanmin(levels), np.nanmax(levels), clip) # second level superclass
        self.levels = levels # alias for boundaries

    def __call__(self, value, clip=None):
        # TODO: Add optional midpoint, this class will probably end up being one of
        # my most used if so. Midpoint would just ensure <value> corresponds to 0.5 in cmap
        # Map data values in range (vmin,vmax) to color indices in colormap
        # If have 11 levels and between ids 9 and 10, interpolant is between .9 and 1
        value = np.atleast_1d(value)
        norm  = np.empty(value.shape)
        for i,v in enumerate(value.flat):
            if np.isnan(v):
                continue
            idxs = np.linspace(0, 1, self.levels.size)
            locs = np.where(v>=self.levels)[0]
            if locs.size==0:
                norm[i] = 0
            elif locs.size==self.levels.size:
                norm[i] = 1
            else:
                cutoff      = locs[-1]
                interpolant = idxs[cutoff:cutoff+2] # the 0-1 normalization
                interpolee  = self.levels[cutoff:cutoff+2] # the boundary level values
                norm[i]     = np.interp(v, interpolee, interpolant) # interpolate between 2 points
        return ma.masked_array(norm, np.isnan(value))

    def inverse(self, norm):
        # Performs inverse operation of __call__
        norm  = np.atleast_1d(norm)
        value = np.empty(norm.shape)
        for i,n in enumerate(norm.flat):
            if np.isnan(n):
                continue
            idxs = np.linspace(0, 1, self.levels.size)
            locs = np.where(n>=idxs)[0]
            if locs.size==0:
                value[i] = np.nanmin(self.levels)
            elif locs.size==self.levels.size:
                value[i] = np.nanmax(self.levels)
            else:
                cutoff = locs[-1]
                interpolee  = idxs[cutoff:cutoff+2] # the 0-1 normalization
                interpolant = self.levels[cutoff:cutoff+2] # the boundary level values
                value[i]    = np.interp(n, interpolee, interpolant) # interpolate between 2 points
        return ma.masked_array(value, np.isnan(norm))

class DiscreteNorm(mcolors.BoundaryNorm):
    """
    Simple normalizer that *interpolates* from an RGB array at point
    (level_idx/num_levels) along the array, instead of choosing color
    from (transform(level_value)-transform(vmin))/(transform(vmax)-transform(vmin))
    where transform can be linear, logarithmic, etc.
    TODO:
    * Allow this to accept transforms too, which will help prevent level edges
      from being skewed toward left or right in case of logarithmic/exponential data.
    Example: Your levels edges are weirdly spaced [-1000, 100, 0, 100, 1000] or
    even [0, 10, 12, 20, 22], but center "colors" are always at colormap
    coordinates [.2, .4, .6, .8] no matter the spacing; levels just must be monotonic.
    """
    def __init__(self, levels=None, midpoint=None, bins=False, clip=False, ncolors=None, **kwargs):
        # Don't need to call partent initializer, this is own implementation; just need
        # it to be subclass so ColorbarBase methods will detect it
        # See BoundaryNorm: https://github.com/matplotlib/matplotlib/blob/master/lib/matplotlib/colors.py
        levels = np.atleast_1d(levels)
        if np.any((levels[1:]-levels[:-1])<=0):
            raise ValueError('Levels passed to Normalize() must be monotonically increasing.')
        self.N = len(levels)
        self.levels = levels
        self.boundaries = levels # alias read by other functions
        self.vmin = levels[0]
        self.vmax = levels[-1]
        self.clip = clip

    def __call__(self, value, clip=None):
        # TODO: Add optional midpoint, this class will probably end up being one of
        # my most used if so. Midpoint would just ensure <value> corresponds to 0.5 in cmap
        # Map data values in range (vmin,vmax) to color indices in colormap
        # If have 11 levels and between ids 9 and 10, interpolant is between .9 and 1
        value = np.atleast_1d(value)
        norm  = np.empty(value.shape)
        for i,v in enumerate(value.flat):
            if np.isnan(v):
                continue
            idxs = np.linspace(0, 1, self.levels.size)
            locs = np.where(v>=self.levels)[0]
            if locs.size==0:
                norm[i] = 0
            elif locs.size==self.levels.size:
                norm[i] = 1
            else:
                cutoff  = locs[-1]
                norm[i] = (idxs[cutoff] + idxs[cutoff+1])/2
        return ma.masked_array(norm, np.isnan(value))

    def inverse(self, norm):
        # Not possible
        raise ValueError('Normalize is not invertible in "bins" mode.')

class StretchNorm(mcolors.Normalize):
    """
    Class that can 'stretch' and 'compress' either side of a colormap about
    some midpoint, proceeding exponentially (exp>0) or logarithmically (exp<0)
    down the linear colormap from the center point. Default midpoint is vmin, i.e.
    we just stretch to the right. For diverging colormaps, use midpoint 0.5.
    """
    def __init__(self, exp=0, extend='neither', midpoint=None, vmin=None, vmax=None, clip=None):
        # User will use -10 to 10 scale; converted to value used in equation
        if abs(exp) > 10: raise ValueError('Warping scale must be between -10 and 10.')
        super().__init__(vmin, vmax, clip)
        self.midpoint = midpoint
        self.exp = exp
        self.extend = extend
        # mcolors.Normalize.__init__(self, vmin, vmax, clip)

    # Function
    def warp(x, exp, exp_max=4):
        # Returns indices stretched so neutral/low values are sampled more heavily
        # Will artifically use exp to signify stretching away from neutral vals,
        # or compressing toward neutral vals
        if exp > 0:
            invert = True
        else:
            invert, exp = False, -exp
        exp = exp*(exp_max/10)
        # Apply function; approaches x=1 as a-->Inf, x=x as a-->0
        if invert: x = 1-x
        value =  (x-1+(np.exp(x)-x)**exp)/(np.e-1)**exp
        if invert:
            value = 1-value # flip on y-axis
        return value

    def __call__(self, value, clip=None):
        # Initial stuff
        if self.midpoint is None:
            midpoint = self.vmin
        else:
            midpoint = self.midpoint
        # Get middle point in 0-1 coords, and value
        midpoint_scaled = (midpoint - self.vmin)/(self.vmax - self.vmin)
        value_scaled    = (value - self.vmin)/(self.vmax - self.vmin)
        try: iter(value_scaled)
        except TypeError:
            value_scaled = np.arange(value_scaled)
        value_cmap = ma.empty(value_scaled.size)
        for i,v in enumerate(value_scaled):
            # Get values, accounting for midpoints
            if v<0:
                v = 0
            if v>1:
                v = 1
            if v>=midpoint_scaled:
                block_width = 1 - midpoint_scaled
                value_cmap[i] = (midpoint_scaled + 
                    block_width*self.warp((v - midpoint_scaled)/block_width, self.exp)
                    )
            else:
                block_width = midpoint_scaled
                value_cmap[i] = (midpoint_scaled - 
                        block_width*self.warp((midpoint_scaled - v)/block_width, self.exp)
                        )
        if self.extend=='both' or self.extend=='max':
            value_cmap[value_cmap>1] = 1
        if self.extend=='both' or self.extend=='min':
            value_cmap[value_cmap<0] = 0
        return value_cmap

#------------------------------------------------------------------------------#
# Visualizations
#------------------------------------------------------------------------------#
def color_show(groups=['open',['crayons','xkcd']], ncols=4, nbreak=15, minsat=0.1):
    """
    Visualize all possible named colors. Wheee!
    Modified from: https://matplotlib.org/examples/color/named_colors.html
    * Special Note: The 'Tableau Colors' are just the *default matplotlib
      color cycle colors*! So don't bother iterating over them.
    """
    # Get colors explicitly defined in _colors_full_map, or the default
    # components of that map (see soure code; is just a dictionary wrapper
    # on some simple lists)
    figs = []
    for group in groups:
        group = group or 'open'
        if type(group) is str:
            group = [group]
        colors = {}
        for name in group:
            # Read colors from current cycler
            if name=='cycle':
                seen = set() # trickery
                cycle_colors = rcParams['axes.prop_cycle'].by_key()['color']
                cycle_colors = [color for color in cycle_colors if not (color in seen or seen.add(color))] # trickery
                colors.update({f'C{i}':v for i,v in enumerate(cycle_colors)})
            # Read custom defined colors
            else:
                colors.update({name:color for name,color in custom_colors[name]}) # convert from list of length-2 tuples to dictionary
        # Group colors together by discrete range of hue, then sort by value
        # For opencolors this is not necessary
        if 'open' in group:
            space = 0.5
            swatch = 1.5
            names = ['gray', 'red', 'pink', 'grape', 'violet', 'indigo', 'blue', 'cyan', 'teal', 'green', 'lime', 'yellow', 'orange']
            nrows, ncols = 10, len(names) # rows and columns
            sorted_names = [[name+str(i) for i in range(nrows)] for name in names]
        # For other palettes this is necessary
        else:
            # Keep in separate columns
            space = 1
            swatch = 1
            ncols = nbreak-1 # group by breakpoint
            colors_hsv = {k:tuple(colormath.rgb_to_hsv(*mcolors.to_rgb(v))) for k,v in colors.items()}
            breakpoints = np.linspace(0,1,nbreak) # group in blocks of 20 hues
            sorted_names = [] # initialize
            testsat = (lambda x: x<minsat) # test saturation
            for n in range(len(breakpoints)):
                if n==0: # grays
                    fcolors = [(name,hsv) for name,hsv in colors_hsv.items()
                        if testsat(hsv[1])]
                    sortfunc = lambda x: 3*x[2]+x[0]
                else: # colors
                    start, end = breakpoints[n-1], breakpoints[n]
                    testhue = (lambda x: start<=x<=end) if end is breakpoints[-1] \
                        else (lambda x: start<=x<end) # two possible tests
                    fcolors = [(name,hsv) for name,hsv in colors_hsv.items()
                        if testhue(hsv[0]) and not testsat(hsv[1])] # grays have separate category
                    sortfunc = lambda x: 3*x[2]+x[1]
                sorted_index = np.argsort([sortfunc(v[1]) for v in fcolors]) # indices to build sorted list
                sorted_names.append([fcolors[i][0] for i in sorted_index]) # append sorted list
            nrows = max(len(huelist) for huelist in sorted_names) # number of rows
            # Now concatenate those columns so get nice rectangle
            names = [i for sublist in sorted_names for i in sublist]
            sorted_names = [[]]
            nrows = len(names)//ncols+1
            for i,name in enumerate(names):
                if ((i + 1) % nrows)==0:
                    sorted_names.append([]) # add new empty list
                sorted_names[-1].append(name)
        # Create plot by iterating over columns 
        figsize = (8*space*(ncols/4), 5*(nrows/40)) # 5in tall with 40 colors in column
        fig, ax = plt.subplots(figsize=figsize)
        X, Y = fig.get_dpi()*fig.get_size_inches() # size in *dots*; make these axes units
        h, w = Y/(nrows+1), X/ncols # height and width of row/column in *dots*
        for col,huelist in enumerate(sorted_names):
            for row,name in enumerate(huelist): # list of colors in hue category
                y = Y - (row * h) - h
                xi_line = w*(col + 0.05)
                xf_line = w*(col + 0.25*swatch)
                xi_text = w*(col + 0.25*swatch + 0.03*swatch)
                print_name = name.split('xkcd:')[-1] # make sure no xkcd:
                ax.text(xi_text, y, print_name, fontsize=h*0.8, ha='left', va='center')
                ax.hlines(y+h*0.1, xi_line, xf_line, color=colors[name], lw=h*0.6)
        ax.set_xlim(0,X)
        ax.set_ylim(0,Y)
        ax.set_axis_off()
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0, hspace=0, wspace=0)
        # Save
        fig.savefig(f'{os.path.dirname(__file__)}/colors_{"-".join(group)}.pdf',
                bbox_inches='tight', format='pdf')
        figs += [fig]
    return figs

def cycle_show():
    """
    Show off the different color cycles.
    Wrote this one myself, so it uses the custom API.
    """
    # cycles = plt.get_cycles() # function should have been added by the rc plugin
    cycles = mcolors.CYCLES
    nrows = len(cycles)//2+len(cycles)%2
    fig, axs = plt.subplots(figsize=(6,nrows*1.5), ncols=2, nrows=nrows)
    axs = [ax for sub in axs for ax in sub]
    fig.subplots_adjust(top=.99, bottom=.01, left=.02, right=0.98, hspace=.2, wspace=.02)
    state = np.random.RandomState(123412)
    for i,(ax,(key,value)) in enumerate(zip(axs,cycles.items())):
        propcycle = cycler('color', value)
        ax.set_prop_cycle(propcycle)
        lines = ax.plot(state.rand(10,len(value)), lw=5, ls='-')
        for j,l in enumerate(lines):
            l.set_zorder(len(lines)-j) # make first lines have big zorder
        title = f'{key}: {len(value)} colors'
        ax.set_xlim((-0.5,10))
        ax.set_title(title)
        for axis in 'xy':
            ax.tick_params(axis=axis, which='both', labelbottom=False, labelleft=False,
                    bottom=False, top=False, left=False, right=False)
    if len(cycles)%2==1:
        axs[-1].set_visible(False)
    # Save
    fig.savefig(f'{os.path.dirname(__file__)}/cycles.pdf',
            bbox_inches='tight', format='pdf')
    return fig

# def cmap_show(N=31, ignore=['Miscellaneous','Sequential2','Diverging2']):
def cmap_show(N=31, ignore=['Diverging Alt', 'Sequential Alt', 'Rainbow Alt', 'Miscellaneous']):
    """
    Plot all current colormaps, along with their catgories.
    This example comes from the Cookbook on www.scipy.org. According to the
    history, Andrew Straw did the conversion from an old page, but it is
    unclear who the original author is.
    See: http://matplotlib.org/examples/color/colormaps_reference.html
    """
    # Have colormaps separated into categories:
    # NOTE: viridis, cividis, plasma, inferno, and magma are all
    # listed colormaps for some reason
    exceptions = ['viridis','cividis','plasma','inferno','magma']
    cmaps_all = [cmap for cmap in mcm.cmap_d.keys() if
            not cmap.endswith('_r')
            and not re.search('[A-Z]',cmap)
            and 'Vega' not in cmap
            and (isinstance(mcm.cmap_d[cmap],mcolors.LinearSegmentedColormap) or cmap in exceptions)]
    cmaps_listed = [cmap for cmap in mcm.cmap_d.keys() if
            not cmap.endswith('_r')
            and not re.search('[A-Z]',cmap)
            and 'Vega' not in cmap
            and (not isinstance(mcm.cmap_d[cmap],mcolors.LinearSegmentedColormap) and cmap not in exceptions)]
    categories = { # initialize as empty lists
        'Custom': [], # should come first
        # 'ColorBrewer': [], # actually *every single colorbrewer map* is implemented already by default, just different names
        'Rainbow':
            sorted(['viridis', 'plasma', 'inferno', 'magma']),
        'Rainbow Alt':
            sorted(['multi', 'cubehelix', 'cividis']),
        'Diverging':
            sorted(['piyg', 'prgn', 'brbg', 'puor', 'rdgy', 'rdbu', 'rdylbu', 'rdylgn', 'spectral']),
        'Sequential':
            sorted(['greys', 'purples', 'blues', 'greens', 'oranges', 'reds',
            'ylorbr', 'ylorrd', 'orrd', 'purd', 'rdpu', 'bupu',
            'gnbu', 'pubu', 'ylgnbu', 'pubugn', 'bugn', 'ylgn']),
        'Sequential Alt':
            sorted(['binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'wistia',
            'coolwarm', 'bwr', 'seismic', # diverging ones
            'afmhot', 'gist_heat', 'copper']),
        'Diverging Alt': sorted(['coolwarm', 'bwr', 'seismic']),
        'Miscellaneous':
            sorted(['flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'cmrmap', 'brg', 'hsv',
            'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar'])}
    # Detect unknown/manually created colormaps, and filter out
    # colormaps belonging to certain section
    cmaps_ignore  = [cmap for cat,cmaps in categories.items() for cmap in cmaps if cat in ignore]
    categories    = {cat:cmaps for cat,cmaps in categories.items() if cat not in ignore}
    cmaps_known   = [cmap for cat,cmaps in categories.items() for cmap in cmaps if cmap in cmaps_all]
    cmaps_missing = [cmap for cat,cmaps in categories.items() for cmap in cmaps if cmap not in cmaps_all]
    cmaps_custom  = [cmap for cmap in cmaps_all if cmap not in cmaps_known and cmap not in cmaps_ignore]
    categories['Custom'] = cmaps_custom
    # categories['Custom'] = [cmap for cmap in cmaps_custom if cmap[:2]!='cb']
    # categories['ColorBrewer'] = [cmap for cmap in cmaps_custom if cmap[:2]=='cb']
    if cmaps_missing:
        print(f'Missing colormaps: {", ".join(cmaps_missing)}')
    if cmaps_ignore:
        print(f'Ignored colormaps: {", ".join(cmaps_ignore)}')
    # print(f'Custom colormaps: {", ".join(cmaps_custom)}')
    # print(f'Listed colormaps: {", ".join(cmaps_listed)}')
    # Array for producing visualization with imshow
    a = np.linspace(0, 1, 257).reshape(1,-1)
    a = np.vstack((a,a))
    # Figure
    extra = 1 # number of axes-widths to allocate for titles
    nmaps = len(cmaps_known) + len(cmaps_custom) + len(categories)*extra
    fig = plt.figure(figsize=(5,0.3*nmaps))
    fig.subplots_adjust(top=0.98, bottom=0.01, left=0.15, right=0.99)
    # Make plot
    ntitles, nplots = 0, 0 # for deciding which axes to plot in
    for cat in categories:
        # Space for title
        ntitles += extra # two axes-widths
        for i,m in enumerate(categories[cat]):
            # Checks
            if i+ntitles+nplots>nmaps:
                break
            if m not in mcm.cmap_d or m not in cmaps_all: # i.e. the expected builtin colormap is missing
                continue
            # Draw, and make axes invisible
            cmap = mcm.get_cmap(m, N) # interpolate
            ax = plt.subplot(nmaps,1,i+ntitles+nplots)
            for s in ax.spines.values():
                s.set_visible(False)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.imshow(a, aspect='auto', cmap=cmap, origin='lower')
            # Category title and colorbar label
            if i==0:
                t = ax.title
                t.set_text(cat) # category name
                t.set_visible(True)
            yl = ax.yaxis.label
            yl.set_text(m) # map name
            yl.set_visible(True)
            yl.set_rotation(0)
            yl.set_ha('right')
            yl.set_va('center')
        # Space for plots
        nplots += len(categories[cat])
    # Save
    filename = f'{os.path.dirname(__file__)}/colormaps.pdf'
    print(f"Saving figure to: {filename}.")
    fig.savefig(filename, bbox_inches='tight')
    return fig

# Finally our dictionary of normalizers
# Includes some custom classes, so has to go at end
normalizers = {
    'none':       mcolors.NoNorm,
    'null':       mcolors.NoNorm,
    'boundary':   mcolors.BoundaryNorm,
    'discrete':   DiscreteNorm,
    'continuous': ContinuousNorm,
    'log':        mcolors.LogNorm,
    'linear':     mcolors.Normalize,
    'power':      mcolors.PowerNorm,
    'symlog':     mcolors.SymLogNorm,
    }

# TODO: Figure out if this is still useful
# ***Inverse of cycle_factory.***
# Generate colormap instance from list of levels and colors.
# * Generally don't want these kinds of colorbars to 'extend', but you can.
# * Object will assume one color between individual levels; for example,
#   if levels are [0,0.5,0.6,1], the first and last color-zones will be way thicker.
# * If you want unevenly space intervals but evenly spaced boundaries, use custom
#   Norm instead of default.
# * This is *one way* to create a colormap from list of colors; another way is
#   to just pass a list of colors to any _cformat method. That method will
#   also generate levels that are always equally spaced.
# if levels is None:
#     levels = np.linspace(0,1,len(colors)+1)
# if len(levels)!=len(colors)+1:
#     raise ValueError(f"Have {len(levels):d} levels and {len(colors):d} colors. Need ncolors+1==nlevels.")
# if extend=='min':
#     colors = ['w', *colors] # add dummy color
# elif extend=='max':
#     colors = [*colors, 'w'] # add dummy color
# elif extend=='both':
#     colors = ['w', *colors, 'w']
# elif extend!='neither':
#     raise ValueError("Unknown extend option \"{extend}\".")
# cmap, norm = mcolors.from_levels_and_colors(levels, colors, extend=extend) # creates ListedColormap!!!
# return cmap
# Generate mappable using contourf
# def Mappable(cmap, samples=None, levels=None, norm=None):
# cmap = cmap_factory(cmap)
# if norm is None:
#     norm = mcolors.Normalize(0,1)
# elif not hasattr(norm,'__call__'):
#     raise ValueError('Norm has to be callable.')
# elif not isinstance(norm,mcolors.Normalize):
#     raise ValueError('Norm has to be an mcolors.Normalize class or subclass.')
# # Specify the *centers*, then interpolate to *edges* according to normalizer
# if samples is not None:
#     samples = np.array(samples)
#     if not isinstance(cmap, mcolors.BoundaryNorm):
#         samples = norm(samples) # translate to normalized-space (e.g. LogNorm)
#     if samples[1]<samples[0]:
#         samples = samples[::-1]
#         reverse = True
#     idelta = samples[1]-samples[0]
#     fdelta = samples[-1]-samples[-2]
#     levels = [samples[0]-idelta/2, *((samples[1:]+samples[:-1])/2), samples[-1]+fdelta/2]
#     if not isinstance(cmap, mcolors.BoundaryNorm):
#         levels = norm.inverse(levels) # translate back from normalized-space
# # Optionally reverse the colormap
# if levels[1]<levels[0]: # specify the *levels*
#     levels = levels[::-1]
#     reverse = True
# if reverse:
#     cmap = cmap.reversed() # reverse the cmap
# m = plt.contourf([0,0], [0,0], np.nan*np.ones((2,2)), cmap=cmap, levels=levels, norm=norm)
# return m