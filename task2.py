from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections,quietRun
from mininet.log import setLogLevel
import argparse
from numbers import Number
from multiprocessing import Process
from subprocess import Popen
import os
from time import time,sleep
from mininet.cli import CLI
class LinearTopo(Topo):
    '''
    Linear Topology of n hosts and n switches, with one host each switch
    '''
    def __init__(self,n,bw,delay,loss,**opts):
        super(LinearTopo,self).__init__(**opts)
        self.n = n # there are n senders in the network
        receiver = self.addHost('receiver')
        last_switch = None
        senders = []
        switches = []
        lconfig = {'bw': bw, 'delay': delay,'loss': loss }
        for i in range(self.n):
            host_name = 'h{}'.format(str(i+1))
            switch_name = 's{}'.format(str(i+1))
            host = self.addHost(host_name)
            switch = self.addSwitch(switch_name)
            senders.append(host)
            switches.append(switch)
            self.addLink(host,switch,**lconfig)
            if last_switch:   # if there is a previous switch, then add link
                self.addLink(switch,last_switch,**lconfig)
            last_switch = switch
        # wire up the receiver to the first swtich
        self.addLink(receiver,switches[0])

def start_tcpprobe(args):
    os.system("rmmod tcp_probe 1>/dev/null 2>&1; modprobe tcp_probe")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.folder, shell=True)

def stop_tcpprobe():
    os.system("killall -9 cat; rmmod tcp_probe")

def monitor_devs_ng(fname, interval_sec=0.01):
    """Uses bwm-ng tool to collect iface tx rate stats.  Very reliable."""
    cmd = ("sleep 1; bwm-ng -t %s -o csv "
           "-u bits -T rate -C ',' > %s" %
           (interval_sec * 1000, fname))
    Popen(cmd, shell=True).wait()


def check_prereqs():
    "Check for necessary programs"
    prereqs = ['telnet', 'bwm-ng', 'iperf', 'ping']
    for p in prereqs:
        if not quietRun('which ' + p):
            raise Exception((
                'Could not find {} - make sure that it is '
                'installed and in your $PATH').format(p))


def waitListening(client, server, port):
    '''
    Wait until server is listening on port
    '''
    if not 'telnet' in client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    while 'Connected' not in client.cmd(cmd):
        output('waiting for', server,
               'to listen on port', port, '\n')
        sleep(.5)


def run_linear_topology_test(net,args):
    '''
    The function is for testing the linear Topology
    '''

    # The monitot is for monitoring the throughput of the network
    n = args.n
    monitor = Process(target=monitor_devs_ng, args=('%s/bwm.txt' % args.folder, 1.0))
    monitor.start()
    start_tcpprobe(args)
    recvr = net.getNodeByName('receiver')
    # the port_num is the port number server waiting for
    port_num = 2048
    recvr.cmd('iperf -s -p', port, '> %s/iperf_server.txt' % args.folder, '&')
    h = [] # Python list of clients
    for i in range(n):
        h.append( net.getNodeByName('h%s' % (i+1)) )
    for i in range(n):
        waitListening(h[i], recvr, port)
     # send iperf cmd to all hosts
    for i in range(n):
        node_name = 'h%s' % (i+1)
        h[i].sendCmd('iperf -c %s -p %s -i 1 -yc > %s/iperf_%s.txt' % (recvr.IP(), port, args.folder, node_name))

    # wait for commands to finish
    iperf_results = {}
    for i in range(n):
        iperf_results[h[i].name] = h[i].waitOutput()
    recvr.cmd('kill %iperf')

    # terminate monitors
    monitor.terminate()
    stop_tcpprobe()

if __name__=='__main__':
    check_prereqs()
    parser = argparse.ArgumentParser(description='Linear Topology Test')
    parser.add_argument('--n','-n',required=True,type=int,help='the number of hosts')
    parser.add_argument('--bandwidth','-b',default=10,type=Number,help='the bandwidth of the link')
    parser.add_argument('--delay','-d',default='10ms',type=str,help='the delay in the link')
    parser.add_argument('--loss','-l',default=10,type=Number,help='the loss rate in the link')
    parser.add_argument('--folder', '-f',help="folder to store outputs",default="results")
    args=parser.parse_args()
    if not os.path.exists(args.folder):
        os.mkdir(args.folder)
    topo = LinearTopo(args.n,args.bandwidth,args.delay,args.loss)
    net = Mininet(topo=topo)
    net.start()
    print('---------------------NODE CONNECTIONS---------------------------------------------')
    CLI(net)
    print('---------------------DUMPIING NETWORK CONNECTIONS---------------------------------')
    dumpNetConnections(net)
    print('---------------------TESTING NETWORK CONNECTIVITY---------------------------------')
    net.pingAll()
    run_linear_topology_test(net,args)
    net.stop()
    os.system('killall -9 bwm-ng')
    print('---------------------TEST FINISHED------------------------------------------------')
