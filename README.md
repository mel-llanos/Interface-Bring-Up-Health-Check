# Interface Bring Up Health Check

The purpose of this script is to monitor for the symptoms associated with CSCwj84211 / CSCwj95850:
- Consistent 0 RX Rate
- No CDP Neighbor Entry (this can be adjusted to check for LLDP Neighbor Entry)
- Bad Preamble Non-Zero

If the symptoms are identified, a syslog will be generated notifying user issue has been triggered.\
If the symptoms are not identified, a syslog will be generated notifying the user issue has not been triggered before performing next actions specified.\
As an example, the actions performed after identifying the issue has not been triggered is to write erase & reload the switch to repeat the cycle.

The script has definitions included to keep track of the amount of times the script has been executed. This provides an accurate count of cycles performed.

The script must be stored in /bootflash/scripts/ folder.

Create file execution_count.txt in bootflash prior to 1st run of script. The file can be empty or contain a value of 0.\
If you change the file's location or name, it will need to be updated in the script under variable count_file

To execute the script on boot up, an EEM script is paired with it.\
The EEM script will execute the script once the last interface with an active connection, meaning the cable must be connected to an online device, comes up.

Configuration to be added to the switch base config file on POAP server:
```
track 1 interface Ethernet1/54 line-protocol

event manager applet INT_UP_HEALTH_CHECK
  event track 1 state up
  action 1.0 cli source interface_health_check.py 
```

Script is based on Python3.\
Script has only been tested on N9K-C9348GC-FXP running 10.3 & 10.5 release trains.
