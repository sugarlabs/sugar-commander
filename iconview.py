#! /usr/bin/env python

import pygtk
pygtk.require('2.0')

import getopt
import sys
import gtk
import gtk.gdk

def extract_filename(filename):
    partition_tuple = filename.rpartition('/')
    return partition_tuple[2]

def make_iconview(args):
    # First create an iconview
    view = gtk.IconView()

    # Create a store for our iconview and fill it with stock icons
    store = gtk.ListStore(str, gtk.gdk.Pixbuf)
    i = 0
    while i < len(args):
        scaled_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(args[i], 160, 120)
        filename = extract_filename(args[i])
        store.append(['%s' % filename, scaled_pixbuf])
        i = i + 1

    # Connect our iconview with our store
    view.set_model(store)
    # Map store text and pixbuf columns to iconview
    view.set_text_column(0)
    view.set_pixbuf_column(1)

    # Pack our iconview into a scrolled window
    swin = gtk.ScrolledWindow()
    swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    swin.add_with_viewport(view)
    swin.show_all()

    # pack the scrolled window into a simple dialog and run it
    dialog = gtk.Dialog('IconView Demo')
    close = dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_NONE)
    dialog.set_default_size(1024,800)
    dialog.vbox.pack_start(swin)
    dialog.run()

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "")
        make_iconview(args)
    except getopt.error, msg:
        print msg
        print "This program has no options"
        sys.exit(2)
