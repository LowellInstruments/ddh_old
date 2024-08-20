# Changelog

4.0.00

    2024 version of the DDH App

4.0.01 

    fixed in_ports_geo.py detection

4.0.02

    added notification field 'dl_files'

4.0.03

    added removal of mobile GPS JSON files older than 2 days

4.0.04

    bug in logs.py in building file_out on testing mode

4.0.05
    
    prevented deletion of error_maps.gif when receiving doppio maps from DDN
    added possibility of water column mode for TDO

4.0.06

    added fix for summary box DO-1 / DO-2

4.0.07

    added water column mode for graphing for DOX and TDO loggers
    added new logs.py entries, with unified timestamp
    added year filtering on AWS uploads

4.0.08

    added new maps GOM / MAB
    fixed bug setup_tab not opening after pressing "cancel without saving"
    cleaned logs generation
    made the graphs show the same order than the history

4.0.09

    Some things were not plotted for LI loggers, re-arranged water column mode

4.0.10

    Fixed command DEL using wrong filename when "testmode_" is ON.
