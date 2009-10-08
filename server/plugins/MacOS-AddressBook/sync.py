# Copyright (C) 2009 Anil Madhavapeddy <anil@recoil.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import sys
sys.path.append ("../support")
from pkg_resources import require
require ("simplejson")

import simplejson
from datetime import datetime
import urllib2

from AppKit import *
import AddressBook
import objc
from AddressBook_util import *

# The names of fields in the export, and the corresponding property.
FIELD_NAMES=(
    ('last_name',   AddressBook.kABLastNameProperty),
    ('first_name',  AddressBook.kABFirstNameProperty),
    ('birthday',   AddressBook.kABBirthdayProperty),
    ('company',    AddressBook.kABOrganizationProperty),
    ('job',        AddressBook.kABJobTitleProperty),
    ('calendar',   AddressBook.kABCalendarURIsProperty),
    ('note',       AddressBook.kABNoteProperty),
    ('middle_name', AddressBook.kABMiddleNameProperty),
    ('title',      AddressBook.kABTitleProperty),
)

FIELD_NAMES_ARRAY=(
    ('address',    AddressBook.kABAddressProperty),
)

SERVICES=(
    ('aim', AddressBook.kABAIMInstantProperty, None),
    ('jabber', AddressBook.kABJabberInstantProperty, None),
    ('msn', AddressBook.kABMSNInstantProperty, None),
    ('yahoo!', AddressBook.kABYahooInstantProperty, None),
    ('icq', AddressBook.kABICQInstantProperty, None),
    ('email', AddressBook.kABEmailProperty, None),
    ('phone', AddressBook.kABPhoneProperty, normalize_phone),
)

SERVICES_URL_LABELS=(
    ('twitter', 'LDB:twitter'),
    ('skype', 'LDB:skype'),
    ('facebook', 'LDB:facebook'),
)

def encodeField(value):
    if value is None:
        return None
    
    if isinstance(value, AddressBook.NSDate):
        return float(value.timeIntervalSince1970())
    elif isinstance(value, AddressBook.NSCFDictionary):
        d = {}
        for k in value:
            d[k] = encodeField(value[k])
        return d
    elif isinstance(value, AddressBook.ABMultiValue):
        # A multi-valued property, merge them into a single string
        result = { }
        for i in range(len(value)):
            l = encodeField(value.labelAtIndex_(i))
            if not l or l == "":
               raise ValueError(l)
            if not l in result:
                result[l] = []
            result[l].append(encodeField(value.valueAtIndex_(i)))
        return result
    elif type(value) == objc.pyobjc_unicode:
        return unicode(value)
    else:
        print type(value)
        raise NotImplemented

def getField(p, fieldName):
    return encodeField(p.valueForProperty_(fieldName))

def writeRecord(p, uid, mtime):
    print "NEW: %s" % addressbook_name(p)
    m = { 'c_origin' : 'com.apple.addressbook', 'c_mtime' : mtime, 'c_uid' : uid }
    meta = {}
    for (fieldname, fieldkey) in FIELD_NAMES:
        v = getField(p, fieldkey)
        if v:
            meta[fieldname] = unicode(v)
    for (fieldname, fieldkey) in FIELD_NAMES_ARRAY:
        def fn (p):
          for a in p:
            for x in a.keys():
              meta[fieldname + "_" + x.lower()] = unicode(a[x])
        v = getField(p, fieldkey)
        if v:   
            if type(v) == dict:
                for k in v:
                   fn(v[k])
            else:
                fn(v)
           
    services = []
    for (fieldname, fieldkey, cb) in SERVICES:
        v = getField(p, fieldkey)
        def rc(f,i,c):
          return { 's_ty': f, 's_id':i, 's_co':c }
        def fn(p, fname, cb):
          if not cb:
            cb = lambda x: x
          return map(lambda x: rc(fname,cb(x.lower()),uid) , p)
        if v:   
            if type(v) == dict:
                for k in v:
                    services.extend(fn(v[k], fieldname, cb))
            else:
                services.extend( fn(v[k], fieldname, cb))
        urls = getField(p, AddressBook.kABURLsProperty)
        for (fieldname, fieldkey) in SERVICES_URL_LABELS:
            if urls and fieldkey in urls:
               services.extend (map (lambda x: rc(fieldname, x, uid ), urls[fieldkey]) )

    m['c_meta'] = meta
    imgdata = p.imageData()
    if False and imgdata:
        tiffData = NSImage.alloc().initWithData_(imgdata).TIFFRepresentation()
        bitmap = NSBitmapImageRep.alloc().initWithData_(tiffData)
        fileType = NSPNGFileType
        imageData = bitmap.representationUsingType_properties_(fileType, None)
        picfname = os.path.join(attdir, (uid+".png"))
        picf = open(picfname, 'wb')
        picf.write(str(imageData.bytes()))
        picf.close ()
        print "NEW: %s" % picfname
        m['image'] = (uid+".png")
        m['_att'] = [(uid+".png")]

    return m, services

def main(argv = None):
    """ main entry point """

    ah = urllib2.HTTPBasicAuthHandler()
    ah.add_password(realm='Personal Container',
                    uri='http://localhost:5985/',
                    user='root',
                    passwd='')
    op = urllib2.build_opener(ah)
    urllib2.install_opener(op)

    uri = "http://localhost:5985" 
    book = AddressBook.ABAddressBook.sharedAddressBook()
    for p in book.people():
        mtime_ts = getField(p, AddressBook.kABModificationDateProperty)
        mtime = datetime.fromtimestamp(mtime_ts)
        uid = getField(p, AddressBook.kABUIDProperty)
        tt = mtime.timetuple()
        m, s = writeRecord(p, uid, mtime_ts)
        mj = simplejson.dumps(m)
        try:
          urllib2.urlopen ("%s/c/%s" % (uri, uid), data=mj)
        except urllib2.HTTPError as e: 
          print e.read ()
          print mj
          os.exit(1)
    
if __name__ == "__main__":
    main()
