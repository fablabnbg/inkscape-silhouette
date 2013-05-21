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
}

class MatFree:
  def __init__(self, preset="default", pen=False):
    """This initializer defines settings for the apply() method.
    """
    self.preset(preset)
    self.tool_pen = pen
    self.points = []
    self.points_dict = {}
    self.points_last_idx = 0
    self.paths = []

  def list_presets(self):
    return copy.deepcopy(presets)

  def preset(self, pre_name):
    pre = presets[pre_name]
    for k in pre.keys():
      self.__dict__[k] = pre[k]

  def load(self, cut):
    """load a sequence of paths, extracting points into a
       seperate list, with attributes like refcount, etc...
    """
    for path in cut:
      new_path = []
      for point in path:
        k = str(point[0])+','+str(point[1])
        if k in self.points_dict:
          idx = self.points_dict[k]
        else:
          idx = len(self.points)
          self.points.append([point[0], point[1], { 'refcount': 0 }])
          self.points_dict[k] = idx
        if len(new_path) == 0 or new_path[-1] != idx:
          # weed out repeated points
          new_path.append(idx)
          self.points[idx][2]['refcount'] += 1
      self.paths.append(new_path)
    
  def apply(self, cut):
    self.load(cut)
    print self.paths, self.points

