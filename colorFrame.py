from reportlab.lib.colors import toColor
from reportlab.platypus import Frame

# ref https://gist.github.com/styrmis/5317292

class ColorFrame(Frame):
    """ Extends the reportlab Frame with the ability to draw a background color. """

    def __init__(self, x1, y1, width,height, leftPadding=6, bottomPadding=6,
            rightPadding=6, topPadding=6, id=None, showBoundary=0,
            overlapAttachedSpace=None,_debug=None,background=None):

        Frame.__init__(self, x1, y1, width, height, leftPadding,
            bottomPadding, rightPadding, topPadding, id, showBoundary,
            overlapAttachedSpace, _debug)

        self.background = background

    def drawBackground(self, canv):
        color = toColor(self.background)

        canv.saveState()
        canv.setFillColor(color)
        canv.rect(
            self._x1, self._y1, self._x2 - self._x1, self._y2 - self._y1,
            stroke=0, fill=1
        )
        canv.restoreState()

    def addFromList(self, drawlist, canv):
        if self.background:
            self.drawBackground(canv)
        Frame.addFromList(self, drawlist, canv)