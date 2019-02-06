# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import numpy as np
import astropy.units as u
from astropy.time import Time
import warnings

from ..exceptions import PlotBelowHorizonWarning
from ..utils import _set_mpl_style_sheet

__all__ = ['plot_sky', 'plot_schedule_sky', 'plot_sky_24hr']


@u.quantity_input(az_label_offset=u.deg)
def plot_sky(target, observer, time, ax=None, style_kwargs=None,
             north_to_east_ccw=True, grid=True, az_label_offset=0.0*u.deg,
             warn_below_horizon=False, style_sheet=None, annotation=None):
    """
    Plots target positions in the sky with respect to the observer's location.

    If a `~matplotlib.axes.Axes` object already exists, plots an additional
    target position on top.
    Otherwise, creates a new `~matplotlib.axes.Axes` object with a sky plot.

    Can pass in a scalar `~astropy.time.Time` object (e.g. ``Time('2000-1-1')``)
    or an array of length one (e.g. ``Time(['2000-1-1'])``) to get plot at one
    instance in time.
    If pass in an `~astropy.time.Time` object with multiple instances of time
    (e.g. ``Time(['2000-1-1 20:00:00', '2000-1-1 20:30:00'])``), target's
    position will be shown at each of these times.

    For examples with plots, visit the documentation of :ref:`plots_sky_charts`.

    Parameters
    ----------
    target : `~astroplan.FixedTarget`
        The celestial body of interest.

    observer : `~astroplan.Observer`
        The person, telescope, observatory, etc. doing the observing.

    time : `~astropy.time.Time`
        If pass in an `~astropy.time.Time` object with just one instance in
        time, whether it be a scalar or an array (e.g. ``Time('2000-1-1')``,
        ``Time(['2000-1-1'])``, ``[Time('2000-1-1')]``),
        `~astroplan.plots.plot_sky` will return plot at one instance in
        time.  If pass in an `~astropy.time.Time` object with multiple
        instances in time (e.g. ``Time(['2000-1-1', '2000-1-2'])``) will
        show positions plotted at the exact times specified.

    ax : `~matplotlib.axes.Axes` or None, optional.
        The `~matplotlib.axes.Axes` object to be drawn on.
        If None, uses the current `~matplotlib.axes.Axes`.

    style_kwargs : dict or None, optional.
        A dictionary of keywords passed into `~matplotlib.pyplot.scatter`
        to set plotting styles.

    north_to_east_ccw : bool, optional.
        True by default, meaning that azimuth is shown increasing
        counter-clockwise (CCW), or with North at top, East at left, etc.
        To show azimuth increasing clockwise (CW), set to False.

    grid : bool, optional.
        True by default, meaning that grid is drawn.

    az_label_offset : ``~astropy.units.degree``, optional.
        DANGER: It is not recommended that you change the default behavior,
        as to do so makes it seem as if N/E/S/W are being decoupled from the
        definition of azimuth (North from az = 0 deg., East from az = 90 deg.,
        etc.).
        An offset for azimuth labels from the North label.  A positive
        offset will increase in the same direction as azimuth
        (see ``north_to_east_ccw`` option).

    warn_below_horizon : bool, optional
        If `False`, don't show warnings when attempting to plot targets below
        the horzion.

    style_sheet : dict or `None` (optional)
        matplotlib style sheet to use. To see available style sheets in
        astroplan, print *astroplan.plots.available_style_sheets*. Defaults
        to the light theme.

    Returns
    -------
    An `~matplotlib.axes.Axes` object (ax) with a map of the sky.

    Notes
    -----
    Using `~astropy.time.Time` objects:
        See `Astropy`_ documentation for more details.

    Coordinate defaults:

        Altazimuth (local horizon) coordinate system.  North is always at top
        of plot, South is always at the bottom, E/W can be right or left
        depending on the ``north_to_east_cw`` option.

        Altitude: 90 degrees (zenith) is at plot origin (center) and 0 degrees
        (horizon) is at plot edge.  This cannot be changed by user.

        Azimuth: 0 degrees is at North (top of plot), 90 degrees at East, etc.
        DANGER: Azimuth labels can be changed by user via the
        ``az_label_offset`` option, but it is not recommended, as to do so
        makes it seem as if N/E/S/W are being decoupled from the definition
        of azimuth (North from az = 0 deg., East from az = 90 deg., etc.).

    """
    # Import matplotlib, set style sheet
    if style_sheet is not None:
        _set_mpl_style_sheet(style_sheet)

    import matplotlib.pyplot as plt

    # Set up axes & plot styles if needed.
    if ax is None:
        ax = plt.gca(projection='polar')
    if style_kwargs is None:
        style_kwargs = {}
    style_kwargs = dict(style_kwargs)
    style_kwargs.setdefault('marker', 'o')

    # Turn scalar Time objects into arrays.
    time = Time(time)
    if time.isscalar:
        time = Time([time])

    # Grab altitude and azimuth from Astroplan objects.
    # Note that values must be made dimensionless before plotting.
    # Modifying altitude is easier than inverting r-axis.
    altitude = (91 * u.deg - observer.altaz(time, target).alt) * (1/u.deg)
    # Azimuth MUST be given to plot() in radians.
    azimuth = observer.altaz(time, target).az * (1/u.deg) * (np.pi/180.0)

    # Some checks & info for labels.
    if not hasattr(target, 'name'):
        target_name = ''
    else:
        target_name = target.name
    style_kwargs.setdefault('label', target_name)

    # We only want to plot positions above the horizon.
    az_plot = None
    for alt in range(0, len(altitude)):
        if altitude[alt] > 91.0:
            if warn_below_horizon:
                msg = 'Target "{0}" is below the horizon at time: {1}'
                msg = msg.format(target_name if target_name else 'Unknown Name',
                                 time[alt])
                warnings.warn(msg, PlotBelowHorizonWarning)
        else:
            if az_plot is None:
                az_plot = np.array([azimuth[alt]])
            else:
                az_plot = np.append(az_plot, azimuth[alt])
    alt_plot = altitude[altitude <= 91.0]
    if az_plot is None:
        az_plot = []

    # More axes set-up.
    # Position of azimuth = 0 (data, not label).
    ax.set_theta_zero_location('N')

    # Direction of azimuth increase. Clockwise is -1
    if north_to_east_ccw is False:
        ax.set_theta_direction(-1)

    # Plot target coordinates.
    ax.scatter(az_plot, alt_plot, **style_kwargs)


    if annotation is not None:
        ax.annotate(str(annotation), xy=[az_plot[0].value, alt_plot[0].value])

    # Set radial limits.
    ax.set_rlim(1, 91)

    # Grid, ticks & labels.
    # May need to set ticks and labels AFTER plotting points.
    if grid is True:
        ax.grid(True, which='major')
    if grid is False:
        ax.grid(False)
    degree_sign = u'\N{DEGREE SIGN}'

    # For positively-increasing range (e.g., range(1, 90, 15)),
    # labels go from middle to outside.
    r_labels = [
        '90' + degree_sign,
        '',
        '60' + degree_sign,
        '',
        '30' + degree_sign,
        '',
        '0' + degree_sign + ' Alt.',
    ]

    theta_labels = []
    for chunk in range(0, 7):
        label_angle = (az_label_offset*(1/u.deg)) + (chunk*45.0)
        while label_angle >= 360.0:
            label_angle -= 360.0
        if chunk == 0:
            theta_labels.append('N ' + '\n' + str(label_angle) + degree_sign
                                + ' Az')
        elif chunk == 2:
            theta_labels.append('E' + '\n' + str(label_angle) + degree_sign)
        elif chunk == 4:
            theta_labels.append('S' + '\n' + str(label_angle) + degree_sign)
        elif chunk == 6:
            theta_labels.append('W' + '\n' + str(label_angle) + degree_sign)
        else:
            theta_labels.append(str(label_angle) + degree_sign)

    # Set ticks and labels.
    ax.set_rgrids(range(1, 106, 15), r_labels, angle=-45)
    ax.set_thetagrids(range(0, 360, 45), theta_labels)

    # Below commands don't seem to work for setting ticks/labels.
    # ax.rgrids(range(1, 91, 15), r_labels, angle=-45)
    # ax.thetagrids(range(0, 360, 45), theta_labels)

    # Redraw the figure for interactive sessions.
    ax.figure.canvas.draw()

    return ax

def plot_schedule_sky(schedule):
    """
    Plots when observations of targets are scheduled to occur superimposed
    upon plots of the altitude of the targets.

    Parameters
    ----------
    schedule : `~astroplan.Schedule`
        a schedule object output by a scheduler

    Returns
    -------
    ax :  `~matplotlib.axes.Axes`
        An ``Axes`` object with added airmass and schedule vs. time plot.
    """

    import matplotlib.pyplot as plt
    sorted_blocks = sorted(schedule.observing_blocks, key=lambda x: x.priority)
    targets = []
    targetsCalibration = []
    observation_nr = 1
    for block in sorted_blocks:
        if block.calibration:
            targetsCalibration.append([block.target, block.start_time, block.end_time, observation_nr])
            observation_nr = observation_nr + 1
        else:
            targets.append([block.target, block.start_time, block.end_time, observation_nr])
            observation_nr = observation_nr + 1

    color_idx = np.linspace(0, 1, len(targets))
    color_idx2 = np.linspace(0, 1, len(targetsCalibration))
    # lighter, bluer colors indicate higher priority
    targets = np.array(targets)
    targetsCalibration = np.array(targetsCalibration)
    for target, start_time, end_time, observation_nr, ci in zip(targets[:,0], targets[:,1], targets[:,2],
                                                                targets[:,3], color_idx):
        delta_t = end_time - start_time
        number_of_dots = (delta_t.sec / 60) / 1
        observe_time = start_time + delta_t * np.linspace(0, 1, number_of_dots)
        if "split" in target.name:
            target.name = str.replace(target.name, " split", "")
            plot_sky(target, schedule.observer, observe_time, style_kwargs=dict(color=plt.cm.jet(color_idx[list(color_idx).index(ci)-1])),
                     annotation=observation_nr)
        else:
            ax = plot_sky(target, schedule.observer, observe_time, style_kwargs=dict(color=plt.cm.jet(ci)),
                     annotation=observation_nr)

    for target, start_time, end_time, observation_nr, ci in zip(targetsCalibration[:,0], targetsCalibration[:,1], targetsCalibration[:,2],
                                                                targetsCalibration[:,3], color_idx2):
        delta_t = end_time - start_time
        number_of_dots = (delta_t.sec / 60) / 1
        observe_time = start_time + delta_t * np.linspace(0, 1, number_of_dots)
        ax = plot_sky(target, schedule.observer, observe_time, style_kwargs=dict(color=plt.cm.brg(ci), marker='x'),
                 annotation=observation_nr)

    return ax
    # TODO: make this output a `axes` object


@u.quantity_input(delta=u.hour)
def plot_sky_24hr(target, observer, time, delta=1*u.hour, ax=None,
                  style_kwargs=None, north_to_east_ccw=True, grid=True,
                  az_label_offset=0.0*u.deg, center_time_style_kwargs=None):
    """
    Plots target positions in the sky with respect to the observer's location
    over a twenty-four hour period centered on ``time``.

    Parameters
    ----------
    target : `~astroplan.FixedTarget`
        The celestial body of interest.

    observer: `~astroplan.Observer`
        The person, telescope, observatory, etc. doing the observing.

    time : `~astropy.time.Time`
        If pass in an `~astropy.time.Time` object with just one instance in
        time, whether it be a scalar or an array (e.g. ``Time('2000-1-1')``,
        ``Time(['2000-1-1'])``, ``[Time('2000-1-1')]``),
        `~astroplan.plots.plot_sky` will return plot at one instance in
        time.  If pass in an `~astropy.time.Time` object with multiple
        instances in time (e.g. ``Time(['2000-1-1', '2000-1-2'])``) will
        show positions plotted at the exact times specified.

    delta : `~astropy.units.Quantity` (optional)
        Interval between times plotted.

    ax : `~matplotlib.axes.Axes` or None, optional.
        The `~matplotlib.axes.Axes` object to be drawn on.
        If None, uses the current `~matplotlib.axes.Axes`.

    style_kwargs : dict or None, optional.
        A dictionary of keywords passed into `~matplotlib.pyplot.scatter`
        to set plotting styles.

    north_to_east_ccw : bool, optional.
        True by default, meaning that azimuth is shown increasing
        counter-clockwise (CCW), or with North at top, East at left, etc.
        To show azimuth increasing clockwise (CW), set to False.

    grid : bool, optional.
        True by default, meaning that grid is drawn.

    az_label_offset : ``~astropy.units.degree``, optional.
        DANGER: It is not recommended that you change the default behavior,
        as to do so makes it seem as if N/E/S/W are being decoupled from the
        definition of azimuth (North from az = 0 deg., East from az = 90 deg.,
        etc.).
        An offset for azimuth labels from the North label.  A positive
        offset will increase in the same direction as azimuth
        (see ``north_to_east_ccw`` option).

    center_time_style_kwargs : dict or `None` (optional)
        Dictionary of style keyword arguments to pass to
        `~matplotlib.pyplot.scatter` to set plotting style of the point at
        time ``time``.

    Returns
    -------
    An `~matplotlib.axes.Axes` object (ax) with a map of the sky.
    """

    time_range = np.arange(-12, 12, delta.to(u.hour).value)*u.hour + time

    ax = plot_sky(target, observer, time_range, ax=ax,
                  style_kwargs=style_kwargs,
                  north_to_east_ccw=north_to_east_ccw, grid=grid,
                  az_label_offset=az_label_offset,
                  warn_below_horizon=False)

    if center_time_style_kwargs is not None:
        ax = plot_sky(target, observer, time, ax=ax,
                      style_kwargs=center_time_style_kwargs,
                      north_to_east_ccw=north_to_east_ccw, grid=grid,
                      az_label_offset=az_label_offset,
                      warn_below_horizon=False)
    return ax
