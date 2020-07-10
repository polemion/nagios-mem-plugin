#!/usr/bin/python3

# A Nagios plugin that checks defined memory limits for a selected process, by name.
# Copyright (C) <2018~> <Dimitrios Koukas>

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published
#   by the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys, psutil
from argparse import ArgumentParser

__author__ = 'Dimitrios Koukas'
__version__ = '1.0'


def pexit(msg, exco):
    """Exit actions."""
    print (msg)
    sys.exit(exco)

def argsDef():
    """Argument rules."""
    argp = ArgumentParser(description='Nagios plugin that checks for swapping and defined memory limits for a selected'
                                      ' process, by name.\n(by %s, v%s)' % (__author__, __version__))
    argp.add_argument('-p', '--proc', dest='proc', type=str, help='process name to track.')
    argp.add_argument('-w', '--wthres', dest='wthres', type=int, help='warning threshold in MBs.')
    argp.add_argument('-c', '--cthres', dest='cthres', type=int, help='critical threshold in MBs.')
    args = argp.parse_args()
    return args.proc, int(args.wthres*1048576), int(args.cthres*1048576) if any((args.proc, args.wthres, args.cthres)) else pexit(
        'WARNING - Insufficient arguments supplied.', 1)

def procDict(proc):
    """Return a dict containing details for each process."""
    def setstate(mem):
        """Check memory limits."""
        if mem < wthres: return 0
        elif mem >= wthres < cthres: return 1
        elif mem >= cthres: return 2
        else: return False
    # Encapsulate data
    memdict = {x.cmdline()[0]: {'vms': x.memory_info().vms,
                                'swap': x.memory_full_info().swap,
                                'product': x.cmdline()[0].replace('/clover/prod/tr/thor-', '').replace('/bin/thor', ''),
                                'state': setstate(x.memory_info().vms)
                                } for x in psutil.process_iter(attrs=['name']) if x.info['name'] == proc}
    # Exit if no process is found
    if not memdict: pexit('MEMORY UNKNOWN - could not find any process named %s.' % proc, 0)
    # Additional data
    state = [memdict[x]['state'] for x in memdict]  # Process threshold state
    swap = any([True if memdict[x]['swap'] else False for x in memdict])  # Are we swapping?
    wrn, crt = state.count(1), state.count(2)  # Count critical and warning states
    memap = ', '.join(['%s:%s' % (memdict[x]['product'], 'SWAPPING' if memdict[x]['swap'] else
            '%sMB' % int(memdict[x]['vms']/1048576)) for x in memdict])  # Create process memory map
    return memdict, wrn, crt, memap, swap


# Get directives from Nagios
proc, wthres, cthres = argsDef()
# Get process(es) information
meminfo, wrn, crt, memap, swap = procDict(proc)
# Prepare results for Nagios
pnum = '' if len(meminfo) == 1 else 'es'
wrnpl = '' if wrn == 1 else 'es'
crtpl = '' if crt == 1 else 'es'
# Return results to Nagios
if wrn == crt == 0 and not swap:  # All OK
    pexit('MEMORY LIMITS OK: "%s" Process%s operating within allowed parameters (%s).' % (proc, pnum, memap), 0)

elif wrn == crt == 0 and swap:  # Critical: Memory OK but swapping
    pexit('CRITICAL: Swapping detected. (%s).' % (memap), 2)

elif wrn > 0 and crt == 0 and not swap:  # Warning: Memory above warning levels
    pexit('WARNING: (%s) Process%s operating above allowed parameters (%s).' % (wrn, wrnpl, memap), 1)

elif wrn > 0 and crt == 0 and swap:  # Critical: Swapping also some process(es) above warning levels
    pexit('CRITICAL: Swapping detected. (%s) Process%s operating above allowed parameters (%s).' % (
        wrn, wrnpl, memap), 2)

elif wrn > 0 and crt > 0 and not swap:  # Critical: Some processes above critical and some above warning levels
    pexit('CRITICAL: (%s) Process%s exceeded critical thresholds and (%s) process%s operating above allowed parameters '
          '(%s).' % (crt,  crtpl, wrn, wrnpl, memap), 2)

elif wrn > 0 and crt > 0 and swap:  # Critical: Swapping also some processes above critical and some above warning levels
    pexit('CRITICAL: Swapping detected. (%s) Process%s exceeded critical thresholds and (%s) process%s operating above allowed '
          'parameters (%s).' % (crt,  crtpl, wrn, wrnpl, memap), 2)

elif wrn == 0 and crt > 0 and not swap:  # Critical: Memory above critical levels
    pexit('CRITICAL: (%s) Process%s exceeded critical thresholds (%s).' % (crt,  crtpl, memap), 2)

elif wrn == 0 and crt > 0 and swap:  # Critical: Swapping, some process(es) above critical levels
    pexit('CRITICAL: Swapping detected. (%s) Process%s exceeded critical thresholds (%s).' % (crt,  crtpl, memap), 2)
