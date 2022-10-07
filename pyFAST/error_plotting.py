
#
# Copyright 2017 National Renewable Energy Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
    This library provides tools for plotting the output channels over time of a
    given solution attribute for two OpenFAST solutions, with the second solution
    assumed to be the baseline for comparison. There are functions for solution
    file I/O, plot creation, and html creation for navigating the plots.
"""

import os
import sys
import shutil
import numpy as np
from typing import List


def _plot_channel(time, test, baseline, xlabel, title1, title2, RTOL_MAGNITUDE, ATOL_MAGNITUDE):
    from bokeh.plotting import figure
    from bokeh.models.tools import HoverTool
    from bokeh.layouts import gridplot
    from bokeh.embed import components

    # Plot the baseline and test channels
    p1 = figure(title=title1)
    p1.title.align = 'center'
    p1.grid.grid_line_alpha = 0.3
    p1.xaxis.axis_label = 'Time (s)'
    p1.line(time, baseline, color='green',
            line_width=3, legend_label='Baseline')
    p1.line(time, test, color='red', line_width=1, legend_label='Local')
    p1.add_tools(
        HoverTool(tooltips=[('Time', '@x'), ('Value', '@y')], mode='vline'))

    # Plot the error and threshold
    p2 = figure(title=title2, x_range=p1.x_range)
    p2.title.align = 'center'
    p2.grid.grid_line_alpha = 0
    p2.xaxis.axis_label = 'Time (s)'
    p2.line(time, abs(baseline - test), color='blue', legend_label="Error")

    # Calculate the threshold
    NUMEPS = 1e-12
    ATOL_MIN = 1e-6
    baseline_offset = baseline - np.min(baseline)
    b_order_of_magnitude = np.floor(np.log10(baseline_offset + NUMEPS))
    rtol = 10**(-1 * RTOL_MAGNITUDE)
    atol = 10**(max(b_order_of_magnitude) - ATOL_MAGNITUDE)
    atol = max(atol, ATOL_MIN)
    passfail_line = atol + rtol * abs(baseline)
    p2.line(time, passfail_line, color='red', legend_label="Threshold")
    # p2.cross(xseries, passfail_line)
    p2.add_tools(
        HoverTool(tooltips=[('Time', '@x'), ('Error', '@y')], mode='vline'))

    grid = gridplot([[p1, p2]], width=650, height=375,
                    sizing_mode="scale_both")

    # Return script and div
    return components(grid)


def plot_channel_data(channels: List[str], units: List[str],
                      test_data, baseline_data, rtol, atol):
    plots = []
    for i, (channel, unit) in enumerate(zip(channels, units)):
        title1 = channel + " (" + unit + ")"
        title2 = "abs(Local - Baseline)"
        xlabel = 'Time (s)'
        script, div = _plot_channel(test_data[:, 0],
                                    test_data[:, i], baseline_data[:, i],
                                    xlabel, title1, title2, rtol, atol)
        plots.append({'channel': channel, 'script': script, 'div': div})
    return plots


def export_case_summary(run_path: str, case: str, channel_names: List[str],
                        channel_ok: List[bool], norms, plots: List[dict]):
    """
    norms: first dimension is the channel and second dimension contains the norms
    channel_ok: 1d boolean array for whether a channel passed the comparison
    """

    with open(os.path.join(run_path, case+".html"), "w") as html:
        html.write(_htmlHead(case + " Summary", plots))

        html.write('<body>\n')
        html.write(
            '  <h2 class="text-center">{}</h2>\n'.format(case + " Summary"))
        html.write('  <div class="container">\n')

        channel_tags = [
            '<a href="#{0}">{0}</a>'.format(channel) for channel in channel_names]

        cols = [
            'Channel',
            'Relative Max Norm',
            'Relative L2 Norm',
            'Infinity Norm'
        ]
        table = _tableHead(cols)

        body = '      <tbody>' + '\n'

        for i, channel_tag in enumerate(channel_tags):
            body += '        <tr>' + '\n'
            body += '          <th scope="row">{}</th>'.format(i+1) + '\n'
            body += '          <td>{0:s}</td>'.format(channel_tag) + '\n'

            fmt = '{0:0.4e}'
            for val in norms[i]:
                if not channel_ok[i]:
                    body += ('          <td class="cell-highlight">' +
                             fmt + '</td>\n').format(val)
                else:
                    body += ('          <td>' + fmt + '</td>\n').format(val)

            body += '        </tr>' + '\n'
        body += '      </tbody>' + '\n'
        table += body
        table += '    </table>' + '\n'
        html.write(table)

        html.write('    <br>' + '\n')
        for plot in plots:
            html.write('    <div style="margin:10 auto"'
                       ' id="{channel}">{div}</div>\n'.format(**plot))

        html.write('  </div>' + '\n')

        html.write('</body>' + '\n')
        html.write(_htmlTail())


def _htmlHead(title, plots):
    from bokeh.resources import CDN
    head = _html_head_template.format(
        title=title, cdn_file_1=CDN.js_files[0], cdn_file_2=CDN.js_files[2],
        scripts='\n'.join([plot['script'] for plot in plots]))
    return head


_html_head_template = '''<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>

  <!-- CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
  <link href="https://cdn.pydata.org/bokeh/release/bokeh-widgets-1.2.0.min.css" rel="stylesheet" type="text/css">
  <link href="https://cdn.pydata.org/bokeh/release/bokeh-1.2.0.min.css" rel="stylesheet" type="text/css">

  <!-- JS -->
  <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/popper.js@1.12.9/dist/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>

  <!-- JS - Bokeh -->
  <script src="{cdn_file_1}"></script>
  <script src="{cdn_file_2}"></script>
  <script type="text/javascript"> Bokeh.set_log_level("info"); </script>

  <!-- JS - Plots -->
  {scripts}

  <style media="screen" type="text/css">
    .cell-warning {{
      background-color: #efc15c;
    }}
    .cell-highlight {{
      background-color: #f5ed86 ;
    }}
  </style>
</head>
'''


def _htmlTail():
    tail = '</html>' + '\n'
    return tail


def _tableHead(columns: List[str]):
    head = _table_head_template.format(columns='</th>\n<th>'.join(columns))
    return head


_table_head_template = '''
    <table class="table table-bordered table-hover table-sm" style="margin: auto; width: 100%; font-size:80%">
      <thead>
        <tr>
          <th>#</th>
          <th>{columns}</th>
        </tr>
      </thead>
'''


def export_results_summary(path, results):
    with open(os.path.join(path, "regression_test_summary.html"), "w") as html:

        html.write(_htmlHead("Regression Test Summary"))

        html.write('<body>' + '\n')
        html.write(
            '  <h2 class="text-center">{}</h2>'.format("Regression Test Summary") + '\n')
        html.write('  <div class="container">' + '\n')

        # Test Case - Pass/Fail - Max Relative Norm
        data = [('<a href="{0}/{0}.html">{0}</a>'.format(r[0]), r[1], r[2],
                 '<a href="{0}/{0}.log">{0}.log</a>'.format(r[0])) for i, r in enumerate(results)]
        table = _tableHead(
            ['Test Case', 'Pass/Fail', 'Completion Code', 'Screen Output'])
        body = '      <tbody>' + '\n'
        for i, d in enumerate(data):
            body += '        <tr>' + '\n'
            body += '          <th scope="row">{}</th>'.format(i+1) + '\n'
            body += '          <td>{0:s}</td>'.format(d[0]) + '\n'

            fmt = '{0:s}'
            if d[1] == "FAIL":
                body += ('          <td class="cell-warning">' +
                         fmt + '</td>').format(d[1]) + '\n'
            else:
                body += ('          <td>' + fmt + '</td>').format(d[1]) + '\n'

            if d[2] != 0:
                body += ('          <td class="cell-warning">{}</td>').format(
                    d[2]) + '\n'
            else:
                body += ('          <td>{}</td>').format(d[2]) + '\n'

            body += '          <td>{0:s}</td>'.format(d[3]) + '\n'

            body += '        </tr>' + '\n'
        body += '      </tbody>' + '\n'
        table += body
        table += '    </table>' + '\n'
        html.write(table)

        html.write('    <br>' + '\n')
        html.write('  </div>' + '\n')
        html.write('</body>' + '\n')
        html.write(_htmlTail())
    html.close()
