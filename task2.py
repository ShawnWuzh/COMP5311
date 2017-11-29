from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNetConnections,quietRun,custom
from mininet.log import setLogLevel,output,lg
import argparse
from numbers import Number
from multiprocessing import Process
from subprocess import Popen
import os
from time import time,sleep
from mininet.cli import CLI
from mininet.link import TCLink
from util.monitor import monitor_devs_ng
class LinearTopo(Topo):
    '''
    Linear Topology of k hosts and k switches, with one host each switch
    '''
    def __init__(self,n,bw=10,delay='10ms',loss=10,**opts):
        super(LinearTopo,self).__init__(**opts)
        self.n = n # there are n senders in the network
        receiver = self.addHost('receiver')
        last_switch = None
        senders = []
        switches = []
        lconf = {'bw':bw,'delay':delay,'loss':loss}
        for i in range(self.n):
            host_name = 'h{}'.format(str(i+1))
            switch_name = 's{}'.format(str(i+1))
            host = self.addHost(host_name)
            switch = self.addSwitch(switch_name)
            senders.append(host)
            switches.append(switch)
            self.addLink(host,switch,**lconf)
            if last_switch:   # if there is a previous switch, then add link
                self.addLink(switch,last_switch,**lconf)
            last_switch = switch
        # wire up the receiver to the first swtich
        self.addLink(receiver,switches[0])

def start_tcpprobe(args):
    os.system("rmmod tcp_probe 1>/dev/null 2>&1; modprobe tcp_probe")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.folder, shell=True)

def stop_tcpprobe():
    os.system("killall -9 cat; rmmod tcp_probe")

def check_prereqs():
    "Check for necessary programs"
    prereqs = ['telnet', 'iperf', 'ping','bwm-ng']
    # bwm-ng if for testing bandwidth
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

    n = args.n
    port = 2048
    monitor = Process(target=monitor_devs_ng,
                      args=('%s/bwm.txt' % args.folder, 1.0))
    monitor.start()
    start_tcpprobe(args)
    recvr = net.getNodeByName('receiver')
    # the port_num is the port number server waiting for
    recvr.cmd('iperf -s -p %s > %s/iperf_server.txt' % (port,args.folder) + '&')
    h = [] # Python list of clients
    for i in range(n):
        h.append( net.getNodeByName('h%s' % (i+1)) )
    waitListening(h[0], recvr, port)
     # send iperf cmd to all hosts
    for i in range(n):
        node_name = 'h%s' % (i+1)
        h[i].sendCmd('iperf -c %s -p %s -i 1 -Z reno -yc > %s/iperf_%s.txt' % (recvr.IP(), port, args.folder, node_name))

    # wait for commands to finish
    iperf_results = {}
    for i in range(n):
        iperf_results[h[i].name] = h[i].waitOutput()
    recvr.cmd('kill %iperf')
    monitor.terminate()
    stop_tcpprobe()

if __name__=='__main__':
    '''
    For varying the bandwidth: we will use 20
    For varying the delay: we will use 5ms
    For varing the loss rate: we will use 2% loss
    '''
    check_prereqs()
    parser = argparse.ArgumentParser(description='Linear Topology Test')
    parser.add_argument('--n','-n',required=True,type=int,help='the number of hosts')
    parser.add_argument('--bandwidth','-b',default=10,type=int,help='the bandwidth of the link')
    parser.add_argument('--delay','-d',default='0ms',type=str,help='the delay in the link')
    parser.add_argument('--loss','-l',default=0,type=int,help='the loss rate in the link')
    parser.add_argument('--folder', '-f',help="folder to store outputs",default="results")
    args=parser.parse_args()
    if not os.path.exists(args.folder):
        os.mkdir(args.folder)
    lconf = {'bw':args.bandwidth,'delay':args.delay,'loss':args.loss}
    link = custom(TCLink,bw=args.bandwidth,delay=args.delay,loss=args.loss)
    topo = LinearTopo(args.n,**lconf)
    net = Mininet(topo=topo,link=link)
    net.start()
    print('---------------------NODE CONNECTIONS---------------------------------------------')
    CLI(net)
    print('---------------------DUMPIING NETWORK CONNECTIONS---------------------------------')
    dumpNetConnections(net)
    print('---------------------TESTING NETWORK CONNECTIVITY---------------------------------')
    net.pingAll()
    run_linear_topology_test(net,args)
    net.stop()
    os.system("killall -9 bwm-ng")

    print('---------------------TEST FINISHED------------------------------------------------')
