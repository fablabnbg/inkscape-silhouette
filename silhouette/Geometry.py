# (c) 2013 jw@suse.de
#
# Geometry.py -- collection of geometric functions.
# Split from silhouette/Strategy.py
# 

# minimum difference for geometric values to be considered equal.
_eps = 1e-10

def dist_sq(A,B):
  """
  Pythagorean distance formula WITHOUT the square root.  Since
  we just want to know if the distance is less than some fixed
  fudge factor, we can just square the fudge factor once and run
  with it rather than compute square roots over and over.
  """
  dx = B.x-A.x
  dy = B.y-A.y
  return dx*dx + dy*dy


def ccw(A,B,C):
  """True, if three points are listed in counter-clockwise order in a right handed coordinate 
     system. 
     Note that Silhouette Cameo uses a left handed coordinate systems, where the clock
     rotates in the bavarian direction.
  """
  ## From http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
  ## FIXME: should integrate colinear() into ccw() returning 
  ##        None when colinear, True when ccw, False when cw.
  return (C.y-A.y)*(B.x-A.x) > (B.y-A.y)*(C.x-A.x)

def colinear(A,B,C):
  """True, if three points are on the same line.
  """
  ## FIXME: test this thoroughly and integrate into ccw()
  return abs((C.y-A.y)*(B.x-A.x) - (B.y-A.y)*(C.x-A.x)) < _eps

def sharp_turn_90(A,B,C):
  """Given the path from A to B to C as two line segments.
     Return true, if the corner at B is more than +/- 90 degree.

     Algorithm:
     For the segment A-B, we construct the normal B-D. 
     The we test, if points A and C lie on the same side of the line(!) B-D.
     If so, it is a sharp turn.

     This 90 deg algoritm is a simplified (and faster) version of the general case
     sharp_turn() using a fwd_ratio.
  """
  dx = B.x-A.x
  dy = B.y-A.y
  D = XY_a((B.x-dy, B.y+dx))        # BD is now the normal to AB

  return ccw(A,B,D) == ccw(C,B,D)


def sharp_turn_116(A,B,C):
  """ A sharp turn of more than 116.565 degree.
  """
  return sharp_turn(A,B,C, -0.5)


def sharp_turn_63(A,B,C):
  """ A sharp turn of more than 63.435 degree.
  """
  return sharp_turn(A,B,C, 0.5)


def sharp_turn_45(A,B,C):
  """ A sharp turn of more than 45 degree.
  """
  return sharp_turn(A,B,C, 1.0)


def sharp_turn_26(A,B,C):
  """ A sharp turn of more than 26.565 degree.
  """
  return sharp_turn(A,B,C, 2.0)


def sharp_turn(A,B,C,fwd_ratio):
  """Given the path from A to B to C as two line segments.
     Return true, if the corner at B is more than +/- cotan(fwd_ratio) degree.
     fwd_ratio is the number of units we continue forward, for one unit we deviate sideways.
     Examples: fwd_ratio=0: 90 deg. fwd_ratio=0.5: 63.435 deg
               fwd_ratio=1: 45 deg, fwd_ratio=2: 26.565 deg
               fwd_ratio=-.5: 116.565 deg.

     Algorithm:
     First we test if C is on the left or right of A-B. 
     We will place D on the same side and remember the side for later.
     For the segment A-B, we construct the normal B-D. 
     Then we extend A-B to E so that distance |B-E| == |B-D|.
     Now we use the weighted vector sum [BE]*fwd_ratio + [BD]*1 == [BF] to create 
     the desired angle A-B-F

     If C is left of AB and C is left of BF, then it is a sharp turn; or
     If C is right of AB and C is right of BF, then it is a sharp turn; 
     else not.

  """
  if fwd_ratio == 0.0: return sharp_turn_90(A,B,C)      # short cut.

  dx = B.x-A.x
  dy = B.y-A.y

  dx_be = dx
  dy_be = dy

  ccw_abc = ccw(A,B,C)
  if ccw_abc:
    # D = (B.x-dy, B.y+dx)        # BD is now the normal to AB ...
    dx_bd = -dy
    dy_bd = +dx
  else:
    # D = (B.x+dy, B.y-dx)        # ... and C, D are on the same side of AB
    dx_bd = +dy
    dy_bd = -dx
  F = XY_a((B.x+fwd_ratio*dx_be+1*dx_bd, B.y+fwd_ratio*dy_be+1*dy_bd))

  return ccw(B,F,C) == ccw_abc


def intersect_lines(A,B,C,D, limit1=False, limit2=False):
  """compute the intersection point of line AB with line CD.
     If limit1 is True, only the segment [AB] is considered.
     If limit2 is True, only the segment [CD] is considered.
     None is returned, if the lines do not intersect or -- 
     with applying limits -- the intersection point is outside 
     a segment.
  """

  def _in_segment(A,B,x,y):
    """ simplified segment test, 
        knowing that point (x,y) is colinar to AB.
    """
    # print "intersect_lines:_in_segment", A, B, x, y
    if (abs(A.x-B.x) > _eps):            # AB is not vertial, test x-coordinate
      if A.x <= x and x <= B.x: return True
      if A.x >= x and x >= B.x: return True
    else:                               # test y-coordinate
      if A.y <= y and y <= B.y: return True
      if A.y >= y and y >= B.y: return True
    return False                        # No, (x,y) is outside of [AB].

  # from http://community.topcoder.com/tc?module=Static&d1=tutorials&d2=geometry2

  _a1 = B.y - A.y
  _b1 = A.x - B.x
  _c1 = _a1 * A.x + _b1 * A.y

  _a2 = D.y - C.y
  _b2 = C.x - D.x
  _c2 = _a2 * C.x + _b2 * C.y

  det = _a1 * _b2 - _a2 * _b1
  if det < _eps and det > -_eps:
    # the segments may be colinear, with many intersecting points.
    if colinear(A,B,C) and colinear(A,B,D):
      if _in_segment(A,B,C.x,C.y): return C     # A--C--B--D or A--C--D--B
      if _in_segment(A,B,D.x,D.y): return D     # A--D--B--C
      if _in_segment(C,D,A.x,A.y): return A     # C--A--B--D 
      #  _in_segment(C,D,B.x,B.y): return B     # see above: A--C--B--D
    return None                                 # A--B--C--D
  x = (_b2*_c1 - _b1*_c2) / float(det)
  y = (_a1*_c2 - _a2*_c1) / float(det)

  if limit1 and not _in_segment(A,B,x,y): return None
  if limit2 and not _in_segment(C,D,x,y): return None
  return (x,y)


def _intersect_y5(Ax,Ay,Bx,By,y_boundary, limit=False):
  """returns the x coordinate, where the line AB crosses the given y_boundary.
     Returns None, if the line is horizontal or if limit applies,
     the intersection is outside [AB].
     Useful to implement fast special case versions of intersect_lines().
  """
  dy = By-Ay
  if abs(dy) < _eps:               # horizontal
    ratio = 1.0
    if abs(By-y_boundary) < _eps:
      return 0.5*(Ax+Bx)              # return anything between A,B
    else:
      return None
  else:
    ratio = (y_boundary-Ay)/float(dy)

  if limit:
    if ratio < 0.0: return None
    if ratio > 1.0: return None
  return Ax + ratio*(Bx-Ax)


def intersect_x(A,B,x_boundary, limit=False):
  """returns the y coordinate, where the line AB crosses the given x_boundary.
     Returns None, if the line is vertical or if limit applies and
     the intersection is outside [AB].
     Same as, but much faster than
     intersect_lines(A,B,(x_boundary,0),(x_boundary,1),limit1=limit,limit2=False)[1]
  """
  return _intersect_y5(A.y, A.x, B.y, B.x, x_boundary, limit)


def intersect_y(A,B,y_boundary, limit=False):
  """returns the x coordinate, where the line AB crosses the given y_boundary.
     Returns None, if the line is horizontal or if limit applies and
     the intersection is outside [AB].
     Same as, but much faster than
     intersect_lines(A,B,(0,y_boundary),(1,y_boundary),limit1=limit,limit2=False)[0]
  """
  return _intersect_y5(A.x, A.y, B.x, B.y, y_boundary, limit)


class XY_a(tuple):
  def __init__(self,t):
    #super(XY_a, self).__init__(tuple(t))
    tuple.__init__(t)
    self.attr = self.__dict__
  @property
  def x(self):
    return self[0]
  @property
  def y(self):
    return self[1]
  ## does not work because tuples are immutable:
  # @x.setter
  # def x(self, value):
  #   super(XY_a,self)[0] = value


class Barrier:
  def __init__(self, points, key):
    """Initialize a barrier by sorting the points according to the given
       sort key. The barrier is placed on the first point, and can be 
       moved by next(n=1) prev(n=1), first(), last(), pos(idx), or 
       find(point). All these method return an index into the sorted list 
       that can be used in pos(idx) or pslice(idx1, idx2).
    """
    self.key=key
    self.points = sorted(points, key=key)
    self.idx = 0

  def first(self):
    """reset the barrier to the first point.
    """
    self.idx = 0
    return self.idx

  def last(self):
    """reset the barrier to the last point.
    """
    self.idx = len(self.points)-1
    return self.idx

  def next(self, count=1):
    """Advance the barrier to the next point. Or by count points.
       If we pass the end of the points, the barrier remains on the last point
       and None is returned.  Otherwise the new index is returned.
    """
    self.idx += count
    if self.idx >= len(self.points):
      self.last()
      return None
    return self.idx

  def prev(self, count=1):
    """Reverse the barrier to the previous point. Or by count points.
       If we pass the beginning of the points, the barrier remains on the first point
       and None is returned.  Otherwise the new index is returned.
    """
    self.idx -= count
    if self.idx < 0:
      self.idx = 0
      return None
    return self.idx
  

  def pos(self, new_idx=None):
    """Returns the current barrier index; optionally setting a new index.
       If new_idx is outside the points list, None is returned, and the index
       is positiond on the first or last point.
    """
    if new_idx is None:
      return self.idx
   
    self.idx = new_idx
    if self.idx < 0:    # inlined self.prev(0)
      self.idx = 0
      return None
    return self.next(0)

  ##  cannot use the name slice here. sigh.
  def pslice(self, first=0, last=None):
    """Returns a list of points that are beween the given indices. Ends inclusive.
       Last defaults to the current barrier position.
    """
    if last is None: last = self.idx
    return self.points[first:last+1]

  def point(self, idx=None):
    """Returns the point at the barrier index.
       Same as slice()[-1]
    """
    if idx is None: return self.points[self.idx]
    return self.points[idx]

  def find(self, targetpoint, backwards=False, start=None):
    """Advance the barrier so that it cuts through targetpoint. This
       targetpoint need not be amongst the set of points for which the barrier
       was created. The index of the last point (from the set) that is still
       within the barrier is returned.  If the barrier is already beyond the
       targetpoint, None is returned and the barrier is not moved.
       Try backwards=True or giving a start index then.
       If the targetpoint is beyond the the end, the barrier remains at the last point.
       Note: 'point(find(target)) == target' may or may not be true.
    """
    saved_idx = self.idx
    if start is not None: self.idx = start

    key_limit = self.key(targetpoint)
    if backwards == True:
      for i in reversed(range(0, self.idx+1)):
        if self.key(self.points[i]) <= key_limit:
          self.idx = prev_idx
          return self.idx
      self.idx = 0
      return self.idx     # stick at first point.

    prev_idx = None
    for i in range(self.idx, len(self.points)):
      if self.key(self.points[i]) > key_limit:
        if prev_idx is None:
          if start is not None: self.idx = saved_idx
          return None
        else:
          self.idx = prev_idx
          return self.idx
      prev_idx = i
    self.idx = prev_idx
    return self.idx     # stick at last point.


  def slice(self, idx1, idx2):
    """return an ordered subset of the points between idx1 and idx2 
       (both inclusive).
       If idx2 is less than idx1, then the returned list is reverse sorted.
    """
    pass
  
  def __iter__(self):
    """ An iterator for advancing next(). Quite useless?
    """
    pass


