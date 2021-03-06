import logging
import os
from datetime import datetime

import h5py
from PyQt5 import QtCore, QtWidgets, QtGui

from artiq.protocols import pyon

logger = logging.getLogger(__name__)


def open_h5(info):
    if not (info.isFile() and info.isReadable() and
            info.suffix() == "h5"):
        return
    try:
        return h5py.File(info.filePath(), "r")
    except:
        logger.warning("unable to read HDF5 file %s", info.filePath(),
                       exc_info=True)


class ThumbnailIconProvider(QtWidgets.QFileIconProvider):
    def icon(self, info):
        icon = self.hdf5_thumbnail(info)
        if icon is None:
            icon = QtWidgets.QFileIconProvider.icon(self, info)
        return icon

    def hdf5_thumbnail(self, info):
        f = open_h5(info)
        if not f:
            return
        with f:
            try:
                t = f["datasets/thumbnail"]
            except KeyError:
                return
            try:
                img = QtGui.QImage.fromData(t.value)
            except:
                logger.warning("unable to read thumbnail from %s",
                               info.filePath(), exc_info=True)
                return
            pix = QtGui.QPixmap.fromImage(img)
            return QtGui.QIcon(pix)


class DirsOnlyProxy(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, row, parent):
        idx = self.sourceModel().index(row, 0, parent)
        if not self.sourceModel().fileInfo(idx).isDir():
            return False
        return QtCore.QSortFilterProxyModel.filterAcceptsRow(self, row, parent)


class ZoomIconView(QtWidgets.QListView):
    zoom_step = 2**.25
    aspect = 2/3
    default_size = 25
    min_size = 10
    max_size = 1000

    def __init__(self):
        QtWidgets.QListView.__init__(self)
        self._char_width = QtGui.QFontMetrics(self.font()).averageCharWidth()
        self.setViewMode(self.IconMode)
        w = self._char_width*self.default_size
        self.setIconSize(QtCore.QSize(w, w*self.aspect))
        self.setFlow(self.LeftToRight)
        self.setResizeMode(self.Adjust)
        self.setWrapping(True)

    def wheelEvent(self, ev):
        if ev.modifiers() & QtCore.Qt.ControlModifier:
            a = self._char_width*self.min_size
            b = self._char_width*self.max_size
            w = self.iconSize().width()*self.zoom_step**(
                ev.angleDelta().y()/120.)
            if a <= w <= b:
                self.setIconSize(QtCore.QSize(w, w*self.aspect))
        else:
            QtWidgets.QListView.wheelEvent(self, ev)


class Hdf5FileSystemModel(QtWidgets.QFileSystemModel):
    def __init__(self):
        QtWidgets.QFileSystemModel.__init__(self)
        self.setFilter(QtCore.QDir.Drives | QtCore.QDir.NoDotAndDotDot |
                       QtCore.QDir.AllDirs | QtCore.QDir.Files)
        self.setNameFilterDisables(False)
        self.setIconProvider(ThumbnailIconProvider())

    def data(self, idx, role):
        if role == QtCore.Qt.ToolTipRole:
            info = self.fileInfo(idx)
            h5 = open_h5(info)
            if h5 is not None:
                try:
                    expid = pyon.decode(h5["expid"].value)
                    start_time = datetime.fromtimestamp(h5["start_time"].value)
                    v = ("artiq_version: {}\nrepo_rev: {}\nfile: {}\n"
                         "class_name: {}\nrid: {}\nstart_time: {}").format(
                             h5["artiq_version"].value, expid["repo_rev"],
                             expid["file"], expid["class_name"],
                             h5["rid"].value, start_time)
                    return v
                except:
                    logger.warning("unable to read metadata from %s",
                                   info.filePath(), exc_info=True)
        return QtWidgets.QFileSystemModel.data(self, idx, role)


class FilesDock(QtWidgets.QDockWidget):
    def __init__(self, datasets, browse_root="", select=None):
        QtWidgets.QDockWidget.__init__(self, "Files")
        self.setObjectName("Files")
        self.setFeatures(self.DockWidgetMovable | self.DockWidgetFloatable)

        self.splitter = QtWidgets.QSplitter()
        self.setWidget(self.splitter)

        self.datasets = datasets

        self.model = Hdf5FileSystemModel()

        self.rt = QtWidgets.QTreeView()
        rt_model = DirsOnlyProxy()
        rt_model.setDynamicSortFilter(True)
        rt_model.setSourceModel(self.model)
        self.rt.setModel(rt_model)
        self.model.directoryLoaded.connect(
            lambda: self.rt.resizeColumnToContents(0))
        self.rt.setAnimated(False)
        if browse_root != "":
            browse_root = os.path.abspath(browse_root)
        self.rt.setRootIndex(rt_model.mapFromSource(
            self.model.setRootPath(browse_root)))
        self.rt.setHeaderHidden(True)
        self.rt.setSelectionBehavior(self.rt.SelectRows)
        self.rt.setSelectionMode(self.rt.SingleSelection)
        self.rt.selectionModel().currentChanged.connect(
            self.tree_current_changed)
        self.rt.setRootIsDecorated(False)
        for i in range(1, 4):
            self.rt.hideColumn(i)
        self.splitter.addWidget(self.rt)

        self.rl = ZoomIconView()
        self.rl.setModel(self.model)
        self.rl.selectionModel().currentChanged.connect(
            self.list_current_changed)
        self.rl.activated.connect(self.list_activated)
        self.splitter.addWidget(self.rl)

        self.restore_selected = select is None
        if select is not None:
            f = os.path.abspath(select)
            if os.path.isdir(f):
                self.select_dir(f)
            else:
                self.select_file(f)

    def tree_current_changed(self, current, previous):
        idx = self.rt.model().mapToSource(current)
        self.rl.setRootIndex(idx)

    def list_current_changed(self, current, previous):
        info = self.model.fileInfo(current)
        f = open_h5(info)
        if not f:
            return
        logger.info("loading datasets from %s", info.filePath())
        with f:
            if "datasets" not in f:
                return
            rd = {k: (True, v.value) for k, v in f["datasets"].items()}
            self.datasets.init(rd)

    def list_activated(self, idx):
        if not self.model.fileInfo(idx).isDir():
            return
        self.rl.setRootIndex(idx)
        idx = self.rt.model().mapFromSource(idx)
        self.rt.expand(idx)
        self.rt.setCurrentIndex(idx)

    def select_dir(self, path):
        if not os.path.exists(path):
            return
        idx = self.model.index(path)
        if not idx.isValid():
            return
        self.rl.setRootIndex(idx)

        # ugly, see Spyder: late indexing, late scroll
        def scroll_when_loaded(p):
            if p != path:
                return
            self.model.directoryLoaded.disconnect(scroll_when_loaded)
            QtCore.QTimer.singleShot(
                100,
                lambda: self.rt.scrollTo(
                    self.rt.model().mapFromSource(self.model.index(path)),
                    self.rt.PositionAtCenter)
            )
        self.model.directoryLoaded.connect(scroll_when_loaded)
        idx = self.rt.model().mapFromSource(idx)
        self.rt.expand(idx)
        self.rt.setCurrentIndex(idx)

    def select_file(self, path):
        if not os.path.exists(path):
            return
        self.select_dir(os.path.dirname(path))
        idx = self.model.index(path)
        if not idx.isValid():
            return
        self.rl.setCurrentIndex(idx)

    def save_state(self):
        return {
            "dir": self.model.filePath(self.rl.rootIndex()),
            "file": self.model.filePath(self.rl.currentIndex()),
            "splitter": bytes(self.splitter.saveState()),
        }

    def restore_state(self, state):
        if self.restore_selected:
            self.select_dir(state["dir"])
            self.select_file(state["file"])
        self.splitter.restoreState(QtCore.QByteArray(state["splitter"]))
