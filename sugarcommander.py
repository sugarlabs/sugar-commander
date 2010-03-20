# SugarCommander.py

# Copyright (C) 2010 James D. Simmons
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
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
import os
import logging
import gtk
import pango

from sugar.activity import activity
from sugar.datastore import datastore
from sugar.graphics.alert import NotifyAlert
from gettext import gettext as _
import gobject

COLUMN_TITLE = 0
COLUMN_MIME = 1
COLUMN_JOBJECT = 2

_logger = logging.getLogger('get-ia-books-activity')

class SugarCommander(activity.Activity):
    def __init__(self, handle, create_jobject=True):
        "The entry point to the Activity"
        activity.Activity.__init__(self, handle,  False)
 
        canvas = gtk.Notebook()
        canvas.props.show_border = True
        canvas.props.show_tabs = True
        canvas.show()
        
        self.ls_journal = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,   gobject.TYPE_PYOBJECT)
        tv_journal = gtk.TreeView(self.ls_journal)
        tv_journal.set_rules_hint(True)
        tv_journal.set_search_column(COLUMN_TITLE)
        selection_journal = tv_journal.get_selection()
        selection_journal.set_mode(gtk.SELECTION_SINGLE)
        selection_journal.connect("changed", self.selection_journal_cb)
        renderer = gtk.CellRendererText()
        self.col_journal = gtk.TreeViewColumn(_('Title'), renderer, text=COLUMN_TITLE)
        self.col_journal.set_sort_column_id(COLUMN_TITLE)
        tv_journal.append_column(self.col_journal)
        
        self.col_mime = gtk.TreeViewColumn(_('MIME'), renderer, text=COLUMN_MIME)
        self.col_mime.set_sort_column_id(COLUMN_MIME)
        tv_journal.append_column(self.col_mime)
        
        self.list_scroller_journal = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.list_scroller_journal.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.list_scroller_journal.add(tv_journal)
        
        self.load_journal_table()

        label_attributes = pango.AttrList()
        label_attributes.insert(pango.AttrSize(14000, 0, -1))
        label_attributes.insert(pango.AttrForeground(65535, 65535, 65535, 0, -1))

        tab1_label = gtk.Label(_("Journal"))
        tab1_label.set_attributes(label_attributes)
        tab1_label.show()
        tv_journal.show()
        self.list_scroller_journal.show()
        canvas.append_page(self.list_scroller_journal,  tab1_label)
 
        self._filechooser = gtk.FileChooserWidget(\
            action=gtk.FILE_CHOOSER_ACTION_OPEN, backend=None)
        self._filechooser.set_current_folder("/media")
        self.copy_button = gtk.Button(_("Copy File To The Journal"))
        self.copy_button.connect('clicked',  self.create_journal_entry)
        self.copy_button.show()
        self._filechooser.set_extra_widget(self.copy_button)
        tab2_label = gtk.Label(_("Files"))
        tab2_label.set_attributes(label_attributes)
        tab2_label.show()
        canvas.append_page(self._filechooser,  tab2_label)
        self.set_canvas(canvas)
        self.show_all()
        
        toolbox = activity.ActivityToolbox(self)
        activity_toolbar = toolbox.get_activity_toolbar()
        activity_toolbar.keep.props.visible = False
        activity_toolbar.share.props.visible = False
        self.set_toolbox(toolbox)
        toolbox.show()

    def close(self,  skip_save=False):
        "Override the close method so we don't try to create a Journal entry."
        activity.Activity.close(self,  True)

    def selection_journal_cb(self, selection):
        tv = selection.get_tree_view()
        model = tv.get_model()
        sel = selection.get_selected()
        if sel:
            model, iter = sel
            jobject = model.get_value(iter,COLUMN_JOBJECT)
            fname = jobject.get_file_path()
            self.selected_journal_entry = jobject
            self.selected_title = model.get_value(iter,COLUMN_TITLE)

    def load_journal_table(self):
        ds_objects, num_objects = datastore.find({})
        self.ls_journal.clear()
        for i in xrange (0, num_objects, 1):
            iter = self.ls_journal.append()
            title = ds_objects[i].metadata['title']
            self.ls_journal.set(iter, COLUMN_TITLE, title)
            mime = ds_objects[i].metadata['mime_type']
            self.ls_journal.set(iter, COLUMN_MIME, mime)
            self.ls_journal.set(iter, COLUMN_JOBJECT, ds_objects[i])
 
        self.ls_journal.set_sort_column_id(COLUMN_TITLE,  gtk.SORT_ASCENDING)

    def create_journal_entry(self,  widget,  data=None):
        filename = self._filechooser.get_filename()
        journal_entry = datastore.create()
        journal_title = filename
        journal_entry.metadata['title'] = journal_title
        journal_entry.metadata['title_set_by_user'] = '1'
        journal_entry.metadata['keep'] = '0'
        if filename.endswith('.djvu'):
            journal_entry.metadata['mime_type'] = 'image/vnd.djvu'
        if filename.endswith('.pdf'):
            journal_entry.metadata['mime_type'] = 'application/pdf'
        if filename.endswith('.jpg') or filename.endswith('.jpeg')  \
            or filename.endswith('.JPG')  or filename.endswith('.JPEG') :
            journal_entry.metadata['mime_type'] = 'image/jpeg'
        if filename.endswith('.gif') or filename.endswith('.GIF'):
            journal_entry.metadata['mime_type'] = 'image/gif'
        if filename.endswith('.tiff') or filename.endswith('.TIFF'):
            journal_entry.metadata['mime_type'] = 'image/tiff'
        if filename.endswith('.png') or filename.endswith('.PNG'):
            journal_entry.metadata['mime_type'] = 'image/png'
        if filename.endswith('.zip') or filename.endswith('.ZIP'):
            journal_entry.metadata['mime_type'] = 'application/zip'
        if filename.endswith('.cbz') or filename.endswith('.CBZ'):
            journal_entry.metadata['mime_type'] = 'application/x-cbz'
        if filename.endswith('.cbr') or filename.endswith('.CBR'):
            journal_entry.metadata['mime_type'] = 'application/x-cbr'
        if filename.endswith('.rtf') or filename.endswith('.RTF'):
            journal_entry.metadata['mime_type'] = 'application/rtf'
        if filename.endswith('.txt') or filename.endswith('.TXT'):
            journal_entry.metadata['mime_type'] = 'text/plain'
        journal_entry.metadata['buddies'] = ''
        journal_entry.metadata['preview'] = ''
        journal_entry.file_path = filename
        datastore.write(journal_entry)
        self.load_journal_table()
        self._alert(_('Success'), filename + _(' added to Journal.'))

    def truncate(self,  str,  length):
        if len(str) > length:
            return str[0:length-1] + '...'
        else:
            return str
    
    def _alert(self, title, text=None):
        alert = NotifyAlert(timeout=20)
        alert.props.title = title
        alert.props.msg = text
        self.add_alert(alert)
        alert.connect('response', self._alert_cancel_cb)
        alert.show()

    def _alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)
        self.textview.grab_focus()
