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
import logging
import os
import gtk
import pango
import mimetypes

from sugar.activity import activity
from sugar.datastore import datastore
from sugar.graphics.alert import NotifyAlert
from sugar.graphics import style
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
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', 500)
        renderer.set_property('width', 500)
        self.col_journal = gtk.TreeViewColumn(_('Title'), renderer, text=COLUMN_TITLE)
        self.col_journal.set_sort_column_id(COLUMN_TITLE)
        tv_journal.append_column(self.col_journal)
        
        self.col_mime = gtk.TreeViewColumn(_('MIME'), renderer, text=COLUMN_MIME)
        self.col_mime.set_sort_column_id(COLUMN_MIME)
        tv_journal.append_column(self.col_mime)
        
        self.list_scroller_journal = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.list_scroller_journal.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.list_scroller_journal.add(tv_journal)
        
        label_attributes = pango.AttrList()
        label_attributes.insert(pango.AttrSize(14000, 0, -1))
        label_attributes.insert(pango.AttrForeground(65535, 65535, 65535, 0, -1))

        tab1_label = gtk.Label(_("Journal"))
        tab1_label.set_attributes(label_attributes)
        tab1_label.show()
        tv_journal.show()
        self.list_scroller_journal.show()
        
        column_table = gtk.Table(rows=1,  columns=2,  homogeneous = False)
        
        image_table = gtk.Table(rows=2,  columns=2,  homogeneous=False)
        self.image = gtk.Image()
        image_table.attach(self.image, 0, 2, 0, 1, xoptions=gtk.FILL|gtk.SHRINK, yoptions=gtk.FILL|gtk.SHRINK, xpadding=10, ypadding=10)

        self.btn_save = gtk.Button(_("Save"))
        self.btn_save.connect('button_press_event',  self.save_button_press_event_cb)
        image_table.attach(self.btn_save,  0, 1, 1, 2,  xoptions=gtk.SHRINK,  yoptions=gtk.SHRINK,  xpadding=10,  ypadding=10)
        self.btn_save.props.sensitive = False
        self.btn_save.show()

        self.btn_delete = gtk.Button(_("Delete"))
        self.btn_delete.connect('button_press_event',  self.delete_button_press_event_cb)
        image_table.attach(self.btn_delete,  1, 2, 1, 2,  xoptions=gtk.SHRINK,  yoptions=gtk.SHRINK,  xpadding=10,  ypadding=10)
        self.btn_delete.props.sensitive = False
        self.btn_delete.show()

        column_table.attach(image_table,  0, 1, 0, 1,  xoptions=gtk.FILL|gtk.SHRINK,  yoptions=gtk.SHRINK,  xpadding=10,  ypadding=10)

        entry_table = gtk.Table(rows=3, columns=2, homogeneous=False)

        title_label = gtk.Label(_("Title"))
        entry_table.attach(title_label, 0, 1, 0, 1, xoptions=gtk.SHRINK, \
                           yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
        title_label.show()
      
        self.title_entry = gtk.Entry(max=0)
        entry_table.attach(self.title_entry, 1, 2, 0, 1, xoptions=gtk.FILL|gtk.SHRINK, \
                           yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
        self.title_entry.connect('key_press_event',  self.key_press_event_cb)
        self.title_entry.show()
    
        description_label = gtk.Label(_("Description"))
        entry_table.attach(description_label, 0, 1, 1, 2, xoptions=gtk.SHRINK, \
                           yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
        description_label.show()
        
        self.description_textview = gtk.TextView()
        self.description_textview.set_wrap_mode(gtk.WRAP_WORD)
        entry_table.attach(self.description_textview, 1, 2, 1, 2, xoptions=gtk.EXPAND|gtk.FILL|gtk.SHRINK, \
                           yoptions=gtk.EXPAND|gtk.FILL|gtk.SHRINK, xpadding=10, ypadding=10)
        self.description_textview.props.accepts_tab = False
        self.description_textview.connect('key_press_event', self.key_press_event_cb)
        self.description_textview.show()

        tags_label = gtk.Label(_("Tags"))
        entry_table.attach(tags_label, 0, 1, 2, 3, xoptions=gtk.SHRINK, \
                           yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
        tags_label.show()
        
        self.tags_textview = gtk.TextView()
        self.tags_textview.set_wrap_mode(gtk.WRAP_WORD)
        entry_table.attach(self.tags_textview, 1, 2, 2, 3, xoptions=gtk.FILL, \
                           yoptions=gtk.EXPAND|gtk.FILL, xpadding=10, ypadding=10)
        self.tags_textview.props.accepts_tab = False
        self.tags_textview.connect('key_press_event',  self.key_press_event_cb)
        self.tags_textview.show()
        
        entry_table.show()

        self.scroller_entry = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.scroller_entry.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.scroller_entry.add_with_viewport(entry_table)
        self.scroller_entry.show()
        
        column_table.attach(self.scroller_entry,  1, 2, 0, 1,  xoptions=gtk.FILL|gtk.EXPAND|gtk.SHRINK,  \
                            yoptions=gtk.FILL|gtk.EXPAND|gtk.SHRINK,  xpadding=10,  ypadding=10)
        image_table.show()
        column_table.show()

        vbox = gtk.VBox(homogeneous=True,  spacing=5)
        vbox.pack_start(column_table)
        vbox.pack_end(self.list_scroller_journal)

        canvas.append_page(vbox,  tab1_label)
 
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

        self.load_journal_table()

        self.selected_journal_entry = None

    def key_press_event_cb(self, entry, event):
        self.btn_save.props.sensitive = True

    def save_button_press_event_cb(self, entry, event):
        self.update_entry()

    def delete_button_press_event_cb(self, entry, event):
        datastore.delete(self.selected_journal_entry.object_id)
        self.title_entry.set_text('')
        description_textbuffer = self.description_textview.get_buffer()
        description_textbuffer.set_text('')
        tags_textbuffer = self.tags_textview.get_buffer()
        tags_textbuffer.set_text('')
        self.image.clear()
        self.image.show()
        self.load_journal_table()

    def update_entry(self):
        needs_update = False
        needs_reload = False
        
        if self.selected_journal_entry is None:
            return

        old_title = self.selected_journal_entry.metadata.get('title', None)
        if old_title != self.title_entry.props.text:
            self.selected_journal_entry.metadata['title'] = self.title_entry.props.text
            self.selected_journal_entry.metadata['title_set_by_user'] = '1'
            needs_update = True
            needs_reload = True

        old_tags = self.selected_journal_entry.metadata.get('tags', None)
        new_tags = self.tags_textview.props.buffer.props.text
        if old_tags != new_tags:
            self.selected_journal_entry.metadata['tags'] = new_tags
            needs_update = True

        old_description = self.selected_journal_entry.metadata.get('description', None)
        new_description = self.description_textview.props.buffer.props.text
        if old_description != new_description:
            self.selected_journal_entry.metadata['description'] = new_description
            needs_update = True

        if needs_update:
            datastore.write(self.selected_journal_entry, update_mtime=False,
                            reply_handler=self._datastore_write_cb,
                            error_handler=self._datastore_write_error_cb)
        if needs_reload:
            self.load_journal_table()

        self.btn_save.props.sensitive = False
    
    def _datastore_write_cb(self):
        pass

    def _datastore_write_error_cb(self, error):
        logging.error('sugarcommander._datastore_write_error_cb: %r' % error)

    def close(self,  skip_save=False):
        "Override the close method so we don't try to create a Journal entry."
        activity.Activity.close(self,  True)

    def selection_journal_cb(self, selection):
        self.btn_delete.props.sensitive = True
        tv = selection.get_tree_view()
        model = tv.get_model()
        sel = selection.get_selected()
        if sel:
            model, iter = sel
            jobject = model.get_value(iter,COLUMN_JOBJECT)
            self.selected_journal_entry = jobject
            self.title_entry.set_text(jobject.metadata['title'])
            description_textbuffer = self.description_textview.get_buffer()
            if jobject.metadata.has_key('description'):
                description_textbuffer.set_text(jobject.metadata['description'])
            else:
                description_textbuffer.set_text('')
            tags_textbuffer = self.tags_textview.get_buffer()
            if jobject.metadata.has_key('tags'):
                tags_textbuffer.set_text(jobject.metadata['tags'])
            else:
                tags_textbuffer.set_text('')
            self.create_preview(jobject.object_id)

    def create_preview(self,  object_id):
        width = style.zoom(320)
        height = style.zoom(240)
        
        jobject = datastore.get(object_id)

        if jobject.metadata.has_key('preview') and \
                len(jobject.metadata['preview']) > 4:
            
            if jobject.metadata['preview'][1:4] == 'PNG':
                preview_data = jobject.metadata['preview']
            else:
                import base64
                preview_data = base64.b64decode(jobject.metadata['preview'])

            fname = os.path.join(self.get_activity_root(), 'instance',  'png_file.png')
            f = open(fname, 'w')
            try:
                f.write(preview_data)
            finally:
                f.close()
            pixbuf = gtk.gdk.pixbuf_new_from_file(fname)
            os.remove(fname)
            scaled_buf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
            self.image.set_from_pixbuf(scaled_buf)
            self.image.show()
        else:
            self.image.clear()
            self.image.show()

    def load_journal_table(self):
        self.btn_save.props.sensitive = False
        self.btn_delete.props.sensitive = False
        ds_mounts = datastore.mounts()
        mountpoint_id = None
        if len(ds_mounts) == 1 and ds_mounts[0]['id'] == 1:
            pass
        else:
            for mountpoint in ds_mounts:
                id = mountpoint['id'] 
                uri = mountpoint['uri']
                if uri.startswith('/home'):
                    mountpoint_id = id
        
        ds_objects, num_objects = datastore.find({})
        self.ls_journal.clear()
        mount = ''
        for i in xrange (0, num_objects, 1):
            if ds_objects[i].metadata.has_key('mountpoint'):
                mount = ds_objects[i].metadata['mountpoint']
            if mountpoint_id is None or mountpoint_id == mount:
                iter = self.ls_journal.append()
                title = ds_objects[i].metadata['title']
                self.ls_journal.set(iter, COLUMN_TITLE, title)
                mime = ds_objects[i].metadata['mime_type']
                self.ls_journal.set(iter, COLUMN_MIME, mime)
                self.ls_journal.set(iter, COLUMN_JOBJECT, ds_objects[i])
 
        self.ls_journal.set_sort_column_id(COLUMN_TITLE,  gtk.SORT_ASCENDING)
        v_adjustment = self.list_scroller_journal.get_vadjustment()
        v_adjustment.value = 0
        return ds_objects[0]

    def create_journal_entry(self,  widget,  data=None):
        filename = self._filechooser.get_filename()
        journal_entry = datastore.create()
        journal_title = filename
        journal_entry.metadata['title'] = journal_title
        journal_entry.metadata['title_set_by_user'] = '1'
        journal_entry.metadata['keep'] = '0'
        file_mimetype = mimetypes.guess_type(filename)
        if not file_mimetype[0] is None:
            journal_entry.metadata['mime_type'] = file_mimetype[0]
        journal_entry.metadata['buddies'] = ''
        journal_entry.metadata['preview'] = ''
        journal_entry.file_path = filename
        datastore.write(journal_entry)
        self.load_journal_table()
        self._alert(_('Success'),  _('%s added to Journal.') % filename)
   
    def _alert(self, title, text=None):
        alert = NotifyAlert(timeout=20)
        alert.props.title = title
        alert.props.msg = text
        self.add_alert(alert)
        alert.connect('response', self._alert_cancel_cb)
        alert.show()

    def _alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)
