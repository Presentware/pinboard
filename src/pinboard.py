#!/usr/bin/env python
import wx
import wx.media

import mimetypes
import random
import os
import os.path
import subprocess, sys
import json
            
class PinboardFrame(wx.Frame):
	apppath = os.path.dirname(os.path.realpath(__file__))+"/"
	pinboard = {"content": [], "links": []}
	hitboxes = []
	holdedcontent = None
	selectedcontent = None
	modified = False
	dc = None

	def __init__(self):
		super(PinboardFrame, self).__init__(None, title='Pinboard', size=(800, 600))
		self.SetIcon(wx.Icon(self.apppath+"ressources/icon.svg"))

		self.Bind(wx.EVT_PAINT, lambda _: self.drawPinboard())
		self.Bind(wx.EVT_SIZE, lambda _: self.Refresh())
		self.Bind(wx.EVT_LEFT_DOWN, lambda e: self.changeHold(True, e))
		self.Bind(wx.EVT_MOTION, self.moveHoldedContent)
		self.Bind(wx.EVT_LEFT_UP, lambda e: self.changeHold(False, e))
		self.Bind(wx.EVT_LEFT_DCLICK, self.openContent)
		self.Bind(wx.EVT_RIGHT_DOWN, self.detectSelection)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.detectSelection)
		
		menu = {"File":
				{"New Project": lambda _: self.newProject(),
				 "Open Project": lambda _: self.openProject(),
				 "Save Project as...": lambda _: self.saveProjectAs(),
				 "Take a screenshot": lambda _: self.screenshot(),
				 "Separator": None,
				 "Exit": lambda _: wx.Exit()},
			"Content":
				{"Add Content": lambda _: self.addContent(),
				 "Remove Content": lambda _: self.removeContent()},
			"Style":
				{"Change background": lambda _: self.changeBackground(),
				 "Change lines color": lambda _: self.changeLineColor()},
			"Settings":
				{"Use Embed Media Player": "Not selected"}
			}
		self.createMenu(menu)

		droptarget = DropTarget(self)
		self.SetDropTarget(droptarget)
		self.Centre()
		self.Show()
		
	def createMenu(self, menu):
		self.menubar = wx.MenuBar()
		for key in menu.keys():
			mainmenu = wx.Menu()
			for keybis, value in menu[key].items():
				if keybis=="Separator":
					mainmenu.AppendSeparator()
					continue
				itemkind = wx.ITEM_CHECK if value=="Selected" or value=="Not selected" else wx.ITEM_NORMAL
				menuitem = wx.MenuItem(mainmenu, wx.ID_ANY, keybis, kind=itemkind)
				if value!="Selected" and value!="Not selected":
					self.Bind(wx.EVT_MENU, value, menuitem)
				mainmenu.Append(menuitem)
				if value=="Selected": menuitem.Check()
			self.menubar.Append(mainmenu, key)
		self.SetMenuBar(self.menubar)
		
	def drawPinboard(self):
		self.hitboxes.clear()
		width, height = self.GetSize()
		self.dc = wx.PaintDC(self)
		
		image = wx.Bitmap(os.path.expanduser(self.defaultOrGet(self.apppath+"ressources/background.svg", "style", "background")))
		if not image.IsOk():
			self.pinboard["style"].pop('background', None)
			return
		image = image.ConvertToImage().Scale(width, height, wx.IMAGE_QUALITY_HIGH)
		self.dc.DrawBitmap(wx.Bitmap(image), 0, 0, True)

		i = 0
		for content in self.pinboard["content"]:
			self.drawImage(PinboardFrame.getFileIcon(content["path"]), int(content["x"]*width), int(content["y"]*height), i)
			i += 1

		for point1, point2 in self.pinboard["links"]:
			x1 = int(self.pinboard["content"][point1]["x"]*width)
			x2 = int(self.pinboard["content"][point2]["x"]*width)
			y1 = int(self.pinboard["content"][point1]["y"]*height)
			y2 = int(self.pinboard["content"][point2]["y"]*height)
			colour = self.defaultOrGet("red", "style", "lineColor")
			self.dc.SetPen(wx.Pen(wx.Colour(colour), 2))
			self.dc.DrawLine(x1, y1, x2, y2)
			
	def drawImage(self, path, x, y, i):
		image = wx.Bitmap(path)
		if not image.IsOk():
			self.pinboard["content"].pop(i)
			return
		image = image.ConvertToImage()
		
		width, height = image.GetSize()
		if width>height:
			image = image.Scale(150, 150*height//width, wx.IMAGE_QUALITY_HIGH)
		else:
			image = image.Scale(150*width//height, 150, wx.IMAGE_QUALITY_HIGH)
			
		width, height = image.GetSize()
		self.dc.DrawBitmap(wx.Bitmap(image), x-width//2, y, True)
		
		pin = wx.Bitmap(self.apppath+"ressources/pin.svg")
		self.dc.DrawBitmap(pin,x,y-30,True)
		
		if self.selectedcontent == i:
			self.dc.SetPen(wx.Pen(wx.CYAN, 3))
			self.dc.SetBrush(wx.Brush(wx.CYAN, style=wx.TRANSPARENT))
			self.dc.DrawRectangle(x-width//2, y, width, height)
		
		self.hitboxes.append((x-width//2, y, x+width//2, y+height))
			
	def getFileIcon(path):
		path = os.path.expanduser(path)
		if not os.path.exists(path):
			return PinboardFrame.apppath+'ressources/not-found.svg'
		if os.path.isdir(path):
			return PinboardFrame.apppath+'ressources/folder.svg'
		if path.endswith(".pinb"):
			return 'ressources/pinb-icon.svg'
		mediaType = SimpleMediaPlayer.getMediaType(path)
		if mediaType == 'image':
			return path
		if mediaType == 'text':
			return PinboardFrame.apppath+'ressources/text-icon.svg'
		if mediaType == 'audio':
			return PinboardFrame.apppath+'ressources/music-icon.svg'
		if mediaType == 'video':
			return PinboardFrame.apppath+'ressources/video-icon.svg'
		return PinboardFrame.apppath+'ressources/unknown.svg'
	
	def detectClickId(self, x, y):
		i = 0
		for coor in self.hitboxes[::-1]:
			if coor[0] <= x <= coor[2] and coor[1] <= y <= coor[3]:
				return len(self.hitboxes)-i-1
			i += 1
		return None

	def detectSelection(self, event):
		self.modified = True
		i = self.detectClickId(event.GetX(), event.GetY())
		if self.selectedcontent == None:
			self.selectedcontent = i
		elif self.selectedcontent == i:
			self.removeContent()
		elif i != None:
			if [self.selectedcontent, i] in self.pinboard["links"]: self.pinboard["links"].remove([self.selectedcontent, i])
			elif [i, self.selectedcontent] in self.pinboard["links"]: self.pinboard["links"].remove([i, self.selectedcontent])
			else: self.pinboard["links"].append([self.selectedcontent, i])
			self.selectedcontent = None
		else:
			self.selectedcontent = None
		self.Refresh()
		
	def changeHold(self, holdStarted, event):
		self.holdedcontent = None
		self.selectedcontent = None
		if holdStarted:
			self.holdedcontent = self.detectClickId(event.GetX(), event.GetY())
	
	def moveHoldedContent(self, event):
		if self.holdedcontent != None:
			self.modified = True
			width, height = self.GetSize()
			x, y = event.GetX()/width, event.GetY()/height
			self.pinboard["content"][self.holdedcontent]["x"] = x
			self.pinboard["content"][self.holdedcontent]["y"] = y
			self.Refresh()
			
	def openContent(self, event):
		i = self.detectClickId(event.GetX(), event.GetY())
		if i == None: return
		path = os.path.expanduser(self.pinboard["content"][i]["path"])
		playercheck = self.GetMenuBar().FindItemById(self.GetMenuBar().FindMenuItem("Settings", "Use Embed Media Player"))
		if path.endswith(".pinb"):
			with open(path) as file:
				if self.warningErase():
					self.modified = False
					self.pinboard = json.load(file)
					self.Refresh()
		elif playercheck.IsChecked() and (PinboardFrame.getFileIcon(path).endswith("icon.svg") or SimpleMediaPlayer.getMediaType(path) == "image"):
			SimpleMediaPlayer(self.pinboard["content"][i])
		elif PinboardFrame.getFileIcon(path) != "ressources/not-found.svg":
			opener = "open" if sys.platform == "darwin" else "xdg-open"
			subprocess.call([opener, path])
	
	def newProject(self):
		if self.warningErase():
			self.modified = False
			self.pinboard = {"content": [], "links": []}
			self.holdedcontent = None
			self.selectedcontent = None
			self.Refresh()

	def openProject(self):
		if self.warningErase():
			with wx.FileDialog(self, "Open Pinboard file", wildcard="PINB file (*.pinb)|*.pinb", size=(800,600),
				style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
					if fileDialog.ShowModal() == wx.ID_CANCEL: return
					path = fileDialog.GetPath()
			with open(path) as file:
				if not PinboardFrame.isInHome(path): return
				self.modified = False
				self.pinboard = json.load(file)
				self.Refresh()
	
	def saveProjectAs(self):
		with wx.FileDialog(self, "Save Pinboard file", wildcard="PINB file (*.pinb)|*.pinb", size=(800,600),
				style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL: return
			path = fileDialog.GetPath()
			if not path.endswith(".pinb"): path += ".pinb"
		with open(path, 'w+') as file:
			if not PinboardFrame.isInHome(path): return
			json.dump(self.pinboard, file, indent=4)
			self.modified = False

	def addContent(self):
		with wx.FileDialog(self, "Add content", wildcard="Any file|*", size=(800,600),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
				if fileDialog.ShowModal() == wx.ID_CANCEL: return
				path = fileDialog.GetPath()

		with open(path) as file:
			if not PinboardFrame.isInHome(path): return
			self.modified = True
			self.pinboard["content"].append({"path": "~/"+os.path.relpath(path, os.path.expanduser("~")),
							 "x": random.uniform(0.1, 0.8),
							 "y": random.uniform(0.1, 0.8)})
			self.Refresh()
			
	def removeContent(self):
		if self.selectedcontent != None:
			self.pinboard["content"].pop(self.selectedcontent)
			self.pinboard["links"] = list(filter(lambda t: self.selectedcontent not in t, self.pinboard["links"]))
			self.pinboard["links"] = list(map(lambda t: [t[0] if t[0] < self.selectedcontent else t[0]-1, t[1] if t[1] < self.selectedcontent else t[1]-1], self.pinboard["links"]))
			self.selectedcontent = None
			self.Refresh()
		else:
			wx.MessageBox("Right click on an element in order to select it (You can also double right click it if you want to delete it)")
	
	def screenshot(self):
		with wx.FileDialog(self, "Save project capture", size=(800,600),
				   wildcard="PNG file (*.png)|*.png|JPEG file (*.jpg, *.jpeg)|*.jpg;*.jpeg|BMP file (*.bmp)|*.bmp",
				   style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL: return
			path = fileDialog.GetPath()
			filefilter = fileDialog.GetFilterIndex()
		if PinboardFrame.isInHome(path): return
		width, height = self.GetSize()
		bmp = wx.Bitmap(width, height-self.menubar.GetRect()[3]-40)
		memDC = wx.MemoryDC()
		memDC.SelectObject(bmp)
		memDC.Blit(0, 0, width, height-self.menubar.GetRect()[3]-40, self.dc, 0, self.menubar.GetRect()[3])
		memDC.SelectObject(wx.NullBitmap)
		if filefilter == 0:
			if not path.endswith(".png"): path += ".png"
			bmp.ConvertToImage().SaveFile(path, wx.BITMAP_TYPE_PNG)
		if filefilter == 1:
			if not path.endswith(".jpg") and not path.endswith(".jpeg") : path += ".jpg"
			bmp.ConvertToImage().SaveFile(path, wx.BITMAP_TYPE_JPEG)
		if filefilter == 2:
			if not path.endswith(".bmp"): path += ".bmp"
			bmp.ConvertToImage().SaveFile(path, wx.BITMAP_TYPE_BMP)
			
	def changeBackground(self):
		with wx.FileDialog(self, "Open image file", size=(800,600),
				   wildcard="PNG file (*.png)|*.png|JPEG file (*.jpg, *.jpeg)|*.jpg;*.jpeg|BMP file (*.bmp)|*.bmp|SVG file (*.svg)|*.svg",
				   style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
				if fileDialog.ShowModal() == wx.ID_CANCEL: return
				if not PinboardFrame.isInHome(fileDialog.GetPath()): return
				path = "~/"+os.path.relpath(fileDialog.GetPath(), os.path.expanduser("~"))
				if not "style" in self.pinboard: self.pinboard["style"] = dict()
				self.pinboard["style"]["background"] = path
				self.Refresh()
	
	def changeLineColor(self):
		dialog = wx.ColourDialog(self)
		dialog.GetColourData().SetChooseFull(True)
		if dialog.ShowModal() == wx.ID_OK:
			if not "style" in self.pinboard: self.pinboard["style"] = dict()
			self.pinboard["style"]["lineColor"] = dialog.GetColourData().GetColour().GetAsString()
			

	def warningErase(self):
		if self.modified: return wx.MessageBox("This action will erase the previous project. Proceed?", "Please confirm", wx.ICON_QUESTION | wx.YES_NO, self) == wx.YES
		return True
		
	def isInHome(path):
		if path.startswith('/home/'): return True
		wx.MessageBox("The file "+path+" cannot be accessed, this app can only access files contained in /home/")
		return False
	
	def defaultOrGet(self, defaultValue, *args):
		value = self.pinboard
		for key in args:
			if not key in value:
				return defaultValue
			value = value[key]
		return value

class SimpleMediaPlayer(wx.Frame):
	def __init__(self, content):
		path = os.path.expanduser(content["path"])
		mediatype = SimpleMediaPlayer.getMediaType(path)
		super(SimpleMediaPlayer, self).__init__(None, title=path)
		self.SetPosition(wx.Point(int(wx.DisplaySize()[0]*content["x"]), int(wx.DisplaySize()[1]*content["y"])))
		
		if mediatype == 'text':
			panel = wx.Panel(self)
			textarea = wx.TextCtrl(panel, style=wx.TE_MULTILINE, pos=(10, 10), size=(580, 340))
			with open(path) as file:
				textarea.WriteText(file.read())
			self.SetMinSize((600, 400))
			self.SetMaxSize((600, 400))
		if mediatype == 'image':
			image = wx.Bitmap(path).ConvertToImage()
			width, height = image.GetWidth(), image.GetHeight()
			ratiow, ratioh = width/max(width,height*3/2), (height*3/2)/max(width,height*3/2)
			if (ratiow==1): width, height = 600, int(ratioh*400)
			else: width, height = int(ratiow*600), 400
			image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
			wx.StaticBitmap(self, -1, wx.Bitmap(image), (0, 0))
			self.SetMinSize((width, height+30))
			self.SetMaxSize((width, height+30))
		if mediatype == 'audio':
			self.media = wx.media.MediaCtrl(self)
			self.SetMinSize((100, 130))
			self.SetMaxSize((100, 130))
			button = wx.Button(self, size=(100, 100), label="| |")
			button.Bind(wx.EVT_LEFT_DOWN, lambda _: self.pauseOrPlay(button))
			self.media.Bind(wx.media.EVT_MEDIA_LOADED, lambda _: self.media.Play())
			self.media.Bind(wx.media.EVT_MEDIA_FINISHED, lambda _: self.Destroy())
			self.media.Load(path)
		if mediatype == 'video':
			self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
			self.panel = wx.Panel(self,size=(600,340))
			self.panel.Layout()
			self.media = wx.media.MediaCtrl(self.panel,size=(600,340))
			self.media.Bind(wx.media.EVT_MEDIA_LOADED, lambda _: self.media.Play())
			self.media.Bind(wx.media.EVT_MEDIA_FINISHED, lambda _: self.Destroy())
			self.media.Bind(wx.EVT_LEFT_DOWN, lambda _: self.pauseOrPlay(None))
			self.media.Load(path)
			self.SetSize((600, 370))
			self.SetMinSize((600, 370))
			self.SetMaxSize((600, 370))
		
		self.Show()

	def getMediaType(path):
		filetype = mimetypes.guess_type(path)[0]
		if filetype != None:
			filetype = filetype.split('/')[0]
		return filetype
		
	def pauseOrPlay(self, button):
		if self.media.GetState() == wx.media.MEDIASTATE_PLAYING:
			self.media.Pause()
			if button != None:
				button.SetLabel("▶")
		else:
			self.media.Play()
			if button != None:
				button.SetLabel("| |")

class DropTarget(wx.FileDropTarget):
	def __init__(self, frame):
		wx.FileDropTarget.__init__(self)
		self.frame = frame

	def OnDropFiles(self, x, y, filenames):
		for path in filenames:
			if not PinboardFrame.isInHome(path): continue
			self.frame.pinboard["content"].append( {"path": "~/"+os.path.relpath(path, os.path.expanduser("~")),
								"x": random.uniform(0.1, 0.8),
								"y": random.uniform(0.1, 0.8)} )
		self.frame.modified = True
		self.frame.Refresh()
		return True

if __name__ == '__main__':
	app = wx.App()
	app.SetAppName("Pinboard")
	app.SetTopWindow(PinboardFrame())
	app.MainLoop()
