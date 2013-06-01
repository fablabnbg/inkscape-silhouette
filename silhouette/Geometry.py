# (c) 2013 jw@suse.de
#
# Geometry.py -- collection of geometric functions.
# Split from silhouette/Strategy.py
# 


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


## From http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def ccw(A,B,C):
  return (C.y-A.y)*(B.x-A.x) > (B.y-A.y)*(C.x-A.x)


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



class XY_a(tuple):
  def __init__(self,t):
    #super(XY_a, self).__init__(tuple(t))
    tuple.__init__(t)
    self.attr = {}
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
    if new_idx is not None:
      self.idx = new_idx
    else:
      return self.idx
    if self.idx < 0:
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

  def point(self):
    """Returns the point at the barrier index.
       Same as slice()[-1]
    """
    return self.points[self.idx]

  def find(self, targetpoint, backwards=False):
    """advance the barrier so that it cuts through targetpoint. This targetpoint need not be amongst the
       set of points for which the barrier was created. The index of the last point (from the set)
       that is still within the barrier is returned.
       If the barrier is already beyond the targetpoint, None is returned and the barrier is not moved.
       Try backwards=True then.
       If the targetpoint is beyond the the end, the barrier remains at the last point.
       Note: 'point(find(target)) == target' may or may not be true.
    """
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


