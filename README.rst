.. Docstrings formatted according to:
   numpy guide:      https://numpydoc.readthedocs.io/en/latest/format.html
   matplotlib guide: https://matplotlib.org/devel/documenting_mpl.html
.. Sphinx is used following this guide (less traditional approach):
   https://daler.github.io/sphinxdoc-test/includeme.html

ProPlot
=======

A library providing helpful and versatile plotting utilities
for making beautiful, publication-quality graphics with ease.

Overview
--------

Import with

::

   import proplot as plot

Most of the features derive from the `~proplot.subplots.subplots` command, inspired
by the pyplot `~matplotlib.pyplot.subplots` command. This generates a scaffolding
of axes and panels, which may have shared axes and spanning axis labels, and optional
geographic projections.

The next most important utility is the `~proplot.axes.BaseAxes.format` method, available
on every axes generated by `~proplot.subplots.subplots`. Use this method to fine-tune
your axis properties, titles, labels, limits, and much more.

Quick overview of additional features:

-  Geometry: A smarter "tight subplots" method. Panels and empty spaces
   are held *fixed*, while the figure and axes dimensions are allowed to
   change. This achieves a "tight border" without messing up axes aspect
   ratios or spaces.
-  Colors: Perceptually distinct named colors, powerful
   colormap-generating tools, ability to trivially swap between "color
   cycles" and "colormaps". A few new, beautiful colormaps and color
   cycles. Make colorbars from lists of lines or colors.
-  Maps: Integration with basemap and cartopy. Generate arbitrary
   grids of map projections in one go. Switch between the cartopy and
   basemap backends painlessly. Add geographical features as part of the
   `~proplot.axes.CartopyAxes.format` process.

Shout out to `bradyrx <https://github.com/bradyrx>`__ for being the
guinea pig and helping me fix a lot of the initial bugs. Check out his `decadal climate prediction package <https://github.com/bradyrx/climpred>`_.

Documentation
-------------
The documentation is published `here <https://lukelbd.github.io/proplot>`_.

Installation
------------

This package is a work-in-progress. Currently there is no formal release
on PyPi. However, feel free to install directly from Github using:

::

   pip install git+https://github.com/lukelbd/proplot.git#egg=proplot

Dependencies are just `matplotlib` and `numpy`. The geographic mapping
mapping features require `cartopy` and/or `basemap`.

How is this different from seaborn?
-----------------------------------

There is already a great matplotlib wrapper called
`seaborn <https://seaborn.pydata.org/>`__. What makes this project
different?

While parts of `proplot` were inspired by seaborn (in particular much
of ``colors.py`` is drawn from seaborn’s ``palettes.py``), the goal for
this project was quite different – it is intended to simplify the task
of making publication-quality figures, and no more.

Seaborn largely attempts to merge the tasks of data analysis and
visualization, and many of its features require neatly tabulated data in
a standard form. ProPlot contains no analysis tools – it is expected
that you analyze your data on your own time.

.. Anyway, as an atmospheric scientist, the datasets I use usually do not
   lend themselves to fitting in a simple DataFrame – so this seaborn
   feature was not particularly useful for me. For data analysis tools I
   use in my physical climatology research, check out my
   `ClimPy <https://github.com/lukelbd/climpy%60>`__ project (still in
   preliminary stages).

By focusing on this single task, I was able to create a number of
powerful features beyond the scope of `seaborn`. I was also able
to integrate my features much more closely with the matplotlib API,
rather than making an entirely new ecosystem that you have to learn
to use from scratch.

See the documentation and showcase for details.

Donations
---------

This package took a shocking amount of time to write and to publish. If you've found it
useful, feel free to buy me a cup of coffee :)

.. image:: https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif
   :target: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5SP6S8RZCYMQA&source=url