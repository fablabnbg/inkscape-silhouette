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
# 2013-05-23, jw, V0.2  -- dedup, subdivide, two options for sharp turn detectors added.
#                          draft for scan_barrier() added.
# 2013-05-25, jw, V0.3  -- corner_detect.py now jumps when not cutting.
#                          Strategy.py: new code: mark_segment_done(), todo_append_or_extend().
#                          completed process_barrier(), tested, debugged, verbose level reduced.
#                          The current slicing and sharp corner strategy appears useful.
# 2013-05-26, jw, V1.0  -- adopted version number from inkscape_silhouette package.
#                          improved path extension logic in todo_append_or_extend(), 
#                          much better, but still not perfect.
#                          Verbose printf's to stderr, so that inkscape survives.  
# 2013-05-26, jw, V1.1  -- path_overshoot() added, this improves quality 
#                          and the paper now comes apart by itself.

import copy
import math
import sys      # only for debug printing.

presets = {
  'default': {
    'pyramid_algorithm': False,
    'corner_detect_min_jump': 2,
    'corner_detect_dup_epsilon': 0.1,
    'monotone_allow_back_travel': 10.0,
    'barrier_increment': 10.0,
    'overshoot': 0.2,     # works well with 80g paper
    'tool_pen': False,
    'verbose': 1
    },
  'pyramid': {
    'pyramid_algorithm': True,
    'monotone_allow_back_travel': 10.0,
    'barrier_increment': 10.0,
    'overshoot': 0.2,     # works well with 80g paper
    'tool_pen': False,
    'do_slicing': False,
    'verbose': 1
    },
  'nop': {
    'do_dedup': False,
    'do_subdivide': False,
    'do_slicing': False,
    'overshoot': 0,
    'tool_pen': False,
    'verbose': 2
  }
}

class XY_a(tuple):
  def __init__(self,t):
    tuple.__init__(t)
    self.attr = {}

class MatFree:
  def __init__(self, preset="default", scale=1.0, pen=None):
    """This initializer defines settings for the apply() method.
       A scale factor is applied to convert input data units to mm.
       This is needed, as the length units used in presets are mm.
    """
    self.verbose  = 0
    self.do_dedup = True
    self.do_subdivide = True
    self.do_slicing = True
    self.tool_pen = False
    self.barrier_increment = 3.0
    self.monotone_allow_back_travel = 3.0
    self.input_scale = scale

    self.preset(preset)

    if pen is not None:
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

  def pt2idx(self, x,y):
    """all points have an index, if the index differs, the point 
       is at a different locations. All points also have attributes
       stored with in the point object itself. Points that appear for the second
       time receive an attribute 'dup':1, which is incremented on further reoccurences.
    """

    k = str(x)+','+str(y)
    if k in self.points_dict:
      idx = self.points_dict[k]
      if self.verbose:
        print >>sys.stderr, "%d found as dup" % idx
      if 'dup' in self.points[idx].attr:
        self.points[idx].attr['dup'] += 1
      else:
        self.points[idx].attr['dup'] = 1
    else:
      idx = len(self.points)
      self.points.append(XY_a((x,y)))
      self.points_dict[k] = idx
      self.points[idx].attr['id'] = idx
    return idx

  def load(self, cut):
    """load a sequence of paths. 
       Nodes are expected as tuples (x, y).
       We extract points into a seperate list, with attributes as a third 
       element to the tuple. Typical attributes to be added by other methods
       are refcount (if commented in), sharp (by method mark_sharp_segs(), 
       ...
    """

    for path in cut:
      new_path = []
      for point in path:
        idx = self.pt2idx(self.input_scale * point[0], self.input_scale * point[1])

        if len(new_path) == 0 or new_path[-1] != idx or self.do_dedup == False:
          # weed out repeated points
          new_path.append(idx)
          # self.points[idx].attr['refcount'] += 1
      self.paths.append(new_path)


  def dist_sq(s, A,B):
    return (B[0]-A[0])*(B[0]-A[0]) + (B[1]-A[1])*(B[1]-A[1])


  def link_points(s):
    """add segments (back and forth) between connected points.
    """
    for path in s.paths:
      A = None
      for pt in path:
        if A is not None:
          if 'seg' in s.points[A].attr:
            s.points[A].attr['seg'].append(pt)
          else:
            s.points[A].attr['seg'] = [ pt ]

          if 'seg' in s.points[pt].attr:
            s.points[pt].attr['seg'].append(A)
          else:
            s.points[pt].attr['seg'] = [ A ]
        A = pt


  def subdivide_segments(s, maxlen):
    """Insert addtional points along the paths, so that
       no segment is longer than maxlen
    """
    if s.do_subdivide == False:
      return
    maxlen_sq = maxlen * maxlen
    for path_idx in range(len(s.paths)):
      path = s.paths[path_idx]
      new_path = []
      for pt in path:
        if len(new_path):
          A = new_path[-1]
          dist_sq = s.dist_sq(s.points[A], s.points[pt])
          if dist_sq > maxlen_sq:
            dist = math.sqrt(dist_sq)
            nsub = int(dist/maxlen)
            seg_len = dist/float(nsub+1)
            dx = (s.points[pt][0] - s.points[A][0])/float(nsub+1)
            dy = (s.points[pt][1] - s.points[A][1])/float(nsub+1)
            if s.verbose > 1:
              print >>sys.stderr, "pt%d -- pt%d: need nsub=%d, seg_len=%g" % (A,pt,nsub,seg_len)
              print >>sys.stderr, "dxdy", dx, dy, "to", (s.points[pt][0], s.points[pt][1]), "from", (s.points[A][0],s.points[A][1])
            for subdiv in range(nsub):
              sub_pt =s.pt2idx(s.points[A][0]+dx+subdiv*dx, 
                               s.points[A][1]+dy+subdiv*dy)
              new_path.append(sub_pt)
              s.points[sub_pt].attr['sub'] = True
              if s.verbose > 1:
                print >>sys.stderr, "   sub", (s.points[sub_pt][0], s.points[sub_pt][1])
        new_path.append(pt)
      s.paths[path_idx] = new_path


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



  def mark_sharp_segs(s):
    """walk all the points and check their segments attributes, 
       to see if there are connections that form a sharp angle.
       This needs link_points() to be called earlier.
       One sharp turn per point is enough to make us careful.
       We don't track which pair of turns actually is a sharp turn, if there
       are more than two segs. Those cases are rare enough to allow the inefficiency.

       TODO: can honor corner_detect_min_jump? Even if so, what should we do in the case
       where multiple points are so close together that the paper is likely to tear?
    """
    for pt in s.points:
      if 'sharp' in pt.attr:
        ## shortcut existing flags. One sharp turn per point is enough to make us careful.
        ## we don't want to track which pair of turns actually is a sharp turn, if there
        ## are more than two segments per point. Those cases are rare enough 
        ## to handle them inefficiently.
        continue
      if 'seg' in pt.attr:
        ll = len(pt.attr['seg'])
        if ll > 4:
          ## you cannot attach 5 lines to a point without creating one sharp angle.
          pt.attr['sharp'] = True
          continue
        ## look at each pair of segments once, check their angle.
        for l1 in range(ll):
          A = s.points[pt.attr['seg'][l1]]
          for l2 in range(l1+1, ll):
            B = s.points[pt.attr['seg'][l2]]
            if s.sharp_turn(A,pt,B):
              pt.attr['sharp'] = True
          if 'sharp' in pt.attr:
            break
      else:
        print >>sys.stderr, "warning: no segments in point %d. Run link_points() before mark_sharp_segs()" % (pt.attr['id'])



  def mark_sharp_paths(s):
    """walk through all paths, and add an attribute { 'sharp': True } to the
       points that respond true with the sharp_turn() method.

       Caution: mark_sharp_paths() walks in the original order, which may be irrelevant 
       after reordering.

       This marks sharp turns only if paths are not intersecting or touching back. 
       Assuming segment counts <= 2. Use mark_sharp_segs() for the general case.
       Downside: mark_sharp_segs() does not honor corner_detect_min_jump.
    """
    min_jump_sq = s.corner_detect_min_jump * s.corner_detect_min_jump
    dup_eps_sq  = s.corner_detect_dup_epsilon * s.corner_detect_dup_epsilon

    idx = 1
    A = None
    B = None 
    for path in s.paths:
      if B is not None and len(path) and s.dist_sq(B,s. points[path[0]]) > min_jump_sq:
        # disconnect the path, if we jump more than 2mm
        A = None
        B = None
        
      for iC in path:
        C = s.points[iC]
        if B is not None and s.dist_sq(B,C) < dup_eps_sq:
          # less than 0.1 mm distance: ignore the point as a duplicate.
          continue

        if A is not None and s.sharp_turn(A,B,C):
          B.attr['sharp'] = True

        A = B
        B = C
      #
    #


  def todo_append_or_extend(s, seg):
    """adds a segment to the todo list. The segment extends the previous segment, 
       if the last point if the previous segment is identical with our first 
       point.  If the segment has no sharp points, we double check if extend 
       would work with the inverted segment. Optionally also flipping around 
       the previous segment if it would help. (FIXME: this possibility should 
       be detected earlier)
       Otherwise, the segment is appended as a new path.
    """
    if not 'todo' in s.__dict__: s.todo = []
    if len(s.todo) and s.verbose > 1:
      print >>sys.stderr, "todo_append...", s.todo[-1][-1], seg
    if (len(s.todo) > 0 and len(s.todo[-1]) >= 2 and 
         'sharp' not in s.todo[-1][0] and
         'sharp' not in s.todo[-1][-1]):
      # we could flip around the previous segment, if needed:
      if (s.todo[-1][0].attr['id'] == seg[0].attr['id'] or
          s.todo[-1][0].attr['id'] == seg[-1].attr['id']):
        # yes, flipping the previous segment, will help below. do it.
        s.todo[-1] = list(reversed(s.todo[-1]))
        if s.verbose:
          print >>sys.stderr, "late flip ", len(s.todo), len(s.todo[-1])
      #
    #

    if len(s.todo) > 0 and s.todo[-1][-1].attr['id'] == seg[0].attr['id']:
      s.todo[-1].extend(seg[1:])
      if s.verbose > 1:
        print >>sys.stderr, "... extend"
    elif len(s.todo) > 0 and s.todo[-1][-1].attr['id'] == seg[-1].attr['id']:
      ## check if we can turn it around
      if 'sharp' not in s.todo[-1][-1].attr and 'sharp' not in seg[-1].attr and 'sharp' not in seg[0].attr:
        s.todo[-1].extend(list(reversed(seg))[1:])
        if s.verbose > 1:
          print >>sys.stderr, "... extend reveresed"
      else:
        s.todo.append(seg)
        if s.verbose > 1:
          print >>sys.stderr, "... append"
      #
    else:
      s.todo.append(seg)
      if s.verbose > 1:
        print >>sys.stderr, "... append"
    #


  def mark_segment_done(s, A,B):
    """process_barrier ignores points and segments that have already been done.
       We call process_barrier() repeatedly, but we want each segment only once.
       Also, a point with a sharp turn can be the start of a segment only once. 
       All its other segments need to be drawn towards such a point.
       mark_segment_done() places the needed markers for this logic.
    """
    A.attr['seen'] = True
    B.attr['seen'] = True
    iA = A.attr['id']
    iB = B.attr['id']
    a_seg_todo = False
    b_seg_todo = False
    for iS in range(len(A.attr['seg'])):
      if A.attr['seg'][iS] == iB: A.attr['seg'][iS] = -iB or -1000000000
      if A.attr['seg'][iS] >= 0: a_seg_todo = True
    for iS in range(len(B.attr['seg'])):
      if B.attr['seg'][iS] == iA: B.attr['seg'][iS] = -iA or -1000000000
      if B.attr['seg'][iS] >= 0: b_seg_todo = True

    # CAUTION: is this really helpful?:
    ## it prevents points from a slice to go into process_barrier()'s segment list,
    ## but it also hides information....
    if not a_seg_todo: s.points[iA] = None
    if not b_seg_todo: s.points[iB] = None


  def process_barrier(s, y_slice, max_y, last_x=0.0):
    """process all lines that segment points in y_slice.
       the slice is examined using a scan-strategy. Either left to right or
       right to left. last_x is used to deceide if the the left or 
       right end of the slice is nearest. We start at the nearer end, and
       work our way to the farther end.
       All line segments that are below max_y are promoted into the todo list, 
       with a carefully chosen ordering and direction. todo_append_or_extend()
       is used to merge segments into longer paths where possible.

       The final x-coordinate is returned, so that the caller can provide us
       with its value on the next call.
    """
    if s.verbose:
      print >>sys.stderr, "process_barrier limit=%g, points=%d, %s" % (max_y, len(y_slice), last_x)
      print >>sys.stderr, "                max_y=%g" % (y_slice[-1][1])

    min_x = None
    max_x = None

    segments = []
    for pt in y_slice:
      if pt is None:            # all segments to that point are done.
        continue
      for iC in pt.attr['seg']:
        if iC < 0:              # this segment is done.
          continue
        C = s.points[iC]
        if C is not None and C[1] <= max_y:
          if s.verbose > 1:
            print >>sys.stderr, "   segments.append", C, pt
          segments.append((C,pt))
          if min_x is None or min_x >  C[0]: min_x =  C[0]
          if min_x is None or min_x > pt[0]: min_x = pt[0]
          if max_x is None or max_x <  C[0]: max_x =  C[0]
          if max_x is None or max_x < pt[0]: max_x = pt[0]
          s.mark_segment_done(C,pt)
        #
      #
    #
    
    left2right = s.decide_left2right(min_x, max_x, last_x)
    xsign = -1.0
    if left2right: xsign = 1.0
    def dovetail_both_key(a):
      return a[0][1]+a[1][1]+xsign*(a[0][0]+a[1][0])
    segments.sort(key=dovetail_both_key)

    for segment in segments:
      ## Flip the orientation of each line segment according to this strategy:
      ## check 'sharp' both ends. (sharp is irrelevent without 'seen')
      ##   if one has 'sharp' (and 'seen'), the other not, then cut towards the 'sharp' end.
      ##   if none has that, cut according to decide_left2right()
      ##   if both have it, we must subdivide the line segment, and cut from the 
      ##   midpoint to each end, in the order indicated by decide_left2right().
      A = segment[0]
      B = segment[1]
      if 'sharp' in A.attr and 'seen' in A.attr:
        if 'sharp' in B.attr and 'seen' in B.attr:              # both sharp
          iM = s.pt2idx((A[0]+B[0])*.5, (A[1]+B[1])*.5 )
          M = s.points[iM]
          if xsign*A[0] <= xsign*B[0]:
            s.todo_append_or_extend([M, A])
            s.todo_append_or_extend([M, B])
          else:
            s.todo_append_or_extend([M, B])
            s.todo_append_or_extend([M, A])
        else:                                                   # only A sharp
          s.todo_append_or_extend([B, A])
      else:
        if 'sharp' in B.attr and 'seen' in B.attr:              # only B sharp
          s.todo_append_or_extend([A, B])
        else:                                                   # none sharp
          if xsign*A[0] <= xsign*B[0]:
            s.todo_append_or_extend([A, B])
          else:
            s.todo_append_or_extend([B, A])
          #
        #
      #
          
    # return the last x coordinate of the last stroke
    return s.todo[-1][-1][0]


  def decide_left2right(s, min_x, max_x, last_x=0.0):
    """given the current x coordinate of the cutting head and
       the min and max coordinates we need to go through, compute the best scan direction, 
       so that we minimize idle movements.
       Returns True, if we should jump to the left end (aka min_x), then work our way to the right.
       Returns False, if we should jump to the right end (aka max_x), then work our way to the left.
       Caller ensures that max_x is >= min_x. ("The right end is to the right of the left end")
    """
    if min_x >= last_x: return True     # easy: all is to the right
    if max_x <= last_x: return False    # easy: all is to the left.
    if abs(last_x - min_x) < abs(max_x - last_x):
      return True                       # the left edge (aka min_x) is nearer
    else:
      return False                      # the right edge (aka max_x) is nearer

  def pyramid_barrier(s):
    """Move a barrier in ascending y direction.
       For each barrier position, find connected segments that are as high above the barrier 
       as possible. A pyramidonal shadow (opening 45 deg in each direction) is cast upward
       to see if a point is acceptable for the next line segment. If the shadow touches other points,
       that still have line segment not yet done, we must chose one of these points first.

       While obeying this shadow rule, we also sweep left and right through the data, similar to the
       scan_barrier() algorithm below.
    """
    if not s.do_slicing:
      s.todo = []
      for path in s.paths:
        s.todo.append([])
        for idx in path:
          s.todo[-1].append(s.points[idx])
          if idx == 33: print s.points[idx].attr
        #
      #
      return

  def scan_barrier(s):
    """move a barrier in ascending y direction. 
       For each barrier position, only try to cut lines that are above the barrier.
       Flip the sign for all segment ends that were cut to negative. This flags them as done.
       Add a 'seen' attribute to all nodes that have been visited once.
       When no more cuts are possible, then move the barrier, try again.
       A point that has all segments with negative signs is removed.

       Input is read from s.paths[] -- having lists of point indices.
       The output is placed into s.todo[] as lists of XY_a() objects
       by calling process_barrier() and friends.
    """

    if not s.do_slicing:
      s.todo = []
      for path in s.paths:
        s.todo.append([])
        for idx in path:
          s.todo[-1].append(s.points[idx])
        #
      #
      return
          
    ## first step sort the points into an additional list by ascending y.
    def by_y_key(a):
      return a[1]
    sy = sorted(s.points, key=by_y_key)

    barrier_y = s.barrier_increment
    barrier_idx = 0     # pointing to the first element that is beyond.
    last_x = 0.0        # we start at home.
    while True:
      old_idx = barrier_idx
      while sy[barrier_idx][1] < barrier_y:
        barrier_idx += 1
        if barrier_idx >= len(sy):
          break
      if barrier_idx > old_idx:
        last_x = s.process_barrier(sy[0:barrier_idx], barrier_y, last_x=last_x)       
      if barrier_idx >= len(sy):
        break
      barrier_y += s.barrier_increment
    #
 

  def apply_overshoot(s, paths, start_travel, end_travel):
    """Extrapolate path in the todo list by the give travel at start and/or end
       Paths are extended linear, curves are not taken into accound.
       The intended effect is that interrupted cuts actually overlap at the 
       split point. The knive may otherwise leave some uncut material around 
       the split point.
    """
    def extend_b(A,B,travel):
      d = math.sqrt(s.dist_sq(A,B))
      if d < 0.000001: return B         # cannot extrapolate if A == B
      ratio = travel/d
      dx = B[0]-A[0]
      dy = B[1]-A[1]
      C = XY_a((B[0]+dx*ratio,  B[1]+dy*ratio))
      if 'sharp' in B.attr: C.attr['sharp'] = True
      return C

    for path in paths:
      if start_travel > 0.0:
        path[0] = extend_b(path[1],path[0], start_travel)
      if end_travel > 0.0:
        path[-1] = extend_b(path[-2],path[-1], end_travel)

    return paths


  def apply(self, cut):
    self.load(cut)
    if 'pyramid_algorithm' in self.__dict__:
      self.link_points()
      self.mark_sharp_segs()
      self.pyramid_barrier() 
    else:
      self.subdivide_segments(self.monotone_allow_back_travel)
      self.link_points()
      self.mark_sharp_segs()
      self.scan_barrier()
    if self.tool_pen == False and self.overshoot > 0.0:
      self.todo = self.apply_overshoot(self.todo, self.overshoot, self.overshoot)

    return self.todo

