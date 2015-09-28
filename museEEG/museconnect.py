import argparse
import math
import time

from pythonosc import dispatcher
from pythonosc import osc_server


class MuseConnect:
    """
    creates osc server and handlers to read data from Interaxon Muse headset

    need to have muse-io installed, get SDK from here:
    https://sites.google.com/a/interaxon.ca/muse-developer-site/download

    load muse OSC output in command line with:
        muse-io --preset 14 --osc osc.udp://localhost:5000
        muse-io --preset 14 --osc osc.udp://localhost:5000 --device Muse-7C56
    """
    def __init__(self, ipAddress="127.0.0.1", port=5000):

        self.oscDispatcher = dispatcher.Dispatcher()
        #oscDispatcher.map("/debug", print)
        self.oscDispatcher.map("/muse/batt", self.battery_handler, "battery")
        self.oscDispatcher.map("/muse/elements/touching_forehead", self.touchingforehead_handler, "touchingforehead")
        self.oscDispatcher.map("/muse/elements/horseshoe", self.horseshoe_handler, "horseshoe")
        # self.oscDispatcher.map("/muse/elements/delta_absolute", self.eeg_delta_handler, "delta_absolute")
        # self.oscDispatcher.map("/muse/elements/theta_absolute", self.eeg_theta_handler, "theta_absolute")
        # self.oscDispatcher.map("/muse/elements/alpha_absolute", self.eeg_alpha_handler, "alpha_absolute")
        # self.oscDispatcher.map("/muse/elements/beta_absolute", self.eeg_beta_handler, "beta_absolute")
        # self.oscDispatcher.map("/muse/elements/gamma_absolute", self.eeg_gamma_handler, "gamma_absolute")

        self.oscDispatcher.map("/muse/elements/delta_relative", self.eeg_delta_relative_handler, "delta_relative")
        self.oscDispatcher.map("/muse/elements/theta_relative", self.eeg_theta_relative_handler, "theta_relative")
        self.oscDispatcher.map("/muse/elements/alpha_relative", self.eeg_alpha_relative_handler, "alpha_relative")
        self.oscDispatcher.map("/muse/elements/beta_relative", self.eeg_beta_relative_handler, "beta_relative")
        self.oscDispatcher.map("/muse/elements/gamma_relative", self.eeg_gamma_relative_handler, "gamma_relative")

        self.battery = None
        self.touchingforehead = None
        self.horseshoe = None
        self.delta_relative = None
        self.theta_relative = None
        self.alpha_relative = None
        self.beta_relative = None
        self.gamma_relative = None

        self.delta_absolute = None
        self.theta_absolute = None
        self.alpha_absolute = None
        self.beta_absolute = None
        self.gamma_absolute = None

        self.oscServer = osc_server.ThreadingOSCUDPServer(
        (ipAddress, args.port), self.oscDispatcher)
        print("Serving OSC on {}".format(self.oscServer.server_address))


    def battery_handler(self, address, name, chargePercent, fuelgaugeBattVolt, ADCBattVolt, temperature):
        """ 
        gets battery data from Muse, with:
        chargePercent = %/100, range (0-10000)
        fuelgaugeBattVolt = mV, 3000-4200 mV
        ADCBattVolt = mV, 3200-4200 mV
        temperature = C, -40 to 125 C
        updates at 0.1 Hz
        """
        # print("battery:", names, ":", chargePercent, fuelgaugeBattVolt, ADCBattVolt,temperature)
        print("battery: {}".format(chargePercent / 100.))
        self.battery = chargePercent / 100.  # return percent charge in floating point


    def touchingforehead_handler(self, address, name, touchingforehead): #unused_addr, touchingforehead, timestamp, timestampMS):
        """
        returns value 1 if touching forehead, 0 if not
        updated at 10 Hz
        """
        print("touchingforehead: {}".format(touchingforehead))
        self.touchingforehead = touchingforehead


    def horseshoe_handler(self, address, name, ch1, ch2, ch3, ch4):
        """
        status indicator for each of the Muse channels
        1 = good, 2 = ok, >=3 bad
        """
        horseshoe = [ch1, ch2, ch3, ch4] 
        print("horseshoe: {}".format(horseshoe))
        self.horseshoe = horseshoe

    def eeg_delta_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontDelta = (ch2 + ch3) / 2
        print("delta: {}".format(frontDelta))
        self.delta_absolute =  frontDelta

    def eeg_theta_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontTheta = (ch2 + ch3) / 2
        print("theta: {}".format(frontTheta))
        self.theta_absolute = frontTheta

    def eeg_alpha_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontAlpha = (ch2 + ch3) / 2
        print("alpha: {}".format(frontAlpha))
        self.alpha_absolute = frontAlpha

    def eeg_beta_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontBeta = (ch2 + ch3) / 2
        print("beta: {}".format(frontBeta))
        self.beta_absolute = frontBeta

    def eeg_gamma_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontGamma = (ch2 + ch3) / 2
        print("gamma: {}".format(frontGamma))
        self.gamma_absolute = frontGamma


    def eeg_delta_relative_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontDelta = (ch2 + ch3) / 2
        print("delta_relative: {}".format(frontDelta))
        self.delta_relative = frontDelta

    def eeg_theta_relative_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontTheta = (ch2 + ch3) / 2
        print("theta_relative: {}".format(frontTheta))
        self.theta_relative = frontTheta

    def eeg_alpha_relative_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontAlpha = (ch2 + ch3) / 2
        print("alpha_relative: {}".format(frontAlpha))
        self.alpha_relative = frontAlpha

    def eeg_beta_relative_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontBeta = (ch2 + ch3) / 2
        print("beta_relative: {}".format(frontBeta))
        self.beta_relative = frontBeta

    def eeg_gamma_relative_handler(self, address, name, ch1, ch2, ch3, ch4):
        frontGamma = (ch2 + ch3) / 2
        print("gamma_relative: {}".format(frontGamma))
        self.gamma_relative = frontGamma



    def run(self):
        """
        start the osc server & message handler
        """
        self.oscServer.serve_forever()


    def shutdown(self):
        """
        close the osc server
        """
        # do we actually even need this?
        self.oscServer.shutdown()



if __name__ == "__main__":
    #import matplotlib.pyplot as plt  # used for live plot updates 

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

    muse.run()

    # ## this doesnt actually do anything
    # try :
    #     while 1 :
    #         time.sleep(5)

    # except KeyboardInterrupt :
    #     print("\nClosing OSCServer.")
    #     muse.shutdown()
