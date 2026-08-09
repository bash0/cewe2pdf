from reportlab.lib.colors import toColor
from reportlab.platypus import Frame

# ref https://gist.github.com/styrmis/5317292

# pylint complains about things which are decided by the base Frame class, so...
# pylint: disable=too-many-arguments,redefined-builtin,too-many-function-args

class ColorFrame(Frame):
    """A Frame which draws CEWE's text-area background with its opacity."""

    def __init__(self, x1, y1, width,height, leftPadding=6, bottomPadding=6,
            rightPadding=6, topPadding=6, id=None, showBoundary=0,
            overlapAttachedSpace=None,_debug=None,background=None, alpha=1.0):

        Frame.__init__(self, x1, y1, width, height, leftPadding,
            bottomPadding, rightPadding, topPadding, id, showBoundary,
            overlapAttachedSpace, _debug)

        self.background = background
        self.alpha = alpha

    def drawBackground(self, canv):
        color = toColor(self.background)

        canv.saveState()
        # ``setFillColor`` otherwise takes alpha from the colour object,
        # which is normally 1.0 and would override a surrounding graphics
        # state's transparency.  Supply CEWE's decoration alpha explicitly.
        canv.setFillColor(color, alpha=self.alpha)
        canv.rect(
            self._x1, self._y1, self._x2 - self._x1, self._y2 - self._y1,
            stroke=0, fill=1
        )
        canv.restoreState()

    def addFromList(self, drawlist, canv):
        if self.background:
            self.drawBackground(canv)
        Frame.addFromList(self, drawlist, canv)
