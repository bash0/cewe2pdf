"""Managed lifetime of one CEWE album-to-PDF conversion."""

# A session coordinates the whole conversion and therefore naturally carries
# more construction data than a small rendering helper.  Keeping this data in
# one named object makes the ownership and cleanup boundary explicit.
# pylint: disable=too-many-arguments,too-many-instance-attributes

from functools import partial
import gc
import logging
import os
import sys

import reportlab.lib.pagesizes
from reportlab.pdfgen import canvas

from albumIndex import AlbumIndex
from ceweInfo import AlbumInfo, CeweInfo, ProductStyle
from conversionSetup import prepareConversion
from conversionState import ConversionState
from extraLoggers import ConversionMessageCounters, configlogger, mustsee
from pageNumbering import PageNumberingInfo
from pages import processPages
from renderContext import RenderContext
from versionInfo import logVersionInformation


class AlbumConversionSession:
    """Own one conversion's resources from validation through cleanup.

    Use this as a context manager.  :meth:`render` creates and saves the PDF;
    leaving the context releases temporary images and unpacked MCFX data even
    when the conversion exits early.
    """

    def __init__(self, albumName, keepDoublePages, pageNumbers, mcfxTmpDir,
                 appDataDir, outputFileName, mcfToReportlab, imageQuality,
                 pilAntialias, automaticWindows=False):
        self.album_name = albumName
        self.keep_double_pages = keepDoublePages
        self.page_numbers = pageNumbers
        self.mcfx_tmp_dir = mcfxTmpDir
        self.app_data_dir = appDataDir
        self.output_file_name = outputFileName
        self.mcf_to_reportlab = mcfToReportlab
        self.image_quality = imageQuality
        self.pil_antialias = pilAntialias
        self.automatic_windows = automaticWindows
        self.automatic_log_file_name = None
        self.automatic_log_handler = None
        self.automatic_loggers = []

        self.state = ConversionState()
        self.state.message_counters = ConversionMessageCounters()
        self.setup = None

    def __enter__(self):
        self._startAutomaticLog()
        logVersionInformation()
        if self.output_file_name is None:
            self.output_file_name = CeweInfo.getOutputFileName(self.album_name)
        CeweInfo.ensureAcceptableOutputFile(self.output_file_name)
        return self

    def __exit__(self, exceptionType, exceptionValue, traceback):
        """Report diagnostics and release files owned by this session."""
        objectsCollected = gc.collect()
        logging.info(f'GC collected objects : {objectsCollected}')

        messageCounters = self.state.message_counters
        if messageCounters is not None:
            messageCounters.print_summary()
            if self.setup is not None:
                messageCounters.verify(self.setup.default_config_section)
            messageCounters.close()

        unpackedFolder = self.setup.unpacked_folder if self.setup is not None else None
        try:
            cleanUpTemporaryFiles(self.state.temporary_files, unpackedFolder)
        finally:
            self._closeAutomaticLog()
        return False

    def _startAutomaticLog(self):
        """Write Explorer-run diagnostics beside the album, if possible."""
        if not self.automatic_windows:
            return
        self.automatic_log_file_name = self.album_name + '.log'
        try:
            self.automatic_log_handler = logging.FileHandler(
                self.automatic_log_file_name, mode='w', encoding='utf-8')
        except OSError as exception:
            logging.warning(
                f'Could not create automatic conversion log '
                f'{self.automatic_log_file_name}: {exception}')
            self.automatic_log_file_name = None
            return

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S')
        self.automatic_log_handler.setFormatter(formatter)

        # The normal YAML configuration deliberately prevents the specialised
        # configuration and must-see loggers propagating to root.  Attach the
        # file handler to those loggers as well.  The frozen EXE normally has
        # no YAML file, in which case they *do* propagate: root already records
        # them, and adding the same handler again would duplicate every line.
        rootLogger = logging.getLogger()
        self.automatic_loggers = [rootLogger]
        for logger in (configlogger, mustsee):
            if not logger.propagate:
                self.automatic_loggers.append(logger)
        for logger in self.automatic_loggers:
            logger.addHandler(self.automatic_log_handler)
        logging.info(f'Writing automatic conversion log to: {self.automatic_log_file_name}')

    def _closeAutomaticLog(self):
        """Detach and close the optional Explorer-run log file."""
        if self.automatic_log_handler is None:
            return
        for logger in self.automatic_loggers:
            logger.removeHandler(self.automatic_log_handler)
        self.automatic_log_handler.close()
        self.automatic_log_handler = None
        self.automatic_loggers = []

    def render(self, processElements):  # noqa: C901
        """Prepare the album, render its pages, and save its primary PDF."""
        self.setup = prepareConversion(
            self.album_name, self.mcfx_tmp_dir, self.app_data_dir, self.state,
            self.automatic_windows)
        albumIndex = self._createAlbumIndex()

        articleConfigElement = self.setup.fotobook.find('articleConfig')
        if articleConfigElement is None:
            logging.error(
                f'{self.album_name} is an old version. Open it in the album editor '
                'and save before retrying the pdf conversion. Exiting.')
            sys.exit(1)

        pageSize, productStyle = self._getProductDetails()
        pageCount = self._getPageCount(articleConfigElement, productStyle)
        imageFolder = self.setup.fotobook.get('imagedir')
        renderContext = RenderContext(
            self.mcf_to_reportlab, self.setup.image_resolution, self.image_quality,
            self.setup.background_resolution, self.pil_antialias,
            self.setup.default_config_section, self.setup.clipart_files,
            self.setup.clipart_paths, self.setup.passepartout_folders,
            self.setup.line_scales)

        pdf = canvas.Canvas(self.output_file_name, pagesize=pageSize)
        pdf.setTitle(self.setup.album_title)
        pageNumberingInfo = self._createPageNumberingInfo(pdf)
        processElementsForAlbum = partial(
            processElements, state=self.state, albumIndex=albumIndex)

        processPages(
            self.setup.fotobook, self.setup.mcf_base_folder, imageFolder,
            productStyle, pdf, pageCount, self.page_numbers,
            self.setup.available_fonts, self.setup.background_locations, self.state,
            renderContext, pageNumberingInfo, processElementsForAlbum)

        try:
            pdf.save()
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logging.error(f'Could not save the output file: {str(exception)}')

        self._createIndexOutput(albumIndex, pageSize)
        if productStyle == ProductStyle.MemoryCard:
            print()
            print('Use Adobe Acrobat to print the memory cards. Set custom pages per sheet, 4 wide x 6 down')
            print(' and print two copies!')
        return True

    def _createAlbumIndex(self):
        if self.setup.configuration is None:
            return AlbumIndex(None)
        try:
            return AlbumIndex(self.setup.configuration['INDEX'])
        except KeyError:
            return AlbumIndex(None)

    def _getProductDetails(self):
        pageSize = reportlab.lib.pagesizes.A4
        productStyle = ProductStyle.AlbumSingleSide
        productName = self.setup.fotobook.get('productname')
        if productName in AlbumInfo.formats:
            pageSize = AlbumInfo.formats[productName]
        if productName in AlbumInfo.styles:
            productStyle = AlbumInfo.styles[productName]
        if self.keep_double_pages:
            if productStyle == ProductStyle.AlbumSingleSide:
                productStyle = ProductStyle.AlbumDoubleSide
            elif productStyle == ProductStyle.MemoryCard:
                logging.warning('keepdoublepages option is irrelevant and ignored for a memory card product')
        return pageSize, productStyle

    @staticmethod
    def _getPageCount(articleConfigElement, productStyle):
        if AlbumInfo.isAlbumProduct(productStyle):
            # Albums record only usable inside pages in normalpages. The two
            # outer covers make the corresponding single-sided PDF page count.
            return int(articleConfigElement.get('normalpages')) + 2
        # Photo Pairs records each card as a real MCF page; it has neither
        # covers nor two-page bundles, so do not apply the album +2 rule.
        return int(articleConfigElement.get('totalpages'))

    def _createPageNumberingInfo(self, pdf):
        pageNumberElement = self.setup.fotobook.find('pagenumbering')
        if pageNumberElement is None or int(pageNumberElement.get('position')) == 0:
            return None
        return PageNumberingInfo(
            pageNumberElement, pdf, self.setup.available_fonts, self.state)

    def _createIndexOutput(self, albumIndex, pageSize):
        if not albumIndex.indexing:
            return
        indexPdfFileName = albumIndex.SaveIndexPdf(
            self.output_file_name, self.setup.album_title, pageSize)
        indexPngFileName = albumIndex.SaveIndexPng(indexPdfFileName)
        albumIndex.MergeAlbumAndIndexPng(self.output_file_name, indexPngFileName)
        if albumIndex.deleteIndexPdf and os.path.exists(indexPdfFileName):
            os.remove(indexPdfFileName)
        if albumIndex.deleteIndexPng and os.path.exists(indexPngFileName):
            os.remove(indexPngFileName)


def cleanUpTemporaryFiles(fileList, unpackedFolder):
    """Remove temporary images and unpacked MCFX data owned by a session."""
    for temporaryFileName in fileList:
        if os.path.exists(temporaryFileName):
            os.remove(temporaryFileName)
    if unpackedFolder is not None:
        unpackedFolder.cleanup()
