#!/usr/bin/env python
"""Discover_Tables.py

Inspects the currently open windows and finds those of interest to us--that is
poker table windows from supported sites.  Returns a list
of Table_Window objects representing the windows found.
"""
#    Copyright 2008, Ray E. Barker

#    
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

########################################################################

#    Standard Library modules
import os
import sys
import re

#    Win32 modules

if os.name == 'nt':
    import win32gui

#    FreePokerTools modules
import Configuration

class Table_Window:
    def __str__(self):
#    __str__ method for testing
        temp = 'TableWindow object\n'
        temp = temp + "    name = %s\n    site = %s\n    number = %s\n    title = %s\n" % (self.name, self.site, self.number, self.title)
#        temp = temp + "    game = %s\n    structure = %s\n    max = %s\n" % (self.game, self.structure, self.max)
        temp = temp + "    width = %d\n    height = %d\n    x = %d\n    y = %d\n" % (self.width, self.height, self.x, self.y)
        if getattr(self, 'tournament', 0):
            temp = temp + "    tournament = %d\n    table = %d" % (self.tournament, self.table)
        return temp

    def get_details(table):
        table.game = 'razz'
        table.max = 8
        table.struture = 'limit'
        table.tournament = 0

def discover(c):
    if os.name == 'posix':
        tables = discover_posix(c)
	return tables
    elif os.name == 'nt':
        tables = discover_nt(c)
	return tables
    elif ox.name == 'mac':
        tables = discover_mac(c)
	return tables
    else: tables = {}
    
    return(tables)

def discover_posix(c):
    """    Poker client table window finder for posix/Linux = XWindows."""
    tables = {}
    for listing in os.popen('xwininfo -root -tree').readlines():
#    xwininfo -root -tree -id 0xnnnnn    gets the info on a single window
        if re.search('Lobby', listing): continue
        if re.search('Instant Hand History', listing): continue
        if not re.search('Logged In as ', listing, re.IGNORECASE): continue
        for s in c.supported_sites.keys():
            if re.search(c.supported_sites[s].table_finder, listing):
                print "listing = ", listing
                print "found ", c.supported_sites[s].site_name
                mo = re.match('\s+([\dxabcdef]+) (.+):.+  (\d+)x(\d+)\+\d+\+\d+  \+(\d+)\+(\d+)', listing)
                if mo.group(2) == '(has no name)': continue
                if re.match('[\(\)\d\s]+', mo.group(2)): continue  # this is a popup
                tw = Table_Window()
                tw.site = c.supported_sites[s].site_name
                tw.number = mo.group(1)
                tw.title  = mo.group(2)
                tw.width  = int( mo.group(3) )
                tw.height = int( mo.group(4) )
                tw.x      = int (mo.group(5) )
                tw.y      = int (mo.group(6) )
                tw.title  = re.sub('\"', '', tw.title)

#    use this eval thingie to call the title bar decoder specified in the config file
                eval("%s(tw)" % c.supported_sites[s].decoder)
                tables[tw.name] = tw
                print "found table named ", tw.name
                print tw
    return tables
#
#    The discover_xx functions query the system and report on the poker clients 
#    currently displayed on the screen.  The discover_posix should give you 
#    some idea how to support other systems.
#
#    discover_xx() returns a dict of TableWindow objects--one TableWindow
#    object for each poker client table on the screen.
#
#    Each TableWindow object must have the following attributes correctly populated:
#    tw.site = the site name, e.g. PokerStars, FullTilt.  This must match the site
#            name specified in the config file.
#    tw.number = This is the system id number for the client table window in the 
#            format that the system presents it.
#    tw.title = The full title from the window title bar.
#    tw.width, tw.height = The width and height of the window in pixels.  This is 
#            the internal width and height, not including the title bar and 
#            window borders.
#    tw.x, tw.y = The x, y (horizontal, vertical) location of the window relative 
#            to the top left of the display screen.  This also does not include the
#            title bar and window borders.  To put it another way, this is the 
#            screen location of (0, 0) in the working window.

def win_enum_handler(hwnd, titles):
    titles[hwnd] = win32gui.GetWindowText(hwnd)

def child_enum_handler(hwnd, children):
    print hwnd, win32.GetWindowRect(hwnd)

def discover_nt(c):
    """    Poker client table window finder for Windows."""
#
#    I cannot figure out how to get the inside dimensions of the poker table
#    windows.  So I just assume all borders are 3 thick and all title bars
#    are 29 high.  No doubt this will be off when used with certain themes.
#
    b_width = 3
    tb_height = 29
    titles = {}
    tables = {}
    win32gui.EnumWindows(win_enum_handler, titles)
    for hwnd in titles.keys():
        if re.search('Logged In as', titles[hwnd]) and not re.search('Lobby', titles[hwnd]):
            tw = Table_Window()
#            tw.site = c.supported_sites[s].site_name
            tw.number = hwnd
            (x, y, width, height) = win32gui.GetWindowRect(hwnd)
            tw.title  = titles[hwnd]
            tw.width  = int( width ) - 2*b_width
            tw.height = int( height ) - b_width - tb_height
            tw.x      = int( x ) + b_width
            tw.y      = int( y ) + tb_height
            eval("%s(tw)" % "pokerstars_decode_table")
            tw.site = "PokerStars"

		
            tables[tw.name] = tw
    return tables

def discover_mac(c):
    """    Poker client table window finder for Macintosh."""
    tables = {}
    return tables

def pokerstars_decode_table(tw):
#    extract the table name OR the tournament number and table name from the title
#    other info in title is redundant with data in the database 
    title_bits = re.split(' - ', tw.title)
    name = title_bits[0]
    mo = re.search('Tournament (\d+) Table (\d+)', name)
    if mo:
        tw.tournament = int( mo.group(1) )
        tw.table      = int( mo.group(2) )
        tw.name       = name
    else:
        tw.tournament = None
        for pattern in [' no all-in', ' fast', ',', ' 50BB min']:
            name = re.sub(pattern, '', name)
        name = re.sub('\s+$', '', name)
        tw.name = name

    mo = re.search('(Razz|Stud H/L|Stud|Omaha H/L|Omaha|Hold\'em|5-Card Draw|Triple Draw 2-7 Lowball)', tw.title)
    
    tw.game = mo.group(1).lower()
    tw.game = re.sub('\'', '', tw.game)
    tw.game = re.sub('h/l', 'hi/lo', tw.game)
    
    mo = re.search('(No Limit|Pot Limit)', tw.title)
    if mo:
        tw.structure = mo.group(1).lower()
    else:
        tw.structure = 'limit'
        
    tw.max = None
    if tw.game in ('razz', 'stud', 'stud hi/lo'):
        tw.max = 8
    elif tw.game in ('5-card draw', 'triple draw 2-7 lowball'):
        tw.max = 6
    elif tw.game == 'holdem':
        pass
    elif tw.game in ('omaha', 'omaha hi/lo'):
        pass

def fulltilt_decode_table(tw):
#    extract the table name OR the tournament number and table name from the title
#    other info in title is redundant with data in the database 
    title_bits = re.split(' - ', tw.title)
    name = title_bits[0]
    tw.tournament = None
#    for pattern in [r' (6 max)', r' (heads up)', r' (deep)', r' (deep hu)', r' (deep 6)',
#                    r' (2)', r' (edu)', r' (edu, 6 max)', r' (6)' ]:
#        name = re.sub(pattern, '', name)
    (tw.name, trash) = name.split(r' (', 1)
    tw.name = tw.name.rstrip()

if __name__=="__main__":
    c = Configuration.Config()
    tables = discover(c)
    
    for t in tables.keys():
        print "t = ", t
        print tables[t]

    print "press enter to continue"
    sys.stdin.readline()