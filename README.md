# FritzBox-monitor
Monitor FritzBox metrics via a telegraf/influxdb/grafana stack that reads data from TR-064

## Background
I have a FritzBox 7490 at home, which is connected to a vDSL 100/40 line - I was wondering regarding my traffic patterns, as well as things like connected WiFi clients, DSL line capacity and so on.

## What you get....
![Grafana dashboard](grafana-fritzbox-dashboard.jpg?raw=true)
* Includes current DSL rates, possible line rates (over time)
* Traffic on DSL line and LAN port (seems to only register LAN1 in TR-064)
* Packets per second on WLAN, LAN and DSL
* Clients associated in WLAN2.4 / WLAN 5 & WLAN guest
* DECT clients, active VOIP numbers

### My use case
The special thing to mention is:
* TR-064 is only accessible from the LAN (for good reasons, in terms of security)
* My monitoring stack of influxDB etc runs on my server in Frankfurt - so the metrics need to get there safely and securly.
* Another open port on my server, e.g. for InfluxDB etc was not deemed acceptable
* For security considerations, I prefer a "direct pull" of metrics, e.g. by telegraf
* So, the _actual_ monitoring collector needs from a decoy host in the LAN, namely my diskstation or one of the raspis
* LAN hosts can be securely / directly accessed by IPv6, and thanks to DNS updates, also carry AAAA entries.

### References
I started looking around, and found a good number of projects and descriptions,  most notably:
* https://github.com/kbr/fritzconnection
* https://github.com/jhubig/FritzBoxShell
* https://github.com/fetzerch/fritzcollectd
on how to do it... but all of those needed quite some extra work, or did not fit my use case
FritzBoxShell did not completely fetch all the information available, as described by https://avm.de/service/schnittstellen/, and the scripts provided with fritzconnection did needed modification as well, the collectd plugin (based on FritzConnection) requires of cause an collectd somewhere in LAN - and an accessible sink.

## Installation
### Pre-requisites

### FritzBox
* Have a recent FritzOS - I have tested with FRITZ!OS 07.19 on a FritzBox 7490
* Enable TR-064 on your fritzbox, and add a dedicated _monitoring_ user (see: https://www.schlaue-huette.de/apis-co/fritz-tr064/ )
* Check from LAN, whether you can access http://fritz.box:49000/tr64desc.xml

### Diskstation extras
* Have a Python 3 installation (install Python package) and fritzconnection running (this is quite a task):
  * Install _opkg_ as your package manager, probably best via EasyBootstrapInstaller (see: https://community.synology.com/enu/forum/1/post/127148 )
  * Have "python3-pip" and "python3-lxml" (to tackle the TR-064 SOAP) ready and installed (either installed via opkg, or via pip-bootstrap - have fun getting lxml running on the diskstation without opkg... as the headers are missing)
  * Make sure you have the fritzconnection module: `pip install fritzconnections`
* Create a _monitoring_ user via web-ui, have this one be an admin user (otherwise ssh-login does not work)
* Add your monitoring servers telegraf ssh key to `~monitoring/.ssh/authorized_keys`

### Monitoring server (in the internet)
* Have a recent telegraf installation running
* Have the local output configured, e.g. `[[outputs.influxdb]]`
* Have grafana ready, to be able to read from said output
  * Install the carpet-plot panel, to get fancy traffic analysis (bucket per time of day on y-axis, and day at x-axis, color is the intensity) https://grafana.com/grafana/plugins/petrslavotinek-carpetplot-panel 
* Configure telegraf to be able to ssh out with key-auth
  * Create an ssh-key for `~telegraf` , probably in `/etc/telegraf/.ssh/id_rsa` *without* passphrase, so it can be called from telegraf directly.
  * Check whether telegraf can log in to your diskstation (in the LAN) via keyauth