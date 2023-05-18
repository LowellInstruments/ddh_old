import json

import iso8601
from matplotlib.ticker import FormatStrFormatter
import numpy as np
from ddh.utils_data import data_glob_files_to_plot
from utils.ddh_shared import (
    send_ddh_udp_gui as _u,
    ddh_get_settings_json_file,
    get_mac_from_folder_path,
    dds_get_json_mac_dns,
    ddh_get_is_last_haul,
    STATE_DDS_NOTIFY_PLOT_RESULT_OK,
    STATE_DDS_NOTIFY_PLOT_RESULT_ERR,
)
from settings import ctx
import logging
from utils.logs import lg_gui as lg

logging.getLogger("matplotlib").setLevel(logging.WARNING)


def _plt_json_get_span_dict():
    j = str(ddh_get_settings_json_file())
    with open(j) as f:
        cfg = json.load(f)
        assert cfg["span_dict"]
        return cfg["span_dict"]


def _plt_get_long_span_description(s):
    d = {"h": "hour", "d": "day", "w": "week", "m": "month", "y": "year"}
    return d[s]


def _plt_get_json_units():
    j = str(ddh_get_settings_json_file())
    with open(j) as f:
        cfg = json.load(f)
    return cfg["units_temp"], cfg["units_depth"]


def _plt_csv_file_suffix_from_metric(m):
    d = {
        "DOS": "_DissolvedOxygen",
        "DOP": "_DissolvedOxygen",
        "DOT": "_DissolvedOxygen",
        "T": "_Temperature",
        "P": "_Pressure"
    }
    return d[m]


# format x-axis labels, the one showing time
def _plt_fmt_x_labels(t, span, sd):
    lb = []
    for each in t:
        fmt_t = iso8601.parse_date(each).strftime(sd[span][3])
        lb.append(fmt_t)
    return lb


# format x-axis ticks
def _plt_fmt_x_ticks(t, span, sd):
    return t[:: (sd[span][4])]


def _plt_fmt_title(t, span):
    last_time = iso8601.parse_date(t[-1])
    title_dict = {
        "h": "last hour: {}".format(last_time.strftime("%b. %d, %Y")),
        "d": "last day: {}".format(last_time.strftime("%b. %d, %Y")),
        "w": "last week: {}".format(last_time.strftime("%b. %Y")),
        "m": "last month: {}".format(last_time.strftime("%b. %Y")),
        "y": "last year",
    }
    return title_dict[span]


def _plt_color_from_csv_column_name(csv_column_name):
    d = {
        "Temperature (C)": "orangered",
        "Pressure (dbar)": "tab:cyan",
        "Dissolved Oxygen (mg/l)": "black",
        "Dissolved Oxygen (%)": "black",
        "DO Temperature (C)": "orangered",
        "Water Detect (%)": "blue",
    }
    return d[csv_column_name]


def _plt_metric_to_csv_column_name(m):
    d = {
        "T": "Temperature (C)",
        "P": "Pressure (dbar)",
        "DOS": "Dissolved Oxygen (mg/l)",
        "DOP": "Dissolved Oxygen (%)",
        "DOT": "DO Temperature (C)",
        "WAT": "Water Detect (%)",
    }
    return d[m]


def _plt_metric_to_legend_name(m):
    d = {
        "T": "Temperature (C)",
        "P": "Depth (m)",
        "DOS": "Dissolved Oxygen (mg/l)",
        "DOP": "Dissolved Oxygen (%)",
        "DOT": "DO Temperature (C)",
        "WAT": "Water Detect (%)",
    }
    return d[m]


def _plot_draw_metric_set(fol, ax, ts, m_s, t, y_set):

    # m_s: metric set
    c0 = _plt_metric_to_csv_column_name(m_s[0])
    c1 = _plt_metric_to_csv_column_name(m_s[1])
    l0 = _plt_metric_to_legend_name(m_s[0])
    l1 = _plt_metric_to_legend_name(m_s[1])
    clr0 = _plt_color_from_csv_column_name(c0)
    clr1 = _plt_color_from_csv_column_name(c1)
    mac = get_mac_from_folder_path(fol)
    my_lg = dds_get_json_mac_dns(mac)
    sd = _plt_json_get_span_dict()
    y0 = y_set[0]
    y1 = y_set[1]
    y2 = []
    if len(y_set) == 3:
        y2 = y_set[2]
        c2 = _plt_metric_to_csv_column_name(m_s[2])
        l2 = _plt_metric_to_legend_name(m_s[2])
        clr2 = _plt_color_from_csv_column_name(c2)

    # plot -> get axis (NOT axes)
    ax.figure.clf()
    ax.figure.tight_layout()
    ax0 = ax.figure.add_subplot(111)
    ax.figure.subplots_adjust(right=0.82)

    # -----------------------
    # metric 1 display hacks
    # -----------------------

    # display hack for Fahrenheits T display
    column_names_temp = ("DO Temperature (C)", "Temperature (C)")
    units_temp, units_depth = _plt_get_json_units()
    if y0 and l0 in column_names_temp and units_temp == "F":
        l0 = l0.replace("(C)", "(F)")
        y0 = [((i * 9 / 5) + 32) for i in y0]

    # hack for _inverted_ P / depth display
    if y0 and l0 == "Depth (m)":
        ax0.invert_yaxis()
        if units_depth == "f":
            y0 = [(i * 0.546) for i in y0]
            l0 = "Depth (f)"

    # -----------------
    # metric 1 -> plot
    # ts: 'h'
    # -----------------
    tit = _plt_fmt_title(t, ts)
    sym = "{} ".format("\u2014")
    ax0.set_ylabel(sym + l0, fontsize="large", fontweight="bold", color=clr0)
    ax0.tick_params(axis="y", labelcolor=clr0)
    ax0.plot(t, y0, label=l0, color=clr0)
    ax0.set_xlabel("time", fontsize="large", fontweight="bold")
    lhf = ddh_get_is_last_haul()
    h = "last haul" if lhf else "all hauls"
    s = h + " for \n" + "logger " + my_lg + ", " + tit
    ax0.set_title(s, fontsize="x-large")
    lbs = _plt_fmt_x_ticks(t, ts, sd)

    # metric 2: not always present
    if y1:
        # get current plot axis
        ax1 = ax0.twinx()

        # -----------------------
        # metric 2 display hacks
        # -----------------------

        # hack for Fahrenheits T display
        if y1 and l1 in column_names_temp and units_temp == "F":
            l1 = l1.replace("(C)", "(F)")
            y1 = [((i * 9 / 5) + 32) for i in y1]

        # hack for _inverted_ P / depth display
        if l1 == "Depth (m)":
            ax1.invert_yaxis()
            if units_depth == "f":
                y1 = [(i * 0.546) for i in y1]
                l1 = "Depth (f)"

        # -----------------
        # metric 2 -> plot
        # -----------------

        sym = "- -  "
        ax1.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
        ax1.set_ylabel(sym + l1, fontsize="large", fontweight="bold", color=clr1)
        ax1.tick_params(axis="y", labelcolor=clr1)
        ax1.plot(t, y1, "--", label=l1, color=clr1)
        ax1.set_xticks(lbs)

    # metric 3: not always present
    if y2:

        # ------------------
        # metric 3 -> plot
        # ------------------

        ax2 = ax0.twinx()
        ax2.spines.right.set_position(("axes", 1.15))
        sym = ". . "
        ax2.set_ylabel(sym + l2, fontsize="large", fontweight="bold", color=clr2)
        ax2.tick_params(axis="y", labelcolor=clr2)
        ax2.plot(
            t,
            y2,
            markersize=6,
            marker=".",
            linestyle=(0, (5, 10)),
            label=l2,
            color=clr2,
        )

    # --------------------------------------------------------
    # x-axis label (time) MUST be formatted here, at the end
    # --------------------------------------------------------

    # cnv.figure.legend(bbox_to_anchor=[0.9, 0.5], loc='center right')
    ax0.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax0.set_xticks(lbs)
    ax0.set_xticklabels(_plt_fmt_x_labels(lbs, ts, sd))
    cnv = ax.figure.canvas
    cnv.draw()


def _plot_one_set_of_metrics(fol, ax, ts, metric_set):

    # one_metric_set: ['DOS', 'DOT', 'WAT'] / another: ['T', 'P']
    mac = get_mac_from_folder_path(fol)
    lhf = ddh_get_is_last_haul()
    sd = _plt_json_get_span_dict()
    h = "last haul" if lhf else "all hauls"
    s = "one_metric_set \n\t{} \n\t{} \n\t{}"
    lg.a(s.format(metric_set, h, mac))

    all_y = []
    for i, metric in enumerate(metric_set):
        try:
            # calculate file suffic from input metric
            suffix = _plt_csv_file_suffix_from_metric(metric)

            # grab the data from within files having the calculated suffix
            # metric: 'DOS'
            # suffix: '_DissolvedOxygen'
            # sd: span dictionary from ddh.json
            # ts: "h" for hour, "d" for day...
            t, y = data_glob_files_to_plot(fol, ts, metric, suffix, sd)
            good_dots = np.count_nonzero(~np.isnan(y))
            if good_dots < 2:
                return 2

            # y: data points for a metric
            all_y.append(y)

        except (AttributeError, Exception) as ex:
            # e.g. no values at all, None.values
            sn = dds_get_json_mac_dns(mac)
            lg.a("error _plot_one_set_of_metrics, exception -> {}".format(ex))
            _ = "{}({}) for {}, mac {}".format(metric, ts, sn, mac)
            if i == 0:
                lg.a("error: critical -> {}".format(_))
                return 1
            lg.a("warning: NON critical -> {}".format(_))

    # ---------------
    # draw the plot
    # ---------------
    _plot_draw_metric_set(fol, ax, ts, metric_set, t, all_y)
    return 0


def gui_plot_all_set_of_metrics():

    fol = ctx.g_p_d
    ax = ctx.g_p_ax
    # ts: for example 'h', set by GUI
    ts = ctx.g_p_ts
    all_metric_sets = ctx.g_p_met

    # ---------------------------------------
    # iterate and try to plot all_metric_sets
    # [ ['DOS', 'DOT', 'WAT'], ['T', 'P'] ]
    # ---------------------------------------
    rv = 0
    for each_metric_set in all_metric_sets:
        args = (fol, ax, ts, each_metric_set)
        rv = _plot_one_set_of_metrics(*args)
        if rv == 0:
            # good!
            _u(STATE_DDS_NOTIFY_PLOT_RESULT_OK)
            return 0

    # ---------------------
    # ALL PLOTS went wrong
    # ---------------------
    _m = get_mac_from_folder_path(fol)
    if rv == 1:
        e = "error: plot '{}'".format(dds_get_json_mac_dns(_m))
        _u("{}/{}".format(STATE_DDS_NOTIFY_PLOT_RESULT_ERR, e))
        lg.a("{}".format(e))

    elif rv == 2:
        s = _plt_get_long_span_description(ts)
        e = "not enough dots to plot\n one {} for '{}'"
        e = e.format(s, dds_get_json_mac_dns(_m))
        _u("{}/{}".format(STATE_DDS_NOTIFY_PLOT_RESULT_ERR, e))
        lg.a("error {}".format(e.replace("\n", "")))

    return rv
