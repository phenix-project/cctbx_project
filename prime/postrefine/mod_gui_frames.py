from __future__ import division, print_function, absolute_import
from past.builtins import range

'''
Author      : Lyubimov, A.Y.
Created     : 05/01/2016
Last Changed: 06/07/2019
Description : PRIME GUI frames module
'''

import os
import wx
import multiprocessing
from wxtbx import bitmaps

from iotbx import phil as ip
from libtbx import easy_run, easy_pickle as ep
import numpy as np

import matplotlib.gridspec as gridspec
from matplotlib import pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure

import iota.components.iota_utils as util
import iota.components.iota_ui_controls as ct
from iota.components.iota_ui_base import IOTABasePanel, IOTABaseFrame

from prime import prime_license, prime_description
import prime.postrefine.mod_gui_dialogs as dlg
import prime.postrefine.mod_threads as thr
from prime.postrefine.mod_input import master_phil
from prime.postrefine.mod_plotter import Plotter, PlotWindow

user = os.getlogin()
ginp = util.InputFinder()
f = util.WxFlags()

# Platform-specific stuff
# TODO: Will need to test this on Windows at some point
if wx.Platform == '__WXGTK__':
  norm_font_size = 10
  button_font_size = 12
  LABEL_SIZE = 14
  CAPTION_SIZE = 12
  python = 'python'
elif wx.Platform == '__WXMAC__':
  norm_font_size = 12
  button_font_size = 14
  LABEL_SIZE = 14
  CAPTION_SIZE = 12
  python = "Python"
elif (wx.Platform == '__WXMSW__'):
  norm_font_size = 9
  button_font_size = 11
  LABEL_SIZE = 11
  CAPTION_SIZE = 9

# def str_split(string, delimiters=(' ', ','), maxsplit=0):
#   import re
#   rexp = '|'.join(map(re.escape, delimiters))
#   return re.split(rexp, string, maxsplit)


# -------------------------------  Main Window ------------------------------  #

class PRIMEWindow(IOTABaseFrame):

  def __init__(self, parent, title, id=-1, prefix='prime'):
    IOTABaseFrame.__init__(self, parent=parent, title=title, id=id,
                           size=(800, 500))

    self.prime_filename = '{}.phil'.format(prefix)
    self.prime_phil = master_phil

    # Toolbar
    self.initialize_toolbar()
    self.tb_btn_quit = self.add_tool(label='Quit',
                                     bitmap=('actions', 'exit'),
                                     shortHelp='Exit PRIME')

    self.tb_btn_prefs = self.add_tool(label='Preferences',
                                      bitmap=('apps', 'advancedsettings'),
                                      shortHelp='PRIME GUI Settings')
    self.add_toolbar_separator()
    self.tb_btn_load = self.add_tool(label='Load Script',
                                     bitmap=('actions', 'open'),
                                     shortHelp='Load PRIME Script')
    self.tb_btn_save = self.add_tool(label='Save Script',
                                     bitmap=('actions', 'save'),
                                     shortHelp='Save PRIME Script')
    self.tb_btn_reset = self.add_tool(label='Reset',
                                                  bitmap=('actions', 'reload'),
                                                  shortHelp='Reset Settings')
    self.toolbar.AddSeparator()
    self.tb_btn_analysis = self.add_tool(label='Recover',
                                         bitmap=(
                                         'mimetypes', 'text-x-generic-2'),
                                         shortHelp='Recover PRIME run')
    self.tb_btn_run = self.add_tool(label='Run',
                                    bitmap=('actions', 'run'),
                                    shortHelp='Run PRIME')
    # These buttons will be disabled until input path is provided
    self.set_tool_state(self.tb_btn_run, enable=False)
    self.realize_toolbar()

    # Instantiate input window
    self.input_window = PRIMEInputWindow(self, phil=self.prime_phil)
    self.main_sizer.Add(self.input_window, 1, flag=wx.ALL | wx.EXPAND,
                        border=10)
    self.main_sizer.Add((-1, 20))

    # Toolbar button bindings
    self.Bind(wx.EVT_TOOL, self.onQuit, self.tb_btn_quit)
    self.Bind(wx.EVT_TOOL, self.onPreferences, self.tb_btn_prefs)
    self.Bind(wx.EVT_TOOL, self.onRecovery, self.tb_btn_analysis)
    self.Bind(wx.EVT_TOOL, self.onRun, self.tb_btn_run)
    self.Bind(wx.EVT_TOOL, self.onLoadScript, self.tb_btn_load)
    self.Bind(wx.EVT_TOOL, self.onSaveScript, self.tb_btn_save)
    self.Bind(wx.EVT_TOOL, self.onReset, self.tb_btn_reset)

    # Input window bindings
    self.Bind(wx.EVT_BUTTON, self.onAdvancedOptions, self.input_window.opt_btn)

  def OnAboutBox(self, e):
    ''' About dialog '''
    info = wx.AboutDialogInfo()
    info.SetName('PRIME')
    info.SetWebSite('http://cci.lbl.gov/xfel')
    info.SetLicense(prime_license)
    info.SetDescription(prime_description)
    info.AddDeveloper('Monarin Uervirojnangkoorn')
    info.AddDeveloper('Axel Brunger')
    wx.AboutBox(info)

  def onPreferences(self, e):
    prefs = dlg.PRIMEPreferences(self,
                                 phil=self.prime_phil,
                                 title='Advanced PRIME Options',
                                 style=wx.DEFAULT_DIALOG_STYLE |
                                       wx.STAY_ON_TOP |
                                       wx.RESIZE_BORDER)
    prefs.SetMinSize((600, -1))
    prefs.Fit()

    if prefs.ShowModal() == wx.ID_OK:
      self.prime_phil = self.prime_phil.fetch(prefs.pref_phil)
      self.input_window.regenerate_params(self.prime_phil)

  def onAdvancedOptions(self, e):
    self.input_window.update_settings()
    self.prime_phil = self.prime_phil.fetch(self.input_window.prime_phil)
    advanced = dlg.PRIMEAdvancedOptions(self,
                                        phil=self.prime_phil,
                                        title='Advanced PRIME Options',
                                        style=wx.DEFAULT_DIALOG_STYLE |
                                              wx.STAY_ON_TOP |
                                              wx.RESIZE_BORDER)
    advanced.SetMinSize((600, -1))
    advanced.Fit()

    if advanced.ShowModal() == wx.ID_OK:
      self.prime_phil = self.prime_phil.fetch(advanced.phil_script)
      self.prime_phil = self.prime_phil.fetch(advanced.new_prime_phil)
      self.input_window.regenerate_params(self.prime_phil)

    advanced.Destroy()

  def onInput(self, e):
    if self.input_window.inp_box.ctr.GetValue() != '':
      self.set_tool_state(self.tb_btn_run, enable=True)
    else:
      self.set_tool_state(self.tb_btn_run, enable=False)

  def init_settings(self):
    self.input_window.update_settings()
    self.pparams = self.input_window.pparams
    self.out_dir = self.input_window.out_dir

  def sanity_check(self):
    '''
    Goes through and checks that the key parameters are populated; pops
    up an error message if they are not
    :return: True if satisfied, False if not
    '''

    # Check to see that pixel size is specified (PRIME won't run without it)
    if self.pparams.pixel_size_mm is None:
      warning = wx.MessageDialog(None,
                                 caption='Warning!',
                                 message='Pixel size not specified!',
                                 style=wx.OK)
      warning.ShowModal()
      warning.Destroy()
      return False

    return True

  def onRecovery(self, e):
    # Find finished runs and display results
    p_folder = os.path.abspath('{}/prime'.format(os.curdir))

    if not os.path.isdir(p_folder):
      open_dlg = wx.DirDialog(self, "Choose the integration run:",
                              style=wx.DD_DEFAULT_STYLE)
      if open_dlg.ShowModal() == wx.ID_OK:
        p_folder = open_dlg.GetPath()
        open_dlg.Destroy()
      else:
        open_dlg.Destroy()
        return

    paths = [os.path.join(p_folder, p) for p in os.listdir(p_folder)]
    paths = [p for p in paths if (os.path.isdir(p) and
                                  os.path.basename(p).isdigit())]

    path_dlg = dlg.RecoveryDialog(self)
    path_dlg.insert_paths(paths)

    if path_dlg.ShowModal() == wx.ID_OK:
      selected = path_dlg.selected
      recovery = path_dlg.recovery_mode
      prime_path = selected[1]
      prime_status = selected[0]
      settings_file = os.path.join(prime_path, 'settings.phil')

      # If neither log-file nor stat file are found, terminate; otherwise
      # import settings
      if not os.path.isfile(settings_file):
        wx.MessageBox('Cannot Import This Run \n(No Files Found!)',
                      'Info', wx.OK | wx.ICON_ERROR)
        return
      else:
        self.reset_settings()
        with open(settings_file, 'r') as sf:
          phil_string = sf.read()
        read_phil = ip.parse(phil_string)
        self.prime_phil = master_phil.fetch(source=read_phil)
        self.pparams = self.prime_phil.extract()
        self.input_window.regenerate_params(self.prime_phil)
        self.update_input_window()

      # If any cycles (or full run) were completed, show results
      if prime_status == 'Unknown':
        return

      if recovery == 0:
        self.prime_run_window = PRIMERunWindow(self, -1,
                                               title='PRIME Output',
                                               params=self.pparams,
                                               prime_file=settings_file,
                                               recover=True)
        self.prime_run_window.place_and_size(set_by='parent')
        self.prime_run_window.Show(True)
        self.prime_run_window.recover()

  def onRun(self, e):
    # Run full processing

    self.init_settings()
    if self.sanity_check():
      prime_phil = master_phil.format(python_object=self.pparams)

      with util.Capturing() as output:
        prime_phil.show()

      txt_out = ''
      for one_output in output:
        txt_out += one_output + '\n'

      source_dir = os.path.dirname(self.out_dir)
      prime_file = os.path.join(source_dir, self.prime_filename)
      out_file = os.path.join(self.out_dir, 'stdout.log')
      with open(prime_file, 'w') as pf:
        pf.write(txt_out)

      self.prime_run_window = PRIMERunWindow(self, -1,
                                             title='PRIME Output',
                                             params=self.pparams,
                                             prime_file=prime_file)
      self.prime_run_window.prev_pids = easy_run.fully_buffered('pgrep -u {} {}'
                                        ''.format(user, python)).stdout_lines
      self.prime_run_window.place_and_size(set_by='parent')
      self.prime_run_window.Show(True)

  def onSequence(self, e):
    pass

  def onSaveScript(self, e):
    self.init_settings()

    # Generate text of params
    final_phil = master_phil.format(python_object=self.pparams)
    with util.Capturing() as txt_output:
      final_phil.show()
    txt_out = ''
    for one_output in txt_output:
      txt_out += one_output + '\n'

    # Save param file
    save_dlg = wx.FileDialog(self,
                             message="Save PRIME Script",
                             defaultDir=os.curdir,
                             defaultFile="*.phil",
                             wildcard="*.phil",
                             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
                             )
    if save_dlg.ShowModal() == wx.ID_OK:
      with open(save_dlg.GetPath(), 'w') as savefile:
        savefile.write(txt_out)

    save_dlg.Destroy()

  def onLoadScript(self, e):
    # Extract params from file
    load_dlg = wx.FileDialog(self,
                             message="Load script file",
                             defaultDir=os.curdir,
                             defaultFile="*.phil",
                             wildcard="*.phil",
                             style=wx.OPEN | wx.FD_FILE_MUST_EXIST,
                             )
    if load_dlg.ShowModal() == wx.ID_OK:
      script = load_dlg.GetPaths()[0]
      out_dir = os.path.dirname(script)
      self.prime_filename=os.path.basename(script)
      self.load_script(out_dir=out_dir)
    load_dlg.Destroy()

  def onReset(self, e):
    self.reset_settings()

  def load_script(self, out_dir):
    ''' Loads PRIME script '''
    script = os.path.join(out_dir, self.prime_filename)
    with open(script, 'r') as sf:
      phil_string = sf.read()

    self.reset_settings()

    user_phil = ip.parse(phil_string)
    self.prime_phil = master_phil.fetch(source=user_phil)
    self.pparams = self.prime_phil.extract()
    self.input_window.pparams = self.pparams
    self.input_window.phil_string = phil_string
    self.update_input_window()


  def update_input_window(self):
    ''' Update input window with current (or default) params'''
    for input_item in self.pparams.data:
      if input_item is not None:
        self.input_window.inp_box.add_item(input_item)

    if self.pparams.run_no is not None:
      current_dir = os.path.dirname(self.pparams.run_no)
    else:
      current_dir = os.path.abspath(os.curdir)
    self.input_window.out_box.ctr.SetValue(str(current_dir))
    if str(self.input_window.out_box.ctr.GetValue).lower() == '':
      self.input_window.out_box.ctr.SetValue(self.out_dir)
    if str(self.pparams.title).lower() != 'none':
      self.input_window.project_title.ctr.SetValue(str(self.pparams.title))
    if str(self.pparams.hklisoin).lower() != 'none':
      self.input_window.inp_box.add_item(self.pparams.hklisoin)
    elif str(self.pparams.hklrefin).lower() != 'none':
      self.input_window.inp_box.add_item(self.pparams.hklrefin)
      self.input_window.opt_chk_useref.Enable()
      self.input_window.opt_chk_useref.SetValue(True)
    if str(self.pparams.n_residues).lower() == 'none':
      self.input_window.opt_spc_nres.ctr.SetValue(500)
    else:
      self.input_window.opt_spc_nres.ctr.SetValue(int(self.pparams.n_residues))
    self.input_window.opt_spc_nproc.ctr.SetValue(int(self.pparams.n_processors))

  def reset_settings(self):
    self.prime_phil = master_phil
    self.pparams = self.prime_phil.extract()
    self.input_window.inp_box.delete_all()
    self.input_window.out_box.reset_default()
    self.input_window.project_title.reset_default()
    self.input_window.opt_chk_useref.SetValue(False)
    self.input_window.opt_spc_nproc.reset_default()
    self.input_window.opt_spc_nres.reset_default()

    # Generate Python object and text of parameters
    with util.Capturing() as txt_output:
      master_phil.show()
    self.phil_string = ''
    for one_output in txt_output:
      self.phil_string += one_output + '\n'

  def onQuit(self, e):

    # Check if proc_thread exists
    try:
      if hasattr(self, 'prime_run_window'):
        if hasattr(self.prime_run_window, 'prime_process'):

          # Check if proc_thread is running
          if self.prime_run_window.prime_process.is_alive():
            self.prime_run_window.abort_run(verbose=False)

            # Close window only when thread is dead
            while self.prime_run_window.prime_process.is_alive():
              print ('THREAD ALIVE? ',
                     self.prime_run_window.prime_process.is_alive())
              continue
    except Exception:
      pass

    self.Close()

class PRIMEInputWindow(IOTABasePanel):
  ''' Main PRIME Window panel '''

  def __init__(self, parent, phil=None):
    IOTABasePanel.__init__(self, parent=parent)

    self.regenerate_params(phil)

    # Title box
    self.project_title = ct.InputCtrl(self, label='Project Title: ',
                                      label_size=(140, -1))
    # Output file box
    self.out_box = ct.InputCtrl(self, label='Project folder: ',
                                label_size=(140, -1),
                                label_style='bold',
                                value=os.path.abspath(os.curdir),
                                buttons=True)
    # Input file box
    self.inp_box = FileListCtrl(self)

    # Options
    opt_box = wx.FlexGridSizer(2, 3, 10, 10)
    self.opt_chk_useref = wx.CheckBox(self, label='Use reference in refinement')
    self.opt_chk_useref.Disable()
    self.opt_spc_nres = ct.SpinCtrl(self,
                                    label='No. of Residues: ',
                                    label_size=(160, -1),
                                    ctrl_size=(100, -1),
                                    ctrl_value=500,
                                    ctrl_min=10,
                                    ctrl_max=100000)
    procs = multiprocessing.cpu_count()
    self.opt_spc_nproc = ct.SpinCtrl(self,
                                     label='No. of Processors: ',
                                     label_size=(160, -1),
                                     ctrl_max=procs,
                                     ctrl_min=1,
                                     ctrl_value=str(int(procs / 2)))
    self.opt_btn = wx.Button(self, label='Advanced Options...')
    opt_box.AddMany([(self.opt_chk_useref), (0, 0),
                     (self.opt_spc_nres),
                     (self.opt_btn), (0, 0),
                     (self.opt_spc_nproc)])
    opt_box.AddGrowableCol(1)

    # Add to sizers
    self.main_sizer.Add(self.project_title, flag=f.expand, border=10)
    self.main_sizer.Add(self.out_box, flag=f.expand, border=10)
    self.main_sizer.Add(self.inp_box, 1, flag=wx.EXPAND | wx.ALL, border=10)
    self.main_sizer.Add(wx.StaticLine(self), flag=wx.EXPAND)
    self.main_sizer.Add(opt_box, flag=wx.ALL | wx.EXPAND, border=10)

    # Button bindings
    self.out_box.btn_browse.Bind(wx.EVT_BUTTON, self.onOutputBrowse)
    self.opt_btn.Bind(wx.EVT_BUTTON, self.onAdvancedOptions)

  def onInputBrowse(self, e):
    """ On clincking the Browse button: show the DirDialog and populate 'Input'
        box w/ selection """
    inp_dlg = wx.DirDialog(self, "Choose the input directory:",
                       style=wx.DD_DEFAULT_STYLE)
    if inp_dlg.ShowModal() == wx.ID_OK:
      self.inp_box.ctr.SetValue(inp_dlg.GetPath())
    inp_dlg.Destroy()
    self.update_settings()
    e.Skip()

  def update_settings(self):
    idxs = self.inp_box.ctr.GetItemCount()
    items = [self.inp_box.ctr.GetItemData(i) for i in range(idxs)]
    inputs = []
    reference = None
    sequence = None

    for i in items:
      inp_type = i.type.type.GetString(i.type_selection)
      if inp_type in ('processed pickle list',
                      'processed pickle folder',
                      'processed pickle'):
        inputs.append(i.path)
      elif inp_type == 'reference MTZ':
        reference = i.path
      elif inp_type == 'sequence':
        sequence = i.path

    self.pparams.data = inputs

    if reference is not None:
      self.pparams.hklisoin = reference
      if self.opt_chk_useref.GetValue():
        self.pparams.hklrefin = reference

    self.out_dir = self.out_box.ctr.GetValue()
    self.pparams.run_no = util.set_base_dir(out_dir=self.out_dir)  # Need to change
    self.pparams.title = self.project_title.ctr.GetValue()
    self.pparams.n_residues = self.opt_spc_nres.ctr.GetValue()
    self.pparams.n_processors = self.opt_spc_nproc.ctr.GetValue()

    update_phil = master_phil.format(python_object=self.pparams)
    self.regenerate_params(update_phil)

  def onOutputBrowse(self, e):
    """ On clicking the Browse button: show the DirDialog and populate 'Output'
        box w/ selection """
    save_dlg = wx.DirDialog(self, "Choose the output directory:",
                       style=wx.DD_DEFAULT_STYLE)
    if save_dlg.ShowModal() == wx.ID_OK:
      self.out_box.ctr.SetValue(save_dlg.GetPath())
    save_dlg.Destroy()
    self.update_settings()
    e.Skip()

  def onAdvancedOptions(self, e):
    e.Skip()

  def regenerate_params(self, phil=None):
    if phil is not None:
      self.prime_phil = master_phil.fetch(source=phil)
    else:
      self.prime_phil = master_phil

    # Generate Python object and text of parameters
    self.generate_phil_string(self.prime_phil)
    self.pparams = self.prime_phil.extract()

  def generate_phil_string(self, current_phil):
    with util.Capturing() as txt_output:
      current_phil.show()
    self.phil_string = ''
    for one_output in txt_output:
      self.phil_string += one_output + '\n'

# ----------------------------  Processing Window ---------------------------  #

class LogTab(wx.Panel):
  def __init__(self, parent):
    wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

    self.log_sizer = wx.BoxSizer(wx.VERTICAL)
    self.log_window = wx.TextCtrl(self,
                                  style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP)
    self.log_window.SetFont(wx.Font(9, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False))
    self.log_sizer.Add(self.log_window, proportion=1, flag= wx.EXPAND | wx.ALL, border=10)
    self.SetSizer(self.log_sizer)

class RuntimeTab(wx.Panel):
  def __init__(self, parent, params=None):
    wx.Panel.__init__(self, parent)
    self.pparams = params

    # For some reason MatPlotLib 2.2.3 on GTK 6 does not create transparent
    # patches (tried set_visible(False), set_facecolor("none"), set_alpha(0),
    # to no avail). Thus, for GTK only, setting facecolor to background
    # color; otherwide to 'none'. This may change if other tests reveal the
    # same problem in other systems.
    if wx.Platform == '__WXGTK__':
      bg_color = [i/255 for i in self.GetBackgroundColour()]
    else:
      bg_color = 'none'

    plt.rc('font', family='sans-serif', size=10)
    plt.rc('mathtext', default='regular')

    # Create figure
    self.prime_sizer = wx.BoxSizer(wx.VERTICAL)
    self.prime_figure = Figure()
    # self.prime_figure.patch.set_alpha(0)
    self.prime_figure.patch.set_facecolor(color=bg_color)

    # Create nested GridSpec
    gsp = gridspec.GridSpec(2, 2, height_ratios=[2, 3])
    self.cc_axes = self.prime_figure.add_subplot(gsp[0])
    self.comp_axes = self.prime_figure.add_subplot(gsp[1])
    self.mult_axes = self.comp_axes.twinx()
    self.rej_table = self.prime_figure.add_subplot(gsp[2])

    gsub = gridspec.GridSpecFromSubplotSpec(3, 1,
                                            subplot_spec=gsp[3],
                                            hspace=0)
    self.bcc_axes = self.prime_figure.add_subplot(gsub[0])
    self.bcomp_axes = self.prime_figure.add_subplot(gsub[1],
                                                    sharex=self.bcc_axes)
    self.bmult_axes = self.prime_figure.add_subplot(gsub[2],
                                                    sharex=self.bcc_axes)
    self.draw_axes()

    # Set layout, create canvas, add to sizer
    self.prime_figure.set_tight_layout(True)
    self.canvas = FigureCanvas(self, -1, self.prime_figure)
    self.prime_sizer.Add(self.canvas, proportion=1, flag =wx.EXPAND)

    # Initialize main sizer
    self.SetSizer(self.prime_sizer)

  def draw_axes(self):
    self.rej_table.axis('off')
    self.cc_axes.set_title(r'$CC_{1/2}$', fontsize=12)
    self.cc_axes.set_xlabel('Cycle')
    self.cc_axes.set_ylabel(r'$CC_{1/2}$ (%)')
    self.cc_axes.ticklabel_format(axis='y', style='plain')

    self.comp_axes.set_title('Completeness / Multiplicity', fontsize=12)
    self.comp_axes.set_xlabel('Cycle')
    self.comp_axes.set_ylabel('Completeness (%)')
    self.mult_axes.set_ylabel('# of Observations')
    self.comp_axes.ticklabel_format(axis='y', style='plain')
    self.mult_axes.ticklabel_format(axis='y', style='plain')

    self.bcc_axes.yaxis.get_major_ticks()[0].label1.set_visible(False)
    self.bcc_axes.yaxis.get_major_ticks()[-1].label1.set_visible(False)

    if self.pparams.target_anomalous_flag:
      self.bcc_axes.set_ylabel(r'$CC_{1/2}$ anom (%)')
    else:
      self.bcc_axes.set_ylabel(r'$CC_{1/2}$ (%)')
    plt.setp(self.bcc_axes.get_xticklabels(), visible=False)
    self.bcomp_axes.yaxis.get_major_ticks()[0].label1.set_visible(False)
    self.bcomp_axes.yaxis.get_major_ticks()[-1].label1.set_visible(False)
    self.bcomp_axes.set_ylabel("Comp (%)")
    plt.setp(self.bcomp_axes.get_xticklabels(), visible=False)
    self.bmult_axes.yaxis.get_major_ticks()[0].label1.set_visible(False)
    self.bmult_axes.yaxis.get_major_ticks()[-1].label1.set_visible(False)
    self.bmult_axes.set_xlabel("Resolution ($\AA$)")
    self.bmult_axes.set_ylabel("# of Obs")

  def draw_plots(self, info, total_cycles):

    # Plot mean CC1/2
    meanCC = info['total_cc12']
    cycles = range(len(meanCC))
    self.cc_axes.clear()
    self.cc_axes.set_xlim(0, total_cycles)
    self.cc_axes.set_ylim(0, 100)
    self.cc_axes.plot(cycles, meanCC, 'o', c='#2b8cbe', ls='-', lw=3)

    # Plot mean completeness and multiplicity
    mean_comp = info['total_completeness']
    mean_mult = info['total_n_obs']
    cycles = range(len(mean_comp))
    self.comp_axes.clear()
    self.mult_axes.clear()
    self.comp_axes.set_xlim(0, total_cycles)
    self.comp_axes.set_ylim(0, 100)
    self.mult_axes.set_xlim(0, total_cycles)
    self.comp_axes.plot(cycles, mean_comp, c='#f03b20', ls='-', lw=2)
    comp = self.comp_axes.scatter(cycles, mean_comp, marker='o', s=25,
                                  edgecolors='black', color='#f03b20')
    self.mult_axes.plot(cycles, mean_mult, c='#feb24c', ls='-', lw=2)
    mult = self.mult_axes.scatter(cycles, mean_mult, marker='o', s=25,
                                  edgecolors='black', color='#feb24c')
    labels = ['Completeness', 'Multiplicity']
    self.comp_axes.legend([comp, mult], labels, loc='upper right',
                          fontsize=9, fancybox=True)

    # Binned bar plots
    x = info['binned_resolution'][-1]
    bins = np.arange(len(x))
    xlabels = ["{:.2f}".format(i) for i in x]
    sel_bins = bins[0::len(bins) // 6]
    sel_xlabels = [xlabels[t] for t in sel_bins]

    # plot binned stats
    self.bcc_axes.clear()
    if self.pparams.target_anomalous_flag:
      binned_cc = [c * 100 for c in info['binned_cc12_anom'][-1]]
    else:
      binned_cc = [c * 100 for c in info['binned_cc12'][-1]]

    self.bcc_axes.bar(bins, binned_cc, color='#2b8cbe',
                      alpha=0.5, width=1, lw=0)
    self.bcc_axes.step(bins, binned_cc, color='blue', where='mid')
    self.bcomp_axes.clear()
    self.bcomp_axes.bar(bins, info['binned_completeness'][-1],
                        alpha=0.5, color='#f03b20', width=1, lw=0)
    self.bcomp_axes.step(bins, info['binned_completeness'][-1], color='red',
                         where='mid')
    self.bmult_axes.clear()
    self.bmult_axes.bar(bins, info['binned_n_obs'][-1],
                        alpha=0.5, color='#feb24c', width=1, lw=0)
    self.bmult_axes.step(bins, info['binned_n_obs'][-1], color='orange',
                         where='mid')

    # Set x-axis tick labels
    self.bmult_axes.set_xticks(sel_bins)
    self.bmult_axes.set_xticklabels(sel_xlabels)
    self.draw_axes()

    # Rejection table
    txt = 'No. good frames:           {}\n' \
          'No. bad CC frames:         {}\n' \
          'No. bad G frames:          {}\n' \
          'No. bad unit cell frames:  {}\n' \
          'No. bad gamma_e frames:    {}\n' \
          'No. bad SE frames:         {}\n' \
          'No. observations:          {}\n' \
          ''.format(info['n_frames_good'][-1],
                    info['n_frames_bad_cc'][-1],
                    info['n_frames_bad_G'][-1],
                    info['n_frames_bad_uc'][-1],
                    info['n_frames_bad_gamma_e'][-1],
                    info['n_frames_bad_SE'][-1],
                    info['n_observations'][-1])

    self.rej_table.clear()
    self.rej_table.axis('off')
    font = {'family': 'monospace',
            'color': 'darkblue',
            'weight': 'normal',
            'size': 11,
            'linespacing': 2.5
            }
    self.rej_table.text(0, 0.85, txt, fontdict=font,
                                  transform=self.rej_table.transAxes,
                                  va='top')

    # Redraw canvas
    self.canvas.draw_idle()
    self.canvas.Refresh()

class SummaryTab(wx.Panel):
  def __init__(self,
               parent,
               pparams,
               info):
    wx.Panel.__init__(self, parent)

    self.info = info
    self.pparams = pparams

    self.summary_sizer = wx.BoxSizer(wx.VERTICAL)

    sfont = wx.Font(norm_font_size, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
    bfont = wx.Font(norm_font_size, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
    self.SetFont(bfont)

    # Run information
    run_box = wx.StaticBox(self, label='Run Information')
    run_box.SetFont(sfont)
    run_box_sizer = wx.StaticBoxSizer(run_box, wx.VERTICAL)
    run_box_grid = wx.FlexGridSizer(3, 2, 5, 20)
    self.title_txt = wx.StaticText(self, label='')
    self.title_txt.SetFont(sfont)
    self.folder_txt = wx.StaticText(self, label='')
    self.folder_txt.SetFont(sfont)

    run_box_grid.AddMany([(wx.StaticText(self, label='Title')),
                          (self.title_txt, 1, wx.EXPAND),
                          (wx.StaticText(self, label='Directory')),
                          (self.folder_txt, 1, wx.EXPAND)])

    run_box_grid.AddGrowableCol(1, 1)
    run_box_sizer.Add(run_box_grid, flag=wx.EXPAND | wx.ALL, border=10)
    self.summary_sizer.Add(run_box_sizer, flag=wx.EXPAND | wx.ALL, border=10)

    # Merging statistics box
    tb1_box = wx.StaticBox(self, label='Merging Statistics')
    tb1_box.SetFont(sfont)
    tb1_box_sizer = wx.StaticBoxSizer(tb1_box, wx.VERTICAL)
    self.tb1_box_grid = wx.GridBagSizer(5, 20)

    # Table 1
    self.tb1_table = Plotter(self, info=self.info)
    self.tb1_table.initialize_figure(figsize=(0.1, 0.1))
    self.tb1_box_grid.Add(self.tb1_table, pos=(0, 0), span=(2, 1), flag=wx.EXPAND)

    # Buttons
    line_bmp = bitmaps.fetch_custom_icon_bitmap('line_graph24')
    self.btn_stats = ct.GradButton(self,
                                   bmp=line_bmp,
                                   label=' Statistical charts', size=(250, -1))
    txt_bmp = bitmaps.fetch_icon_bitmap('mimetypes', 'txt', scale=(24, 24))
    self.btn_table1 = ct.GradButton(self,
                                    bmp=txt_bmp,
                                    label=' Output Table 1', size=(250, -1))
    self.tb1_box_grid.Add(self.btn_stats, pos=(0, 1), flag=wx.ALIGN_RIGHT)
    self.tb1_box_grid.Add(self.btn_table1, pos=(1, 1), flag=wx.ALIGN_RIGHT)

    # Insert into sizers
    tb1_box_sizer.Add(self.tb1_box_grid, 1, flag=wx.EXPAND | wx.ALL, border=10)
    self.summary_sizer.Add(tb1_box_sizer, 1, flag=wx.EXPAND | wx.ALL, border=10)

    # Button bindings
    self.Bind(wx.EVT_BUTTON, self.onPlotStats, self.btn_stats)
    self.Bind(wx.EVT_BUTTON, self.onWriteTableOne, self.btn_table1)

    self.SetSizer(self.summary_sizer)
    self.Refresh()
    self.Layout()

  def update(self):
    # Table 1
    self.tb1_table.table_one_figure()
    self.tb1_box_grid.AddGrowableCol(0)
    self.tb1_box_grid.AddGrowableRow(1)

  def onPlotStats(self, e):
    self.plot_window = PlotWindow(None, -1, title='PRIME Statistics')
    self.plot = Plotter(self.plot_window, info=self.info,
                        anomalous_flag=self.pparams.target_anomalous_flag)
    self.plot.initialize_figure(figsize=(9, 9))
    self.plot.stat_charts()
    self.plot_window.plot()
    self.plot_window.Show(True)

  def onWriteTableOne(self, e):
    ''' Write Table 1 to a file '''

    save_dlg = wx.FileDialog(self,
                             message="Save Table 1",
                             defaultDir=os.curdir,
                             defaultFile="table_1.txt",
                             wildcard="*.txt",
                             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
                             )
    if save_dlg.ShowModal() == wx.ID_OK:
      with open(save_dlg.GetPath(), 'a') as tb1_file:
        tb1_text = self.tb1_table.table_one_text()
        tb1_file.write(tb1_text)
       # for i in range(len(self.tb1_data)):
       #    line = u'{:<25} {:<40}\n'.format(self.tb1_labels[i],
       #                                     self.tb1_data[i][0])
       #    tb1_file.write(to_str(line))

class PRIMERunWindow(IOTABaseFrame):
  ''' New frame that will show processing info '''

  def __init__(self, parent, id, title, params,
               prime_file, mp_method='python', command=None, recover=False):
    IOTABaseFrame.__init__(self, parent, id, title, size=(800, 900),
                           style=wx.SYSTEM_MENU |
                                 wx.CAPTION |
                                 wx.CLOSE_BOX |
                                 wx.RESIZE_BORDER)

    self.logtext = ''
    self.pparams = params
    self.prime_file = prime_file
    self.out_file = os.path.join(self.pparams.run_no, 'log.txt')
    self.bookmark = 0
    self.prev_pids = []
    self.aborted = False
    self.command=command
    self.mp_method = mp_method
    self.current_cycle = -1

    # Toolbar
    self.initialize_toolbar()
    self.tb_btn_abort = self.add_tool(label='Abort',
                                      bitmap=('actions', 'stop'),
                                      shortHelp='Abort')
    self.realize_toolbar()

    # Status box
    self.status_panel = wx.Panel(self)
    self.status_sizer = wx.BoxSizer(wx.VERTICAL)
    self.status_box = wx.StaticBox(self.status_panel, label='Status')
    self.status_box_sizer = wx.StaticBoxSizer(self.status_box, wx.HORIZONTAL)
    self.status_txt = wx.StaticText(self.status_panel, label='')
    self.status_box_sizer.Add(self.status_txt, flag=wx.ALL | wx.ALIGN_CENTER,
                              border=10)
    self.status_sizer.Add(self.status_box_sizer,
                          flag=wx.EXPAND | wx.ALL, border=3)
    self.status_panel.SetSizer(self.status_sizer)

    # Tabbed output window(s)
    self.prime_panel = wx.Panel(self)
    self.prime_nb = wx.Notebook(self.prime_panel, style=0)
    self.log_tab = LogTab(self.prime_nb)
    self.graph_tab = RuntimeTab(self.prime_nb, params=self.pparams)
    self.prime_nb.AddPage(self.log_tab, 'Log')
    self.prime_nb.AddPage(self.graph_tab, 'Charts')
    self.prime_nb.SetSelection(1)
    self.prime_sizer = wx.BoxSizer(wx.VERTICAL)
    self.prime_sizer.Add(self.prime_nb, 1, flag=wx.EXPAND | wx.ALL, border=3)
    self.prime_panel.SetSizer(self.prime_sizer)

    self.main_sizer.Add(self.status_panel, flag=wx.EXPAND | wx.ALL, border=3)
    self.main_sizer.Add(self.prime_panel, 1, flag=wx.EXPAND | wx.ALL, border=3)

    #Processing status bar
    self.sb = self.CreateStatusBar()
    self.sb.SetFieldsCount(2)
    self.sb.SetStatusWidths([-1, -2])

    # Output gauge in status bar
    self.gauge_prime = wx.Gauge(self.sb, -1,
                                style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
    rect = self.sb.GetFieldRect(0)
    self.gauge_prime.SetPosition((rect.x + 2, rect.y + 2))
    self.gauge_prime.SetSize((rect.width - 4, rect.height - 4))
    self.gauge_prime.Hide()

    # Output polling timer
    self.timer = wx.Timer(self)

    # Event bindings
    self.Bind(thr.EVT_ALLDONE, self.onFinishedProcess)
    self.sb.Bind(wx.EVT_SIZE, self.onStatusBarResize)
    self.Bind(wx.EVT_TIMER, self.onTimer, id=self.timer.GetId())

    # Button bindings
    self.Bind(wx.EVT_TOOL, self.onAbort, self.tb_btn_abort)

    if not recover:
     self.run()

  def onStatusBarResize(self, e):
    rect = self.sb.GetFieldRect(0)
    self.gauge_prime.SetPosition((rect.x + 2, rect.y + 2))
    self.gauge_prime.SetSize((rect.width - 4, rect.height - 4))

  def onAbort(self, e):
    self.status_txt.SetForegroundColour('red')
    self.status_txt.SetLabel('Aborting...')
    self.toolbar.EnableTool(self.tb_btn_abort.GetId(), False)
    self.abort_run()

  def abort_run(self, verbose=True):
    if self.mp_method == 'python':
      self.pids = easy_run.fully_buffered('pgrep -u {} {}'
                                          ''.format(user, python)).stdout_lines
      self.pids = [i for i in self.pids if i not in self.prev_pids]
      for i in self.pids:
        easy_run.fully_buffered('kill -9 {}'.format(i))
        if verbose:
         print ('killing PID {}'.format(i))
    self.aborted = True

  def run(self):
    self.status_txt.SetForegroundColour('black')
    self.status_txt.SetLabel('Running...')
    self.gauge_prime.SetRange(self.pparams.n_postref_cycle)

    self.prime_process = thr.PRIMEThread(self,
                                         self.prime_file,
                                         self.out_file,
                                         command=self.command)
    self.prime_process.start()
    self.timer.Start(5000)

  def recover(self):
    self.status_txt.SetForegroundColour('black')
    self.status_txt.SetLabel('Displaying results from {}'
                             ''.format(self.pparams.run_no))

    # Plot results
    self.plot_runtime_results()
    self.plot_final_results()

  def display_log(self):
    ''' Display PRIME stdout '''
    if os.path.isfile(self.out_file):
      with open(self.out_file, 'r') as out:
        out.seek(self.bookmark)
        output = out.readlines()
        self.bookmark = out.tell()

      ins_pt = self.log_tab.log_window.GetInsertionPoint()
      for i in output:
        self.log_tab.log_window.AppendText(i)
        self.log_tab.log_window.SetInsertionPoint(ins_pt)


  def plot_runtime_results(self):
    ''' Plot results for each cycle upon cycle completion '''

    # Find pickle_*.stat file
    stats_folder = os.path.join(self.pparams.run_no, 'stats')
    stat_files = [os.path.join(stats_folder, i) for i in
                  os.listdir(stats_folder) if i.endswith('stat')]

    if stat_files != []:
      assert len(stat_files) == 1
      stat_file = stat_files[0]
      if os.path.isfile(stat_file):
        info = ep.load(stat_file)
      else:
        info = {}
    else:
      info = {}

    if 'binned_resolution' in info:
      self.graph_tab.draw_plots(info, self.pparams.n_postref_cycle)
      self.current_cycle = len(info['total_cc12']) - 1

  def plot_final_results(self):
    ''' Plot final results '''

    # Find pickle_*.stat file
    stats_folder = os.path.join(self.pparams.run_no, 'stats')
    stat_files = [os.path.join(stats_folder, i) for i in
                  os.listdir(stats_folder) if i.endswith('stat')]

    if stat_files != []:
      assert len(stat_files) == 1
      stat_file = stat_files[0]
      if os.path.isfile(stat_file):
        info = ep.load(stat_file)
      else:
        info = {}
    else:
      info = {}

    self.summary_tab = SummaryTab(self.prime_nb,
                                  self.pparams,
                                  info)

    self.summary_tab.title_txt.SetLabel(self.pparams.title)
    self.summary_tab.folder_txt.SetLabel(self.pparams.run_no)
    self.summary_tab.update()

    # Update log
    self.display_log()

    # Display summary
    self.prime_nb.AddPage(self.summary_tab, 'Analysis')
    self.prime_nb.SetSelection(2)

  def onTimer(self, e):
    # If not done yet, write settings file for this run
    settings_file = os.path.join(self.pparams.run_no, 'settings.phil')
    if not os.path.isfile(settings_file):
      try:
        with open(self.prime_file, 'r') as pf:
          settings = pf.read()
        with open(settings_file, 'w') as sf:
          sf.write(settings)
      except Exception:
        pass

    # Inspect output and update gauge
    self.gauge_prime.Show()
    if self.current_cycle == -1:
      self.sb.SetStatusText(('Merging...'), 1)
      self.gauge_prime.SetValue(0)
    else:
      self.sb.SetStatusText('Macrocycle {} of {} completed...' \
                            ''.format(self.current_cycle,
                                      self.pparams.n_postref_cycle), 1)
      self.gauge_prime.SetValue(self.current_cycle)

    # Plot runtime results
    self.plot_runtime_results()

    # Update log
    self.display_log()

    # Sense aborted run
    if self.aborted:
      self.final_step()

    # Sense end of cycle
    if self.current_cycle >= self.pparams.n_postref_cycle:
      self.final_step()


  def onFinishedProcess(self, e):
    self.final_step()


  def final_step(self):
    font = self.status_txt.GetFont()
    font.SetWeight(wx.FONTWEIGHT_BOLD)

    # Check for aborted run
    if self.aborted:
      self.sb.SetStatusText(('Aborted by user'), 1)
      self.status_txt.SetForegroundColour('orange')
      self.status_txt.SetLabel('ABORTED BY USER')
      self.status_txt.SetFont(font)
    else:
      self.sb.SetStatusText(('Run finished'), 1)
      self.status_txt.SetForegroundColour('blue')
      self.status_txt.SetLabel('DONE')
      self.status_txt.SetFont(font)

      # Show final results
      self.plot_runtime_results()
      self.plot_final_results()

      # Copy final results to special folder
      import shutil

      # Make the folder
      fin_folder = "merged_dataset_{}".format(os.path.basename(self.pparams.run_no))
      dst_dir = os.path.abspath(os.path.join(os.curdir, fin_folder))
      os.makedirs(dst_dir)

      # Copy files
      run_no = int(os.path.basename(self.pparams.run_no))
      src_dir = os.path.abspath(self.pparams.run_no)
      src_mtz = 'postref_cycle_{}_merge.mtz'.format(self.current_cycle)
      dst_mtz = 'run_{:03d}_final_merged.mtz'.format(run_no)
      shutil.copyfile(src=os.path.join(src_dir, src_mtz),
                      dst=os.path.join(dst_dir, dst_mtz))
      src_hkl = 'postref_cycle_{}_merge.hkl'.format(self.current_cycle)
      dst_hkl = 'run_{:03d}_final_merged.hkl'.format(run_no)
      shutil.copyfile(src=os.path.join(src_dir, src_hkl),
                      dst=os.path.join(dst_dir, dst_hkl))
      dst_log = 'run_{}_log.txt'.format(run_no)
      shutil.copyfile(src=os.path.join(src_dir, 'log.txt'),
                      dst=os.path.join(dst_dir, dst_log))

    # Finish up
    self.display_log()
    self.gauge_prime.Hide()
    self.toolbar.EnableTool(self.tb_btn_abort.GetId(), False)
    self.timer.Stop()


class FileListCtrl(ct.CustomListCtrl):
  ''' File list window for the input tab '''

  def __init__(self, parent, size=(-1, 300)):
    ct.CustomListCtrl.__init__(self, parent=parent, size=size)

    self.main_window = parent.GetParent()
    self.input_window = parent

    # Initialize dictionaries for imported data types
    self.all_data_images = {}
    self.all_img_objects = {}
    self.all_proc_pickles = {}

    # Generate columns
    self.ctr.InsertColumn(0, "Path")
    self.ctr.InsertColumn(1, "Input Type")
    self.ctr.InsertColumn(2, "Action")
    self.ctr.setResizeColumn(1)

    # Add file / folder buttons
    self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    self.btn_add_file = wx.Button(self, label='Add File...')
    self.btn_add_dir = wx.Button(self, label='Add Folder...')
    self.button_sizer.Add(self.btn_add_file)
    self.button_sizer.Add(self.btn_add_dir, flag=wx.LEFT, border=10)

    self.sizer.Add(self.button_sizer, flag=wx.TOP | wx.BOTTOM, border=10)

    # Event bindings
    self.Bind(wx.EVT_BUTTON, self.onAddFile, self.btn_add_file)
    self.Bind(wx.EVT_BUTTON, self.onAddFolder, self.btn_add_dir)

  def view_all_images(self):
    if self.ctr.GetItemCount() > 0:
      file_list = []
      for i in range(self.ctr.GetItemCount()):
        type_ctrl = self.ctr.GetItemWindow(i, col=1).type
        type_choice = type_ctrl.GetString(type_ctrl.GetSelection())
        if type_choice in ('processed pickle folder'):
          for root, dirs, files in os.walk(self.ctr.GetItemText(i)):
            for filename in files:
              file_list.append(os.path.join(root, filename))
        if type_choice in ('processed pickle'):
          file_list.append(self.ctr.GetItemText(i))

      try:
        file_string = ' '.join(file_list)
        easy_run.fully_buffered('cctbx.image_viewer {}'.format(file_string))
      except Exception as e:
        print (e)

    else:
      wx.MessageBox('No data found', 'Error', wx.OK | wx.ICON_ERROR)

  def onAddFile(self, e):
    file_dlg = wx.FileDialog(self,
                             message="Load File",
                             defaultDir=os.curdir,
                             defaultFile="*",
                             wildcard="*",
                             style=wx.FD_OPEN |
                                   wx.FD_FILE_MUST_EXIST)
    if file_dlg.ShowModal() == wx.ID_OK:
      self.add_item(file_dlg.GetPaths()[0])
    file_dlg.Destroy()
    e.Skip()

  def onAddFolder(self, e):
    dlg = wx.DirDialog(self, "Load Folder:",
                       style=wx.DD_DEFAULT_STYLE)
    if dlg.ShowModal() == wx.ID_OK:
      self.add_item(dlg.GetPath())
    dlg.Destroy()
    e.Skip()

  def set_type_choices(self, path):
    # Determine what type of input this is and present user with choices
    # (this so far works for images ONLY)
    type_choices = ['[  SELECT INPUT TYPE  ]']
    preferred_selection = 0
    if os.path.isdir(path):
      type_choices.extend(['processed pickle folder'])
      dir_type = ginp.get_folder_type(path)
      if dir_type in type_choices:
        preferred_selection = type_choices.index(dir_type)
    elif os.path.isfile(path):
      file_type = ginp.get_file_type(path)
      if file_type in ('processed pickle', 'reference MTZ', 'sequence'):
        type_choices.extend(['processed pickle',
                             'reference MTZ',
                             'sequence'])
        if file_type in type_choices:
          preferred_selection = type_choices.index(file_type)
      elif file_type == 'processed pickle list':
        type_choices.extend(['processed pickle list'])
        preferred_selection = type_choices.index('processed pickle list')
      elif file_type in ('IOTA settings',
                         'PRIME settings',
                         'LABELIT target',
                         'DIALS target'):
        type_choices.extend(['IOTA settings', 'PRIME settings',
                             'LABELIT target', 'DIALS target'])
        preferred_selection = type_choices.index(file_type)

    return type_choices, preferred_selection

  def add_item(self, path):
    # Generate item
    inp_choices, inp_sel = self.set_type_choices(path)
    type_choice = ct.DataTypeChoice(self.ctr,
                                    choices=inp_choices)
    item = ct.InputListItem(path=path,
                            type=type_choice,
                            buttons=ct.MiniButtonBoxInput(self.ctr))

    self.Bind(wx.EVT_CHOICE, self.onTypeChoice, item.type.type)
    item.buttons.btn_mag.Bind(wx.EVT_BUTTON, self.onMagButton)
    item.buttons.btn_delete.Bind(wx.EVT_BUTTON, self.onDelButton)
    item.buttons.btn_info.Bind(wx.EVT_BUTTON, self.onInfoButton)

    # Insert list item
    idx = self.ctr.InsertStringItem(self.ctr.GetItemCount() + 1, item.path)
    self.ctr.SetItemWindow(idx, 1, item.type, expand=True)
    self.ctr.SetItemWindow(idx, 2, item.buttons, expand=True)

    # Set drop-down selection, check it for data and open other tabs
    item.type.type.SetSelection(inp_sel)
    if item.type.type.GetString(inp_sel) in ['processed pickle',
                                           'processed pickle list',
                                           'processed pickle folder']:
      self.main_window.toolbar.EnableTool(
        self.main_window.tb_btn_run.GetId(),True)
    elif item.type.type.GetString(inp_sel) == 'reference MTZ':
      self.input_window.opt_chk_useref.Enable()
    elif item.type.type.GetString(inp_sel) == 'sequence':
      pass
    else:
      warn_bmp = bitmaps.fetch_icon_bitmap('actions', 'status_unknown',
                                           size=16)
      item.buttons.btn_info.SetBitmapLabel(warn_bmp)
      item.warning = True

    # Record index in all relevant places
    item.id = idx
    item.buttons.index = idx
    item.type.index = idx
    item.type_selection = inp_sel

    # Resize columns to fit content
    col1_width = max([self.ctr.GetItemWindow(s, col=1).type.GetSize()[0]
                      for s in range(self.ctr.GetItemCount())]) + 5
    col2_width = item.buttons.GetSize()[0] + 15
    col0_width = self.ctr.GetSize()[0] - col1_width - col2_width
    self.ctr.SetColumnWidth(0, col0_width)
    self.ctr.SetColumnWidth(1, col1_width)
    self.ctr.SetColumnWidth(2, col2_width)

    # Make sure all the choice lists are the same size
    if item.type.type.GetSize()[0] < col1_width - 5:
      item.type.type.SetSize((col1_width - 5, -1))

    # Attach data object to item
    self.ctr.SetItemData(item.id, item)

  def onTypeChoice(self, e):
    type = e.GetEventObject().GetParent()
    item_data = self.ctr.GetItemData(type.index)
    item_data.type.type.SetSelection(type.type.GetSelection())
    item_data.type_selection = type.type.GetSelection()

    # Evaluate whether data folders / files are present
    data_items = 0
    for idx in range(self.ctr.GetItemCount()):
      if self.ctr.GetItemData(idx).type_selection != 0:
        data_items += 1
    if data_items > 0:
      self.main_window.toolbar.EnableTool(self.main_window.tb_btn_run.GetId(),
                                          True)
    else:
      self.main_window.toolbar.EnableTool(self.main_window.tb_btn_run.GetId(),
                                          False)
    e.Skip()


  def onMagButton(self, e):
    idx = e.GetEventObject().GetParent().index
    item_obj = self.ctr.GetItemData(idx)
    path = item_obj.path
    type = item_obj.type.type.GetString(item_obj.type_selection)

    if os.path.isfile(path):
      if type in ('processed pickle list', 'sequence', 'text'):
        with open(path, 'r') as f:
          msg = f.read()
        textview = dlg.TextFileView(self, title=path, contents=msg)
        textview.ShowModal()
      #TODO: when individual pickle, show pickle info; also include json files
      # else:
      #   wx.MessageBox('Unknown file type', 'Warning',
      #                 wx.OK | wx.ICON_EXCLAMATION)
    elif os.path.isdir(path):
      inputs, _ = ginp.get_input(path, filter=False)
      file_list = '\n'.join(inputs)
      filelistview = dlg.TextFileView(self, title=path, contents=file_list)
      filelistview.ShowModal()

  def onDelButton(self, e):
    item = e.GetEventObject().GetParent()
    self.delete_button(item.index)
    self.ctr.Refresh()

  def delete_all(self):
    for idx in range(self.ctr.GetItemCount()):
      self.delete_button(index=0)

  def delete_button(self, index):
    item_data = self.ctr.GetItemData(index)
    if item_data.type.type.GetString(item_data.type_selection) == 'reference MTZ':
      self.input_window.opt_chk_useref.Disable()
      self.input_window.opt_chk_useref.SetValue(False)

    self.ctr.DeleteItem(index)

    # Refresh widget and list item indices
    if self.ctr.GetItemCount() != 0:
      for i in range(self.ctr.GetItemCount()):
        item_data = self.ctr.GetItemData(i)
        item_data.id = i
        item_data.buttons.index = i
        item_data.type.index = i
        type_choice = self.ctr.GetItemWindow(i, col=1)
        type_selection = item_data.type.type.GetSelection()
        type_choice.type.SetSelection(type_selection)
        self.ctr.SetItemData(i, item_data)

  def onInfoButton(self, e):
    ''' Info / alert / error button (will change depending on circumstance) '''
    idx = e.GetEventObject().GetParent().index
    item_obj = self.ctr.GetItemData(idx)
    item_type = item_obj.type.type.GetString(item_obj.type_selection)

    if item_obj.warning:
      wx.MessageBox(item_obj.info['WARNING'], 'Warning', wx.OK |
                    wx.ICON_EXCLAMATION)
    else:
      wx.MessageBox(item_obj.info[item_type], 'Info', wx.OK |
                    wx.ICON_INFORMATION)
