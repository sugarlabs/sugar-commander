# SugarCommander.py

# Copyright (C) 2014 James D. Simmons <nicestep@gmail.com>
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
import time
from sugar3.activity import activity
from sugar3.activity.widgets import ActivityToolbar, StopButton
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import cairo
from gi.repository import Pango
from gi.repository import PangoCairo
from gi.repository import GdkPixbuf
from sugar3.activity import widgets
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3 import mime
from sugar3.datastore import datastore
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics import style
from gettext import gettext as _
import pygame
import zipfile
from gi.repository import GObject
import dbus

COLUMN_TITLE = 0
COLUMN_SIZE = 1
COLUMN_MIME = 2
COLUMN_JOBJECT = 3

ARBITRARY_LARGE_HEIGHT = 10000
JPEG_QUALITY = 80

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

_logger = logging.getLogger('sugar-commander')

class SugarCommander(activity.Activity):
    def __init__(self, handle, create_jobject=True):
        "The entry point to the Activity"
        activity.Activity.__init__(self, handle)
        self.selected_journal_entry = None
        self.selected_path = None
        self.update_log_entries = ''
        self.close_requested = False
        
        canvas = Gtk.Notebook()
        canvas.props.show_border = True
        canvas.props.show_tabs = True
        canvas.show()
        
        self.ls_journal = Gtk.ListStore(str,  GObject.TYPE_UINT64,  str,  GObject.TYPE_PYOBJECT)
        self.tv_journal = Gtk.TreeView(self.ls_journal)
        self.tv_journal.set_rules_hint(True)
        self.tv_journal.set_search_column(COLUMN_TITLE)
        self.selection_journal = self.tv_journal.get_selection()
        self.selection_journal.set_mode(Gtk.SelectionMode.SINGLE)
        self.selection_journal.connect("changed", self.selection_journal_cb)
        renderer = Gtk.CellRendererText()
        renderer.set_property('wrap-mode', Pango.WrapMode.WORD)
        renderer.set_property('wrap-width', 500)
        renderer.set_property('width', 500)
        self.col_journal = Gtk.TreeViewColumn(_('Title'), renderer, 
                                              text=COLUMN_TITLE)
        self.col_journal.set_sort_column_id(COLUMN_TITLE)
        self.tv_journal.append_column(self.col_journal)
        
        size_renderer = Gtk.CellRendererText()
        size_renderer.set_property('width', 100)
        size_renderer.set_property('alignment', Pango.Alignment.RIGHT)
        size_renderer.set_property('xalign', 0.8)
        self.col_size = Gtk.TreeViewColumn(_('Size (KB)'), size_renderer, 
                                           text=COLUMN_SIZE)
        self.col_size.set_sort_column_id(COLUMN_SIZE)
        self.tv_journal.append_column(self.col_size)
        
        mime_renderer = Gtk.CellRendererText()
        mime_renderer.set_property('width', 200)
        self.col_mime = Gtk.TreeViewColumn(_('MIME Type'), mime_renderer, 
                                           text=COLUMN_MIME)
        self.col_mime.set_sort_column_id(COLUMN_MIME)
        self.tv_journal.append_column(self.col_mime)
        
        self.list_scroller_journal = Gtk.ScrolledWindow(
                        hadjustment=None, vadjustment=None)
        self.list_scroller_journal.set_policy(
                    Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.list_scroller_journal.add(self.tv_journal)
        
        tab1_label = Gtk.Label()
        tab1_label.set_markup("<span foreground='#FFF'" \
                        " size='14000'>" +_("Journal") + "</span>")
        tab1_label.show()
        self.tv_journal.show()
        self.list_scroller_journal.show()
        
        column_table = Gtk.Table(2,  2,  False)
        column_table.set_col_spacings(10)
        column_table.set_row_spacings(10)
        
        image_table = Gtk.Table(2,  2,  False)
        
        self.btn_resize = Gtk.Button(_("Resize To Width"))
        self.btn_resize.connect('button_press_event',  
                              self.resize_button_press_event_cb)
        image_table.attach(self.btn_resize,  0, 1, 2, 3)

        self.resize_width_entry = Gtk.Entry()
        self.resize_width_entry.set_max_length(4)
        image_table.attach(self.resize_width_entry, 1, 2, 2, 3)
        self.resize_width_entry.set_text('600')
        self.resize_width_entry.connect('key_press_event', 
                                    self.resize_key_press_event_cb)

        self.btn_save = Gtk.Button(_("Save"))
        self.btn_save.connect('button_press_event',  
                              self.save_button_press_event_cb)
        image_table.attach(self.btn_save,  0, 1, 3, 4)
        self.btn_save.props.sensitive = False
        self.btn_save.show()

        self.btn_delete = Gtk.Button(_("Delete"))
        self.btn_delete.connect('button_press_event',  
                                self.delete_button_press_event_cb)
        image_table.attach(self.btn_delete,  1, 2, 3, 4)
        self.btn_delete.props.sensitive = False
        self.btn_delete.show()

        self.image = Gtk.Image()
        image_table.set_col_spacings(10)
        image_table.set_row_spacings(10)
        image_table.attach(self.image, 0, 2, 0, 1)

        self.dimension_label = Gtk.Label("")
        image_table.attach(self.dimension_label,  0, 2, 1, 2)

        entry_table = Gtk.Table(2,  2,  False)
        entry_table.set_col_spacings(10)
        entry_table.set_row_spacings(10)

        title_label = Gtk.Label(_("Title"))
        entry_table.attach(title_label, 0, 1, 0, 1)
        title_label.show()
      
        self.title_entry = Gtk.Entry()
        entry_table.attach(self.title_entry, 1, 2, 0, 1)
        self.title_entry.connect('key_press_event',  
                                 self.key_press_event_cb)
        self.title_entry.show()
    
        description_label = Gtk.Label(_("Description"))
        entry_table.attach(description_label, 0, 1, 1, 2)
        description_label.show()
        
        self.description_textview = Gtk.TextView()
        self.description_textview.set_wrap_mode(Pango.WrapMode.WORD)
        entry_table.attach(self.description_textview, 1, 2, 1, 2)
        self.description_textview.props.accepts_tab = False
        self.description_textview.connect('key_press_event', 
                                          self.key_press_event_cb)
        self.description_textview.show()

        tags_label = Gtk.Label(_("Tags"))
        entry_table.attach(tags_label, 0, 1, 2, 3)
        tags_label.show()
        
        self.tags_textview = Gtk.TextView()
        self.tags_textview.set_wrap_mode(Pango.WrapMode.WORD)
        entry_table.attach(self.tags_textview, 1, 2, 2, 3)
        self.tags_textview.props.accepts_tab = False
        self.tags_textview.connect('key_press_event', 
                                    self.key_press_event_cb)
        self.tags_textview.show()
        
        entry_table.show()

        scroller_image = Gtk.ScrolledWindow(
                                                hadjustment=None, vadjustment=None)
        scroller_image.set_hexpand(False)
        scroller_image.set_vexpand(True)
        scroller_image.add_with_viewport(image_table)
        scroller_image.show()
        
        self.scroller_entry = Gtk.ScrolledWindow(
                                                hadjustment=None, vadjustment=None)
        self.scroller_entry.set_hexpand(False)
        self.scroller_entry.set_vexpand(True)
        self.scroller_entry.add_with_viewport(entry_table)
        self.scroller_entry.show()
        
        column_table.attach(scroller_image,  0, 1, 0, 1)

        column_table.attach(self.scroller_entry,  1, 2, 0, 1)
                            
        image_table.show()
        column_table.show()
        self.btn_resize.hide()
        self.resize_width_entry.hide()

        vbox = Gtk.VBox(homogeneous=True,  spacing=5)
        vbox.pack_start(column_table,  expand=True, fill=True, padding=0)
        vbox.pack_end(self.list_scroller_journal,  expand=True, fill=True, padding=0)

        canvas.append_page(vbox,  tab1_label)
 
        self._filechooser = Gtk.FileChooserWidget(
            action=Gtk.FileChooserAction.OPEN)
        self._filechooser.set_current_folder("/media")
        self.copy_button = Gtk.Button(_("Copy File To The Journal"))
        self.copy_button.connect('clicked',  self.create_journal_entry)
        self.copy_button.show()
        self._filechooser.set_extra_widget(self.copy_button)
        preview = Gtk.Image()
        self._filechooser.set_preview_widget(preview)
        self._filechooser.connect("update-preview", 
                                  self.update_preview_cb, preview)
        tab2_label = Gtk.Label()
        tab2_label.set_markup("<span foreground='#FFF'" \
                        " size='14000'>" + _("Files")  + "</span>")
        tab2_label.show()
        canvas.append_page(self._filechooser,  tab2_label)

        self.set_canvas(canvas)
        self.show_all()
        self.btn_resize.hide()
        self.resize_width_entry.hide()
        self.dimension_label.hide()
        
        toolbox = ActivityToolbar(self)

        stop_button = StopButton(self)
        stop_button.show()
        toolbox.insert(stop_button, -1)

        self.set_toolbar_box(toolbox)
        toolbox.show()

        self.load_journal_table()

        bus = dbus.SessionBus()
        remote_object = bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH)
        _datastore = dbus.Interface(remote_object, DS_DBUS_INTERFACE)
        _datastore.connect_to_signal('Created', self.datastore_created_cb)
        _datastore.connect_to_signal('Updated', self.datastore_updated_cb)
        _datastore.connect_to_signal('Deleted', self.datastore_deleted_cb)

        self.selected_journal_entry = None

    def update_preview_cb(self, file_chooser, preview):
        filename = file_chooser.get_preview_filename()
        try:
            file_mimetype = mime.get_for_file(filename)
            if file_mimetype.startswith('image/')  and file_mimetype != 'image/vnd.djvu':
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 
                                                          style.zoom(320), style.zoom(240))
                preview.set_from_pixbuf(pixbuf)
                have_preview = True
            elif file_mimetype  == 'application/x-cbz':
                fname = self.extract_image(filename)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(fname, 
                                                          style.zoom(320), style.zoom(240))
                preview.set_from_pixbuf(pixbuf)
                have_preview = True
                os.remove(fname)
            else:
                have_preview = False
        except:
            have_preview = False
        file_chooser.set_preview_widget_active(have_preview)
        return

    def key_press_event_cb(self, entry, event):
        self.btn_save.props.sensitive = True

    def resize_key_press_event_cb(self, entry, event):
        keyname = Gtk.Gdk.keyval_name(event.keyval)
        if ((keyname < '0' or keyname > '9') and keyname != 'BackSpace'
            and keyname != 'Left' and keyname != 'Right'
            and keyname != 'KP_Left' and keyname != 'KP_Right'
            and keyname != 'Delete' and keyname != 'End'
            and keyname != 'KP_End' and keyname != 'Home'
            and keyname != 'KP_Home' and keyname != 'KP_Delete'):
            return True
        else:
            return False

    def resize_button_press_event_cb(self, entry, event):
        jobject = self.selected_journal_entry
        filename = jobject.get_file_path()
        im = pygame.image.load(filename)
        image_width, image_height = im.get_size()
        resize_to_width = int(self.resize_width_entry.get_text())
        if (image_width < resize_to_width):
            self.alert(_('Error'),  _('Image cannot be made larger, only smaller.')) 
            return
        tempfile = os.path.join(self.get_activity_root(), 'instance',
                            'tmp%i' % time.time())
        try:
            scaled_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, resize_to_width, ARBITRARY_LARGE_HEIGHT)
            scaled_pixbuf.save(tempfile, "jpeg", {"quality":"%d" % JPEG_QUALITY})
        except:
            print('File could not be converted')
            return

        jobject.file_path = tempfile
        jobject.metadata['mime_type'] = 'image/jpeg'
        im = pygame.image.load(tempfile)
        image_width, image_height = im.get_size()
        self.dimension_label.set_text(str(image_width) + "x" + str(image_height))
        self.dimension_label.show()
        datastore.write(jobject, update_mtime=False,
                        reply_handler=self.datastore_write_cb,
                        error_handler=self.datastore_write_error_cb)
        title = jobject.metadata.get('title', None)
        self.update_log_entries += '\n' + _('Entry %s resized.') % title
        
    def save_button_press_event_cb(self, entry, event):
        self.update_entry()

    def delete_button_press_event_cb(self, entry, event):
        datastore.delete(self.selected_journal_entry.object_id)

    def datastore_created_cb(self, uid):
        new_jobject = datastore.get(uid)
        iter = self.ls_journal.append()
        title = new_jobject.metadata['title']
        self.ls_journal.set(iter, COLUMN_TITLE, title)
        mime = new_jobject.metadata['mime_type']
        self.ls_journal.set(iter, COLUMN_MIME, mime)
        self.ls_journal.set(iter, COLUMN_JOBJECT, new_jobject)
        size = self.get_size(new_jobject) / 1024
        self.ls_journal.set(iter, COLUMN_SIZE, size)
        
    def datastore_updated_cb(self,  uid):
        new_jobject = datastore.get(uid)
        iter = self.ls_journal.get_iter_first()
        for row in self.ls_journal:
            jobject = row[COLUMN_JOBJECT]
            if jobject.object_id == uid:
                title = jobject.metadata['title']
                self.ls_journal.set(iter, COLUMN_TITLE, title)
                mime = jobject.metadata['mime_type']
                self.ls_journal.set(iter, COLUMN_MIME, mime)
                size = self.get_size(jobject) / 1024
                self.ls_journal.set(iter, COLUMN_SIZE, size)
            iter = self.ls_journal.iter_next(iter)
        object_id = self.selected_journal_entry.object_id
        if object_id == uid:
            self.set_form_fields(new_jobject)
        
    def datastore_deleted_cb(self,  uid):
        save_path = self.selected_path
        iter = self.ls_journal.get_iter_first()
        for row in self.ls_journal:
            jobject = row[COLUMN_JOBJECT]
            if jobject.object_id == uid:
                title = jobject.metadata.get('title', None)
                self.update_log_entries += '\n' + _('Entry %s deleted.') % title
                self.ls_journal.remove(iter)
                break
            iter = self.ls_journal.iter_next(iter)
            

        try:
            self.selection_journal.select_path(save_path)
            self.tv_journal.grab_focus()
        except:
            self.title_entry.set_text('')
            description_textbuffer = self.description_textview.get_buffer()
            description_textbuffer.set_text('')
            tags_textbuffer = self.tags_textview.get_buffer()
            tags_textbuffer.set_text('')
            self.btn_save.props.sensitive = False
            self.btn_delete.props.sensitive = False
            self.image.clear()
            self.image.show()
        
    def update_entry(self):
        needs_update = False
        
        if self.selected_journal_entry is None:
            return

        object_id = self.selected_journal_entry.object_id
        jobject = datastore.get(object_id)
        
        old_title = jobject.metadata.get('title', None)
        if old_title != self.title_entry.props.text:
            jobject.metadata['title'] = self.title_entry.props.text
            jobject.metadata['title_set_by_user'] = '1'
            self.update_log_entries += '\n' + _('Entry title changed to %s') % self.title_entry.props.text
            needs_update = True

        old_tags = jobject.metadata.get('tags', None)
        new_tags = self.tags_textview.props.buffer.props.text
        if old_tags != new_tags:
            jobject.metadata['tags'] = new_tags
            self.update_log_entries += '\n' + _('Entry %s tags updated.') % self.title_entry.props.text
            needs_update = True

        old_description = jobject.metadata.get('description', None)
        new_description = self.description_textview.props.buffer.props.text
        if old_description != new_description:
            jobject.metadata['description'] = new_description
            self.update_log_entries += '\n' + _('Entry %s description updated.') % self.title_entry.props.text
            needs_update = True

        if needs_update:
            datastore.write(jobject, update_mtime=False,
                            reply_handler=self.datastore_write_cb,
                            error_handler=self.datastore_write_error_cb)
        self.btn_save.props.sensitive = False
    
    def datastore_write_cb(self):
        pass

    def datastore_write_error_cb(self, error):
        logging.error('sugarcommander.datastore_write_error_cb: %r' % error)

    def read_file(self, file_path):
        """Load a file from the datastore on activity start"""
        _logger.debug('sugarcommander.read_file: %s', file_path)
   
    def write_file(self, filename):
        "Save meta data for the file."
        old_description = self.metadata.get('description', 'Sugar Commander log:')
        new_description = old_description + self.update_log_entries
        self.metadata['description'] = new_description
        self.metadata['mime_type'] = 'text/plain'
        f = open(filename, 'w')
        try:
            f.write(new_description)
        finally:
            f.close()
        self.update_log_entries = ''

    def can_close(self):
        self.close_requested = True
        return True

    def selection_journal_cb(self, selection):
        self.btn_delete.props.sensitive = True
        tv = selection.get_tree_view()
        model = tv.get_model()
        sel = selection.get_selected()
        if sel:
            model, iter = sel
            jobject = model.get_value(iter,COLUMN_JOBJECT)
            jobject = datastore.get(jobject.object_id)
            self.selected_journal_entry = jobject
            self.set_form_fields(jobject)
            if jobject.metadata['mime_type'] .startswith('image/')  \
                and jobject.metadata['mime_type'] != 'image/vnd.djvu':
                self.btn_resize.show()
                self.resize_width_entry.show()
                filename = jobject.get_file_path()
                im = pygame.image.load(filename)
                image_width, image_height = im.get_size()
                self.dimension_label.set_text(str(image_width) + "x" + str(image_height))
                self.dimension_label.show()
            else:
                self.btn_resize.hide()
                self.resize_width_entry.hide()
                self.dimension_label.hide()
            self.selected_path = model.get_path(iter)

    def set_form_fields(self, jobject):
        self.title_entry.set_text(jobject.metadata['title'])
        description_textbuffer = self.description_textview.get_buffer()
        if 'description' in jobject.metadata:
            description_textbuffer.set_text(jobject.metadata['description'])
        else:
            description_textbuffer.set_text('')
        tags_textbuffer = self.tags_textview.get_buffer()
        if 'tags' in jobject.metadata:
            tags_textbuffer.set_text(jobject.metadata['tags'])
        else:
            tags_textbuffer.set_text('')
        self.create_preview(jobject.object_id)

    def create_preview(self,  object_id):
        jobject = datastore.get(object_id)
        
        if 'preview' in jobject.metadata:
            preview = jobject.metadata['preview']
            if preview is None or preview == '' or preview == 'None':
                if jobject.metadata['mime_type'] .startswith('image/') and \
                    jobject.metadata['mime_type'] != 'image/vnd.djvu':
                    filename = jobject.get_file_path()
                    self.show_image(filename)
                    return
                if jobject.metadata['mime_type']  == 'application/x-cbz':
                    filename = jobject.get_file_path()
                    fname = self.extract_image(filename)
                    self.show_image(fname)
                    os.remove(fname)
                    return
                self.show_image('xoimage.jpg')
                return

        if 'preview' in jobject.metadata and \
                len(jobject.metadata['preview']) > 4:
            preview_data = jobject.metadata['preview']
            loader = GdkPixbuf.PixbufLoader()
            loader.write(preview_data)
            scaled_buf = loader.get_pixbuf()
            loader.close()
            self.image.set_from_pixbuf(scaled_buf)
            self.image.show()
        else:
            self.image.clear()
            self.image.show()

    def load_journal_table(self):
        self.btn_save.props.sensitive = False
        self.btn_delete.props.sensitive = False
        query = {}
        ds_objects, num_objects = datastore.find(query, properties=['uid', 
            'title',  'mime_type'])

        self.ls_journal.clear()
        for i in range (0, num_objects, 1):
            iter = self.ls_journal.append()
            title = ds_objects[i].metadata['title']
            self.ls_journal.set(iter, COLUMN_TITLE, title)
            mime = ds_objects[i].metadata['mime_type']
            self.ls_journal.set(iter, COLUMN_MIME, mime)
            self.ls_journal.set(iter, COLUMN_JOBJECT, ds_objects[i])
            size = self.get_size(ds_objects[i]) / 1024
            self.ls_journal.set(iter, COLUMN_SIZE, size)

        v_adjustment = self.list_scroller_journal.get_vadjustment()
        v_adjustment.value = 0

    def get_size(self, jobject):
        """Return the file size for a Journal object."""
        logging.debug('get_file_size %r', jobject.object_id)
        path = jobject.get_file_path()
        if not path:
            return 0

        return os.stat(path).st_size

    def create_journal_entry(self,  widget,  data=None):
        filename = self._filechooser.get_filename()
        journal_entry = datastore.create()
        journal_entry.metadata['title'] = self.make_new_filename(filename)
        journal_entry.metadata['title_set_by_user'] = '1'
        journal_entry.metadata['keep'] = '0'
        file_mimetype = mime.get_for_file(filename)
        if not file_mimetype is None:
            journal_entry.metadata['mime_type'] = file_mimetype
        journal_entry.metadata['buddies'] = ''
        if file_mimetype.startswith('image/')  and file_mimetype != 'image/vnd.djvu':
            preview = self.create_preview_metadata(filename)
        elif file_mimetype  == 'application/x-cbz':
            fname = self.extract_image(filename)
            preview = self.create_preview_metadata(fname)
            os.remove(fname)
        else:
            preview = ''
        if not preview  == '':
            journal_entry.metadata['preview'] =  dbus.ByteArray(preview)
        else:
            journal_entry.metadata['preview'] =  ''
            
        journal_entry.file_path = filename
        datastore.write(journal_entry)
        self.update_log_entries += '\n' + _('File %s copied to the Journal.') % filename
        self.alert(_('Success'),  _('%s added to Journal.') 
                    % self.make_new_filename(filename))
   
    def alert(self, title, text=None):
        alert = NotifyAlert(timeout=20)
        alert.props.title = title
        alert.props.msg = text
        self.add_alert(alert)
        alert.connect('response', self.alert_cancel_cb)
        alert.show()

    def alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)

    def show_image(self, filename):
        "display a resized image in a preview"
        scaled_buf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 
                                                          style.zoom(300), style.zoom(225))
        self.image.set_from_pixbuf(scaled_buf)
        self.image.show()

    def extract_image(self,  filename):
        zf = zipfile.ZipFile(filename, 'r')
        image_files = zf.namelist()
        image_files.sort()
        file_to_extract = image_files[0]
        extract_new_filename = self.make_new_filename(file_to_extract)
        if extract_new_filename is None or extract_new_filename == '':
            # skip over directory name if the images are in a subdirectory.
            file_to_extract = image_files[1]
            extract_new_filename = self.make_new_filename(file_to_extract)
            
        if len(image_files) > 0:
            if self.save_extracted_file(zf, file_to_extract):
                fname = os.path.join(self.get_activity_root(), 'instance',  
                                     extract_new_filename)
                return fname

    def save_extracted_file(self, zipfile, filename):
        "Extract the file to a temp directory for viewing"
        try:
            filebytes = zipfile.read(filename)
        except zipfile.BadZipfile as err:
            print('Error opening the zip file: %s' % (err))
            return False
        except KeyError as  err:
            self.alert('Key Error', 'Zipfile key not found: '  
                        + str(filename))
            return
        outfn = self.make_new_filename(filename)
        if (outfn == ''):
            return False
        fname = os.path.join(self.get_activity_root(), 'instance',  outfn)
        f = open(fname, 'w')
        try:
            f.write(filebytes)
        finally:
            f.close()
        return True

    def make_new_filename(self, filename):
        partition_tuple = filename.rpartition('/')
        return partition_tuple[2]

    def create_preview_metadata(self,  filename):

        file_mimetype = mime.get_for_file(filename)
        if not file_mimetype.startswith('image/'):
            return ''
            
        scaled_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename,
                                                              style.zoom(320), style.zoom(240))
        preview_data = []

        success, preview_data = scaled_pixbuf.save_to_bufferv('png', [], [])
        str_preview_data = bytes(preview_data) 

        return preview_data
