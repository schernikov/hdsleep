hdsleep
=======

Drives monitoring tool. 
It can also put drives to sleep using `hdparm -y ...` if `hdparm -SXXX ...` does not work for some reason.

Here is sample output for monitoring mode.
<pre>
linux>$ sudo python hdsleep.py -m 10 /dev/sd[cb]
polling every 10 seconds
  /dev/disk/by-id/wwn-0x500XXXXXXXXXXXX0 -> /dev/sdb (active/idle) reads:13189 writes:4843
  /dev/disk/by-id/wwn-0x500XXXXXXXXXXXX3 -> /dev/sdc (active/idle) reads:80104 writes:23979

  /dev/sdb         r +6=13195          w +4=4847   4 minutes    2013-01-19 10:46:26.592732  
  /dev/sdc                                         5 minutes    2013-01-19 10:46:36.601310 standby
  /dev/sdb                             w +2=4849  40 seconds    2013-01-19 10:47:06.632266  
  /dev/sdc                                        10 minutes    2013-01-19 10:56:41.226495 active/idle
  /dev/sdc       r +987=81091         w +3=23982  10 seconds    2013-01-19 10:56:51.242651  
  /dev/sdc       r +459=81550                     10 seconds    2013-01-19 10:57:01.247861  
  /dev/sdc                            w +4=23986  10 seconds    2013-01-19 10:57:11.260513  
  /dev/sdc         r +1=81551         w +5=23991  10 seconds    2013-01-19 10:57:21.274861  
  /dev/sdc                           w +22=24013  10 seconds    2013-01-19 10:57:31.285458  
  /dev/sdc         r +1=81552         w +8=24021  10 seconds    2013-01-19 10:57:41.297062  
  /dev/sdc                            w +4=24025  10 seconds    2013-01-19 10:57:51.307475  
  /dev/sdc                            w +3=24028  30 seconds    2013-01-19 10:58:21.340573
  /dev/sdb                                        16 minutes    2013-01-19 11:03:41.720453 standby
</pre>
