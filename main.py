import sys
import random
from os.path import abspath
# sys.path.insert(0, abspath(".."))
sys.path.insert(0, abspath("cloudbrain-master"))
import json
import time
from websocket import create_connection
import threading
import webbrowser
from state_control.state_control import ChangeYourBrainStateControl
from ecg.neurosky_ecg import NeuroskyECG
import serial
from museEEG.museconnect import MuseConnect

# eeg_source = "real"  # fake or real
eeg_source = "fake"  # fake or real

# ecg_source = "real"  # fake or real
ecg_source = "fake"  # fake or real

# timing = "live"  # for full timing as in exploratorium visitor mode
timing = "debug"  # for quick debug timing

eeg_connect_string = "connect"
eeg_disconnect_string = "disconnect"
ecg_comPort = "COM7"  # windows com port

base_path = abspath(".")
biodata_viz_url = base_path + "/Live_Visualization/biodata_visualization.html"
# biodata_viz_url = 'file:///C:/Users/ExplorCogTech/src/live-visualization/Live_Visualization/biodata_visualization.html'


class SpacebrewServer(object):
    def __init__(self, muse_ids, server, port):
        self.server = server
        self.port = port
        self.muse_ids = muse_ids
        self.osc_paths = [
            {'address': "/muse/elements/alpha_absolute", 'arguments': 4},
        ]

        self.ws = create_connection("ws://%s:%s" % (self.server, self.port))
        print('initializing SpacebrewServer. Created websocket connection: {}'.format(self.ws))

        if (port == 9002):
            config = {'config': {
                        'name': 'booth-7',
                        'publish': {'messages': [{'name': 'eeg_ecg', 'type': 'string'}, {'name': 'instruction', 'type': 'string'}]}
                        }
                      }
            self.ws.send(json.dumps(config))
        else:
            raise Exception('unknown port!')


class eeg_fake():  # FAKE BRAIN
    def __init__(self,sec_til_start=4):
        self.num_per_call = 10
        self.time_stamp = -self.num_per_call
        self.onForehead = True
        self.curSensorState = [1, 1, 1, 1]
        self.init_time = time.time()
        self.sec_til_start = sec_til_start

    def get_alpha(self):
        self.time_stamp += self.num_per_call  
        return [random.random() for _ in range(self.num_per_call)]
        # return [(t + self.time_stamp, v) for t, v in enumerate(random.random() for _ in range(self.num_per_call))]

    def is_on_forehead(self):
        if time.time() - self.init_time > self.sec_til_start:
            return 1
        return 0

    def get_sec_since_last_forehead_trans(self):
        return 4


class ecg_fake():  # FAKE HEART

    def __init__(self):
        self.lead_count = 0
        self.cur_lead_on = False

    def is_lead_on(self):
        self.lead_count += 1
        if self.lead_count > 5:
            self.cur_lead_on = True
            # print('ecg lead on')
            return True
        else:
            self.cur_lead_on = False
            # print('ecg lead off')
            return False

    def get_hrv(self):
        return random.random()

    def get_hrv_t(self):
        return random.random()

    def get_rri(self):
        return random.random()


class ecg_real(object):
    def __init__(self, port="COM7"):
        self.lead_count = 0
        target_port = port
        # target_port = 'devA/tty.XXXXXXX'  #change this to work on OSX

        try:
            self.nskECG = NeuroskyECG(target_port)
        except serial.serialutil.SerialException:
            print("Could not open target serial port: %s" % target_port)
            sys.exit(1)

        # optional call, default is already 1
        self.nskECG.setHRVUpdate(1)  # update hrv every 1 detected pulses

        # want the LEAD_TIMEOUT to hold on to values between baseline and test, but reset between users
        self.LEAD_TIMEOUT = 30  # reset algorithm if leadoff for more than this many seconds
        self.cur_lead_on = False
        self.cur_hrv = 0

    def start(self):
        # start running the serial producer thread
        self.nskECG.start()

        # this loop is the consumer thread, and will pop
        # dict values (with 'timestamp', 'ecg_raw', and 'leadoff'
        # from the internal buffer and run the analysis on the
        # data.

        self.cur_hrv = None  # whatever the current hrv value is
        self.cur_hrv_t = None  # timestamp with the current hrv
        self.cur_rri = None  # R to R interval as an int representing # samples

        sample_count = 0  # keep track of numbers of samples we've processed
        leadoff_count = 0  # counter for length of time been leadoff
        while True:
            if not self.nskECG.isBufferEmpty():
                sample_count += 1
                D = self.nskECG.popBuffer()  # get the oldest dict

                if D['leadoff'] == 200:
                    self.cur_lead_on = True  # lead is on
                else:
                    self.cur_lead_on = False  # no connection between leads

                # if we are more than LEAD_TIMEOUT seconds in and leadoff is still zero
                if D['leadoff'] == 0:
                    leadoff_count += 1
                    if leadoff_count > self.nskECG.Fs * self.LEAD_TIMEOUT:
                        if self.nskECG.getTotalNumRRI() != 0:
                            # reset the library
                            self.nskECG.ecgResetAlgLib()
                        self.nskECG.ecg_buffer.task_done()  # let queue know that we're done
                        continue
                else:  # leadoff==200, or lead is on
                    leadoff_count = 0

                D = self.nskECG.ecgalgAnalyzeRaw(D)

                if 'hrv' in D:
                    self.cur_hrv = D['hrv']
                    self.cur_hrv_t = D['timestamp']

                if 'rri' in D:
                    self.cur_rri = D['rri']

            # we keep looping until something tells us to stop
        pass  #

    def is_lead_on(self):
        return self.cur_lead_on

    def get_hrv(self):
        if self.cur_hrv:
            return self.cur_hrv
        else:
            return -1

    def get_hrv_t(self):
        if self.cur_hrv_t:
            return self.cur_hrv_t
        else:
            return -1

    def get_rri(self):
        if self.cur_rri:
            return self.cur_rri
        else:
            return -1


if __name__ == "__main__":
    # VISUALIZATION SERVER: used for sending out instructions & processed EEG/ECG to the viz
    global sb_server_2
    sb_server_2 = SpacebrewServer(server='127.0.0.1', port=9002, muse_ids=['booth-7'])

    print('Started SpaceBrew visualization server: ready to send instructions and processed EEG/ECG')

    if (ecg_source == 'real'):
        # ecg = ecg_real(ecg_comPort)
        ecg = ecg_real()
        t1 = threading.Thread(target=ecg.start)
        t1.daemon = False
        t1.start()
    else:
        ecg = ecg_fake()

    if (eeg_source == 'real'):
        eeg = MuseConnect(verbose=False)
        eeg.start()
    else:
        eeg = eeg_fake()

    print('Started SpaceBrew Client & Listener thread')

    # TODO: unhardcode these filepaths

    print('Loading Chrome on platform: ', sys.platform)

    if sys.platform == 'win32':  # windoze
        chrome_path = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe %s'
        webbrowser.open(biodata_viz_url)
    elif sys.platform == 'darwin':  # MAC OSX
        chrome_path = 'open -a /Applications/Google\ Chrome.app %s'
        webbrowser.get(chrome_path).open(biodata_viz_url)
    else:  # Linux
        chrome_path = '/usr/bin/google-chrome %s'
        webbrowser.get(chrome_path).open(biodata_viz_url)
    print('Chrome Loaded')

    if timing == "live":     # run full timing #TODO: change 'booth-7' name in live routes json etc
        sc = ChangeYourBrainStateControl('booth-7', sb_server_2, eeg=eeg, ecg=ecg, vis_period_sec=.25, baseline_sec=30, condition_sec=90, baseline_inst_sec=6, condition_inst_sec=9)
    elif timing == "debug":  # run expidited timing (DO NOT CHANGE VALUES)
        sc = ChangeYourBrainStateControl('booth-7', sb_server_2, eeg=eeg, ecg=ecg, vis_period_sec=.25, baseline_sec=5, condition_sec=5, baseline_inst_sec=2, condition_inst_sec=2)
    print('ChangeYourBrain state engine started, beginning protocol.')

    # print('waiting for tag in')
    # TODO: this will need to be a keyboard tag in. OR ... we could 'tag_out' after 5 seconds of EEG disconnect
    # if (eeg_source == 'fake'):
    #     time.sleep(4)
    #     sc.tag_in()
    #     # time.sleep(12)
    #     # sc.tag_in()  # TEST
