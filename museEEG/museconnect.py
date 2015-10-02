"""
MuseConnect
reads OSC input from muse-io and creates queues to hold each value, pulled exernally when needed

author: Mike Pesavento
date: 2015.09.30
"""


import argparse
import threading
import time

from collections import deque

from pythonosc import dispatcher
from pythonosc import osc_server


class MuseConnect(object):
    """
    Creates osc server and handlers to read data from Interaxon Muse headset
    It is meant to be the producer side of a producer-consumer design pattern

    You need to have muse-io installed, get SDK from here:
    https://sites.google.com/a/interaxon.ca/muse-developer-site/download

    load muse OSC output in command line with:
        muse-io --preset 14 --osc osc.udp://localhost:5000 --osc-timestamp
        muse-io --preset 14 --osc osc.udp://localhost:5000 --osc-timestamp --device Muse-7C56
    The "--osc-timestamp" adds on 2 extra elements to each OSC message, containing
    a long int for the unix epoch time, and another int for the milliseconds

    Each member that catches information from the muse-io OSC output puts it in a deque object after
    some basic analysis (eg averaging the frontal sensors only)

    """
    def __init__(self, ipAddress="127.0.0.1", port=5000, verbose=True):
        self.verbose = verbose  # if true, print all caught OSC packet analysis products

        self.connected = False
        self.oscDispatcher = dispatcher.Dispatcher()
        # oscDispatcher.map("/debug", print)
        self.oscDispatcher.map("/muse/batt", self.battery_handler, "battery")
        self.oscDispatcher.map("/muse/elements/touching_forehead", self.touchingforehead_handler, "touchingforehead")
        self.oscDispatcher.map("/muse/elements/horseshoe", self.horseshoe_handler, "horseshoe")

        self.oscDispatcher.map("/muse/elements/delta_absolute", self.eeg_bandpower_handler, "delta_absolute")
        self.oscDispatcher.map("/muse/elements/theta_absolute", self.eeg_bandpower_handler, "theta_absolute")
        self.oscDispatcher.map("/muse/elements/alpha_absolute", self.eeg_bandpower_handler, "alpha_absolute")
        self.oscDispatcher.map("/muse/elements/beta_absolute", self.eeg_bandpower_handler, "beta_absolute")
        self.oscDispatcher.map("/muse/elements/gamma_absolute", self.eeg_bandpower_handler, "gamma_absolute")

        self.oscDispatcher.map("/muse/elements/delta_relative", self.eeg_bandpower_handler, "delta_relative")
        self.oscDispatcher.map("/muse/elements/theta_relative", self.eeg_bandpower_handler, "theta_relative")
        self.oscDispatcher.map("/muse/elements/alpha_relative", self.eeg_bandpower_handler, "alpha_relative")
        self.oscDispatcher.map("/muse/elements/beta_relative", self.eeg_bandpower_handler, "beta_relative")
        self.oscDispatcher.map("/muse/elements/gamma_relative", self.eeg_bandpower_handler, "gamma_relative")

        # each of these should be an empty queue,
        # where each element holds a tuple of (timestamp, value)
        # get all values from the queue with (times, values) = muse.popValue()
        self.battery = deque()
        # self.touchingforehead = deque()
        self.onForehead = None
        self.sec_since_last_forehead_trans = 0  # the time delta since the last time the forehead contact changed state
        self._contactTransTime = 0  # the time that we observed the transition of contact state
        self.horseshoe = deque()
        self.curSensorState = None  # hold just the most recent value from horseshoe

        self.delta_absolute = deque()
        self.theta_absolute = deque()
        self.alpha_absolute = deque()
        self.beta_absolute = deque()
        self.gamma_absolute = deque()

        self.delta_relative = deque()
        self.theta_relative = deque()
        self.alpha_relative = deque()
        self.beta_relative = deque()
        self.gamma_relative = deque()

        self.oscServer = osc_server.ThreadingOSCUDPServer((ipAddress, port), self.oscDispatcher)
        self.oscServer.daemon = True
        print("Muse OSC client running on {}".format(self.oscServer.server_address))

    def start(self):
        """
        start the osc server & message handler
        """
        self.connected = True
        # self.oscServer.serve_forever()
        t = threading.Thread(target=self.oscServer.serve_forever)
        print("test")
        t.daemon = True
        t.start()
        print("Started Muse OSC reader")

    def shutdown(self):
        """
        close the osc server
        """
        # do we actually even need this?
        self.oscServer.shutdown()

    def vprint(self, value):
        """
        verbose print, only if verbose is on
        """
        if self.verbose:
            print(value)

    def _timestamp(self, ts, tsms):
        """
        return the epoch timestamp in floating point
        """
        return ts + float(tsms) / 1e6

    def _averageFront(self, channelValues):
        """
        average the front sensor values
        """
        return (channelValues[1] + channelValues[2]) / 2.

    def battery_handler(self, address, name, chargePercent, fuelgaugeBattVolt, ADCBattVolt, temperature, ts, tsms):
        """
        gets battery data from Muse, with:
        chargePercent = %/100, range (0-10000)
        fuelgaugeBattVolt = mV, 3000-4200 mV
        ADCBattVolt = mV, 3200-4200 mV
        temperature = C, -40 to 125 C
        updates at 0.1 Hz
        """
        # print("battery:", name, ":", chargePercent, fuelgaugeBattVolt, ADCBattVolt, temperature, ts, tsms)
        self.vprint("battery: {}".format(chargePercent / 100.))
        element = (self._timestamp(ts, tsms), chargePercent / 100.)
        self.battery.append(element)  # return percent charge in floating point

    def touchingforehead_handler(self, address, name, touchingforehead):
        """
        returns value 1 if touching forehead, 0 if not
        updated at 1 Hz
        """
        self.vprint("touchingforehead: {}".format(touchingforehead))
        curtime = time.time()
        # if len(self.touchingforehead) == 0 or self.touchingforehead[-1][1] != touchingforehead:
        #     self._contactTransTime = curtime
        # self.touchingforehead.extend((curtime, touchingforehead))
        self.onForehead = touchingforehead
        self.sec_since_last_forehead_trans = curtime - self._contactTransTime

    def horseshoe_handler(self, address, name, ch1, ch2, ch3, ch4):
        """
        status indicator for each of the Muse channels
        1 = good, 2 = ok, >=3 bad
        """
        horseshoe = [ch1, ch2, ch3, ch4]
        self.vprint("horseshoe: {}".format(horseshoe))
        # element = (self.timestamp(ts, tsms), horseshoe)
        self.horseshoe.append(horseshoe)
        self.currentSensorState = horseshoe

    def eeg_bandpower_handler(self, address, name, ch1, ch2, ch3, ch4):
        """
        uses class attributes to append values to the correct attribute queue
        """
        values = [ch1, ch2, ch3, ch4]
        out = self._averageFront(values)
        self.vprint("{}: {}".format(name[0], out))
        attr = self.__getattribute__(name[0])
        attr.append(out)

    def popAll(self, name):
        """
        clear the queue, using muse attribute "name", e.g. "alpha_absolute"
        """
        attr = self.__getattribute__(name)
        return [attr.popleft() for _i in range(len(attr))]

    def pop(self, name):
        """
        get oldest value in attribute with name, e.g. "alpha_absolute"
        """
        attr = self.__getattribute__(name)
        return attr.popleft()

    def get_alpha(self):
        """
        the specific function used in Change Your Mind to get
        the absolute alpha power
        """
        return self.popAll("alpha_absolute")

    def is_on_forehead(self):
        return self.onForehead

    def get_sec_since_last_forehead_trans(self):
        return self.sec_since_last_forehead_trans

    def getSensorState(self):
        """
        return the buffer of sensor states.
        typically only the last one matters
        """
        return self.popAll("horseshoe")


if __name__ == "__main__":
    # import matplotlib.pyplot as plt  # used for live plot updates

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
                        default="127.0.0.1",
                        help="The ip to listen on")
    parser.add_argument("--port",
                        type=int,
                        default=5000,
                        help="The port to listen on")
    args = parser.parse_args()

    muse = MuseConnect(args.ip, args.port)

    muse.start()  # this is a blocking call!!! wtf!!!??

    # ## this doesnt actually do anything
    # try :
    #     while 1 :
    #         time.sleep(1)

    # except KeyboardInterrupt :
    #     print("\nClosing OSCServer.")
    #     muse.shutdown()
