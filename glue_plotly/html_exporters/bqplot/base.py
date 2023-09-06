from os import getcwd
from os.path import exists

from glue.viewers.common.tool import Tool

import ipyvuetify as v
from ipywidgets import HBox
from IPython.display import display
from ipyfilechooser import FileChooser

from glue_plotly import PLOTLY_LOGO


class PlotlyBaseBqplotExport(Tool):
    icon = PLOTLY_LOGO
    action_text = 'Save Plotly HTML page'
    tool_tip = 'Save Plotly HTML page'

    def activate(self):
        file_chooser = FileChooser(getcwd())
        ok_btn = v.Btn(color='success', disabled=True, children=['Ok'])
        close_btn = v.Btn(color='error', children=['Close'])
        dialog = v.Dialog(
            width='500',
            children=[
                v.Card(children=[
                    v.CardTitle(primary_title=True, children=["Select output filepath"]),
                    file_chooser,
                    HBox(children=[ok_btn, close_btn]
                )])
            ]
        )

        def on_ok_click(button, event, data):
            self.maybe_save_figure(file_chooser.selected)
            dialog.v_model = False

        def on_close_click(button, event, data):
            dialog.v_model = False

        def on_selected_change(chooser):
            ok_btn.disabled = not bool(chooser.selected_filename)

        ok_btn.on_event('click', on_ok_click)
        close_btn.on_event('click', on_close_click)
        file_chooser.register_callback(on_selected_change)

        with self.viewer.output_widget:
            dialog.v_model = True
            display(dialog)


    def maybe_save_figure(self, filepath):
        if exists(filepath):
            yes_btn = v.Btn(color='success', children=["Yes"])
            no_btn = v.Btn(color='error', children=["No"])
            check_dialog = v.Dialog(
                width='500',
                children=[
                    v.Card(children=[
                        v.CardText(children=["This filepath already exists. Are you sure you want to overwrite it?"]),
                        HBox(children=[no_btn, yes_btn])
                    ]
                )
            ])
            def on_yes_click(button, event, data):
                self.save_figure(filepath)
                check_dialog.v_model = False
            def on_no_click(button, event, data):
                check_dialog.v_model = False
            yes_btn.on_event('click', on_yes_click)
            no_btn.on_event('click', on_no_click)
            with self.viewer.output_widget:
                check_dialog.v_model = True
                display(check_dialog)
        else:
            self.save_figure(filepath)


    def save_figure(self, filepath):
        raise NotImplementedError()
