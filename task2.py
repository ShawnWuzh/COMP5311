from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

class LinearTopo(Topo):
    '''
    Linear Topology of n hosts and n switches, with one host each switch
    '''
    def __init__(self,n,**opts):
        super.__init__(**opts)
        self.n = n # there are n senders in the network
        receiver = self.addHost('receiver')
        last_switch = None
        senders = []
        switches = []
        for i in range(self.n):
            host_name = 'h{}'.format(str(i+1))
            switch_name = 's{}'.format(str(i+1))
            host = self.addHost(host_name)
            switch = self.addSwitch(switch_name)
            senders.append(host)
            switches.append(switch)
            self.addLink(host,switch)
            switch += 1
            if last_switch:   # if there is a previous switch, then add link
                self.addLink(switch,last_switch)
            last_switch = switch
        # wire up the receiver to the first swtich
        self.addLink(receiver,switches[0])
