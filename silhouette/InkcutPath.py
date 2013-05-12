#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#             InkCut, Plot HPGL directly from Inkscape.
#       hpgl.py
#                functions to send finished data to plotter/cutter
#       
#       Copyright 2010 Jairus Martin <frmdstryr@gmail.com>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#

import sys
sys.path.append('/usr/share/inkscape/extensions')
import cubicsuperpath, simplepath, cspsubdiv, simpletransform,bezmisc,copy,math
from pprint import pprint
import inkex

units = {'in':90.0, 'pt':1.25, 'px':1, 'mm':3.5433070866, 'cm':35.433070866, 'm':3543.3070866,'km':3543307.0866, 'pc':15.0, 'yd':3240 , 'ft':1080}

class Plot:
        def __init__(self,settings = {}):
                default = {
                        'margin':4*units['mm'],
                        'cutSettings':False,
                        'velocity':4, # cm/s or in/s, depends on cutter
                        'force':80, # g
                        'scale':1016/units['in'], # according to inkscape & hpgl scale
                        'calibration':1, # scale adjustment if needed
                        'smoothness':.1*units['mm'], # 1 um
                        'overcut': units['mm'], # 1 mm
                        'offset':0,
                        'copies':1,
                        'spacing':(.25*units['cm'],.25*units['cm']),
                        'startPosition':(0,4*units['mm']), # y pos = margin
                        'finishPosition':(0,0),
                        'feed':0,
                        'dimensions':(100*units['m'],30*units['cm']), # swapped
                        'weedHorizontal':False,
                        'weedVertical':False,
                        'weedBox':False,
                        'sortTracking':False,
                        'sortFastest':False
                }
                default.update(settings) # update with passed in data
                
                # set defaults
                for k,v in default.iteritems():
                        setattr(self,k,v)
                #self.weedHorizontal = 
                
        
        # ------------- load graphic ---------------------------------
        def loadGraphic(self,svgPathNodes): #todo multiple graphics?
                self.graphic = Graphic(svgPathNodes)
                
                # set graphic defaults
                self.graphic.setPosition(self.startPosition)
                self.graphic.setScale(self.scale)
                self.graphic.setSmoothness(self.smoothness)
                self.graphic.setOvercut(self.overcut)
                self.graphic.setBladeOffset(self.offset)
                
                # read new plot properties
                self.data = self.getData()
                self.size = self.getSize()
        
        def createTiledClones(self): #does a lot of work
                # set some useful variables
                start = self.startPosition
                c = self.copies
                dm = self.dimensions
                pad = self.spacing
                sz = self.graphic.size
                pos = [0,0] #self.graphic.position[:]
                clones = []
                used = [sz[0]+pos[0],sz[1]+pos[1]]
                first = True
                limit = (dm[0]-start[0],dm[1]-start[1]-self.margin)
                if (dm[0] == 0): limit[0]=pos[0] + pad[0] + 2*sz[0]+1 # should result in an always true test
                
                # create tiled clones
                stacks = 1
                while c > 0:
                        if first:
                                first = False
                        elif (pos[1] + pad[1]+2*sz[1]) <= limit[1]: #add to stack
                                pos[1] += pad[1] + sz[1] # add copy size and padding
                                used[1] = max(used[1],pos[1]+sz[1])
                        elif (pos[0] + pad[0] + 2*sz[0]) <= limit[0]: # stack full, create row
                                pos[1] = 0 # reset stack
                                pos[0] += pad[0] + sz[0] # change x to current position plus copy width and padding
                                stacks +=1
                        # else max reached?
                        # should i create clones here or just get positions?
                        clone = copy.deepcopy(self.graphic)
                        # add start position
                        spos = (pos[0]+start[0],pos[1]+start[1])
                        clone.setPosition(spos)
                        clones.append(clone)
                        c -=1
                        
                # update plot size
                used[0] = pos[0]+sz[0]+start[0]
                self.size = used # l,w
                
                
                # weeding lines
                self.weedlines = []
                stackSize = self.getStackSize()
                
                # add weedline around plot
                if self.weedBox:
                        spacing = (pad[0]/2,pad[1]/2)
                        topright = [used[0]+start[0]+spacing[0]-self.margin,used[1]+start[1]+spacing[1]]
                        topleft = [start[0]-spacing[0],used[1]+start[1]+spacing[1]]
                        bottomright = [used[0]+start[0]+spacing[0]-self.margin,start[1]-spacing[1]]
                        bottomleft = [start[0]-spacing[0],start[1]-spacing[1]]
                        bp = [['M',bottomleft],['L',topleft],['L',topright],['L',bottomright],['L',bottomleft]]
                        box = Path(bp)
                        self.weedlines.append(box)
                
                # add vertical weedlines
                if self.weedVertical and stacks > 1:
                        bp  = [['M',[sz[0]+pad[0]/2,start[1]]],['L',[sz[0]+pad[0]/2,used[1]+start[1]+pad[1]/2]]] # could go off page if margin is less than half of pad
                        vline = Path(bp)
                        self.weedlines.append(vline)
                        for i in range(2,stacks):
                                vline = copy.deepcopy(vline)
                                vline.translatePath(sz[0]+pad[0],0)
                                self.weedlines.append(vline)
                
                # add horz weedlines
                if self.weedHorizontal and self.copies > 1:
                        bp  = [['M',[start[0],sz[1]+pad[1]/2+start[1]]],['L',[used[0]+pad[0]/2,sz[1]+pad[1]/2+start[1]]]]
                        hline = Path(bp)
                        self.weedlines.append(hline)
                        for i in range(2,stackSize):
                                hline = copy.deepcopy(hline)
                                hline.translatePath(0,sz[1]+pad[1])
                                self.weedlines.append(hline)
                
                # update finish position
                if not list(self.finishPosition) == [0,0]:
                        self.finishPosition = (used[0]+self.feed,0)
                
                #inkex.debug([dm[1]-self.startPosition[1]-self.margin,used[1]])
                return clones
        
        # ------------- plot properties ---------------------------------
        def getData(self):
                data = []
                data.extend(self.graphic.data)
                return data
        
        def getLength(self):
                try:
                        l = self.graphic.length
                        return l
                except:
                        l = self.graphic.getLength()
                        self.length = l
                return l
        
        def getSize(self):
                self.createTiledClones() # will set self.size
                return self.size
                
        def setCalibration(self,s):
                self.calibration = s
                self.scale = 1016/units['in']*s
                self.graphic.setScale(self.scale)
        
        def setCopies(self,c):
                self.copies = c
                # update size
                self.getSize()
        
        def getStackSize(self):
                limit = (self.dimensions[1]-self.startPosition[1]-self.margin)
                size = self.graphic.size[1]
                pad = self.spacing[1]
                stack = math.floor((limit+pad)/(size+pad))
                return int(stack)
        
        def setSmoothness(self,s):
                self.smoothness = s
                self.graphic.setSmoothness(s)
        
        def setOvercut(self,d):
                self.overcut = d
                self.graphic.setOvercut(d)
        
        def setBladeOffset(self,d):
                self.offset = d
                self.graphic.setBladeOffset(d)
        
        # ------------- plot settings ---------------------------------                
        def setSpacing(self,(x,y)):
                self.spacing = (x,y)
        
        def setDimensions(self,(x,y)):
                self.dimensions = (x,y)
        
        def setMargin(self,m):
                last = self.margin
                pos = list(self.startPosition)
                pos[1] -=last
                pos[0] -=last
                self.margin = m
                self.setStartPosition(pos)
        
        def setStartPosition(self,(x,y)):
                self.startPosition = (x+self.margin,y+self.margin)
                self.graphic.setPosition((x,y))
                
        def setFinishPosition(self,(x,y)):
                self.finishPosition = (x,y)
                
                
        # ------------- plot export ---------------------------------
        def applyOffset(self,plot):
                d = self.offset*self.scale
                def angleBetween(axis,p0,p1):
                        def dotP(p0,p1):
                                p = 0
                                for a1,a2 in zip(p0,p1):
                                        p +=a1*a2
                                return p                                
                        def norm(p0):
                                n = 0
                                for a in p0:
                                        n +=a*a
                                return math.sqrt(n)        
                        p0 = [p0[0]-axis[0],p0[1]-axis[1]]
                        p1 = [p1[0]-axis[0],p1[1]-axis[1]]
                        assert norm(p0) > 0 and norm(p1) > 0, "invalid points"
                        r = dotP(p0,p1)/(norm(p0)*norm(p1))
                        if -1 <= r <= 1:
                                        return math.acos(r)
                        else:
                                return math.pi
                
                def arcto(radius,theta,(x,y),p0):
                        poly = []
                        arc = ['A',[radius,radius,theta,0,1,x,y]]
                        d = simplepath.formatPath([['M',p0],arc])
                        p = cubicsuperpath.parsePath(d)
                        cspsubdiv.cspsubdiv(p, self.smoothness*self.scale)
                        for sp in p:
                                first = True
                                for csp in sp:
                                        if first:
                                                first = False
                                        else:
                                                for subpath in csp:        
                                                        poly.append(list(subpath))
                        return poly
                def curveto(p0,curve,flat):
                        poly = []
                        d = simplepath.formatPath([['M',p0],curve])
                        p = cubicsuperpath.parsePath(d)
                        cspsubdiv.cspsubdiv(p, flat)
                        for sp in p:
                                first = True
                                for csp in sp:
                                        if first:
                                                first = False
                                        else:
                                                for subpath in csp:        
                                                        poly.append(['L',list(subpath)])
                        return poly
                
                
                
                if  d <= 0:
                        return plot
                
                #poly = plot.parse(plot)
                
                last = ['PU',[0,0]] # start position 
                cur = [plot[0][:2],map(int,plot[0][2:].split(','))]
                i = 1
                while i < len(plot):
                        cmd = plot[i][:2]
                        point = map(int,plot[i][2:].split(','))
                        next = [cmd,point]
                        if not last[1] == cur[1] and not cur[1] == next[1]:
                                theta = angleBetween(cur[1],last[1],next[1]) 
                                if theta < math.pi/1.1:
                                        # start point
                                        dist = bezmisc.pointdistance(last[1],cur[1])
                                        t = d/dist+1
                                        start = bezmisc.tpoint(last[1],cur[1],t)
                                        # end point
                                        dist = bezmisc.pointdistance(cur[1],next[1])
                                        t = (4*d)/dist
                                        end = bezmisc.tpoint(cur[1],next[1],t)
                                        if t<=1:
                                                # go distance d past actual point 
                                                plot[i-1]='%s%d,%d'%(cur[0],start[0],start[1])
                                        
                                                # curve to end point 
                                                #for pt in arcto(d,0,end,start):
                                                #        plot.insert(i,'%s%d,%d'%(cur[0],pt[0],pt[1]))
                                                #        i+=1        
                                                
                                                # end point, probably dont need
                                                plot.insert(i,'%s%d,%d'%(next[0],end[0],end[1]))
                                                i+=1
                        """
                        # skip double points
                        if not last[1] == cur[1] and not cur[1] == next[1]: # where are doubles coming from?
                                # get the angle between the two vectors using cur as origin
                                theta = angleBetween(cur[1],last[1],next[1]) 
                                if theta < math.pi/1.1:
                                        # go past by offset amount
                                        dist = bezmisc.pointdistance(last[1],cur[1])
                                        t1 = d/dist+1
                                        start = bezmisc.tpoint(last[1],cur[1],t1)
                                        
                                        # come back to next line
                                        dist = bezmisc.pointdistance(cur[1],next[1])
                                        t2 = (4*d)/dist
                                        finish = bezmisc.tpoint(cur[1],next[1],t2)
                                        if t2 <= 1:
                                                # add cur point
                                                plot.insert(i-1,['L',list(start)])
                                                
                                                plot[i-1] = ['L',list(finish)]
                                        
                                        
                                        
                        #else:
                        #        inkex.debug("failed on %i with points %s,%s and %s"%(i,last,cur,next))        
                        
                        """
                        # shift to next point
                        last = cur[:]
                        cur = next[:]
                        i+=1
                return plot
        
        
        def changeOrder(self,clones):
                # if sorting we have to get all the paths then reorder
                # these sort the entire plot
                plot = []
                if self.sortTracking or self.sortFastest:
                        # sort them
                        paths = []
                        for clone in clones:
                                paths.extend(clone.paths)
                        
                        if self.sortTracking:
                                paths.sort(key=lambda p: p.bbox[1])
                        else: # sortFastest, dont know algorithm yet...
                                paths.sort(key=lambda p: math.sqrt(p.bbox[1]**2+p.bbox[0]**2))
                        for path in paths:
                                plot.extend(path.toHPGL())
                # sort on a per clone basis
                else:
                        for clone in clones:
                                # quick sort 4 tracking...
                                #clone.paths.sort(key=lambda p: p.bbox[1])
                                plot.extend(clone.toHPGL())
                                
                return plot
 
        def toHPGL(self):
                #inkex.debug(['path',self])
                hpgl = ['IN','SP1']
                if self.cutSettings:
                        hpgl.extend(['VS%d'%(self.velocity),'FS%d'%(self.force)])
                
                # reorder paths
                data = self.changeOrder(self.createTiledClones())
                # go back and weed
                for line in self.weedlines:
                        #inkex.debug(line)
                        data.extend(line.toHPGL())
                
                # adjust for blade offset
                data = self.applyOffset(data)
                hpgl.extend(data)
                
                hpgl.append('PU%d,%d'%(self.finishPosition[0]*self.scale,self.finishPosition[1]*self.scale))
                hpgl.extend(['IN'])
                return ";".join(hpgl)+";"
 
        def toCutList(self):
                return self.graphic.toCutList()

class Graphic: # a group of paths
        def __init__(self,svgElements):
                self.data = self.toBasicPaths(self.fromSVG(svgElements))
                self.paths = self.toPathObjs()
                self.mirror = [False,False]
                self.bbox = self.boundingBox()
                self.position = (0,0) # relative to starting position
                self.size = self.getSize()
                self.mirrorYAxis()
                #self.length = self.getLength()
                #self.getSize()
                
        
        # --------------------------graphic properties --------------------------
        def getLength(self):
                l = 0
                for path in self.paths:
                        l +=path.length
                self.length = l
                return l
        
        
        def setBladeOffset(self,d):
                self.offset = d
                for path in self.paths:
                        path.setBladeOffset(d)
                
        
        def setScale(self,s):
                self.scale = s
                for path in self.paths:
                        path.setScale(s)
        
        def setSmoothness(self,s):
                self.smoothness = s
                for path in self.paths:
                        path.setSmoothness(s)
        
        def setOvercut(self,d):
                self.overcut = d
                for path in self.paths:
                        path.setOvercut(d)
        
        
        # --------------------------graphic adjustments --------------------------
        def setPosition(self,(x,y)):
                mirrorx = 1
                mirrory = -1
                if self.mirror[0]:
                        mirrorx = -1
                if self.mirror[1]:
                        mirrory = 1
                x,y = mirrorx*(x-self.bbox[0]),mirrory*(y+self.bbox[2]) # shift distance from orign
                for path in self.paths:
                        # reset to start
                        path.translatePath(-self.position[0],-self.position[1])
                        # move to new position
                        path.translatePath(x,y)
                        # update new position
                self.position = (x,y)
        
        def mirrorYAxis(self):
                if not (self.mirror[1]):
                        self.mirror[1] = True
                else:
                        self.mirror[1] = False
                for path in self.paths:
                        path.translatePath(0,-1*self.size[1]) # shift 
                        path.scalePath(1,-1) # mirror
        
        def mirrorXAxis(self):
                if not (self.mirror[0]):
                        self.mirror[0] = True
                        for path in self.paths:
                                path.translatePath(-1*self.size[0],0)  # shift
                                path.scalePath(-1,1)        # mirror
                        
        # --------------------------graphic settings --------------------------
        def getPosition(self):
                try:
                        return self.position
                except:
                        try: 
                                self.bbox
                                return (self.bbox[0],self.bbox[2])
                        except:
                                self.bbox = self.boundingBox()
                        return (self.bbox[0],self.bbox[2]) # minx, miny (top left corner?)
        
        def getSize(self):
                try: 
                        self.bbox
                except:
                        self.bbox = self.boundingBox()
                bbox = self.bbox
                size = (bbox[1]-bbox[0],bbox[3]-bbox[2]) # x size, y size
                return size
        
        def boundingBox(self):
                bbox = self.paths[0].boundingBox() # initialize
                for p in self.paths:
                        bbox = [min(bbox[0],p.boundingBox()[0]),max(bbox[1],p.boundingBox()[1]),
                                        min(bbox[2],p.boundingBox()[2]),max(bbox[3],p.boundingBox()[3])]
                return bbox
        # --------------------------graphic conversion --------------------------
        def toPathObjs(self): # makes path objects from basic path list
                paths = []
                for bp in self.data:
                        paths.append(Path(bp))
                return paths
                
        def toBasicPaths(self,spl): # break a complex path with subpaths into individual paths
                bpl = [] # list of basic paths
                i=-1
                for cmd in spl:
                        if cmd[0]=='M': # start new path!        
                                bpl.append([cmd])
                                i+=1
                        else:
                                bpl[i].append(cmd)
                return bpl
        
        # --------------------------graphic import --------------------------
        def fromSVG(self,nodes):
                # takes in a list of lxml elements
                # returns a list of inkscape compound simplepaths (paths in paths etc...)
                # could possibly push up into Plot
                spl = []
                for node in nodes:
                        tag = node.tag[node.tag.rfind("}")+1:]
                        if tag == 'path':
                                if node.get("transform"):
                                  print >>sys.stderr, "path: transform on %s not implemnented; try to combine paths." % node.get('id')
                                spl.extend(simplepath.parsePath(node.get("d")))
                        elif tag == 'rect':
                                import xml.etree.ElementTree as ET
                                w=float(node.get('width'))
                                h=float(node.get('height'))
                                x=float(node.get('x'))
                                y=float(node.get('y'))
                                d = "m %g,%g %g,0 0,%g %g,0 z" % (x,y, w, h, -w) 
                                # how about transformation??
                                if node.get("transform"):
                                  print >>sys.stderr, "rect: transform on %s not implemnented; try to combine paths." % node.get('id')
                                spl.extend(simplepath.parsePath(d))
                        elif tag in ('rect', 'text'):
                                # how do I convert rect to path??
                                raise AssertionError("Cannot handle '%s' objects, covert to path first."%(tag))
                        elif tag == 'g':
                                if node.get("transform"):
					# does it nale sense to apply the own transform??
					# it fails when "translate(0,-2.5390623e-6)"
					tr = simpletransform.parseTransform(node.get("transform"))
                                        simpletransform.applyTransformToNode(tr,node)
                                spl.extend(self.fromSVG(list(node)))
                        else:
                                raise AssertionError("Cannot handle tag '%s'"%(tag))
                return spl
                
        # --------------------------graphic export --------------------------
        def toHPGL(self):
                hpgl = []
                for path in self.paths:
                        hpgl.extend(path.toHPGL())
                return hpgl

        def toCutList(self):
                cut = []
                for path in self.paths:
                        cut.extend(path.toCutList())
                return cut

class Path: # a single path
        def __init__(self,basicpath,settings={}):
                default = {
                'overcut':0,
                'offset':0,
                'smoothness':.1*units['mm'], # 1 um
                'scale': 1016/units['in']
                }
                default.update(settings)
                for k,v in default.iteritems():
                                setattr(self,k,v)
                self.data = basicpath
                self.closed = self.isClosed()
                
                #self.smoothness = .1
                self.bbox = self.boundingBox()
                #self.length = self.getPathLength()
                #self.position = (self.bbox[0],self.bbox[2])
                #self.scale = 11.288888889
                
        # --------------------------path adjustments --------------------------
        
        def translatePath(self,x,y):
                simplepath.translatePath(self.data,x,y)
        
        def rotatePath(self,a,x=0,y=0):
                simplepath.rotatePath(self.data,a,x,y)
        
        def scalePath(self,x,y):
                simplepath.scalePath(self.data,x,y)
        
        
        # --------------------------path properties --------------------------
        def boundingBox(self):
                csp = cubicsuperpath.CubicSuperPath(self.data)
                self.bbox = list(simpletransform.roughBBox(csp))
                return list(simpletransform.roughBBox(csp)) # [minx,maxx,miny,maxy]
        
        def getPathLength(self): # close enough...
                poly = self.toPolyline()
                i = 1
                d = 0
                while i < len(poly):
                        last = poly[i-1][1]
                        cur = poly[i][1]
                        d += bezmisc.pointdistance(last,cur)
                        i+=1
                return d
        
        def isClosed(self):
                try:
                        return self.closed
                except:
                        ans = self.data[-1][0] == "Z"
                        self.closed = ans
                        return ans
                
                
                
        
        # --------------------------path settings --------------------------        
        def setSmoothness(self,s):
                self.smoothness = s
        
        def setScale(self,s):
                self.scale = s
                
        def setBladeOffset(self,d):
                self.offset = d
        
        def setOvercut(self,d):
                self.overcut = d
                
                if self.closed and d > 0:
                        # replace z with the start point
                        """
                        pprint(self.data)
                        endp = self.data.pop()
                        if endp[0]=='Z':
                                endp = ['L',self.data[0][1]]
                                self.data.append(endp)
                        """
                # below does not work, beziersplitatt does not give the correct bezier....
                """
                if self.closed and d > 0:
                        # replace z with the start point
                        self.data.pop()
                        endp = ['L',self.data[0][1]]
                        self.data.append(endp)
                        
                        # find overcut point d away from start, todo, don't use polylines
                        i = 1
                        last = self.data[0][1][:]  # start position
                        while d > 0:
                                cur = self.data[i][1][:]
                                cmd = self.data[i][0]
                                # get distance to next point
                                if cmd=='L':
                                        dist = bezmisc.pointdistance(last,cur)
                                elif cmd=='C':
                                        curve = ((cur[0],cur[1]),(cur[2],cur[3]),(cur[4],cur[5]),last)
                                        dist = bezmisc.bezierlength(curve)
                                
                                # check distance
                                if d<dist: # last point
                                        t = d/dist
                                        if cmd=='L':
                                                self.data.append(['L',list(bezmisc.tpoint(last,cur,t))])
                                        elif cmd=='C':
                                                curve = ((cur[0],cur[1]),(cur[2],cur[3]),(cur[4],cur[5]),last)
                                                first,second = bezmisc.beziersplitatt(curve,t)
                                                self.data.append(['C',[first[0][0],first[0][1],first[1][0],first[1][1],first[2][0],first[2][1]]])
                                else: 
                                        self.data.append([cmd,cur])
                                
                                # update last
                                if cmd=='L':
                                        last = cur
                                elif cmd=='C':        
                                        last = [cur[4],cur[5]]
                                d -= dist
                                i +=1
                        """
        
        
        #--------------------------apply path changes --------------------------
        
        def applyOvercut(self,poly): # good old polyline overcut...
                d = self.overcut
                if self.closed and d > 0:
                        # find overcut point d away from start, todo, don't use polylines, see setOvecut commented...
                        i = 1 # skip move to
                        last = poly[0][1][:]  # start position
                        while d > 0:
                                cur = poly[i][1][:]
                                cmd = poly[i][0]
                                # get distance to next point
                                dist = bezmisc.pointdistance(last,cur)                                
                                # check distance
                                if d<dist: # last point
                                        t = d/dist
                                        poly.append(['L',list(bezmisc.tpoint(last,cur,t))])
                                else: 
                                        poly.append([cmd,cur])
                                
                                # update last
                                last = cur
                                d -= dist
                                i +=1
                return poly
        
        def applyOffset(self,poly): # adjust for blade offset
                #todo, this haha
                d = abs(self.offset)
                def angleBetween(axis,p0,p1):
                        def dotP(p0,p1):
                                p = 0
                                for a1,a2 in zip(p0,p1):
                                        p +=a1*a2
                                return p                                
                        def norm(p0):
                                n = 0
                                for a in p0:
                                        n +=a*a
                                return math.sqrt(n)        
                        p0 = [p0[0]-axis[0],p0[1]-axis[1]]
                        p1 = [p1[0]-axis[0],p1[1]-axis[1]]
                        assert norm(p0) > 0 and norm(p1) > 0, "invalid points"
                        r = dotP(p0,p1)/(norm(p0)*norm(p1))
                        if -1 <= r <= 1:
                                        return math.acos(r)
                        else:
                                return math.pi
                
                def arcto(radius,theta,(x,y),p0):
                        poly = []
                        arc = ['A',[radius,radius,theta,0,0,x,y]]
                        d = simplepath.formatPath([['M',p0],arc])
                        p = cubicsuperpath.parsePath(d)
                        cspsubdiv.cspsubdiv(p, self.smoothness)
                        for sp in p:
                                first = True
                                for csp in sp:
                                        if first:
                                                first = False
                                        else:
                                                for subpath in csp:        
                                                        poly.append(['L',list(subpath)])
                        return poly
                def curveto(p0,curve,flat):
                        poly = []
                        d = simplepath.formatPath([['M',p0],curve])
                        p = cubicsuperpath.parsePath(d)
                        cspsubdiv.cspsubdiv(p, flat)
                        for sp in p:
                                first = True
                                for csp in sp:
                                        if first:
                                                first = False
                                        else:
                                                for subpath in csp:        
                                                        poly.append(['L',list(subpath)])
                        return poly
                
                
                if  d <= 0:
                        return poly
                
                # start position
                last = poly[0][1][:]
                cur = poly[1][1][:]
                i = 2
                while i < len(poly):
                        next = poly[i][1][:]
                        # skip double points
                        if not last == cur and not cur == next: # where are doubles coming from?
                                # get the angle between the two vectors using cur as origin
                                theta = angleBetween(cur,last,next) 
                                if theta < math.pi/1.1:
                                        # go past by offset amount
                                        dist = bezmisc.pointdistance(last,cur)
                                        t1 = d/dist+1
                                        start = bezmisc.tpoint(last,cur,t1)
                                        
                                        # come back to next line
                                        dist = bezmisc.pointdistance(cur,next)
                                        t2 = (4*d)/dist
                                        finish = bezmisc.tpoint(cur,next,t2)
                                        if t2 <= 1:
                                                # add cur point
                                                poly.insert(i-1,['L',list(start)])
                                                i+=1
                                                poly[i-1] = ['L',list(finish)]
                                        
                                        
                                        
                        #else:
                        #        inkex.debug("failed on %i with points %s,%s and %s"%(i,last,cur,next))        
                                        
                        
                        # shift to next point
                        last = cur[:]
                        cur = next[:]
                        i+=1
                        
                return poly

        # --------------------------path export --------------------------
        def toPolyline(self):
                smoothness = self.smoothness # smoothness is in px?
                def curveto(p0,curve,flat):
                        poly = []
                        d = simplepath.formatPath([['M',p0],curve])
                        p = cubicsuperpath.parsePath(d)
                        cspsubdiv.cspsubdiv(p, flat)
                        for sp in p:
                                first = True
                                for csp in sp:
                                        if first:
                                                first = False
                                        else:
                                                for subpath in csp:        
                                                        poly.append(['L',list(subpath)])
                        return poly
                        
                poly = []
                last = self.data[0][1][:]  # start position
                for i in range(0,len(self.data)):
                        cmd = self.data[i][0]
                        params = self.data[i][1]
                        if cmd=='L' or cmd=='M':
                                poly.append([cmd,params])
                                last = params
                        elif cmd=='C':
                                poly.extend(curveto(last,[cmd,params],smoothness))
                                last = [params[4],params[5]]
                        elif cmd=='A':
                                poly.extend(curveto(last,[cmd,params],smoothness))
                                last = [params[5],params[6]]
                        elif cmd=='Z': #don't know
                                        #poly.append(['L',self.data[0][1][:]])
                                        last = last
                        else: #unknown?
                                raise AssertionError("Polyline only handles, (L, C, A,& Z) path cmds, given %s"%(cmd))
                #pprint(poly)
                
                # remove double points
                last = poly[0][1]
                i = 1
                while i < len(poly)-1: # skip last
                        cur = poly[i][1]
                        if cur == last:
                                poly.pop(i)
                        i +=1
                        last = cur[:]
                
                return poly
                
        
        def toHPGL(self):
                # get final polyline
                poly = self.toPolyline()
                poly = self.applyOvercut(poly)
                #poly = self.applyOffset(poly)
                
                # convert to hpgl 
                hpgl = []
                line = poly.pop(0) # first is moveto/pen up
                hpgl.append('PU%d,%d'%(round(line[1][0]*self.scale),round(line[1][1]*self.scale)))
                for line in poly:
                        hpgl.append('PD%d,%d'%(round(line[1][0]*self.scale),round(line[1][1]*self.scale)))
                return hpgl

        def toCutList(self):
                # get final polyline
                poly = self.toPolyline()
                
                cut = []
                for line in poly:
                  cut.append((round(line[1][0]*self.scale, 4),round(line[1][1]*self.scale,4)))
                return [ cut ]

def addPoints(p0,p1):
        p=[]
        for c0,c1 in zip(p0,p1):
                p.append(c0+c1)
        return p
        
