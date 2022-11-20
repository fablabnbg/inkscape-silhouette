import wx
from wx.lib.agw import genericmessagedialog as gmd

class Dialog:
    def confirm(parent, question, caption = 'Silhouette Multiple Actions'):
        dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result

    def info(parent, message, extended = '',
                    caption = 'Silhouette Multiple Actions',):
        dlg = gmd.GenericMessageDialog(
            parent, message, caption, wrap=1000,
            agwStyle=wx.OK | wx.ICON_INFORMATION | gmd.GMD_USE_AQUABUTTONS)
        # You might wonder about the choice of "aquabuttons" above. It's the
        # only option that led to the buttons being visible on the system
        # this was first tested on.
        dlg.SetLayoutAdaptationMode(wx.DIALOG_ADAPTATION_MODE_ENABLED)
        if extended:
            dlg.SetExtendedMessage(extended)
        dlg.ShowModal()
        dlg.Destroy()
