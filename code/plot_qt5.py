from PyQt5.QtWidgets import QSizePolicy, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from astroplan.plots import  plot_schedule_altitude, plot_schedule_sky


class Plot(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)

        FigureCanvas.__init__(self, self.fig)
        self.parent = parent
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


    def add_subplot(self,ax):
        self.fig.add_subplot(ax)

    def plot_sky_schedule(self, schedule):
        plot_schedule_sky(schedule, fig=self.fig)
        handles, labels = self.fig.axes[0].get_legend_handles_labels()
        handle_list, label_list = [], []
        for handle, label in zip(handles, labels):
            if label not in label_list and handle not in handle_list:
                handle_list.append(handle)
                label_list.append(label)
        self.fig.axes[0].legend(handle_list, label_list, loc="center left", bbox_to_anchor=(1.15, 0.5))
        self.fig.tight_layout()
        self.draw()

    def plot_altitude_schedule(self, schedule):
        plot_schedule_altitude(schedule, fig=self.fig)
        handles, labels = self.fig.axes[0].get_legend_handles_labels()
        handle_list, label_list = [], []
        for handle, label in zip(handles, labels):
            if label not in label_list and handle not in handle_list:
                handle_list.append(handle)
                label_list.append(label)

        self.fig.axes[0].legend(handle_list, label_list, loc="center left", bbox_to_anchor=(1, 0.5))

        self.fig.tight_layout()
        self.draw()