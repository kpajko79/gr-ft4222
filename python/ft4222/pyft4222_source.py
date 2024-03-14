#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 Patrik Kluba <kpajko79@gmail.com>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
import numpy as np
from gnuradio import gr
import struct
import threading
import collections

from koda import Err, Ok
import pyft4222 as ft
from pyft4222.stream import InterfaceType
from pyft4222.wrapper.spi import ClkPhase, ClkPolarity
from pyft4222.wrapper.spi.slave import IoProtocol
from pyft4222.wrapper.gpio import Direction, PortId
from time import sleep
from time import time as gettime

class pyft4222_source(gr.sync_block):
    """
    docstring for block pyft4222_source
    """
    def __init__(self, srate, source_type, vec_len):
        self.vec_len = vec_len
        self.unit_size = 2 * vec_len
        self.do_scaling = False
        self.make_complex = False

        # the device sends 16-bit units with MSB first
        # we are reading 8-bit units with MSB first
        # so the higher order byte is stored first in the buffer,
        # followed by the lower one
        self.be16 = np.dtype(np.int16).newbyteorder('>')

        match source_type:
            case 'float':
                gr.sync_block.__init__(self,
                    name="pyft4222_source",
                    in_sig=None,
                    out_sig=[np.float32])
                self.do_scaling = True
            case 'complex':
                gr.sync_block.__init__(self,
                    name="pyft4222_source",
                    in_sig=None,
                    out_sig=[np.complex64])
                self.unit_size = 4
                self.do_scaling = True
                self.make_complex = True
            case 'short':
                match vec_len:
                    case 1:
                        gr.sync_block.__init__(self,
                            name="pyft4222_source",
                            in_sig=None,
                            out_sig=[np.int16])
                    case 2:
                        gr.sync_block.__init__(self,
                            name="pyft4222_source",
                            in_sig=None,
                            out_sig=[(np.int16, 2)])
                        self.make_complex = True

        # the maximum buffer size seems to be 65534 + 1 bytes
        # aim to process the half of it, minus some guard time (5%)
        # the limit shall be a multiple of the unit size
        self.maxbytes = int(65534 * 0.95 / 2)
        self.maxunits = self.maxbytes // self.unit_size
        if srate > 0:
            self.maxtime = self.maxunits / srate
            print("Buffer period is {} seconds".format(self.maxtime))

        print("Setting the maximum output size to {}".format(self.maxunits))
        self.set_max_noutput_items(self.maxunits)

        for dev in ft.get_device_info_list():
            print(dev)

        gpiodev = ft.open_by_idx(1)
        match gpiodev:
            case Ok(handle):
                if handle.tag == InterfaceType.GPIO:
                    gpio = handle.init_gpio((Direction.INPUT, Direction.INPUT, Direction.OUTPUT, Direction.INPUT))
                    gpio.set_suspend_out(False)
                    gpio.set_wakeup_interrupt(True)
                    self.gpio = gpio
                else:
                    handle.close()
                    print("FT4222 is in invalid mode!")
                    sys.exit(1)

                self.gpiohandle = handle

            case Err(err):
                print("Couldn't open the handle: {}".format(err))
                sys.exit(1)

        spidev = ft.open_by_idx(0)
        match spidev:
            case Ok(handle):
                if handle.tag == InterfaceType.DATA_STREAM:
                    spi_slave = handle.init_raw_spi_slave()
                    spi_slave.set_mode(ClkPolarity.CLK_IDLE_LOW, ClkPhase.CLK_TRAILING)
                    self.spi_slave = spi_slave
                else:
                    handle.close()
                    self.gpio.close()
                    self.gpiohandle.close()
                    self.gpiohandle = None
                    self.gpio = None
                    print("FT4222 is in invalid mode!")
                    sys.exit(1)

                self.spihandle = handle

            case Err(err):
                self.gpio.close()
                self.gpiohandle.close()
                self.gpiohandle = None
                self.gpio = None
                print("Couldn't open the handle: {}".format(err))
                sys.exit(1)

        self.event = threading.Event()
        self.queue = collections.deque()

    def start(self):
        nreset_gpio = PortId.PORT_2

        self.event.clear()
        self.thread = threading.Thread(target = self.process, args = ())

        self.gpio.write(nreset_gpio, False)
        sleep(0.1)
        self.spi_slave.reset_transaction(0)
        sleep(0.1)
        self.gpio.write(nreset_gpio, True)

        self.thread.start()

    def stop(self):
        if hasattr(self, 'thread'):
            self.event.set()
            self.thread.join()
            self.thread = None
            del self.thread
        return True

    def __del__(self):
        if hasattr(self, 'spi_slave'):
            self.spi_slave.close()
        if hasattr(self, 'spihandle'):
            self.spihandle.close()
        if hasattr(self, 'gpio'):
            self.gpio.close()
        if hasattr(self, 'gpiohandle'):
            self.gpiohandle.close()

    def work(self, input_items, output_items):
        if (len(self.queue) < 1):
            return 0

        req = len(output_items[0])
        avail = len(self.queue[0])
        if req < avail:
            return 0
        elif req > avail:
            req = avail

        if self.vec_len == 1:
            output_items[0][:req] = np.resize(self.queue.pop(), req)
        else:
            output_items[0][:req] = np.resize(self.queue.pop(), (req, self.vec_len))

        return avail

    def process(self):
        while not self.event.is_set():
            starttime = gettime()

            count = self.spi_slave.get_rx_status()

            if count == 65535:
                self.spi_slave.reset_transaction(0)
                sys.stdout.write('O')
                continue

            if count < self.unit_size:
                if hasattr(self, 'maxtime'):
                    runtime = gettime() - starttime
                    if runtime < self.maxtime:
                        sleep(self.maxtime - runtime)
                continue

            # round down to the multiple of unit size in bytes
            count = count // self.unit_size
            # set the limit
            if count > self.maxunits:
                count = self.maxunits

            data = self.spi_slave.read(count * self.unit_size)
            samples = np.frombuffer(data, dtype=self.be16)
            del data

            if self.make_complex:
                samples = samples.reshape((-1, 2))

            if self.do_scaling:
                if self.make_complex:
                    self.queue.append(np.frombuffer(np.float32(samples / 32768.0), dtype=np.complex64))
                else:
                    self.queue.append(np.float32(samples / 32768.0))
            else:
                self.queue.append(samples)

            del samples

            runtime = gettime() - starttime
            if hasattr(self, 'maxtime') and runtime < self.maxtime:
                sleep(self.maxtime - runtime)
