#!/usr/bin/env bash


export FOL_PI=/home/pi
export FOL_LI=$FOL_PI/li
export FOL_DDH=$FOL_LI/ddh
export FOL_VEN=$FOL_LI/venv
export FOL_VAN=$FOL_LI/venv_api


# 0 black, 1 red, 2 green, 3 yellow
# 4 blue, 5 magenta, 6 cyan, 7 white
function _p_color { tput setaf "$1"; printf "%s\n" "$2"; tput sgr0; }
function _pr { _p_color 1 "$1"; }
function _pg { _p_color 2 "$1"; }
function _py { _p_color 3 "$1"; }
function _pb { _p_color 6 "$1"; }
function _e {
    if [ "$1" -ne 0 ]; then
        _pr "error: $2, the error rv is $1"; exit "$1";
    fi
}


function check_already_running {
    # $1: main_dds_controller
    pgrep -f "$1"
    rv=$?
    if [ "$rv" -eq 0 ]; then
        _s="$1 is already running"
        _py "$_s"
        exit 0;
    fi
}
