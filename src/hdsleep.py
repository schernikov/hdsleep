'''
Created on Jan 12, 2013

@author: schernikov
'''

import os, sys, re, subprocess, datetime, time

statre = re.compile('\s*(?P<devmaj>\d+)\s+(?P<devmin>\d+)\s+(?P<devname>\w+)\s+'
                        '(?P<goodreads>\d+)\s+(?P<mergedreads>\d+)\s+(?P<sectorsread>\d+)\s+(?P<millisread>\d+)\s+'
                        '(?P<goodwrites>\d+)\s+(?P<mergedwrites>\d+)\s+(?P<sectorswritten>\d+)\s+(?P<milliswrite>\d+)\s+'
                        '(?P<currentIOs>\d+)\s+(?P<millisIOs>\d+)\s+(?P<millisIOspent>\d+)')
drivere = re.compile('\s*drive state is:\s*(?P<state>[^\s]+)')
diskline = re.compile('\s*/dev/(?P<name>\w+)\:')

diskpref = '/dev/disk/by-id/'
polltime = 10 # seconds

def main():
    if len(sys.argv) < 3:
        usage()
        return
    if os.getuid() != 0:
        print "use sudo to run in admin mode"
        return 
    try:
        minutes = float(sys.argv[1])
    except:
        print "expected minutes, got %s"%(sys.argv[1])
        return
    if minutes <= 0:
        print "idle time should be positive, got %.2f"%(minutes)
        return
    idle = datetime.timedelta(minutes=minutes)
    disks = []
    for dn in sys.argv[2:]:
        if not dn.startswith(diskpref):
            print "expected disk name '%s', got '%s'"%(diskpref, dn)
            return
        disks.append(dn)
    print "idle minutes: %.2f"%(minutes)
    print "polling every %d seconds"%(polltime)
    dmap = diskmap(disks)
    dset = sorted(dmap.keys())
    dstates = state(dset)
    dstats = stats(dset)
    prevstate = {}
    stamps = {}
    now = datetime.datetime.now()
    for nm in dset:
        print "  %s -> %s (%s)"%(dmap[nm], devname(nm), dstates[nm])
        prevstate[nm] = dstats[nm]['reads']+dstats[nm]['writes']
        stamps[nm] = now
    while True:
        time.sleep(polltime)
        dstats = stats(dset)
        dstates = state(dset)
        now = datetime.datetime.now()
        for nm in dset: 
            st = dstats[nm]['reads']+dstats[nm]['writes']
            if prevstate[nm] != st:
                prevstate[nm] = st
                stamps[nm] = now
            else:
                if (stamps[nm] + idle) <= now:  # time to put it to sleep
                    if dstats[nm]['activeIOs'] == 0: # do this only if no active IO is going on
                        if dstates[nm].find('active') >= 0: # and only if it is currently active
                            #print "putting %s to sleep"%(nm)
                            sleep(nm)

def usage():
    print "Usage: '%s <idle-minutes> %s<diskname> [%s<diskname> ..]'"%(os.path.basename(sys.argv[0]), diskpref, diskpref)

def devname(nm):
    return '/dev/%s'%(nm)

def diskmap(disks):
    dset = {}
    for dn in disks:
        nm = os.path.realpath(dn)
        dset[os.path.basename(nm)] = dn
    return dset

def sleep(nm):
    subprocess.call('hdparm -y %s'%(devname(nm)))

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

if __name__ == '__main__':
    main()