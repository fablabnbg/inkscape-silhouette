# (c) 2013 jw@suse.de
#
# cut strategy algorithms for a Graphtec Silhouette Cameo plotter.
#
# In order to support operation without a cutting mat, a strategic
# rearrangement of cuts is helpful.
# e.g. 
#  * With a knive, sharp turns are to be avoided. They easily rupture the paper.
#  * With some pens, the paper may become unstable if soaked with too much ink.
#    Avoid backwards or inwards strokes.
#  * In general, cut paper is fragile. Do not move backwards and cut, where other cuts 
#    were placed. We require (strict) monotonic progression along the sheet with 
#    minimal backwards movement.
#
# 2013-05-21, jw, V0.1  -- initial draught.

import copy

presets = {
  'default': {
    'corner_detect_min_jump': 2,
    'corner_detect_dup_epsilon': 0.1,
    'monotone_allow_back_travel': 10,
    'tool_pen': False
    },
  'nop': {
    'load_dedup': False
  }
}

class MatFree:
  def __init__(self, preset="default", pen=False):
    """This initializer defines settings for the apply() method.
    """
    self.load_dedup = True

    self.preset(preset)

    self.tool_pen = pen
    self.points = []
    self.points_dict = {}
    self.paths = []

  def list_presets(self):
    return copy.deepcopy(presets)

  def preset(self, pre_name):
    if not pre_name in presets:
      raise ValueError(pre_name+': no such preset. Try "'+'", "'.join(presets.keys())+'"')
    pre = presets[pre_name]
    for k in pre.keys():
      self.__dict__[k] = pre[k]

  def export(self):
    """reverse of load(), except that the nodes are tuples of
       [x, y, { ... attrs } ]
       Most notable attributes:
       - 'sharp', it is present on nodes where the path turns by more 
          than 90 deg.
    """
    cut = []
    for path in self.paths:
      new_path = []
      for pt in path:
        new_path.append(self.points[pt])
      cut.append(new_path)
    return cut

  def load(self, cut):
    """load a sequence of paths. 
       Nodes are expected as tuples (x, y).
       We extract points into a seperate list, with attributes as a third 
       element to the tuple. Typical attributes to be added by other methods
       are refcount (if commented in), sharp (by method mark_sharp_turns(), 
       ...
    """
    class XY_a(tuple):
      def __init__(self,t):
        tuple.__init__(t)
        self.attr = {}

    for path in cut:
      new_path = []
      for point in path:
        k = str(point[0])+','+str(point[1])
        if k in self.points_dict:
          idx = self.points_dict[k]
        else:
          idx = len(self.points)
          self.points.append(XY_a(point))
          self.points_dict[k] = idx
        if len(new_path) == 0 or new_path[-1] != idx or self.load_dedup == False:
          # weed out repeated points
          new_path.append(idx)
          # self.points[idx].attr['refcount'] += 1
      self.paths.append(new_path)

  def sharp_turn(s, A,B,C):
    """Given the path from A to B to C as two line segments.
       Return true, if the corner at B is more than +/- 90 degree.

       Algorithm:
       For the segment A-B, we construct the normal B-D. 
       The we test, if points A and C lie on the same side of the line(!) B-D.
       If so, it is a sharp turn.
    """
    dx = B[0]-A[0]
    dy = B[1]-A[1]
    D = (B[0]-dy, B[1]+dx)        # BD is now the normal to AB

    ## From http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    def ccw_t(A,B,C):
      """same as ccw, but expecting tuples"""
      return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

    return ccw_t(A,B,D) == ccw_t(C,B,D)

  def mark_sharp_turns(s):
    """walk through all paths, and add an attribute { 'sharp': True } to the
       points that respond true with the sharp_turn() method.
    """
    min_jump_sq = s.corner_detect_min_jump * s.corner_detect_min_jump
    dup_eps_sq  = s.corner_detect_dup_epsilon * s.corner_detect_dup_epsilon
    def dist_sq(A,B):
      return (B[0]-A[0])*(B[0]-A[0]) + (B[1]-A[1])*(B[1]-A[1])

    idx = 1
    A = None
    B = None 
    for path in s.paths:
      if B is not None and len(path) and dist_sq(B,s. points[path[0]]) > min_jump_sq:
        # disconnect the path, if we jump more than 2mm
        A = None
        B = None
        
      for iC in path:
        C = s.points[iC]
        if B is not None and dist_sq(B,C) < dup_eps_sq:
          # less than 0.1 mm distance: ignore the point as a duplicate.
          continue

        if A is not None and s.sharp_turn(A,B,C):
          B.attr['sharp'] = True

        A = B
        B = C
      #
    #

 
  def apply(self, cut):
    self.load(cut)
    self.mark_sharp_turns()
    return self.export()

