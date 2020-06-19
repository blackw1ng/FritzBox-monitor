#!/opt/bin/python3

from fritzconnection import FritzConnection
import sys

FRITZBOX_USER = "monitoring"
FRITZBOX_PASSWORD = "xxx"

try:
    fc = FritzConnection(address='192.168.178.1', user=FRITZBOX_USER, password=FRITZBOX_PASSWORD, timeout=2.0)

except BaseException:
    print("Cannot connect to fritzbox.")
    sys.exit(1)


def readout(module, action, variable=None, show=False, numeric=True):
    '''
    Generic readout function, that wraps values in a json-compliant way.
    :module: TR-064 sub-modules, such as 'WANIPConn1'
    :action: Calls an action, e.g. 'GetStatusInfo', as defined by TR-04 (cf. https://avm.de/service/schnittstellen/)
    :variable: (optional) a specific variable out of this set to extract
    :show: print variable name
    :numeric: cast value to numeric
    '''
    try:
        answer_dict = fc.call_action(module, action)
    except BaseException:
        print(f"Could not query {module} with action {action}")
        raise

    # cast the 64 bit traffic counters into int
    if action == "GetAddonInfos":
        answer_dict['NewX_AVM_DE_TotalBytesSent64'] = int(answer_dict['NewX_AVM_DE_TotalBytesSent64'])
        answer_dict['NewX_AVM_DE_TotalBytesReceived64'] = int(answer_dict['NewX_AVM_DE_TotalBytesReceived64'])

    if variable:
        # single variable extraction mode
        answer_dict = str(answer_dict[variable])

        # FIXME: try type-conversion to int, then fallback to string.
        if not numeric:
            answer_dict = '"' + answer_dict + '"'

        if show:
            answer_dict = '"' + variable + '": ' + answer_dict
    else:
        # remove unwanted keys in a safe way
        entitiesToRemove = ('NewAllowedCharsSSID', 'NewDNSServer1', 'NewDNSServer2', 'NewVoipDNSServer1',
                            'NewVoipDNSServer2', 'NewATURVendor', 'NewATURCountry', 'NewDeviceLog')
        entitiesToRemove = [answer_dict.pop(k, None) for k in entitiesToRemove]

        # cast to string, omit the {} without a regex :)
        answer_dict = str(answer_dict)[1:-1]

    # handle stupid naming of counters in LAN, so we can use grouping in grafana...
    answer_dict = answer_dict.replace("NewBytes", "NewTotalBytes")
    answer_dict = answer_dict.replace("NewPackets", "NewTotalPackets")

    # ugly string-cast to a dictionary that has json compliant "
    flattened_string = answer_dict.replace("'", '"').replace("True", "true").replace("False", "false")

    return flattened_string


def assemble(*args):
    # ugly hack json array constructor.
    json_dict = "\t v: {" + ', '.join(list(args)) + "}"
    print(json_dict)


def add_device_tag(starting=False):
    if starting:
        comma = ""
    else:
        comma = ","
    print('\t' + comma + '{"box": "' + deviceinfo + '",')


def add_interface_tag(interface):
    print('\t"interface": ' + interface + ',')


def end_device():
    print('\t}')


#############

# tag every meaurement by fritzbox serial number
deviceinfo = readout('DeviceInfo1', 'GetInfo', 'NewSerialNumber')

# list of measurements - so telegraf puts them in separate lines
print('[')

# box generic info
add_device_tag(starting=True)
uptime = readout('DeviceInfo1', 'GetInfo', 'NewUpTime', show=True)
version = readout('DeviceInfo1', 'GetInfo', 'NewDescription', show=True, numeric=False)
dhcp_leases = readout('Hosts1', 'GetHostNumberOfEntries', show=True)
assemble(uptime, version, dhcp_leases)
end_device()

# tag list by box & interface
add_device_tag()
add_interface_tag("wan")
status = readout('WANIPConn1', 'GetStatusInfo')
link = readout('WANCommonIFC1', 'GetCommonLinkProperties')
my_ip = readout('WANIPConn', 'GetExternalIPAddress')
my_ipv6 = readout('WANIPConn', 'X_AVM_DE_GetExternalIPv6Address', 'NewExternalIPv6Address', show=True, numeric=False)
# my_ipv6_prefix = readout('WANIPConn','X_AVM_DE_GetIPv6Prefix','NewIPv6Prefix', show=False)+"/"+
#                  readout('WANIPConn','X_AVM_DE_GetIPv6Prefix','NewPrefixLength', show=False)
info = readout('WANDSLInterfaceConfig1', 'GetInfo')
traffic = readout('WANCommonIFC1', 'GetAddonInfos')
assemble(status, link, my_ip, my_ipv6, info, traffic)
end_device()

# check dect
add_device_tag()
add_interface_tag("dect")
registered = readout('X_AVM-DE_Dect1', 'GetNumberOfDectEntries')
assemble(registered)
end_device()

# check voip
add_device_tag()
add_interface_tag("voip")
registered = readout('X_VoIP1', 'X_AVM-DE_GetNumberOfNumbers')
assemble(registered)
end_device()

# tag list for the other networks
for i, interface in enumerate(['lan', 'wlan24', 'wlan5', 'wlanGuest']):
    add_device_tag()
    add_interface_tag(interface)
    if i == 0:
        assemble(readout('LANEthernetInterfaceConfig1', 'GetStatistics'))

    else:
        stats = readout('WLANConfiguration'+str(i), 'GetStatistics')
        associations = readout('WLANConfiguration'+str(i), 'GetTotalAssociations')
        info = readout('WLANConfiguration'+str(i), 'GetInfo', "NewChannel", show=True)
        assemble(stats, associations, info)
    end_device()

print("]")
