'''
Created on Jan 12, 2013

@author: schernikov
'''

import os, re, subprocess, datetime, time, argparse

statre = re.compile('\s*(?P<devmaj>\d+)\s+(?P<devmin>\d+)\s+(?P<devname>\w+)\s+'
                        '(?P<goodreads>\d+)\s+(?P<mergedreads>\d+)\s+(?P<sectorsread>\d+)\s+(?P<millisread>\d+)\s+'
                        '(?P<goodwrites>\d+)\s+(?P<mergedwrites>\d+)\s+(?P<sectorswritten>\d+)\s+(?P<milliswrite>\d+)\s+'
                        '(?P<currentIOs>\d+)\s+(?P<millisIOs>\d+)\s+(?P<millisIOspent>\d+)')
drivere = re.compile('\s*drive state is:\s*(?P<state>[^\s]+)')
diskline = re.compile('\s*/dev/(?P<name>\w+)\:')

DEVNULL = open(os.devnull, 'wb')
diskpref = '/dev/disk/by-id/'
polltime = 10 # seconds
posttimes = 2 # times

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-S', '--sleep-minutes', metavar='minutes', help='idle minutes before sleep', type=float)
    parser.add_argument('-m', '--monitor-seconds', metavar='seconds', default=polltime, type=float, 
                        help='monitor disk usage (default:%(default)ss)')
    parser.add_argument('-p', '--postpone', metavar='N', default=posttimes, 
                        help="delay sending 'hdparm -y ...' N monitoring cycles "
                        "and hope drive will go sleep itself (default:%(default)s)", type=int)
    parser.add_argument('disks', metavar='disk', type=str, nargs='+', help='disk name')
    args = parser.parse_args()
    try:
        process(args)
    except (KeyboardInterrupt, SystemExit):
        print "exiting"
        return

def process(args):
    if os.getuid() != 0:
        print "use sudo to run in admin mode"
        return 

    minutes = args.sleep_minutes
    if minutes:
        if minutes <= 0:
            print "idle time should be positive, got %.2f"%(minutes)
            return
        idle = datetime.timedelta(minutes=minutes)
        if args.postpone < 0:
            print "postpone count must be non-negative, got %d"%(args.postpone)
            return
        remcode = time2hdparm(idle.total_seconds())
    else:
        idle = None
    disks = []
    for dn in args.disks:
        if not dn.startswith(diskpref):
            if not os.path.exists(dn):
                print "expected disk name '%s', got '%s'"%(diskpref, dn)
                return
            for nm in os.listdir(diskpref):
                dd = os.path.join(diskpref, nm)
                if os.path.realpath(dd) == dn:
                    disks.append(dd)
                    break
            else:
                print "can not find %s in %s"%(dn, diskpref)
                return
        else:
            disks.append(dn)
    if minutes: 
        print "put drives to sleep in %.2f idle minutes"%(minutes)
    else:
        print "monitoring mode"
    print "polling every %d seconds"%(args.monitor_seconds)
    dmap = diskmap(disks)
    dset = sorted(dmap.keys())
    dstates = state(dset)
    dstats = stats(dset)
    prevmod = {}
    prevstat = {}
    stamps = {}
    postpone = {}
    now = datetime.datetime.now()
    for nm in dset:
        dstat = dstats[nm]
        print "  %s -> %s (%s) reads:%d writes:%d"%(dmap[nm], devname(nm), dstates[nm], dstat['reads'], dstat['writes'])
        prev = {}
        prev['reads'] = dstat['reads']
        prev['writes'] = dstat['writes']
        prevstat[nm] = prev
        prevmod[nm] = dstates[nm]
        postpone[nm] = None
        stamps[nm] = now
    print

    while True:
        time.sleep(args.monitor_seconds)
        dstats = stats(dset)
        dstates = state(dset)
        now = datetime.datetime.now()
        for nm in dset:
            dstat = dstats[nm] 
            reads = checktype(prevstat[nm], dstat, 'reads')
            writes = checktype(prevstat[nm], dstat, 'writes')
            if reads != 0 or writes != 0 or prevmod[nm] != dstates[nm]:
                if reads != 0:
                    rs = "%7s=%d"%('r +%d'%reads, dstat['reads'])
                else:
                    rs = ' '
                if writes != 0:
                    ws = "%7s=%d"%('w +%d'%writes, dstat['writes'])
                else:
                    ws = ' '
                if prevmod[nm] != dstates[nm]:
                    ms = dstates[nm]
                else:
                    ms = ' '
                val, txt = date_diff(stamps[nm], now)
                print "%10s %18s %18s %3s %-10s %-s %s"%(devname(nm), rs, ws, str(val) if val!=0 else ' ', txt, now.strftime('%Y-%m-%d %H:%M:%S'), ms)
                stamps[nm] = now
            prevmod[nm] = dstates[nm]
            if idle:
                if (stamps[nm] + idle) <= now:  # time to put it to sleep
                    if dstates[nm].find('active') >= 0: # and only if it is currently active
                        if postpone[nm] is None: 
                            postpone[nm] = args.postpone
                            remind(nm, remcode, now)    # remind this drive that it has to go to sleep sometimes
                        else:
                            postpone[nm] -= 1
                        if postpone[nm] <= 0 and dstat['activeIOs'] == 0:
                            # do this only if no active IO is going on
                            sleep(nm, now)
                            postpone[nm] = None
                    else:
                        postpone[nm] = None
                else:
                    postpone[nm] = None

def updatestate(prev, cur, tp):
    prev[tp] = cur[tp]

def checktype(prev, cur, tp):
    diff = cur[tp]-prev[tp]
    if diff > 0: prev[tp] = cur[tp]
    return diff

def devname(nm):
    return '/dev/%s'%(nm)

def diskmap(disks):
    dset = {}
    for dn in disks:
        nm = os.path.realpath(dn)
        dset[os.path.basename(nm)] = dn
    return dset

def date_diff(older, newer):
    if newer < older:
        timeDiff = older - newer
        post = ' in future'
    else:
        timeDiff = newer - older
        post = ''

    if timeDiff.days > 1:
        return timeDiff.days, 'days'+post
    total_seconds = int(timeDiff.total_seconds())
    hours = total_seconds/3600
    if hours > 1:
        return hours, 'hours'+post
    minutes = total_seconds/60
    if minutes > 1:
        return minutes, 'minutes'+post
    if total_seconds > 1:
        return total_seconds, 'seconds'+post
    if total_seconds == 1:
        return 1, 'second'+post
    return 0, 'now'

def sleep(nm, now):
    print "putting %s to sleep (%s)"%(devname(nm), now.strftime('%Y-%m-%d %H:%M:%S'))
    subprocess.call(['hdparm', '-y', devname(nm)], stdout=DEVNULL, stderr=DEVNULL)

def remind(nm, code, now):
    if code is None: return
    print "setting %s sleep time (%s)"%(devname(nm), now.strftime('%Y-%m-%d %H:%M:%S'))
    subprocess.call(['hdparm', '-S%d'%code, devname(nm)], stdout=DEVNULL, stderr=DEVNULL)

def state(disks):
    cmd = ['hdparm', '-C']
    for dn in disks:
        cmd.append(devname(dn))
    output = subprocess.check_output(cmd)
    disk = None
    dstates = {}
    for line in output.splitlines():
        m = diskline.match(line)
        if m:
            dsk = m.groupdict()['name']
            if not dsk in disks: continue
            disk = dsk
            continue
        m = drivere.match(line)
        if m:
            if not disk: continue
            dstates[disk] = m.groupdict()['state']
            disk = None 
    return dstates

def stats(disks):
    res = {}
    with open('/proc/diskstats') as f:
        for line in f:
            m = statre.match(line)
            if not m: continue
            dd = m.groupdict()
            if not dd['devname'] in disks: continue
            reads = int(dd['goodreads'])
            writes = int(dd['goodwrites'])
            ios = int(dd['currentIOs'])
            res[dd['devname']] = {'reads':reads, 'writes':writes, 'activeIOs':ios}
    return res

def time2hdparm(seconds):
    if 240*5 >= seconds:
        return int((seconds+4)/5)
    if 21*60 == seconds:
        return 252
    if (251-240)*1800 >= seconds:
        idx = int((seconds+1800-1)/1800)
        return idx+240
    return None

if __name__ == '__main__':
    main()